from sqlalchemy import Column, Integer, String, Text, Float, ForeignKey, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from pgvector.sqlalchemy import Vector
import datetime

Base = declarative_base()

class Student(Base):
    __tablename__ = "students"
    id = Column(Integer, primary_key=True)
    email = Column(Text, unique=True)
    password_hash = Column(Text)
    full_name = Column(Text)
    student_id = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Assignment(Base):
    __tablename__ = "assignments"
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"))
    filename = Column(Text)
    original_text = Column(Text)
    topic = Column(Text)
    academic_level = Column(Text)
    word_count = Column(Integer)
    uploaded_at = Column(DateTime, default=datetime.datetime.utcnow)

class AnalysisResult(Base):
    __tablename__ = "analysis_results"
    id = Column(Integer, primary_key=True)
    assignment_id = Column(Integer, ForeignKey("assignments.id"), unique=True)
    suggested_sources = Column(JSON) # JSONB in Postgres
    plagiarism_score = Column(Float)
    flagged_sections = Column(JSON)
    research_suggestions = Column(Text)
    citation_recommendations = Column(Text)
    confidence_score = Column(Float)
    analyzed_at = Column(DateTime, default=datetime.datetime.utcnow)

class AcademicSource(Base):
    __tablename__ = "academic_sources"
    id = Column(Integer, primary_key=True)
    title = Column(Text)
    authors = Column(Text)
    publication_year = Column(Integer)
    abstract = Column(Text)
    full_text = Column(Text)
    source_type = Column(String) # 'paper', 'textbook', etc.
    embedding = Column(Vector(768)) # Match nomic-embed-text size