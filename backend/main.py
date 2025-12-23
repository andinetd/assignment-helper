from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import create_engine, text ,func
from sqlalchemy.orm import Session, sessionmaker
from pydantic import BaseModel
import models, auth, requests, os, uuid, rag_service

# --- DATABASE SETUP ---
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(title="Academic Assignment Helper API")

# --- SCHEMAS (For validation & documentation) ---
class RegisterSchema(BaseModel):
    email: str
    password: str
    name: str

# --- DEPENDENCIES ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- STARTUP EVENT ---
@app.on_event("startup")
def startup_event():
    # 1. Create extension first
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    # 2. Create tables
    models.Base.metadata.create_all(bind=engine)
    print("Database initialized and pgvector verified.")

# --- AUTH ENDPOINTS ---

@app.post("/auth/register")
def register(student: RegisterSchema, db: Session = Depends(get_db)):
    # Check if user exists
    existing_user = db.query(models.Student).filter(models.Student.email == student.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = auth.get_password_hash(student.password)
    new_student = models.Student(
        email=student.email, 
        password_hash=hashed_pw, 
        full_name=student.name,
        student_id=str(uuid.uuid4())[:8] # Requirement: unique student_id
    )
    db.add(new_student)
    db.commit()
    return {"message": "Student registered successfully"}

@app.post("/auth/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.Student).filter(models.Student.email == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    access_token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

# --- ASSIGNMENT ENDPOINTS ---

@app.post("/upload")
async def upload_assignment(
    file: UploadFile = File(...), 
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Save data and student info
    user = db.query(models.Student).filter(models.Student.email == current_user['email']).first()
    file_content = await file.read()
    decoded_text = file_content.decode('utf-8', errors='ignore') # Simple extraction for RAG

    # 2. RAG: Search for top 2 relevant academic sources
    # Even with Mock embeddings, this demonstrates the RAG Pipeline
    sources = rag_service.search_sources(db, decoded_text, limit=2)
    context_str = "\n".join([f"Source: {s.title} - Content: {s.full_text}" for s in sources])

    # 3. Save Assignment
    new_assignment = models.Assignment(
        student_id=user.id,
        filename=file.filename,
        original_text=decoded_text[:1000] # Store preview
    )
    db.add(new_assignment)
    db.commit()
    db.refresh(new_assignment)

    # 4. Trigger n8n with RAG Context
    n8n_url = os.getenv("N8N_WEBHOOK_URL")
    try:
        files = {'file': (file.filename, file_content)}
        data = {
            "assignment_id": new_assignment.id,
            "rag_context": context_str # <--- The "Augmentation" part of RAG
        }
        requests.post(n8n_url, files=files, data=data)
    except Exception as e:
        print(f"n8n trigger failed: {e}")

    return {"job_id": new_assignment.id, "status": "processing"}

@app.get("/analysis/{job_id}")
def get_analysis(job_id: str, current_user: dict = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    # Query logic would go here in Phase 4
    return {"job_id": job_id, "status": "results pending n8n processing"}

@app.get("/sources")
def search_sources(query: str, db: Session = Depends(get_db), current_user: dict = Depends(auth.get_current_user)):
    # RAG Search logic from Phase 3
    results = rag_service.search_sources(db, query)
    return [{"title": r.title, "author": r.authors, "year": r.publication_year} for r in results]

# --- ADMIN ENDPOINTS ---

@app.post("/admin/ingest")
def ingest_data(db: Session = Depends(get_db)):
    import json
    data_path = "/app/data/sample_academic_sources.json"
    
    if not os.path.exists(data_path):
        data_path = "data/sample_academic_sources.json"
        if not os.path.exists(data_path):
            return {"error": f"Sample data file not found at {data_path}"}

    with open(data_path, "r") as f:
        sources = json.load(f)

    for item in sources:
        exists = db.query(models.AcademicSource).filter(models.AcademicSource.title == item['title']).first()
        if not exists:
            embedding = rag_service.get_embedding(item['full_text'])
            new_source = models.AcademicSource(
                title=item['title'],
                authors=item.get('authors', "Unknown"),
                publication_year=item.get('publication_year', 2023),
                full_text=item['full_text'],
                source_type=item.get('source_type', 'paper'),
                embedding=embedding
            )
            db.add(new_source)
    
    db.commit()
    return {"message": "Ingestion complete"}

@app.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """
    Instructor Dashboard:
    Provides high-level analytics on system usage and academic integrity.
    """
    # 1. Count total assignments uploaded
    total_assignments = db.query(models.Assignment).count()
    
    # 2. Calculate average plagiarism score across all analyzed files
    # Using func.avg for database-side calculation
    avg_plagiarism = db.query(func.avg(models.AnalysisResult.plagiarism_score)).scalar()
    
    # Handle case where no analyses have been performed yet
    display_avg = f"{avg_plagiarism:.2f}%" if avg_plagiarism is not None else "0.00%"
    
    # 3. Get total academic sources in the RAG database
    total_sources = db.query(models.AcademicSource).count()

    return {
        "status": "Academic System Overview",
        "total_processed_assignments": total_assignments,
        "system_average_plagiarism": display_avg,
        "rag_knowledge_base_size": total_sources
    }