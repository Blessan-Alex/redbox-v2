# Redbox Worker Service Audit

**Audit Date**: September 2025
**Target**: 3-5 person hackathon team  
**Timeline**: 1-3 days implementation  

## Executive Summary

The Redbox Worker Service is a **simplified document processing pipeline** built on Django-Q that handles file ingestion, OCR, and basic text extraction. However, it **lacks the full RAG pipeline** described in the architecture documentation - specifically missing chunking, embedding generation, and vector search capabilities.

**Key Finding**: The current implementation is a **text-only system** that stores full documents as strings, not the sophisticated vector-based RAG system described in the docs.

## 1. Project-Wide Inventory

### Root Directory Structure
| Directory | Size | Worker Relevance | Notes |
|-----------|------|------------------|-------|
| `django_app/` | ~125 files | **PRIMARY** | Main Django application with worker |
| `redbox-core/` | ~147 lines | **CORE** | Shared RAG logic and LLM integration |
| `docs/` | ~50 files | **REFERENCE** | Architecture docs (partially outdated) |
| `data/` | - | **STORAGE** | MinIO object store and queue data |
| `infrastructure/` | ~15 files | **DEPLOYMENT** | AWS Terraform configs |
| `notebooks/` | ~20 files | **EXPERIMENTAL** | Jupyter notebooks for testing |
| `tests/` | ~10 files | **TESTING** | Limited worker test coverage |

### Worker-Related Files
- **`django_app/redbox_app/worker.py`** - Main worker implementation (73 lines)
- **`django_app/redbox_app/redbox_core/models.py`** - File and task models (750+ lines)
- **`django_app/redbox_app/settings.py`** - Django-Q configuration (427 lines)
- **`docker-compose.yml`** - Worker service definition (lines 70-90)

## 2. Dependency Scan

### Core Worker Dependencies
```toml
# django_app/pyproject.toml
django-q2 = "^1.6.2"           # Queue backend
markitdown = "^0.0.1a3"        # Document parsing
pytesseract = "^0.3.13"        # OCR engine
pdf2image = "^1.17.0"          # PDF to image conversion
elasticsearch = "^8.17.1"      # Vector storage (unused)
langchain = "^0.3.4"           # LLM integration
```

### Missing Dependencies for Full Pipeline
- **Chunking**: No dedicated chunking library
- **Embeddings**: No sentence-transformers or embedding models
- **Vector Search**: Elasticsearch installed but not used for vectors

## 3. Targeted Code Search Results

### Worker Keywords Found
| Keyword | Files | Matches | Key Locations |
|---------|-------|---------|---------------|
| `worker.py` | 1 | 1 | Main worker file |
| `django_q` | 3 | 5 | Settings, models, imports |
| `async_task` | 2 | 3 | Models, task enqueueing |
| `ingest` | 8 | 15 | Worker function, models, views |
| `ocr` | 2 | 8 | Worker OCR implementation |
| `embedding` | 0 | 0 | **NOT FOUND** - Critical gap |
| `chunk` | 0 | 0 | **NOT FOUND** - Critical gap |
| `elasticsearch` | 2 | 3 | Settings only, not used for vectors |

## 4. Entrypoints & Execution

### Worker Entrypoints
```bash
# Primary entrypoint
python manage.py qcluster

# Docker command
docker-compose up worker
```

### Docker Configuration
```yaml
# docker-compose.yml lines 70-90
worker:
  image: redbox-worker:latest
  build:
    context: .
    dockerfile: django_app/Dockerfile
  command: "venv/bin/django-admin qcluster"
  depends_on:
    - minio
    - django-app
    - db
```

### Django-Q Configuration
```python
# django_app/redbox_app/settings.py lines 379-384
Q_CLUSTER = {
    "name": "redbox_django",
    "timeout": env.int("Q_TIMEOUT", 300),
    "retry": env.int("Q_RETRY", 900),
    "catch_up": False,
    "orm": "default",
}
```

## 5. Task Definitions & Pipeline

### Current Task Functions

