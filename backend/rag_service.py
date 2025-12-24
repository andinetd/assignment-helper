import requests

def get_embedding(text: str):
    try:
        response = requests.post(
            "http://ollama:11434/api/embed",
            json={"model": "nomic-embed-text", "input": str(text)[:1000]},
            timeout=10
        )
        return response.json()['embeddings'][0]
    except Exception as e:
        print(f"Embedding failed: {e}")
        return [0.0] * 768  

def search_sources(db, query_text, limit=2):
    from models import AcademicSource
    query_vector = get_embedding(query_text)
    return db.query(AcademicSource).order_by(
        AcademicSource.embedding.cosine_distance(query_vector)
    ).limit(limit).all()