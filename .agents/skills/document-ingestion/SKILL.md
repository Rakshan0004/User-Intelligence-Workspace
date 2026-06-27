---
name: document-ingestion
description: Multi-format document ingestion pipeline for the User Intelligence Workspace. Covers processing of PDF, DOCX, XLSX, Images (OCR/vision), Audio (Whisper), Video, URLs, and YouTube URLs. Each processor extracts clean text content that feeds into the knowledge extraction pipeline.
---

# Document Ingestion Skill

## Overview
The document ingestion pipeline handles all supported input formats, converting them into clean text content that can be processed by the knowledge extraction engine. All content is **chunked** before LLM processing — no document is sent to an LLM in its entirety. The system determines what matters, what is repetitive, what is noise, and what should become knowledge.

## Supported Formats & Processors

| Format | Library | Processing Strategy |
|--------|---------|-------------------|
| **PDF** | PyMuPDF (fitz) + pdfplumber | Text extraction + table extraction |
| **DOCX** | python-docx | Paragraph + table extraction |
| **XLSX** | openpyxl + pandas | Sheet-by-sheet structured extraction |
| **Images** | Pillow + OpenAI Vision API / Gemini Vision | OCR + visual content description |
| **Audio** | openai-whisper / OpenAI Whisper API | Speech-to-text transcription |
| **Video** | ffmpeg + Whisper | Extract audio → transcribe |
| **URLs** | httpx + trafilatura / BeautifulSoup | Web content extraction |
| **YouTube** | yt-dlp + Whisper | Download audio → transcribe + metadata |

## Common Interface

```python
from abc import ABC, abstractmethod
from pydantic import BaseModel

class ProcessedDocument(BaseModel):
    source_id: str
    source_type: str          # "pdf", "docx", "xlsx", etc.
    title: str
    content: str              # Clean extracted text
    sections: list[Section]   # Structured sections if available
    tables: list[Table]       # Extracted tables if available
    metadata: dict            # Format-specific metadata
    content_length: int
    processing_time_ms: int
    quality_score: float      # 0-1, assessed post-extraction

class Section(BaseModel):
    heading: str
    content: str
    level: int                # Heading level (1-6)

class Table(BaseModel):
    caption: str | None
    headers: list[str]
    rows: list[list[str]]

class DocumentProcessor(ABC):
    @abstractmethod
    async def process(self, file_path: str | None, url: str | None, raw_bytes: bytes | None) -> ProcessedDocument:
        """Process a document and return structured content."""
    
    @abstractmethod
    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
```

## PDF Processor
```python
# Key implementation details:
# 1. Use PyMuPDF for fast text extraction
# 2. Use pdfplumber for table extraction (more accurate for tables)
# 3. Fall back to OCR (vision API) for scanned PDFs with no extractable text
# 4. Handle multi-page documents by preserving page structure
# 5. Extract images from PDF if they contain relevant diagrams

class PDFProcessor(DocumentProcessor):
    async def process(self, file_path, url, raw_bytes) -> ProcessedDocument:
        # 1. Try text extraction with PyMuPDF
        # 2. If text is too short/empty → likely scanned → use Vision API
        # 3. Extract tables with pdfplumber
        # 4. Combine text + tables into structured output
        pass
```

## DOCX Processor
```python
# Key implementation details:
# 1. Extract paragraphs preserving heading hierarchy
# 2. Extract tables with headers
# 3. Handle embedded images (extract + Vision API description)
# 4. Preserve list structure (bullets, numbered)

class DOCXProcessor(DocumentProcessor):
    async def process(self, file_path, url, raw_bytes) -> ProcessedDocument:
        # 1. Load with python-docx
        # 2. Walk paragraphs, detect heading styles → create Sections
        # 3. Extract tables → Table objects
        # 4. Combine into ProcessedDocument
        pass
```

## XLSX Processor
```python
# Key implementation details:
# 1. Process each sheet separately
# 2. Detect header rows automatically
# 3. Convert structured data into natural language summaries (LLM)
# 4. Handle merged cells, formulas (values only)
# 5. Skip empty sheets

class XLSXProcessor(DocumentProcessor):
    async def process(self, file_path, url, raw_bytes) -> ProcessedDocument:
        # 1. Load with openpyxl
        # 2. For each sheet: detect headers, extract rows
        # 3. Use LLM to summarize tabular data into knowledge-ready text
        # 4. Preserve raw table structure for reference
        pass
```

## Image Processor
```python
# Key implementation details:
# 1. Use Vision API (OpenAI GPT-4o-vision or Gemini Vision)
# 2. Prompt: "Describe this image in detail. Extract any text, data, 
#    diagrams, charts, or factual information visible."
# 3. OCR for text-heavy images
# 4. Handle infographics, charts, diagrams

class ImageProcessor(DocumentProcessor):
    async def process(self, file_path, url, raw_bytes) -> ProcessedDocument:
        # 1. Load image, check dimensions/format
        # 2. Send to Vision API with extraction prompt
        # 3. If text-heavy → also run OCR for accuracy
        # 4. Combine descriptions into ProcessedDocument
        pass
```

## Audio Processor
```python
# Key implementation details:
# 1. Use OpenAI Whisper API (or local whisper model)
# 2. Support: mp3, wav, m4a, flac, ogg
# 3. For long audio: chunk into segments (max 25MB per API call)
# 4. Include timestamps in transcript for reference

class AudioProcessor(DocumentProcessor):
    async def process(self, file_path, url, raw_bytes) -> ProcessedDocument:
        # 1. Validate audio format
        # 2. If > 25MB, split into chunks
        # 3. Transcribe each chunk with Whisper
        # 4. Combine transcripts with timestamps
        pass
```