#### 1. File Ingestion Task
**File**: `django_app/redbox_app/worker.py:41-72`
```python
def ingest(file_id: UUID) -> None:
    """Main ingestion task - extracts text from files"""
    file = File.objects.get(id=file_id)
    
    if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp']:
        # OCR processing for images
        text_content = extract_text_with_ocr(file.url, file_extension)
    else:
        # MarkItDown processing for other formats
        markdown = md.convert(file.url)
        text_content = markdown.text_content
    
    file.text = sanitise_string(text_content)
    file.token_count = len(tokeniser.encode(file.text))
    file.status = File.Status.complete
    file.save()
```

#### 2. OCR Text Extraction
**File**: `django_app/redbox_app/worker.py:15-38`
```python
def extract_text_with_ocr(file_path: str, file_extension: str) -> str:
    """Extract text from images and PDFs using OCR"""
    if file_extension.lower() in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp']:
        # Direct image OCR
        image = Image.open(file_path)
        return pytesseract.image_to_string(image)
    elif file_extension.lower() == '.pdf':
        # Convert PDF pages to images and OCR each
        images = convert_from_path(file_path)
        text_parts = []
        for i, image in enumerate(images):
            text = pytesseract.image_to_string(image)
            if text.strip():
                text_parts.append(f"Page {i+1}:\n{text}")
        return "\n\n".join(text_parts)
```

### Missing Pipeline Components
1. **Chunking Worker**: No implementation found
2. **Embedding Worker**: No implementation found  
3. **Vector Storage**: No Elasticsearch vector operations
4. **Semantic Search**: No similarity search implementation

## 6. Integration Points

### Service Connections
```mermaid
graph TD
    A[Django App] -->|async_task| B[Django-Q Queue]
    B --> C[Worker Service]
    C --> D[MinIO/S3 Storage]
    C --> E[PostgreSQL Database]
    C --> F[OCR Engine]
    A --> G[Elasticsearch]
    A --> H[LLM APIs]
    
    style C fill:#ff9999
    style G fill:#ffcccc
    style H fill:#ffcccc
```

### Current Integrations
- **Django App → Worker**: `async_task(ingest, file_id)` in models.py:544
- **Worker → MinIO**: File download via `file.url` 
- **Worker → PostgreSQL**: Status updates and text storage
- **Django App → Elasticsearch**: Chat message logging only (not vectors)
- **Django App → LLM**: Direct API calls via LangChain

### Missing Integrations
- **Worker → Elasticsearch**: No vector storage
- **Worker → Embedding APIs**: No embedding generation
- **Chunking Pipeline**: No document segmentation

## 7. Queue Orchestration

### Queue Backend: Django-Q
```python
# Configuration
Q_CLUSTER = {
    "name": "redbox_django",
    "timeout": 300,  # 5 minutes
    "retry": 900,    # 15 minutes
    "catch_up": False,
    "orm": "default",  # Uses PostgreSQL as broker
}
```

### Task Enqueueing
```python
# django_app/redbox_app/redbox_core/models.py:544
def ingest(self, sync: bool = False):
    task = async_task(ingest, self.id, task_name=self.file_name, group="ingest", sync=sync)
    if sync:
        result = Success.objects.get(pk=task)
        self.status = self.Status.complete if result.success else self.Status.errored
    else:
        self.task = next(item for item in OrmQ.objects.all() if item.task["id"] == task)
    self.save()
```

### Task Consumption
- **Command**: `python manage.py qcluster`
- **Concurrency**: Single worker process
- **Retry Logic**: 15-minute retry on failure
- **Monitoring**: Django admin interface

## 8. Error Handling & Logging

### Error Handling Pattern
```python
# django_app/redbox_app/worker.py:69-72
try:
    # Processing logic
    file.status = File.Status.complete
except (Exception, UnsupportedFormatException) as error:
    file.status = File.Status.errored
    file.ingest_error = str(error)
file.save()
```

### Logging Configuration
```python
# Basic logging setup
logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)
```

### Error States
- **File.Status.processing**: Task queued
- **File.Status.complete**: Successfully processed
- **File.Status.errored**: Failed with error message

