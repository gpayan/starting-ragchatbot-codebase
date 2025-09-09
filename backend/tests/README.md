# Test Suite for RAG Chatbot

## Test Files

### Unit Tests
These test individual components in isolation with mocked dependencies:

- **`test_ai_generator.py`** (11.5 KB)
  - Tests the AIGenerator class
  - 8 test cases covering tool calling, response generation, error handling
  - Uses mocked Anthropic client

- **`test_search_tools.py`** (13.5 KB)  
  - Tests CourseSearchTool and CourseOutlineTool classes
  - Tests ToolManager for tool registration and execution
  - 39 test cases total with mocked vector store

- **`test_vector_store.py`** (16.8 KB)
  - Tests VectorStore class and SearchResults dataclass
  - 20 test cases covering search, filtering, metadata management
  - Uses mocked ChromaDB client

- **`test_rag_system.py`** (13.8 KB)
  - Tests the main RAGSystem orchestrator
  - 11 test cases for query processing, document addition, analytics
  - All dependencies mocked

### Integration Tests
These test multiple components working together:

- **`test_integration.py`** (9.4 KB)
  - Tests with real ChromaDB instance
  - 3 comprehensive integration scenarios
  - Tests end-to-end flow with real vector storage

### Diagnostic Tests
Combined diagnostic tool for testing the live system:

- **`test_diagnostics.py`** (11.5 KB)
  - Consolidates all diagnostic testing
  - Tests live system components
  - Tests API endpoints (requires running server)
  - Tests content queries with real AI
  - Replaces the previous separate diagnostic scripts

## Running Tests

### Run all unit tests:
```bash
uv run python -m unittest discover tests/ -v
```

### Run specific test file:
```bash
uv run python -m unittest tests.test_vector_store -v
```

### Run diagnostic tests (requires server running):
```bash
# Start server first
uv run uvicorn app:app --reload --port 8000

# In another terminal
uv run python tests/test_diagnostics.py
```

### Run integration tests:
```bash
uv run python -m unittest tests.test_integration -v
```

## Test Coverage

- **Unit Test Coverage**: ~78 test cases
- **Components Tested**: 
  - Vector storage and retrieval
  - Search tool execution
  - AI integration and tool calling
  - RAG system orchestration
  - Session management
  - API endpoints

## Notes

- All test files are self-contained and can run independently
- Unit tests use mocks and don't require external services
- Integration tests create temporary ChromaDB instances
- Diagnostic tests require a running server and valid API key