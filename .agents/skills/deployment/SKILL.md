---
name: deployment
description: Deployment strategy and configuration for the User Intelligence Workspace. Covers Vercel deployment for the Next.js frontend, Railway/Render deployment for the FastAPI backend, Neo4j Aura, Qdrant Cloud, PostgreSQL (Supabase/Neon), environment configuration, and CI/CD pipeline.
---

# Deployment Skill

## Overview
The User Intelligence Workspace deploys as two separate services:
- **Frontend**: Next.js on **Vercel** (free tier)
- **Backend**: FastAPI on **Railway** or **Render** (free tier)
- **Neo4j**: Neo4j Aura (free tier — 1 instance, 200k nodes)
- **Qdrant**: Qdrant Cloud (free tier — 1GB)
- **PostgreSQL**: Supabase (free tier) or Neon (free tier) — sessions, memory, conversation history

## Architecture: Deployment View

```
┌──────────────┐         ┌──────────────────┐
│   Vercel     │ ──API──▶│  Railway/Render   │
│  (Next.js)   │  + SSE  │   (FastAPI)       │
│  Frontend    │◀──SSE───│   Backend         │
└──────────────┘         └───────┬───────────┘
                                 │
                    ┌────────────┼────────────┬──────────┐
                    ▼            ▼             ▼          ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Neo4j    │ │ Qdrant   │ │PostgreSQL│ │ R2/Local │
              │ Aura     │ │ Cloud    │ │(Supabase)│ │ (Files)  │
              │ (Graph)  │ │ (Vector) │ │(Sessions)│ │          │
              └──────────┘ └──────────┘ └──────────┘ └──────────┘
```

## Frontend Deployment (Vercel)

### Setup
```bash
# From the frontend/ directory
npm install -g vercel
vercel login
vercel --prod
```

### vercel.json
```json
{
  "framework": "nextjs",
  "buildCommand": "npm run build",
  "outputDirectory": ".next",
  "env": {
    "NEXT_PUBLIC_API_URL": "@api-url"
  },
  "rewrites": [
    {
      "source": "/api/backend/:path*",
      "destination": "https://your-backend-url.railway.app/:path*"
    }
  ]
}
```

### Environment Variables (Vercel Dashboard)
| Variable | Value | Description |
|----------|-------|-------------|
| `NEXT_PUBLIC_API_URL` | `https://your-backend.railway.app` | Backend API URL |

## Backend Deployment (Railway)

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### railway.toml
```toml
[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3
```

### Environment Variables (Railway Dashboard)
| Variable | Value | Description |
|----------|-------|-------------|
| `NEO4J_URI` | `neo4j+s://xxx.databases.neo4j.io` | Neo4j Aura connection |
| `NEO4J_USERNAME` | `neo4j` | Neo4j username |
| `NEO4J_PASSWORD` | `***` | Neo4j password |
| `QDRANT_URL` | `https://xxx.aws.cloud.qdrant.io` | Qdrant Cloud URL |
| `QDRANT_API_KEY` | `***` | Qdrant API key |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@host:5432/db` | PostgreSQL (Supabase/Neon) |
| `OPENAI_API_KEY` | `***` | OpenAI API key |
| `TAVILY_API_KEY` | `***` | Tavily search API key |
| `CORS_ORIGINS` | `https://your-app.vercel.app` | Allowed CORS origins |

## PostgreSQL Setup (Supabase — Recommended)

### Why PostgreSQL over SQLite
- **Data persistence**: SQLite is file-based and loses data on container restart (Railway/Render)
- **Concurrent access**: PostgreSQL handles async connections properly
- **Cloud-hosted**: No local file system dependency
- **Free tier**: Supabase offers 500MB free, Neon offers 512MB free

