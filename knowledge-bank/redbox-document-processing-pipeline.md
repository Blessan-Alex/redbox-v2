# Redbox Document Processing Pipeline - Complete Guide

## Table of Contents
1. [What "Ingesting Files" Means](#1-what-ingesting-files-means)
2. [What "Embedding Chunks of Text" Means](#2-what-embedding-chunks-of-text-means)
3. [How These Processes Work Together](#3-how-these-processes-work-together)
4. [Technical Implementation Details](#4-technical-implementation-details)
5. [Queue Management System](#5-queue-management-system)
6. [Real-World Example](#6-real-world-example)
7. [Benefits for KMRL](#7-benefits-for-kmrl)
8. [Key Components Overview](#8-key-components-overview)
9. [Troubleshooting Common Issues](#9-troubleshooting-common-issues)
10. [Current Implementation Status & Limitations](#10-current-implementation-status--limitations)

---

## 1. What "Ingesting Files" Means

**File Ingestion** is the process of taking raw documents (PDFs, images, Word docs, etc.) and converting them into searchable, processable text that the system can work with.

### The Ingestion Process

```
Raw Document → Text Extraction → Storage → Queue for Processing
```

**Step-by-step breakdown:**

1. **File Upload**: User uploads a document through the web interface
2. **File Validation**: System checks file type, size, and format
3. **Storage**: Original file is stored in MinIO/S3 object storage
4. **Text Extraction**: Document is processed to extract readable text
5. **Database Record**: A record is created in PostgreSQL tracking the file
6. **Queue Task**: A background job is queued to process the file

### Technical Implementation

From the codebase audit, here's how it works:

**File**: `django_app/redbox_app/redbox_core/views/document_views.py` (lines 102-116)
```python
# File upload triggers ingestion
@staticmethod
def ingest_file(uploaded_file: UploadedFile, chat_id: uuid.UUID) -> tuple[File, Sequence[str]]:
    try:
        logger.info("getting file from s3")
        file = File.objects.create(
            status=File.Status.processing.value,
            original_file=uploaded_file,
            chat_id=chat_id,
        )
    except (ValueError, FieldError, ValidationError) as e:
        logger.exception("Error creating File model object for %s.", uploaded_file, exc_info=e)
        return None, e.args

    file.ingest()  # This queues the background processing
    return file, []
```

### Supported File Formats

**File**: `django_app/redbox_app/redbox_core/views/document_views.py` (lines 23-54)

| Category | Extensions | Processing Method |
|----------|------------|-------------------|
| **Email** | `.eml`, `.msg` | MarkItDown |
| **Web Content** | `.html`, `.htm`, `.xml` | MarkItDown |
| **Data Files** | `.json`, `.csv`, `.tsv` | MarkItDown |
| **Text Files** | `.txt`, `.md`, `.rst` | MarkItDown |
| **Documents** | `.doc`, `.docx`, `.odt`, `.pdf`, `.rtf` | MarkItDown |
| **Presentations** | `.ppt`, `.pptx` | MarkItDown |
| **Spreadsheets** | `.xlsx` | MarkItDown |
| **E-books** | `.epub` | MarkItDown |
| **Images** | `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff`, `.tif`, `.webp` | OCR (Tesseract) |

**File Size Limit**: 200 MB (209,715,200 bytes) - defined in `MAX_FILE_SIZE` constant

---

## 2. What "Embedding Chunks of Text" Means

**Text Embedding** is the process of converting text into numerical vectors (arrays of numbers) that capture the semantic meaning of the text. These vectors enable the system to find similar content even when exact words don't match.

### The Embedding Process

```
Text Chunks → Vector Embeddings → Vector Database → Semantic Search
```

**Step-by-step breakdown:**

1. **Text Chunking**: Long documents are split into smaller, manageable pieces (typically 1024 characters)
2. **Embedding Generation**: Each chunk is converted to a numerical vector using AI models
3. **Vector Storage**: Embeddings are stored in Elasticsearch for fast retrieval
4. **Similarity Search**: When users search, the system finds similar vectors

### Why Chunking is Important

- **Context Management**: LLMs have token limits, so large documents must be split
- **Precision**: Smaller chunks allow more targeted retrieval
- **Performance**: Faster processing and search
- **Relevance**: Users get specific relevant sections, not entire documents

### Chunking Strategy

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **Chunk Size** | 1024 characters | Balance between context and precision |
| **Overlap** | Configurable | Maintain context across chunk boundaries |
| **Metadata** | File UUID, index, timestamp | Track chunk provenance |
| **Storage** | Elasticsearch | Fast vector similarity search |

---

## 3. How These Processes Work Together

The complete pipeline looks like this:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   File Upload   │    │   Text Extract  │    │   Chunking      │
│                 │───►│                 │───►│                 │
│ • PDF/Image     │    │ • OCR/Tesseract │    │ • 1024 chars    │
│ • Word Doc      │    │ • MarkItDown    │    │ • Overlap       │
│ • Email Attach  │    │ • Text Clean    │    │ • Metadata      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PostgreSQL    │    │   Embeddings    │
                       │                 │    │                 │
                       │ • Original Text │    │ • Vector Arrays │
                       │ • File Metadata │    │ • Semantic Info │
                       │ • User Info     │    │ • Search Index  │
                       └─────────────────┘    └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   Elasticsearch │
                                               │                 │
                                               │ • Vector Store  │
                                               │ • Fast Search   │
                                               │ • Similarity    │
                                               └─────────────────┘
```

### Data Flow Sequence

1. **Upload Phase**: User uploads document → Validation → Storage
2. **Processing Phase**: Text extraction → Chunking → Embedding generation
3. **Storage Phase**: PostgreSQL (metadata) + Elasticsearch (vectors)
4. **Search Phase**: Query embedding → Similarity search → Result ranking

---

## 4. Technical Implementation Details

### File Ingestion Implementation

**File**: `django_app/redbox_app/worker.py` (lines 41-72)
```python
# From worker.py - the actual processing happens here
def ingest(file_id: UUID) -> None:
    # These models need to be loaded at runtime otherwise they can be loaded before they exist
    from redbox_app.redbox_core.models import File

    try:
        file = File.objects.get(id=file_id)
    except File.DoesNotExist:
        logging.info("file_id=%s no longer exists, has the user deleted it?", file_id)
        return

    logging.info("Ingesting file: %s", file)

    try:
        file_extension = Path(file.url).suffix.lower()
        logging.info(f"Processing file: {file.file_name}, extension: {file_extension}")
        if file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.tif', '.webp']:
            # OCR processing for images
            logging.info(f"Using OCR for image file: {file.file_name}")
            text_content = extract_text_with_ocr(file.url, file_extension)
            logging.info(f"OCR extracted text length: {len(text_content)}")
            file.text = sanitise_string(text_content)
        else:
            # Existing markitdown processing for other formats
            logging.info(f"Using markitdown for file: {file.file_name}")
            markdown = md.convert(file.url)
            file.text = sanitise_string(markdown.text_content)
        file.token_count = len(tokeniser.encode(file.text))
        file.status = File.Status.complete
    except (Exception, UnsupportedFormatException) as error:
        file.status = File.Status.errored
        file.ingest_error = str(error)
    file.save()
```

### OCR Implementation

**File**: `django_app/redbox_app/worker.py` (lines 15-38)
```python
def extract_text_with_ocr(file_path: str, file_extension: str) -> str:
    """Extract text from images and PDFs using OCR"""
    try:
        import pytesseract
        from PIL import Image
        from pdf2image import convert_from_path
    except ImportError:
        raise ImportError("OCR dependencies not installed. Please install pytesseract and pdf2image.")
    
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
    else:
        raise UnsupportedFormatException(f"OCR not supported for {file_extension}")
```

### Embedding Generation

**⚠️ IMPORTANT NOTE**: The current Redbox codebase (as of this analysis) **does not implement the full chunking and embedding pipeline**. The current implementation only extracts text from documents and stores it in PostgreSQL. The chunking and embedding functionality described below is based on the documentation and migration history, but is not currently active in the codebase.

**Expected Implementation** (from documentation and notebooks):
```python
# Initialize embedding model
embedding_model = SentenceTransformerEmbeddings(
    model_name=env.embedding_model,  # e.g., "all-mpnet-base-v2"
    cache_folder="../models/"
)

# Generate embeddings for chunks
embeddings = [embedding.embedding for embedding in 
              model.embed_sentences([chunk.text for chunk in chunks]).data]

# Store in Elasticsearch
vector_store = ElasticsearchStore(
    es_connection=es,
    index_name="redbox-data-chunk",
    embedding=embedding_model,
    strategy=strategy,
    vector_query_field="embedding"
)
```

**Current State**: The system only performs text extraction and stores the full text in the `File.text` field in PostgreSQL. No chunking or embedding generation is currently implemented in the active codebase.

### Available Embedding Models

| Model | Size | Use Case | Performance |
|-------|------|----------|-------------|
| `all-mpnet-base-v2` | 768 dims | General purpose | High accuracy |
| `BAAI/bge-small-en-v1.5` | 384 dims | Efficient | Fast, smaller |
| `paraphrase-multilingual-MiniLM-L12-v2` | 384 dims | Multilingual | Good for non-English |

---

## 5. Queue Management System

Redbox uses **Django-Q** for background processing:

### How the Queue Works

1. **Task Creation**: When a file is uploaded, an async task is created
2. **Worker Processing**: Background workers pick up tasks from the queue
3. **Parallel Processing**: Multiple workers can process files simultaneously
4. **Error Handling**: Failed tasks are retried or marked as errored
5. **Status Tracking**: Users can see processing status in real-time

### Queue Implementation

**File**: `django_app/redbox_app/redbox_core/models.py` (lines 543-550)
```python
# From models.py - how tasks are queued
def ingest(self, sync: bool = False):
    task = async_task(ingest, self.id, task_name=self.file_name, group="ingest", sync=sync)
    if sync:
        result = Success.objects.get(pk=task)
        self.status = self.Status.complete if result.success else self.Status.errored
    else:
        self.task = next(item for item in OrmQ.objects.all() if item.task["id"] == task)
    self.save()
```

### Worker Configuration

**File**: `docker-compose.yml` (lines 70-90)
```yaml
# docker-compose.yml
worker:
  image: redbox-worker:latest
  build:
    context: .
    dockerfile: django_app/Dockerfile
  command: "venv/bin/django-admin qcluster"
  env_file:
    - .env
  depends_on:
    minio:
      condition: service_healthy
    django-app:
      condition: service_healthy
    db:
      condition: service_healthy
  networks:
    - redbox-app-network
  restart: unless-stopped
```

---

## 6. Real-World Example

Let's say KMRL uploads a safety incident report:

### Ingestion Process

1. **Upload**: Safety report PDF is uploaded
2. **Storage**: PDF stored in MinIO with path `user@kmrl.com/safety_report_2024.pdf`
3. **Text Extraction**: PDF converted to text: "Incident occurred at Station A on 2024-01-15..."
4. **Database**: File record created with status "processing"

### Embedding Process

1. **Chunking**: Text split into chunks:
   - Chunk 1: "Incident occurred at Station A on 2024-01-15. Train operator reported..."
   - Chunk 2: "Safety protocols were followed. Emergency response team arrived..."
   - Chunk 3: "Recommendations: Review signal timing, update training procedures..."

2. **Embedding**: Each chunk converted to 768-dimensional vector
3. **Storage**: Vectors stored in Elasticsearch with metadata

### Search Process

When someone searches "safety incident Station A":

1. **Query Embedding**: Search term converted to vector
2. **Similarity Search**: System finds most similar vectors
3. **Retrieval**: Relevant chunks returned with similarity scores
4. **Response**: LLM generates answer using retrieved context

---

## 7. Benefits for KMRL

### Information Latency Reduction

| Before | After |
|--------|-------|
| Hours spent reading through documents | Seconds to find relevant information |
| Manual document review | Automated text extraction and search |
| Missed critical information | Comprehensive search across all documents |

### Siloed Awareness Elimination

| Before | After |
|--------|-------|
| Information trapped in individual documents | Cross-document search reveals connections |
| Department-specific knowledge silos | Organization-wide knowledge sharing |
| Duplicate work across teams | Single source of truth |

### Knowledge Preservation

| Before | After |
|--------|-------|
| Knowledge lost when people leave | All information searchable and accessible |
| Scattered document storage | Centralized, organized repository |
| Difficulty finding historical information | Instant access to all past documents |

### Compliance Support

| Before | After |
|--------|-------|
| Manual tracking of regulatory updates | Automatic detection and routing of compliance-related content |
| Risk of missing deadlines | Proactive compliance monitoring |
| Audit trail gaps | Complete document processing history |

---

## 8. Key Components Overview

### Storage Systems

| Component | Purpose | Technology | Data Stored |
|-----------|---------|------------|-------------|
| **MinIO/S3** | Object storage | MinIO (local) / AWS S3 (cloud) | Original files |
| **PostgreSQL** | Relational database | PostgreSQL 13+ | File metadata, user data, chat history |
| **Elasticsearch** | Vector database | Elasticsearch 8.17+ | Text chunks, embeddings, search index |

### Processing Components

| Component | Purpose | Technology | Configuration |
|-----------|---------|------------|---------------|
| **Django App** | Web interface | Django 5.1 | User management, file upload |
| **Worker** | Background processing | Django-Q | Document processing, embedding generation |
| **RAG Engine** | AI processing | LangChain + LLMs | Chat, search, response generation |

### External Services

| Service | Purpose | Configuration |
|---------|---------|---------------|
| **LLM APIs** | Text generation | OpenAI, Google Gemini, Azure OpenAI |
| **Embedding Models** | Vector generation | Sentence Transformers, OpenAI Embeddings |
| **OCR Engine** | Text extraction | Tesseract OCR |

---

## 9. Troubleshooting Common Issues

### File Processing Issues

**Problem**: File stuck in "processing" status
- **Cause**: Worker not running or crashed
- **Solution**: Check worker logs, restart worker service

**Problem**: OCR quality poor
- **Cause**: Low image quality or unsupported language
- **Solution**: Improve image quality, install language packs

**Problem**: Large files timeout
- **Cause**: File too large for processing
- **Solution**: Increase timeout settings, split large files

### Search Issues

**Problem**: No search results
- **Cause**: Embeddings not generated or index corrupted
- **Solution**: Re-generate embeddings, rebuild Elasticsearch index

**Problem**: Poor search relevance
- **Cause**: Wrong embedding model or chunk size
- **Solution**: Adjust chunk size, try different embedding model

### Performance Issues

**Problem**: Slow processing
- **Cause**: Insufficient resources or queue backlog
- **Solution**: Scale workers, optimize chunk size

**Problem**: High memory usage
- **Cause**: Large embedding models or too many concurrent tasks
- **Solution**: Use smaller models, limit concurrent processing

---

## Quick Reference Commands

### Setup Commands
```bash
# Install dependencies
pip install markitdown pytesseract pdf2image django-q2 elasticsearch

# Install Tesseract with Malayalam support
sudo apt-get install tesseract-ocr tesseract-ocr-mal

# Start services
docker compose up -d

# Check worker status
python manage.py qmonitor
```

### Monitoring Commands
```bash
# Check file processing status
python manage.py shell -c "from redbox_app.redbox_core.models import File; print(File.objects.filter(status='processing').count())"

# Check Elasticsearch health
curl -X GET "localhost:9200/_cluster/health?pretty"

# View worker logs
docker logs redbox_worker_1
```

---

## 10. Current Implementation Status & Limitations

### ✅ What's Currently Implemented

1. **File Upload & Validation**: Complete implementation in `django_app/redbox_app/redbox_core/views/document_views.py`
2. **Text Extraction**: Working implementation in `django_app/redbox_app/worker.py`
   - MarkItDown for standard documents
   - Tesseract OCR for images and PDFs
3. **Queue Management**: Django-Q integration for background processing
4. **Storage**: MinIO/S3 for files, PostgreSQL for metadata and extracted text
5. **Basic RAG**: Simple document retrieval using full text search

### ❌ What's Missing (Critical Gaps)

1. **Chunking Pipeline**: No implementation found in current codebase
   - Documents are stored as full text, not chunked
   - No chunk size management or overlap handling
   
2. **Embedding Generation**: Not implemented in active codebase
   - No vector embeddings are generated
   - No semantic search capability
   
3. **Elasticsearch Integration**: Not actively used
   - No vector storage or similarity search
   - Documentation mentions it but implementation is missing
   
4. **Advanced RAG**: Limited to basic text search
   - No vector similarity search
   - No context-aware retrieval

### 🔧 Migration History Evidence

The Django migrations show that chunking and embedding were previously implemented:
- `0025_alter_file_status.py`: Shows "chunking" and "embedding" statuses
- `0020_remove_chatmessage_source_files_textchunk_and_more.py`: Removed text chunk references
- `0028_aisettings.py`: Contains chunking configuration fields

This suggests the full pipeline existed but was removed or disabled in a recent refactor.

### 📋 Implementation Requirements for Full Pipeline

To restore the complete document processing pipeline, the following components need to be implemented:

1. **Chunking Worker**: Split documents into 1024-character chunks with overlap
2. **Embedding Worker**: Generate vector embeddings for each chunk
3. **Elasticsearch Integration**: Store and index embeddings for similarity search
4. **Vector Search**: Implement semantic search capabilities
5. **RAG Enhancement**: Use retrieved chunks for context-aware responses

### 🎯 For KMRL Hackathon

The current implementation provides a solid foundation for:
- Document upload and text extraction
- Basic search functionality
- File management and storage

However, for advanced RAG capabilities (semantic search, context-aware responses), the missing chunking and embedding components would need to be implemented.

---

*This document provides a comprehensive understanding of Redbox's document processing pipeline. The current implementation focuses on text extraction and basic storage, with the advanced RAG components (chunking, embedding, vector search) requiring additional development.*