## 9. Data Flow Diagram

### Current Simplified Flow
```mermaid
sequenceDiagram
    participant U as User
    participant D as Django App
    participant Q as Django-Q
    participant W as Worker
    participant S as MinIO/S3
    participant DB as PostgreSQL
    
    U->>D: Upload file
    D->>S: Store file
    D->>DB: Create File record
    D->>Q: Queue ingest task
    Q->>W: Process task
    W->>S: Download file
    W->>W: Extract text (OCR/MarkItDown)
    W->>DB: Update File.text
    W->>DB: Set status=complete
```

### Missing RAG Flow
```mermaid
sequenceDiagram
    participant W as Worker
    participant C as Chunking
    participant E as Embedding
    participant ES as Elasticsearch
    participant V as Vector Search
    
    Note over W,V: MISSING IMPLEMENTATION
    W->>C: Chunk document
    C->>E: Generate embeddings
    E->>ES: Store vectors
    ES->>V: Semantic search
```

## 10. Storage & Provenance

### Current Storage
- **Files**: MinIO/S3 with user-based paths (`{email}/{filename}`)
- **Text**: PostgreSQL `File.text` field (full document)
- **Metadata**: PostgreSQL with timestamps, status, error messages
- **Provenance**: Basic file tracking via `File` model

### Missing Storage
- **Chunks**: No document segmentation storage
- **Embeddings**: No vector storage
- **Search Index**: No Elasticsearch vector index

### Provenance Tracking
```python
# django_app/redbox_app/redbox_core/models.py:455-482
class File(UUIDPrimaryKeyBase):
    status = models.CharField(choices=Status.choices)
    original_file = models.FileField(storage=settings.STORAGES["default"]["BACKEND"])
    ingest_error = models.TextField(max_length=2048, blank=True, null=True)
    text = models.TextField(null=True, blank=True)
    token_count = models.PositiveIntegerField(null=True, blank=True)
    task = models.ForeignKey(OrmQ, on_delete=models.SET_NULL, null=True, blank=True)
```

## 11. Tests

### Worker Test Coverage
- **File**: `django_app/tests/test_consumers.py` (575 lines)
- **Focus**: WebSocket chat functionality, not worker tasks
- **Missing**: No dedicated worker task tests
- **Management**: `django_app/tests/management/test_commands.py` (minimal)

### Test Gaps
- No `test_worker.py` or `test_ingest.py`
- No OCR functionality tests
- No error handling tests for worker tasks
- No queue processing tests

## 12. Security & Secrets

### Secret Management
```python
# django_app/redbox_app/settings.py
SECRET_KEY = env.str("DJANGO_SECRET_KEY")
ELASTIC_CLOUD_ID = env.str("ELASTIC_CLOUD_ID")
ELASTIC_API_KEY = env.str("ELASTIC_API_KEY")
```

### Security Findings
- ✅ **Good**: Environment variable usage for secrets
- ✅ **Good**: No hardcoded credentials found
- ⚠️ **Warning**: Default MinIO credentials in docker-compose.yml
- ⚠️ **Warning**: No API key validation in worker

## 13. Runbook & Dev Playbook

### Local Development Setup
```bash
# 1. Start services
docker-compose up -d db minio

# 2. Run migrations
cd django_app
python manage.py migrate

# 3. Start worker
python manage.py qcluster

# 4. Start Django app
python manage.py runserver
```

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://redbox-core:insecure@localhost:5432/redbox-core

# Storage
AWS_ACCESS_KEY=minioadmin
AWS_SECRET_KEY=minioadmin
MINIO_HOST=localhost
MINIO_PORT=9000

# Queue
Q_TIMEOUT=300
Q_RETRY=900

# Optional
ELASTIC_CLOUD_ID=your_cloud_id
ELASTIC_API_KEY=your_api_key
```

### Demo Script (5 minutes)
```bash
# 1. Upload document
curl -X POST http://localhost:8090/upload/ \
  -F "file=@sample.pdf" \
  -F "chat_id=123e4567-e89b-12d3-a456-426614174000"