### Supabase Setup
1. Go to [Supabase](https://supabase.com/)
2. Create a new project (free tier)
3. Go to Project Settings → Database → Connection string
4. Use the `postgresql+asyncpg://` format for SQLAlchemy async
5. Run Alembic migrations to create tables

### Neon Setup (Alternative)
1. Go to [Neon](https://neon.tech/)
2. Create a free project
3. Copy the connection string
4. Same migration process as Supabase

### Schema Initialization
```bash
# From backend/ directory
alembic upgrade head
```

## Neo4j Aura Setup

### Free Tier Limits
- 1 database instance
- 200,000 nodes
- 400,000 relationships
- Sufficient for single-user workspace

### Setup Steps
1. Go to [Neo4j Aura](https://console.neo4j.io/)
2. Create a free AuraDB instance
3. Save the connection URI, username, and password
4. Configure constraints and indexes:

```cypher
// Constraints
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT fact_id IF NOT EXISTS FOR (f:Fact) REQUIRE f.id IS UNIQUE;
CREATE CONSTRAINT evidence_id IF NOT EXISTS FOR (e:Evidence) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT source_id IF NOT EXISTS FOR (s:Source) REQUIRE s.id IS UNIQUE;
CREATE CONSTRAINT decision_id IF NOT EXISTS FOR (d:Decision) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT question_id IF NOT EXISTS FOR (q:Question) REQUIRE q.id IS UNIQUE;
CREATE CONSTRAINT insight_id IF NOT EXISTS FOR (i:Insight) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT memory_id IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE;

// Indexes
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX entity_name_topic IF NOT EXISTS FOR (e:Entity) ON (e.name, e.topic);
CREATE INDEX entity_status IF NOT EXISTS FOR (e:Entity) ON (e.status);
CREATE INDEX fact_status IF NOT EXISTS FOR (f:Fact) ON (f.status);
CREATE INDEX fact_status_confidence IF NOT EXISTS FOR (f:Fact) ON (f.status, f.confidence);
CREATE INDEX fact_topic IF NOT EXISTS FOR (f:Fact) ON (f.topic);
CREATE INDEX question_status IF NOT EXISTS FOR (q:Question) ON (q.status);
CREATE INDEX question_topic IF NOT EXISTS FOR (q:Question) ON (q.topic);
CREATE INDEX memory_session IF NOT EXISTS FOR (m:Memory) ON (m.session_id);
CREATE INDEX memory_type IF NOT EXISTS FOR (m:Memory) ON (m.type);
```

## Qdrant Cloud Setup

### Free Tier Limits
- 1 GB storage
- 1 cluster
- Sufficient for thousands of embeddings

### Setup Steps
1. Go to [Qdrant Cloud](https://cloud.qdrant.io/)
2. Create a free cluster
3. Create collections:

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)

# Knowledge embeddings collection
client.create_collection(
    collection_name="knowledge_embeddings",
    vectors_config=VectorParams(
        size=1536,  # OpenAI text-embedding-3-small
        distance=Distance.COSINE
    )
)

# Memory embeddings collection (NEW)
client.create_collection(
    collection_name="memory_embeddings",
    vectors_config=VectorParams(
        size=1536,
        distance=Distance.COSINE
    )
)
```

## Local Development Setup

### docker-compose.yml (for local dev)
```yaml
version: '3.8'

services:
  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"  # Browser
      - "7687:7687"  # Bolt
    environment:
      NEO4J_AUTH: neo4j/localdevpassword
      NEO4J_PLUGINS: '["apoc"]'
    volumes:
      - neo4j_data:/data

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage

  postgres:
    image: postgres:16-alpine
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: intelligence
      POSTGRES_PASSWORD: localdevpassword
      POSTGRES_DB: intelligence_workspace
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  neo4j_data:
  qdrant_data:
  postgres_data:
```

### .env.example
```bash
# LLM
OPENAI_API_KEY=sk-xxx
# Or for Gemini:
# GOOGLE_API_KEY=xxx

# Neo4j (local)
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=localdevpassword

# Qdrant (local)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# PostgreSQL (local)
DATABASE_URL=postgresql+asyncpg://intelligence:localdevpassword@localhost:5432/intelligence_workspace

# Web Search
TAVILY_API_KEY=tvly-xxx

# CORS
CORS_ORIGINS=http://localhost:3000

# App
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# File Storage (local dev uses local filesystem)
FILE_STORAGE_TYPE=local
FILE_STORAGE_PATH=./uploads
# For production: FILE_STORAGE_TYPE=r2, R2_BUCKET=xxx, R2_ACCESS_KEY=xxx, R2_SECRET_KEY=xxx
```

## Health Check Endpoint
```python
@app.get("/health")
async def health_check():
    """Health check endpoint for deployment platforms."""
    checks = {
        "status": "healthy",
        "neo4j": await check_neo4j_connection(),
        "qdrant": await check_qdrant_connection(),
        "postgres": await check_postgres_connection(),
        "timestamp": datetime.utcnow().isoformat()
    }
    return checks
```

## CI/CD (GitHub Actions)

### .github/workflows/deploy.yml
```yaml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./frontend
          vercel-args: '--prod'

  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: bervProject/railway-deploy@main
        with:
          railway_token: ${{ secrets.RAILWAY_TOKEN }}
          service: backend
```
