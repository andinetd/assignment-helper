from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import create_engine, text ,func
from sqlalchemy.orm import Session, sessionmaker
from pydantic import BaseModel
import models, auth, requests, os, uuid, rag_service
import redis
import json
from fastapi.middleware.cors import CORSMiddleware
import hashlib

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI(title="Academic Assignment Helper API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

class RegisterSchema(BaseModel):
    email: str
    password: str
    name: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def startup_event():
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        conn.commit()
    models.Base.metadata.create_all(bind=engine)
    print("Database initialized and pgvector verified.")


@app.post("/auth/register")
def register(student: RegisterSchema, db: Session = Depends(get_db)):
    existing_user = db.query(models.Student).filter(models.Student.email == student.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_pw = auth.get_password_hash(student.password)
    new_student = models.Student(
        email=student.email, 
        password_hash=hashed_pw, 
        full_name=student.name,
        student_id=str(uuid.uuid4())[:8] 
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

@app.post("/upload")
async def upload_assignment(
    file: UploadFile = File(...), 
    current_user: dict = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    try:
        user = db.query(models.Student).filter(models.Student.email == current_user['email']).first()
        
    
        file_content = await file.read()
        
        import hashlib
        file_hash = hashlib.md5(file_content).hexdigest()
        cache_key = f"analysis:{file_hash}"

        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                return {"job_id": "cached", "status": "completed", "results": json.loads(cached_result)}
        except: pass

        decoded_text = file_content.decode('utf-8', errors='ignore')
        clean_text = "".join(c for c in decoded_text if c.isprintable() or c in "\n\r\t").replace('\x00', '')

        context_str = "No specific context found."
        try:
            sources = rag_service.search_sources(db, clean_text[:800], limit=2)
            if sources:
                context_str = "\n".join([f"Source: {s.title}" for s in sources])
        except: pass

        new_assignment = models.Assignment(
            student_id=user.id,
            filename=file.filename,
            original_text=clean_text[:1000]
        )
        db.add(new_assignment)
        db.commit()
        db.refresh(new_assignment)

        n8n_url = os.getenv("N8N_WEBHOOK_URL")
        if n8n_url:
            payload = {
                "assignment_id": str(new_assignment.id),
                "file_hash": str(file_hash),
                "student_email": str(user.email),
                "rag_context": str(context_str)
            }
            
            files = {
                'file': (file.filename, file_content, 'application/pdf')
            }

            try:
                requests.post(n8n_url, data=payload, files=files, timeout=1)
            except requests.exceptions.ReadTimeout:
                pass 
            except Exception as e:
                print(f"n8n link failed: {e}")

        return {"job_id": new_assignment.id, "status": "processing"}

    except Exception as e:
        db.rollback()
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analysis/{job_id}")
def get_analysis(job_id: int, current_user: dict = Depends(auth.get_current_user), db: Session = Depends(get_db)):
    """
    Fetches the analysis results saved by n8n.
    """
    result = db.query(models.AnalysisResult).filter(models.AnalysisResult.assignment_id == job_id).first()
    
    if not result:
        return {
            "job_id": job_id, 
            "status": "processing", 
            "message": "AI is still analyzing or record not found."
        }
        
    return {
        "job_id": job_id,
        "status": "completed",
        "data": {
            "topic": result.topic,
            "academic_level": result.academic_level,
            "plagiarism_score": f"{result.plagiarism_score}%",
            "suggestions": result.research_suggestions,
            "analyzed_at": result.analyzed_at
        }
    }

@app.get("/sources")
def search_sources(query: str, db: Session = Depends(get_db), current_user: dict = Depends(auth.get_current_user)):
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
    cached_stats = redis_client.get("system_stats")
    if cached_stats:
        return json.loads(cached_stats)

    total_assignments = db.query(models.Assignment).count()
    avg_plagiarism = db.query(func.avg(models.AnalysisResult.plagiarism_score)).scalar()
    total_sources = db.query(models.AcademicSource).count()

    stats = {
        "total_processed_assignments": total_assignments,
        "system_average_plagiarism": f"{avg_plagiarism or 0:.2f}%",
        "rag_knowledge_base_size": total_sources
    }

    redis_client.setex("system_stats", 300, json.dumps(stats))
    
    return stats