 Academic Assignment Helper & Plagiarism Detector (RAG-Powered)

A comprehensive AI-driven automation system designed to assist students and instructors. This system uses Retrieval-Augmented Generation (RAG) to analyze student assignments, compare them against an academic knowledge base for plagiarism detection, and provide intelligent research suggestions via automated email notifications.
System Architecture

The project follows a Microservices Architecture orchestrated with Docker Compose:

    Frontend: Nginx-based dashboard providing a clean UI for students to upload papers and view results.

    Backend (API): FastAPI (Python) managing JWT authentication, file processing, and database interactions.

    Orchestration: n8n (10-node workflow) acting as the ETL engine and AI manager.

    AI Engine: Ollama (Local) running llama3 for analysis and nomic-embed-text for vector embeddings.

    Vector Database: PostgreSQL with the pgvector extension for semantic similarity search.

    Cache: Redis for high-speed retrieval of previously analyzed documents (MD5 hashing).

 Quick Start & Installation
1. Prerequisites

    Docker & Docker Compose

    Minimum 16GB RAM recommended for running local LLMs (Ollama).

2. Clone the Repository
code Bash

    
git clone <your-repository-url>
cd academic-assignment-helper

  

3. Environment Configuration

Create a .env file from the provided example and fill in your specific credentials (SMTP, JWT secrets):
code Bash

    
cp .env.example .env

  

4. Launch the Stack
code Bash

    
docker-compose up -d --build

  

5. Prepare Local AI Models

Once the containers are healthy, download the required models into the Ollama container:
code Bash

    
docker exec -it ollama ollama pull llama3
docker exec -it ollama ollama pull nomic-embed-text

  
 Configuration & Setup
1. Database Initialization (RAG Ingestion)

To populate the system with academic papers and course materials for the RAG pipeline:

    Open the FastAPI Documentation: http://localhost:8000/docs

    Authenticate using the /auth/register and /auth/login endpoints.

    Execute the POST /admin/ingest endpoint.

        This converts data/sample_academic_sources.json into 1536-dimension vectors in the database.

2. n8n Workflow Import

    Access n8n: http://localhost:5678.

    Create a "New Workflow" and Import from File: workflows/assignment_analysis_workflow.json.

    Setup Credentials: Configure the following in the n8n UI:

        Postgres: Host: postgres, User: student.

        Redis: Host: redis, Port: 6379.

        SMTP: Configure Gmail (App Password) or Mailtrap settings.

    Activate: Toggle the workflow to Active.
 Project Structure
code Text

    
├── backend/            # FastAPI, SQLAlchemy Models, Auth logic, RAG Service
├── frontend/           # HTML/JS UI served via Nginx
├── workflows/          # Exported n8n automation pipeline (.json)
├── data/               # Sample academic source materials for RAG
├── docker-compose.yml  # Multi-service orchestration file
├── .env.example        # Environment variable template
└── README.md           # Documentation

  

 Core Features & Highlights
 RAG-Powered Plagiarism Detection

Unlike standard keyword matching, this system uses Vector Embeddings. Student assignments are compared semantically against stored academic papers using the <=> (Cosine Distance) operator in pgvector. A plagiarism score is calculated mathematically: (1 - distance) * 100.
Intelligent AI Analysis

The system uses the llama3 model to extract:

    Assignment Topic and core themes.

    Academic Level Assessment.

    Research Suggestions based specifically on the retrieved RAG context.

 High-Performance Caching

By implementing Redis, the system generates an MD5 hash of every uploaded PDF. If a student re-uploads the same document, the system bypasses the LLM and returns the result instantly from the cache.
 SQL Safety & Error Handling

    Sanitization: Custom logic to escape single quotes and strip NUL characters from binary PDF data to prevent database crashes.

    Fail-safes: Deep-hunt logic in n8n ensures assignment_id is never "undefined" during database updates.