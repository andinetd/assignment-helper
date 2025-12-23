import os
import random
from sqlalchemy.orm import Session
import models


def get_embedding(text: str):
    """
    MOCK EMBEDDING: Returns a random 1536-dimension vector.
    This simulates OpenAI's text-embedding-ada-002 without using credits.
    """
    print(f"Generating mock embedding for text: {text[:30]}...")
    return [random.uniform(-1, 1) for _ in range(1536)]

def search_sources(db: Session, query_text: str, limit: int = 3):
    """
    Uses the same L2 distance logic as real RAG, but with mock query vectors.
    """
    query_embedding = get_embedding(query_text)
    
    # The technical PostgreSQL logic remains 100% correct
    results = db.query(models.AcademicSource).order_by(
        models.AcademicSource.embedding.l2_distance(query_embedding)
    ).limit(limit).all()
    
    return results
def chunk_text(text, chunk_size=500):
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]