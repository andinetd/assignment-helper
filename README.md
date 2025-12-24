# Academic Assignment Helper & Plagiarism Detector (RAG-Powered)

<div align="center">

![License](https://img.shields.io/badge/License-MIT-blue.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-4169E1?logo=postgresql&logoColor=white)
![LLaMA3](https://img.shields.io/badge/LLM-LLaMA3-orange)
![Redis](https://img.shields.io/badge/Redis-Caching-DC382D?logo=redis&logoColor=white)

**High-performance AI-driven academic automation system with semantic plagiarism detection**

[Quick Start](#-quick-start) • [Architecture](#-architecture) • [API Testing](#-testing-with-insomnia) • [Features](#-technical-highlights)

</div>

## 📋 Overview

This project is a high-performance AI-driven academic automation system. It analyzes student assignments via a secured API, performs Retrieval-Augmented Generation (RAG) against a vector database of academic sources, calculates plagiarism similarity scores, and provides intelligent research suggestions through automated email reports.

## 🏗️ System Architecture

The system utilizes a **Microservices Architecture** orchestrated with Docker Compose:

| Component | Technology | Purpose |
|-----------|------------|---------|
| **API Interface** | Insomnia / FastAPI Swagger UI | API testing and documentation |
| **Backend (API)** | FastAPI (Python) | JWT authentication, PDF text extraction, database interactions |
| **Orchestration** | n8n (10-node workflow) | AI management and data delivery pipeline |
| **AI Engine** | Ollama (Local) | Runs `llama3` for analysis and `nomic-embed-text` for embeddings |
| **Vector Database** | PostgreSQL + pgvector | Semantic similarity search |
| **Cache** | Redis | High-speed retrieval using MD5 content hashing |

![alt text](deepseek_mermaid_20251224_20f97b.png)

## 🚀 Quick Start & Installation

### 1. Prerequisites

- **Docker & Docker Compose**
- **16GB RAM** recommended for running local LLMs (Ollama)

### 2. Setup Environment

```bash
# Clone the repository
git clone git@github.com:andinetd/assignment-helper.git
cd academic-assignment-helper

# Create environment configuration
cp .env.example .env

# Edit .env with your credentials
nano .env  # or open in your preferred editor
```

**Required `.env` configurations:**
```env
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
SMTP_HOST=smtp.gmail.com  # or use Mailtrap for testing
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. Launch the Stack

```bash
docker-compose up -d --build
```

### 4. Download AI Models

```bash
# Download LLaMA3 for analysis
docker exec -it ollama ollama pull llama3

# Download nomic-embed-text for embeddings
docker exec -it ollama ollama pull nomic-embed-text
```

## ⚙️ Configuration & Setup

### 1. Initialize Vector Database (RAG Ingestion)

To populate the system with academic source materials:

```bash
# Using curl
curl -X POST "http://localhost:8000/admin/ingest" \
  -H "Content-Type: application/json"

# Or use Insomnia/Postman
# Endpoint: POST http://localhost:8000/admin/ingest
```

**What happens:**
- Converts `data/sample_academic_sources.json` into 768-dimension vectors
- Stores embeddings in PostgreSQL with pgvector extension
- Creates semantic search index for plagiarism detection

### 2. Import n8n Workflow

1. **Access n8n Dashboard:** http://localhost:5678
2. **Create New Workflow** → **Import from File**
3. Select `workflows/assignment_analysis_workflow.json`
4. **Configure Credentials:**
   - **Postgres:** Host=`postgres`, Database=`academic_db`
   - **Redis:** Host=`redis`, Port=`6379`
   - **SMTP:** Your email provider details
5. **Toggle** workflow to **Active**

## 🧪 Testing with Insomnia (Workflow Steps)

Follow this sequence to demonstrate the complete system:

### 1. Register a Student

**Request:**
```http
POST http://localhost:8000/auth/register
Content-Type: application/json

{
  "email": "student@example.com",
  "password": "password123",
  "name": "John Doe"
}
```

### 2. Login to Get JWT Token

**Request:**
```http
POST http://localhost:8000/auth/login
Content-Type: application/x-www-form-urlencoded

username: student@example.com
password: password123
```

**Response:** Copy the `access_token` from response

### 3. Upload Assignment

**Request:**
```http
POST http://localhost:8000/upload
Authorization: Bearer YOUR_COPIED_TOKEN
Content-Type: multipart/form-data

file: [Select your PDF file]
```

**Behavior:**
- n8n workflow triggers automatically
- Watch the workflow turn green in n8n UI
- Email notification sent upon completion

### 4. Retrieve Analysis Results

**Request:**
```http
GET http://localhost:8000/analysis/{id}
Authorization: Bearer YOUR_COPIED_TOKEN
```

**Response Includes:**
- AI-generated topic analysis
- Academic level assessment
- Plagiarism percentage
- Research suggestions
- Similar academic sources

## 🛠️ Technical Highlights

### 🔍 RAG Implementation
- **Context-aware analysis** retrieves relevant academic papers before generating suggestions
- **Semantic search** using 768-dimension vector embeddings
- **Dynamic context retrieval** based on assignment content

### 📊 Plagiarism Scoring Algorithm
```sql
-- Mathematical calculation using pgvector
similarity_score = (1 - (embedding1 <=> embedding2)) * 100
-- Where <=> is the cosine distance operator
```

**Scoring Interpretation:**
- **0-70%:** Original work
- **71-84%:** Moderate similarity (review recommended)
- **85-100%:** High similarity (potential plagiarism)

### ⚡ Redis Caching Strategy
- **MD5 hashing** on PDF content for duplicate detection
- **<100ms response time** for cached documents
- **Automatic cache invalidation** after configurable TTL

### 🔒 SQL Safety & Data Integrity
```python
# Custom sanitization logic
def sanitize_sql_input(text: str) -> str:
    # Strip NUL characters from binary data
    text = text.replace('\x00', '')
    # Escape single quotes to prevent SQL injection
    text = text.replace("'", "''")
    return text
```

### 🛡️ Error Handling & Pipeline Integrity
- **10-node n8n workflow** with comprehensive error handling
- **"Deep Hunt" logic** ensures data integrity across pipeline
- **Fallback mechanisms** for LLM failures
- **Automatic retries** for transient errors

## 📊 Service Endpoints

| Service | URL | Port | Purpose |
|---------|-----|------|---------|
| **FastAPI Backend** | http://localhost:8000 | 8000 | Main API & Swagger UI |
| **n8n Orchestration** | http://localhost:5678 | 5678 | Workflow management |
| **PostgreSQL** | localhost:5432 | 5432 | Vector database |
| **Redis** | localhost:6379 | 6379 | Caching layer |
| **Ollama AI** | http://localhost:11434 | 11434 | Local LLM API |

## 📁 Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/           # FastAPI routes
│   │   ├── models/        # SQLAlchemy models
│   │   ├── services/      # Business logic & RAG service
│   │   └── core/          # Config, auth, security
│   └── requirements.txt
├── workflows/             # n8n automation pipeline
│   └── assignment_analysis_workflow.json
├── data/                  # Academic source materials
│   └── sample_academic_sources.json
├── docker-compose.yml     # Multi-service orchestration
├── .env.example          # Environment template
└── README.md             # This documentation
```

## 🔧 Troubleshooting Guide

### Common Issues

| Issue | Solution |
|-------|----------|
| **n8n workflow not triggering** | Check workflow is active, verify webhook URL in FastAPI |
| **Ollama out of memory** | Reduce model size or increase Docker memory allocation |
| **PDF parsing errors** | Ensure PDFs are text-based (not scanned images) |
| **Email delivery failures** | Verify SMTP credentials in n8n and `.env` file |
| **Vector search slow** | Check pgvector index creation: `CREATE INDEX ON documents USING ivfflat (embedding vector_cosine_ops);` |

### Health Check Commands

```bash
# Check all services status
docker-compose ps

# View logs for specific service
docker-compose logs -f backend

# Test API health
curl http://localhost:8000/health

# Check Redis cache
docker exec redis redis-cli INFO memory

# Monitor n8n workflow execution
# Visit http://localhost:5678 and check Execution tab
```

## 📈 Performance Metrics

| Operation | Typical Duration | Cached Duration |
|-----------|-----------------|-----------------|
| PDF Upload & Processing | 5-10 seconds | N/A |
| Vector Embedding Generation | 3-5 seconds | N/A |
| Semantic Search | 1-3 seconds | < 100ms |
| AI Analysis (llama3) | 10-20 seconds | N/A |
| **Total Processing** | **20-40 seconds** | **< 100ms** |

---

<div align="center">

**Built for academic integrity and innovation**

*Need help? Open an issue or check the troubleshooting guide above.*

</div>