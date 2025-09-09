"""Tests for rag_system.py - RAGSystem class"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, MagicMock, patch, call
from rag_system import RAGSystem
from models import Course, Lesson, CourseChunk


class TestRAGSystem(unittest.TestCase):
    """Test RAGSystem functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create mock config
        self.mock_config = Mock()
        self.mock_config.CHUNK_SIZE = 1000
        self.mock_config.CHUNK_OVERLAP = 200
        self.mock_config.CHROMA_PATH = "./test_chroma"
        self.mock_config.EMBEDDING_MODEL = "test_model"
        self.mock_config.MAX_RESULTS = 5
        self.mock_config.ANTHROPIC_API_KEY = "test_key"
        self.mock_config.ANTHROPIC_MODEL = "test_model"
        self.mock_config.MAX_HISTORY = 10
        
        # Patch all dependencies
        with patch('rag_system.DocumentProcessor') as MockDocProcessor, \
             patch('rag_system.VectorStore') as MockVectorStore, \
             patch('rag_system.AIGenerator') as MockAIGenerator, \
             patch('rag_system.SessionManager') as MockSessionManager, \
             patch('rag_system.ToolManager') as MockToolManager, \
             patch('rag_system.CourseSearchTool') as MockSearchTool, \
             patch('rag_system.CourseOutlineTool') as MockOutlineTool:
            
            # Create mocks
            self.mock_doc_processor = Mock()
            self.mock_vector_store = Mock()
            self.mock_ai_generator = Mock()
            self.mock_session_manager = Mock()
            self.mock_tool_manager = Mock()
            self.mock_search_tool = Mock()
            self.mock_outline_tool = Mock()
            
            # Configure constructors to return our mocks
            MockDocProcessor.return_value = self.mock_doc_processor
            MockVectorStore.return_value = self.mock_vector_store
            MockAIGenerator.return_value = self.mock_ai_generator
            MockSessionManager.return_value = self.mock_session_manager
            MockToolManager.return_value = self.mock_tool_manager
            MockSearchTool.return_value = self.mock_search_tool
            MockOutlineTool.return_value = self.mock_outline_tool
            
            # Create RAGSystem instance
            self.rag_system = RAGSystem(self.mock_config)
    
    def test_initialization(self):
        """Test RAGSystem initialization"""
        # Verify all components are initialized
        self.assertIsNotNone(self.rag_system.document_processor)
        self.assertIsNotNone(self.rag_system.vector_store)
        self.assertIsNotNone(self.rag_system.ai_generator)
        self.assertIsNotNone(self.rag_system.session_manager)
        self.assertIsNotNone(self.rag_system.tool_manager)
        
        # Verify tools are registered
        self.mock_tool_manager.register_tool.assert_any_call(self.mock_search_tool)
        self.mock_tool_manager.register_tool.assert_any_call(self.mock_outline_tool)
    
    def test_query_successful(self):
        """Test successful query processing"""
        # Setup mocks
        self.mock_session_manager.get_conversation_history.return_value = "Previous conversation"
        self.mock_ai_generator.generate_response.return_value = "This is the AI response about Python"
        self.mock_tool_manager.get_tool_definitions.return_value = [{"name": "search_tool"}]
        self.mock_tool_manager.get_last_source_objects.return_value = [
            {
                "title": "Python Course - Lesson 1",
                "course_title": "Python Course",
                "lesson_number": 1,
                "link": "https://example.com/lesson1"
            }
        ]
        
        # Execute query
        response, sources = self.rag_system.query(
            query="What is Python?",
            session_id="session123"
        )
        
        # Verify response
        self.assertEqual(response, "This is the AI response about Python")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["course_title"], "Python Course")
        self.assertEqual(sources[0]["lesson_number"], 1)
        
        # Verify AI generator was called correctly
        self.mock_ai_generator.generate_response.assert_called_once_with(
            query="Answer this question about course materials: What is Python?",
            conversation_history="Previous conversation",
            tools=[{"name": "search_tool"}],
            tool_manager=self.mock_tool_manager
        )
        
        # Verify session was updated
        self.mock_session_manager.add_exchange.assert_called_once_with(
            "session123",
            "What is Python?",
            "This is the AI response about Python"
        )
        
        # Verify sources were reset
        self.mock_tool_manager.reset_sources.assert_called_once()
    
    def test_query_without_session(self):
        """Test query without session ID"""
        # Setup mocks
        self.mock_ai_generator.generate_response.return_value = "Response without session"
        self.mock_tool_manager.get_last_source_objects.return_value = []
        self.mock_tool_manager.get_last_sources.return_value = ["Manual Source"]
        
        # Execute query without session
        response, sources = self.rag_system.query(query="Test query")
        
        # Verify response
        self.assertEqual(response, "Response without session")
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["title"], "Manual Source")
        
        # Verify no session history was retrieved
        self.mock_session_manager.get_conversation_history.assert_not_called()
        
        # Verify no session exchange was added
        self.mock_session_manager.add_exchange.assert_not_called()
    
    def test_query_with_new_session(self):
        """Test query with new session creation"""
        # Setup mocks
        self.mock_session_manager.create_session.return_value = "new_session_123"
        self.mock_ai_generator.generate_response.return_value = "Response"
        self.mock_tool_manager.get_last_source_objects.return_value = []
        self.mock_tool_manager.get_last_sources.return_value = []
        
        # Execute query with session
        response, sources = self.rag_system.query(
            query="Test",
            session_id="session456"
        )
        
        # Verify session history was retrieved
        self.mock_session_manager.get_conversation_history.assert_called_once_with("session456")
    
    def test_add_course_document_successful(self):
        """Test successful course document addition"""
        # Setup mock course and chunks
        mock_course = Course(
            title="Test Course",
            instructor="Test Instructor",
            course_link="https://example.com/course",
            lessons=[
                Lesson(lesson_number=1, title="Lesson 1", lesson_link="https://example.com/lesson1")
            ]
        )
        mock_chunks = [
            CourseChunk(
                course_title="Test Course",
                lesson_number=1,
                chunk_index=0,
                content="Chunk content"
            )
        ]
        
        self.mock_doc_processor.process_course_document.return_value = (mock_course, mock_chunks)
        
        # Execute
        course, chunk_count = self.rag_system.add_course_document("/path/to/course.txt")
        
        # Verify results
        self.assertEqual(course, mock_course)
        self.assertEqual(chunk_count, 1)
        
        # Verify document processor was called
        self.mock_doc_processor.process_course_document.assert_called_once_with("/path/to/course.txt")
        
        # Verify vector store was updated
        self.mock_vector_store.add_course_metadata.assert_called_once_with(mock_course)
        self.mock_vector_store.add_course_content.assert_called_once_with(mock_chunks)
    
    def test_add_course_document_with_error(self):
        """Test course document addition with error"""
        # Setup mock to raise exception
        self.mock_doc_processor.process_course_document.side_effect = Exception("Processing error")
        
        # Execute
        course, chunk_count = self.rag_system.add_course_document("/path/to/bad_course.txt")
        
        # Verify error handling
        self.assertIsNone(course)
        self.assertEqual(chunk_count, 0)
        
        # Verify vector store was not updated
        self.mock_vector_store.add_course_metadata.assert_not_called()
        self.mock_vector_store.add_course_content.assert_not_called()
    
    @patch('rag_system.os.path.exists')
    @patch('rag_system.os.listdir')
    @patch('rag_system.os.path.isfile')
    @patch('rag_system.os.path.join')
    def test_add_course_folder(self, mock_join, mock_isfile, mock_listdir, mock_exists):
        """Test adding courses from folder"""
        # Setup file system mocks
        mock_exists.return_value = True
        mock_listdir.return_value = ["course1.txt", "course2.pdf", "readme.md"]
        mock_isfile.side_effect = [True, True, True]
        mock_join.side_effect = lambda a, b: f"{a}/{b}"
        
        # Setup existing courses
        self.mock_vector_store.get_existing_course_titles.return_value = []
        
        # Setup course processing
        mock_course1 = Course(
            title="Course 1",
            instructor="Instructor 1",
            course_link="link1",
            lessons=[]
        )
        mock_course2 = Course(
            title="Course 2",
            instructor="Instructor 2",
            course_link="link2",
            lessons=[]
        )
        
        self.mock_doc_processor.process_course_document.side_effect = [
            (mock_course1, [Mock(), Mock()]),  # 2 chunks
            (mock_course2, [Mock(), Mock(), Mock()]),  # 3 chunks
            (None, [])  # readme.md doesn't match extension
        ]
        
        # Execute
        total_courses, total_chunks = self.rag_system.add_course_folder("/docs", clear_existing=False)
        
        # Verify results
        self.assertEqual(total_courses, 2)
        self.assertEqual(total_chunks, 5)
        
        # Verify vector store was not cleared
        self.mock_vector_store.clear_all_data.assert_not_called()
    
    @patch('rag_system.os.path.exists')
    @patch('rag_system.os.listdir')
    def test_add_course_folder_with_clear(self, mock_listdir, mock_exists):
        """Test adding courses with clear existing flag"""
        mock_exists.return_value = True
        mock_listdir.return_value = []  # Empty folder
        
        # Mock get_existing_course_titles to return an empty list
        self.mock_vector_store.get_existing_course_titles.return_value = []
        
        # Execute with clear flag
        self.rag_system.add_course_folder("/docs", clear_existing=True)
        
        # Verify data was cleared
        self.mock_vector_store.clear_all_data.assert_called_once()
    
    @patch('rag_system.os.path.exists')
    def test_add_course_folder_nonexistent(self, mock_exists):
        """Test adding courses from nonexistent folder"""
        mock_exists.return_value = False
        
        # Execute
        total_courses, total_chunks = self.rag_system.add_course_folder("/nonexistent")
        
        # Verify results
        self.assertEqual(total_courses, 0)
        self.assertEqual(total_chunks, 0)
    
    def test_get_course_analytics(self):
        """Test getting course analytics"""
        # Setup mock data
        self.mock_vector_store.get_course_count.return_value = 5
        self.mock_vector_store.get_existing_course_titles.return_value = [
            "Course 1", "Course 2", "Course 3", "Course 4", "Course 5"
        ]
        
        # Execute
        analytics = self.rag_system.get_course_analytics()
        
        # Verify results
        self.assertEqual(analytics["total_courses"], 5)
        self.assertEqual(len(analytics["course_titles"]), 5)
        self.assertIn("Course 1", analytics["course_titles"])
    
    def test_query_error_handling(self):
        """Test query error handling"""
        # Setup AI generator to raise exception
        self.mock_ai_generator.generate_response.side_effect = Exception("AI error")
        
        # Execute and expect exception to propagate
        with self.assertRaises(Exception) as context:
            self.rag_system.query("Test query")
        
        self.assertIn("AI error", str(context.exception))
    
    def test_source_fallback(self):
        """Test source fallback when no structured sources"""
        # Setup mocks
        self.mock_ai_generator.generate_response.return_value = "Response"
        self.mock_tool_manager.get_last_source_objects.return_value = []
        self.mock_tool_manager.get_last_sources.return_value = ["Source 1", "Source 2"]
        
        # Execute
        response, sources = self.rag_system.query("Test")
        
        # Verify fallback sources
        self.assertEqual(len(sources), 2)
        self.assertEqual(sources[0]["title"], "Source 1")
        self.assertEqual(sources[1]["title"], "Source 2")
        # Verify fallback sources have proper structure
        self.assertIsNone(sources[0]["lesson_number"])
        self.assertIsNone(sources[0]["link"])


if __name__ == "__main__":
    unittest.main()