## Video Processor
```python
# Key implementation details:
# 1. Extract audio track using ffmpeg
# 2. Transcribe audio with Whisper
# 3. Optionally: sample key frames → Vision API for visual content
# 4. Combine audio transcript + visual descriptions

class VideoProcessor(DocumentProcessor):
    async def process(self, file_path, url, raw_bytes) -> ProcessedDocument:
        # 1. Extract audio with ffmpeg
        # 2. Transcribe with AudioProcessor
        # 3. Sample frames at intervals (every 30s)
        # 4. Describe key frames with Vision API
        # 5. Combine into unified document
        pass
```

## URL Processor
```python
# Key implementation details:
# 1. Use httpx for async fetching
# 2. Use trafilatura for content extraction (best for articles)
# 3. Fall back to BeautifulSoup if trafilatura fails
# 4. Extract: title, main content, author, date, metadata
# 5. Handle JavaScript-rendered pages via playwright (optional)
# 6. Store file metadata in PostgreSQL uploaded_files table

class URLProcessor(DocumentProcessor):
    async def process(self, file_path, url, raw_bytes) -> ProcessedDocument:
        # 1. Fetch URL with httpx
        # 2. Extract main content with trafilatura
        # 3. Fall back to BeautifulSoup if needed
        # 4. Extract metadata (title, author, date)
        # 5. Clean and structure content
        pass
```

## YouTube Processor
```python
# Key implementation details:
# 1. Use yt-dlp to extract metadata + download audio
# 2. First try: get existing subtitles/captions
# 3. Fall back: transcribe audio with Whisper
# 4. Extract: title, description, channel, duration, views
# 5. Structure transcript with timestamps

class YouTubeProcessor(DocumentProcessor):
    async def process(self, file_path, url, raw_bytes) -> ProcessedDocument:
        # 1. Extract video metadata with yt-dlp
        # 2. Try to get existing captions
        # 3. If no captions → download audio → transcribe
        # 4. Combine metadata + transcript
        pass
```

## Ingestion Router

```python
class IngestionRouter:
    """Routes incoming documents to the appropriate processor."""
    
    processors: dict[str, DocumentProcessor] = {
        "pdf": PDFProcessor(),
        "docx": DOCXProcessor(),
        "xlsx": XLSXProcessor(),
        "image": ImageProcessor(),
        "audio": AudioProcessor(),
        "video": VideoProcessor(),
        "url": URLProcessor(),
        "youtube": YouTubeProcessor(),
    }
    
    def detect_type(self, filename: str = None, url: str = None, mime_type: str = None) -> str:
        """Auto-detect document type from filename, URL, or MIME type."""
    
    async def ingest(self, file_path: str = None, url: str = None, raw_bytes: bytes = None) -> ProcessedDocument:
        """Route to appropriate processor and return structured content."""
```

## Post-Processing Pipeline
After any processor extracts content:
1. **Language detection** — verify content is processable
2. **Content quality check** — minimum length, coherence
3. **Deduplication check** — compare against existing sources via embedding similarity
4. **Document chunking** — split into semantic or fixed-size chunks (~1000 tokens, 200 overlap)
5. **Send chunks to Knowledge Extraction** — extract entities, facts, relationships per chunk
6. **Create Source node** in Neo4j with metadata, quality score, and chunk_count
7. **Track in PostgreSQL** — update `uploaded_files` with processing status

## Document Chunking Strategy

### Why Chunking is Required
LLMs have context window limits (4K-128K tokens). A 50-page PDF (~25,000 tokens) cannot be reliably processed in one call. Chunking ensures:
- Consistent extraction quality across document length
- Cost control (smaller chunks = cheaper LLM calls)
- Better entity/fact extraction (focused context)

### Chunking Approaches

#### Semantic Chunking (Preferred)
```python
def semantic_chunk(content: str, max_tokens: int = 1000, overlap_tokens: int = 200) -> list[str]:
    """
    1. Split by natural boundaries: paragraphs, headings, section breaks
    2. Merge consecutive small paragraphs into chunks up to max_tokens
    3. Add overlap from previous chunk for context continuity
    """
```

#### Fixed-Size Chunking (Fallback)
```python
def fixed_chunk(content: str, max_tokens: int = 1000, overlap_tokens: int = 200) -> list[str]:
    """
    1. Split into chunks of max_tokens
    2. Overlap by overlap_tokens between adjacent chunks
    3. Avoid splitting mid-sentence where possible
    """
```

### Chunk → Evidence Mapping
- Each chunk becomes one or more Evidence nodes in Neo4j
- Evidence nodes store `chunk_index` and `chunk_total`
- Entity resolution runs across all chunks of the same source to merge duplicates

## File Storage Strategy

### Local Development
- Files stored in `uploads/{source_id}/{filename}`
- Directory created per source for organization

### Production
- **Cloudflare R2** (S3-compatible, free tier: 10GB)
- Files uploaded with key: `{topic}/{source_id}/{filename}`
- URL stored in PostgreSQL `uploaded_files.storage_path`
- Raw files preserved for re-processing if extraction model improves

## File Size Limits
| Format | Max Size | Rationale |
|--------|----------|-----------|
| PDF | 50 MB | Large PDFs with images |
| DOCX | 25 MB | Embedded images |
| XLSX | 10 MB | Memory constraints for large spreadsheets |
| Images | 20 MB | High-res images |
| Audio | 100 MB | Long recordings |
| Video | 500 MB | Extracted audio only |
| URLs | N/A | Content extraction |
| YouTube | N/A | Audio download + transcribe |
