"""
Shared pytest fixtures and configuration for all tests.
"""

import pytest
import os
import sys
import tempfile
import shutil
from typing import Generator, Dict, Any, List
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from config import Config
from rag_system import RAGSystem
from session_manager import SessionManager
from vector_store import VectorStore
from document_processor import DocumentProcessor
from ai_generator import AIGenerator


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_config(temp_dir: Path) -> Config:
    """Create a mock configuration for testing."""
    config = Config()
    config.CHROMADB_PATH = str(temp_dir / "test_chroma_db")
    config.CHUNK_SIZE = 500
    config.CHUNK_OVERLAP = 100
    config.MAX_SEARCH_RESULTS = 3
    config.ANTHROPIC_API_KEY = "test-api-key"
    return config


@pytest.fixture
def mock_anthropic_client():
    """Mock the Anthropic client."""
    with patch('ai_generator.anthropic.Anthropic') as mock_client:
        # Mock the messages.create method
        mock_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(text="This is a test response based on the search results.")
        ]
        mock_instance.messages.create.return_value = mock_response
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_course_data() -> Dict[str, Any]:
    """Sample course data for testing."""
    return {
        "title": "Test Course: Introduction to Testing",
        "lessons": [
            {
                "lesson_number": 1,
                "lesson_title": "Getting Started with Testing",
                "transcript": "Welcome to testing. This lesson covers basic testing concepts including unit tests, integration tests, and test-driven development.",
                "video_link": "https://example.com/lesson1"
            },
            {
                "lesson_number": 2,
                "lesson_title": "Advanced Testing Techniques",
                "transcript": "In this lesson, we explore advanced testing patterns such as mocking, fixtures, and continuous integration.",
                "video_link": "https://example.com/lesson2"
            }
        ]
    }


@pytest.fixture
def sample_course_file(temp_dir: Path, sample_course_data: Dict[str, Any]) -> Path:
    """Create a sample course file for testing."""
    course_file = temp_dir / "test_course.txt"
    
    content = f"Course Title: {sample_course_data['title']}\n\n"
    for lesson in sample_course_data["lessons"]:
        content += f"Lesson {lesson['lesson_number']}: {lesson['lesson_title']}\n"
        content += f"Video link: {lesson['video_link']}\n"
        content += f"{lesson['transcript']}\n\n"
    
    course_file.write_text(content)
    return course_file


@pytest.fixture
def mock_vector_store(mock_config: Config) -> VectorStore:
    """Create a mock vector store for testing."""
    with patch('vector_store.chromadb.PersistentClient'):
        with patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
            store = VectorStore(
                chroma_path=mock_config.CHROMADB_PATH,
                embedding_model="all-MiniLM-L6-v2",
                max_results=mock_config.MAX_SEARCH_RESULTS
            )
            # Mock the search method
            store.search = MagicMock(return_value=[
                {
                    "content": "This is test content about testing.",
                    "course_title": "Test Course",
                    "lesson_number": 1,
                    "lesson_title": "Introduction to Testing",
                    "video_link": "https://example.com/lesson1"
                }
            ])
            return store


@pytest.fixture
def mock_session_manager() -> SessionManager:
    """Create a mock session manager."""
    manager = SessionManager()
    manager.create_session = MagicMock(return_value="test-session-id")
    manager.get_history = MagicMock(return_value=[])
    manager.add_exchange = MagicMock()
    return manager


@pytest.fixture
def mock_rag_system(mock_config: Config, mock_vector_store: VectorStore, 
                    mock_session_manager: SessionManager, mock_anthropic_client) -> RAGSystem:
    """Create a mock RAG system for testing."""
    with patch('rag_system.VectorStore', return_value=mock_vector_store):
        with patch('rag_system.SessionManager', return_value=mock_session_manager):
            with patch('rag_system.AIGenerator') as mock_ai_gen:
                # Setup AI generator mock
                mock_ai_instance = MagicMock()
                mock_ai_instance.generate_response.return_value = (
                    "This is a test response.",
                    [{"title": "Test Course - Lesson 1", "course_title": "Test Course", 
                      "lesson_number": 1, "link": "https://example.com/lesson1"}]
                )
                mock_ai_gen.return_value = mock_ai_instance
                
                rag_system = RAGSystem(mock_config)
                rag_system.vector_store = mock_vector_store
                rag_system.session_manager = mock_session_manager
                rag_system.ai_generator = mock_ai_instance
                # Mock the query method to return tuple properly
                rag_system.query = MagicMock(return_value=(
                    "This is a test response.",
                    [{"title": "Test Course - Lesson 1", "course_title": "Test Course", 
                      "lesson_number": 1, "link": "https://example.com/lesson1"}]
                ))
                return rag_system


@pytest.fixture
def test_app(mock_rag_system: RAGSystem):
    """
    Create a test FastAPI app with mocked dependencies.
    This creates the API endpoints inline to avoid static file mounting issues.
    """
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
    from typing import List, Optional, Dict, Any
    
    # Create test app
    app = FastAPI(title="Test RAG System")
    
    # Define models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None
    
    class QueryResponse(BaseModel):
        answer: str
        sources: List[Dict[str, Any]]
        session_id: str
    
    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]
    
    class ClearSessionRequest(BaseModel):
        session_id: str
    
    # Define endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id or "test-session-id"
            answer, sources = mock_rag_system.query(request.query, session_id)
            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            # Mock analytics
            analytics = {
                "total_courses": 2,
                "course_titles": ["Test Course 1", "Test Course 2"]
            }
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/api/session/clear")
    async def clear_session(request: ClearSessionRequest):
        try:
            mock_rag_system.session_manager.clear_session(request.session_id)
            return {"status": "success", "message": f"Session {request.session_id} cleared"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/")
    async def root():
        return {"message": "Test RAG System API"}
    
    return TestClient(app)


@pytest.fixture
def mock_search_results() -> List[Dict[str, Any]]:
    """Mock search results for testing."""
    return [
        {
            "content": "Testing is essential for software quality. Unit tests verify individual components work correctly.",
            "course_title": "Software Testing Fundamentals",
            "lesson_number": 1,
            "lesson_title": "Introduction to Testing",
            "video_link": "https://example.com/testing/lesson1"
        },
        {
            "content": "Integration tests ensure different parts of your system work together properly.",
            "course_title": "Software Testing Fundamentals", 
            "lesson_number": 2,
            "lesson_title": "Integration Testing",
            "video_link": "https://example.com/testing/lesson2"
        }
    ]


@pytest.fixture
def mock_document_processor(mock_config: Config) -> DocumentProcessor:
    """Create a mock document processor."""
    processor = DocumentProcessor(mock_config)
    processor.process_course_file = MagicMock(return_value=(
        {
            "title": "Test Course",
            "lessons": [
                {
                    "lesson_number": 1,
                    "lesson_title": "Test Lesson",
                    "transcript": "Test content",
                    "video_link": "https://example.com/lesson1"
                }
            ]
        },
        [
            {
                "content": "Test content",
                "course_title": "Test Course",
                "lesson_number": 1,
                "lesson_title": "Test Lesson",
                "video_link": "https://example.com/lesson1",
                "chunk_index": 0,
                "total_chunks": 1
            }
        ]
    ))
    return processor