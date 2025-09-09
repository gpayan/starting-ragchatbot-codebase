# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Starting the Application
```bash
# Quick start using the provided script
./run.sh

# Manual start
cd backend
uv run uvicorn app:app --reload --port 8000
```

### Dependency Management
```bash
# Install dependencies (uses uv package manager)
uv sync

# Add new dependencies
uv add <package-name>
```

## Architecture Overview

This is a **Retrieval-Augmented Generation (RAG) system** for querying course materials. The system uses semantic search with vector embeddings to find relevant content and generates AI-powered responses.

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Web UI)                     │
│                     /frontend/index.html                     │
│                         script.js                            │
└────────────────────┬───────────────────┬────────────────────┘
                     │                   │
                     ▼                   ▼
            ┌────────────────┐   ┌────────────────┐
            │  /api/query    │   │  /api/courses  │
            └───────┬────────┘   └───────┬────────┘
                    │                     │
     ┌──────────────▼─────────────────────▼──────────────┐
     │                   FastAPI (app.py)                 │
     │              - CORS middleware enabled             │
     │              - Static file serving                 │
     │              - Request/Response models             │
     └──────────────────────┬────────────────────────────┘
                            │
     ┌──────────────────────▼────────────────────────────┐
     │              RAGSystem (rag_system.py)            │
     │         Central orchestrator coordinating:         │
     └──────┬──────────┬──────────┬──────────┬──────────┘
            │          │          │          │
     ┌──────▼────┐ ┌──▼────┐ ┌──▼────┐ ┌──▼──────────┐
     │ Document  │ │Vector │ │  AI   │ │   Session   │
     │ Processor │ │ Store │ │  Gen  │ │   Manager   │
     └───────────┘ └───┬───┘ └───┬───┘ └─────────────┘
                       │          │
                  ┌────▼────┐ ┌──▼──────────────┐
                  │ChromaDB │ │ Anthropic Claude│
                  └─────────┘ └─────────────────┘
```

### Core Components

**Backend Architecture** (`backend/`):

#### 1. Entry Point & API Layer
- **`app.py`**: FastAPI application entry point
  - `/api/query`: Process user queries and return AI-generated responses with sources
  - `/api/courses`: Return course statistics and metadata
  - Serves frontend static files from `/frontend` directory
  - Configures CORS for cross-origin requests

#### 2. Core RAG System
- **`rag_system.py`**: Main orchestrator that coordinates all RAG components
  - Manages document processing, vector storage, AI generation, and session management
  - Implements tool-based search using registered search tools
  - Methods:
    - `add_course_document()`: Process and store single course
    - `add_course_folder()`: Batch process course documents
    - `query()`: Handle user queries with AI and return responses
    - `get_course_analytics()`: Retrieve course statistics

#### 3. Document Processing Pipeline
- **`document_processor.py`**: Handles document parsing and chunking
  - Extracts course structure (title, lessons, content)
  - Creates overlapping chunks for better context preservation
  - Configurable chunk size (default 1000) and overlap (default 200)

#### 4. Vector Storage & Retrieval
- **`vector_store.py`**: ChromaDB wrapper for vector storage and semantic search
  - Stores course metadata and content chunks as embeddings
  - Performs similarity search to find relevant content
  - Uses sentence-transformers for embedding generation
  - Maintains separate collections for metadata and content

#### 5. AI Generation System
- **`ai_generator.py`**: Anthropic Claude integration for response generation
  - Uses tool-calling to search course content
  - Generates contextual responses based on retrieved information
  - Maintains conversation context for coherent multi-turn interactions

#### 6. Search Tools Framework
- **`search_tools.py`**: Tool management system for AI search capabilities
  - `CourseSearchTool`: Allows AI to search course content during response generation
  - `ToolManager`: Registers and manages available tools
  - Tracks sources used in responses for citation

#### 7. Session Management
- **`session_manager.py`**: Manages user conversation sessions
  - Tracks conversation history per session
  - Configurable history length (default 10 exchanges)
  - Enables context-aware responses across multiple queries

#### 8. Data Models
- **`models.py`**: Pydantic models for data validation
  - `Course`: Course metadata structure
  - `Lesson`: Individual lesson information
  - `CourseChunk`: Content chunk with metadata

#### 9. Configuration
- **`config.py`**: Centralized configuration management
  - API keys and model settings
  - Chunk size and overlap parameters
  - Database paths and search limits

### Frontend Architecture (`frontend/`)
- **`index.html`**: Single-page application interface
- **`script.js`**: Client-side logic for API interaction
- **`style.css`**: UI styling and responsive design

### Data Flow

```
1. Document Ingestion:
   docs/ → DocumentProcessor → CourseChunks → VectorStore → ChromaDB

2. Query Processing:
   User Query → RAGSystem → AIGenerator → Tool Calls → VectorStore
                                ↓
                         Search Results
                                ↓
                      Context + Response → User

3. Session Management:
   Query/Response → SessionManager → Conversation History
                           ↓
                   Context for next query
```

### Key Design Patterns

1. **Tool-Based Search**: AI uses defined tools to search content rather than direct retrieval
2. **Chunking Strategy**: Overlapping chunks ensure context preservation across boundaries
3. **Session Persistence**: Maintains conversation context for coherent multi-turn dialogue
4. **Modular Architecture**: Each component has single responsibility for maintainability

**Key Dependencies**:
- **ChromaDB**: Vector database for semantic search
- **Anthropic Claude**: AI model for response generation (claude-3-5-sonnet)
- **Sentence Transformers**: For creating text embeddings (all-MiniLM-L6-v2)
- **FastAPI**: Web framework with automatic API documentation at `/docs`
- **uv**: Modern Python package manager for dependency management

## Environment Configuration

Required environment variable in `.env`:
```
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

## Document Storage

Course documents are stored in `docs/` directory and automatically loaded on startup. Supported formats: `.txt`, `.pdf`, `.docx`
- always use uv to run the server do not use pip directly
- make sure to use uv to manage all dependencies