# 2. Check processing status
curl http://localhost:8090/api/files/

# 3. Chat with document
curl -X POST http://localhost:8090/ws/chat/123e4567-e89b-12d3-a456-426614174000/ \
  -d '{"message": "What is this document about?"}'
```

## 14. Gaps & Limitations

### Critical Missing Features
1. **No Chunking Pipeline**: Documents stored as full text
2. **No Embedding Generation**: No vector representations
3. **No Vector Search**: No semantic similarity search
4. **No Advanced RAG**: Limited to basic text matching

### KMRL-Specific Gaps
1. **Malayalam OCR**: No Malayalam language support
2. **Table Extraction**: No structured data extraction
3. **Multi-format Parsing**: Limited format support
4. **Source Connectors**: No email/SharePoint integration
5. **Language Detection**: No bilingual processing

### Technical Limitations
1. **Single Worker**: No horizontal scaling
2. **No Retry Logic**: Basic error handling
3. **No Monitoring**: Limited observability
4. **No Caching**: No performance optimization

## 15. Quick Wins & Hackathon Plan

### Quick Wins (1-2 days)

#### 1. Add Malayalam OCR Support (4 hours)
```python
# django_app/redbox_app/worker.py
def extract_text_with_ocr(file_path: str, file_extension: str, language: str = 'eng+mal') -> str:
    # Install: apt-get install tesseract-ocr-mal
    return pytesseract.image_to_string(image, lang=language)
```

#### 2. Add Basic Chunking (6 hours)
```python
# New file: django_app/redbox_app/redbox_core/chunking.py
def chunk_text(text: str, chunk_size: int = 1024, overlap: int = 128) -> list[str]:
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks
```

#### 3. Add Simple Embeddings (8 hours)
```python
# New file: django_app/redbox_app/redbox_core/embeddings.py
from sentence_transformers import SentenceTransformer

def generate_embeddings(text: str) -> list[float]:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    return model.encode(text).tolist()
```

#### 4. Add Vector Storage (6 hours)
```python
# django_app/redbox_app/redbox_core/vector_storage.py
def store_vectors(chunks: list[str], embeddings: list[list[float]], file_id: str):
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        settings.ELASTIC_CLIENT.index(
            index="redbox-chunks",
            body={
                "file_id": file_id,
                "chunk_index": i,
                "text": chunk,
                "embedding": embedding
            }
        )
```

### 3-Day Hackathon Plan

#### Day 1: Core Enhancement
- **Morning**: Add Malayalam OCR support
- **Afternoon**: Implement basic chunking pipeline
- **Evening**: Set up embedding generation

#### Day 2: Vector Search
- **Morning**: Implement vector storage in Elasticsearch
- **Afternoon**: Add semantic search functionality
- **Evening**: Integrate with chat system

#### Day 3: Polish & Demo
- **Morning**: Add error handling and monitoring
- **Afternoon**: Create demo scenarios
- **Evening**: Prepare presentation

### Team Roles
- **Person 1**: OCR and document processing
- **Person 2**: Chunking and embedding pipeline
- **Person 3**: Vector search and Elasticsearch
- **Person 4**: Integration and testing
- **Person 5**: UI/UX and demo preparation

## Summary: Worker Service vs KMRL Needs

### Current State
The Redbox Worker Service is a **basic document ingestion system** that:
- ✅ Extracts text from various formats
- ✅ Handles OCR for images and PDFs
- ✅ Uses background processing with Django-Q
- ✅ Stores files and metadata properly

### Missing for KMRL
The system **lacks the core RAG capabilities** needed for KMRL:
- ❌ **No semantic search** (biggest gap)
- ❌ **No Malayalam language support**
- ❌ **No table extraction**
- ❌ **No source connectors**

### Single Biggest Missing Feature
**Vector-based semantic search** - The system cannot find relevant information across documents based on meaning, only exact text matches. This is the core capability needed for KMRL's document intelligence requirements.

---

**Next Steps**: Implement the chunking and embedding pipeline to transform this from a text storage system into a true RAG system capable of semantic document search.
