"""Integration tests for the RAG system with real components"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, patch
import tempfile
import shutil
from config import Config
from rag_system import RAGSystem
from vector_store import VectorStore
from search_tools import CourseSearchTool


class TestIntegration(unittest.TestCase):
    """Integration tests with real ChromaDB"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        # Create a temporary directory for ChromaDB
        cls.temp_dir = tempfile.mkdtemp()
        
        # Create test config
        cls.config = Config()
        cls.config.CHROMA_PATH = os.path.join(cls.temp_dir, "test_chroma")
        cls.config.ANTHROPIC_API_KEY = "test_key"  # Will mock API calls
        
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        # Remove temporary directory
        if os.path.exists(cls.temp_dir):
            shutil.rmtree(cls.temp_dir)
    
    def setUp(self):
        """Set up for each test"""
        # Clean ChromaDB directory
        if os.path.exists(self.config.CHROMA_PATH):
            shutil.rmtree(self.config.CHROMA_PATH)
    
    def test_vector_store_search_real(self):
        """Test VectorStore with real ChromaDB"""
        # Create real VectorStore
        vector_store = VectorStore(
            chroma_path=self.config.CHROMA_PATH,
            embedding_model="all-MiniLM-L6-v2",
            max_results=5
        )
        
        # Add test course metadata
        from models import Course, Lesson
        course = Course(
            title="Python Basics",
            instructor="John Doe",
            course_link="https://example.com/python",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="Introduction",
                    lesson_link="https://example.com/lesson1"
                ),
                Lesson(
                    lesson_number=2,
                    title="Variables",
                    lesson_link="https://example.com/lesson2"
                )
            ]
        )
        
        vector_store.add_course_metadata(course)
        
        # Add test content
        from models import CourseChunk
        chunks = [
            CourseChunk(
                course_title="Python Basics",
                lesson_number=1,
                chunk_index=0,
                content="Python is a high-level programming language known for its simplicity."
            ),
            CourseChunk(
                course_title="Python Basics",
                lesson_number=1,
                chunk_index=1,
                content="Python uses indentation to define code blocks instead of curly braces."
            ),
            CourseChunk(
                course_title="Python Basics",
                lesson_number=2,
                chunk_index=0,
                content="Variables in Python are dynamically typed. You can assign any type to a variable."
            )
        ]
        
        vector_store.add_course_content(chunks)
        
        # Test search without filters
        results = vector_store.search(query="What is Python?")
        self.assertFalse(results.is_empty())
        self.assertIn("Python", results.documents[0])
        
        # Test search with course name
        results = vector_store.search(
            query="programming language",
            course_name="Python"
        )
        self.assertFalse(results.is_empty())
        
        # Test search with lesson number
        results = vector_store.search(
            query="variables",
            lesson_number=2
        )
        self.assertFalse(results.is_empty())
        self.assertIn("Variables", results.documents[0])
        
        # Test course name resolution
        resolved = vector_store._resolve_course_name("Python")
        self.assertEqual(resolved, "Python Basics")
    
    def test_search_tool_with_real_vector_store(self):
        """Test CourseSearchTool with real VectorStore"""
        # Create real VectorStore
        vector_store = VectorStore(
            chroma_path=self.config.CHROMA_PATH,
            embedding_model="all-MiniLM-L6-v2",
            max_results=5
        )
        
        # Add test data
        from models import Course, Lesson, CourseChunk
        course = Course(
            title="Introduction to AI",
            instructor="Jane Smith",
            course_link="https://example.com/ai",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="What is AI?",
                    lesson_link="https://example.com/ai/lesson1"
                )
            ]
        )
        
        vector_store.add_course_metadata(course)
        
        chunks = [
            CourseChunk(
                course_title="Introduction to AI",
                lesson_number=1,
                chunk_index=0,
                content="Artificial Intelligence (AI) is the simulation of human intelligence by machines."
            )
        ]
        
        vector_store.add_course_content(chunks)
        
        # Create search tool
        search_tool = CourseSearchTool(vector_store)
        
        # Test execute method
        result = search_tool.execute(
            query="What is artificial intelligence?",
            course_name="AI"
        )
        
        # Verify results
        self.assertIn("Introduction to AI", result)
        self.assertIn("Artificial Intelligence", result)
        self.assertIn("simulation of human intelligence", result)
        
        # Check sources
        self.assertEqual(len(search_tool.last_sources), 1)
        self.assertEqual(search_tool.last_sources[0], "Introduction to AI - Lesson 1")
        
        # Check structured sources
        self.assertEqual(len(search_tool.last_source_objects), 1)
        source_obj = search_tool.last_source_objects[0]
        self.assertEqual(source_obj["course_title"], "Introduction to AI")
        self.assertEqual(source_obj["lesson_number"], 1)
        self.assertEqual(source_obj["link"], "https://example.com/ai/lesson1")
    
    @patch('ai_generator.anthropic.Anthropic')
    def test_rag_system_end_to_end(self, mock_anthropic_class):
        """Test complete RAG system flow"""
        # Mock Anthropic client
        mock_client = Mock()
        mock_anthropic_class.return_value = mock_client
        
        # Create RAG system with real components
        rag_system = RAGSystem(self.config)
        
        # Add test course document
        from models import Course, Lesson
        
        # Mock document processor to return test data
        mock_course = Course(
            title="Machine Learning Fundamentals",
            instructor="Dr. Smith",
            course_link="https://example.com/ml",
            lessons=[
                Lesson(
                    lesson_number=1,
                    title="Introduction to ML",
                    lesson_link="https://example.com/ml/1"
                )
            ]
        )
        
        from models import CourseChunk
        mock_chunks = [
            CourseChunk(
                course_title="Machine Learning Fundamentals",
                lesson_number=1,
                chunk_index=0,
                content="Machine learning is a subset of AI that enables systems to learn from data."
            )
        ]
        
        # Patch document processor
        with patch.object(rag_system.document_processor, 'process_course_document') as mock_process:
            mock_process.return_value = (mock_course, mock_chunks)
            
            # Add course
            course, chunk_count = rag_system.add_course_document("/fake/path.txt")
            self.assertEqual(course.title, "Machine Learning Fundamentals")
            self.assertEqual(chunk_count, 1)
        
        # Now test query with mocked AI response
        # Setup AI mock to simulate tool use
        mock_tool_response = Mock()
        mock_tool_response.type = "tool_use"
        mock_tool_response.name = "search_course_content"
        mock_tool_response.input = {"query": "machine learning"}
        mock_tool_response.id = "tool_123"
        
        mock_initial = Mock()
        mock_initial.content = [mock_tool_response]
        mock_initial.stop_reason = "tool_use"
        
        mock_final = Mock()
        mock_final.content = [Mock(text="Machine learning is a powerful AI technique.")]
        
        mock_client.messages.create.side_effect = [mock_initial, mock_final]
        
        # Execute query
        response, sources = rag_system.query("What is machine learning?")
        
        # Verify response
        self.assertEqual(response, "Machine learning is a powerful AI technique.")
        
        # The sources should include our test data
        # (The actual search was performed by the tool)
        self.assertIsInstance(sources, list)


if __name__ == "__main__":
    unittest.main()