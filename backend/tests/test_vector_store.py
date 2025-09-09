"""Tests for vector_store.py - VectorStore class"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, MagicMock, patch, call
from vector_store import VectorStore, SearchResults
from models import Course, Lesson, CourseChunk
import json


class TestSearchResults(unittest.TestCase):
    """Test SearchResults dataclass"""
    
    def test_from_chroma(self):
        """Test creating SearchResults from ChromaDB results"""
        chroma_results = {
            "documents": [["doc1", "doc2"]],
            "metadatas": [[{"key": "value1"}, {"key": "value2"}]],
            "distances": [[0.1, 0.2]]
        }
        
        results = SearchResults.from_chroma(chroma_results)
        
        self.assertEqual(results.documents, ["doc1", "doc2"])
        self.assertEqual(results.metadata, [{"key": "value1"}, {"key": "value2"}])
        self.assertEqual(results.distances, [0.1, 0.2])
        self.assertIsNone(results.error)
    
    def test_from_chroma_empty(self):
        """Test creating SearchResults from empty ChromaDB results"""
        chroma_results = {
            "documents": [],
            "metadatas": [],
            "distances": []
        }
        
        results = SearchResults.from_chroma(chroma_results)
        
        self.assertEqual(results.documents, [])
        self.assertEqual(results.metadata, [])
        self.assertEqual(results.distances, [])
    
    def test_empty(self):
        """Test creating empty SearchResults with error"""
        results = SearchResults.empty("No results found")
        
        self.assertEqual(results.documents, [])
        self.assertEqual(results.metadata, [])
        self.assertEqual(results.distances, [])
        self.assertEqual(results.error, "No results found")
    
    def test_is_empty(self):
        """Test is_empty method"""
        # Test with empty results
        empty_results = SearchResults(documents=[], metadata=[], distances=[])
        self.assertTrue(empty_results.is_empty())
        
        # Test with non-empty results
        non_empty_results = SearchResults(
            documents=["doc1"],
            metadata=[{}],
            distances=[0.1]
        )
        self.assertFalse(non_empty_results.is_empty())


class TestVectorStore(unittest.TestCase):
    """Test VectorStore functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock ChromaDB and its components
        with patch('vector_store.chromadb.PersistentClient') as MockClient, \
             patch('vector_store.chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction') as MockEmbedding:
            
            self.mock_client = Mock()
            self.mock_embedding = Mock()
            MockClient.return_value = self.mock_client
            MockEmbedding.return_value = self.mock_embedding
            
            # Setup collections
            self.mock_catalog = Mock()
            self.mock_content = Mock()
            self.mock_client.get_or_create_collection.side_effect = [
                self.mock_catalog,
                self.mock_content
            ]
            
            # Create VectorStore instance
            self.vector_store = VectorStore(
                chroma_path="./test_chroma",
                embedding_model="test_model",
                max_results=5
            )
            
            # Assign mocks to the instance for testing
            self.vector_store.course_catalog = self.mock_catalog
            self.vector_store.course_content = self.mock_content
    
    def test_initialization(self):
        """Test VectorStore initialization"""
        self.assertEqual(self.vector_store.max_results, 5)
        self.assertIsNotNone(self.vector_store.course_catalog)
        self.assertIsNotNone(self.vector_store.course_content)
    
    def test_search_with_course_name(self):
        """Test search with course name filter"""
        # Setup course name resolution
        self.vector_store._resolve_course_name = Mock(return_value="Python Course")
        
        # Setup search results
        mock_chroma_results = {
            "documents": [["Python basics content"]],
            "metadatas": [[{"course_title": "Python Course", "lesson_number": 1}]],
            "distances": [[0.3]]
        }
        self.mock_content.query.return_value = mock_chroma_results
        
        # Execute search
        results = self.vector_store.search(
            query="What is Python?",
            course_name="Python"
        )
        
        # Verify results
        self.assertFalse(results.is_empty())
        self.assertEqual(results.documents[0], "Python basics content")
        self.assertEqual(results.metadata[0]["course_title"], "Python Course")
        
        # Verify query was called with correct filter
        self.mock_content.query.assert_called_once_with(
            query_texts=["What is Python?"],
            n_results=5,
            where={"course_title": "Python Course"}
        )
    
    def test_search_with_lesson_number(self):
        """Test search with lesson number filter"""
        # Setup search results
        mock_chroma_results = {
            "documents": [["Lesson 2 content"]],
            "metadatas": [[{"course_title": "Course", "lesson_number": 2}]],
            "distances": [[0.2]]
        }
        self.mock_content.query.return_value = mock_chroma_results
        
        # Execute search
        results = self.vector_store.search(
            query="lesson content",
            lesson_number=2
        )
        
        # Verify filter
        self.mock_content.query.assert_called_once_with(
            query_texts=["lesson content"],
            n_results=5,
            where={"lesson_number": 2}
        )
    
    def test_search_with_both_filters(self):
        """Test search with both course name and lesson number"""
        # Setup course name resolution
        self.vector_store._resolve_course_name = Mock(return_value="Python Course")
        
        # Setup search results
        mock_chroma_results = {
            "documents": [["Specific content"]],
            "metadatas": [[{"course_title": "Python Course", "lesson_number": 3}]],
            "distances": [[0.1]]
        }
        self.mock_content.query.return_value = mock_chroma_results
        
        # Execute search
        results = self.vector_store.search(
            query="specific query",
            course_name="Python",
            lesson_number=3
        )
        
        # Verify combined filter
        self.mock_content.query.assert_called_once_with(
            query_texts=["specific query"],
            n_results=5,
            where={"$and": [
                {"course_title": "Python Course"},
                {"lesson_number": 3}
            ]}
        )
    
    def test_search_no_course_found(self):
        """Test search when course name doesn't exist"""
        # Setup course name resolution to return None
        self.vector_store._resolve_course_name = Mock(return_value=None)
        
        # Execute search
        results = self.vector_store.search(
            query="test",
            course_name="Nonexistent Course"
        )
        
        # Verify error result
        self.assertTrue(results.is_empty())
        self.assertIn("No course found matching", results.error)
        self.assertIn("Nonexistent Course", results.error)
    
    def test_search_with_exception(self):
        """Test search error handling"""
        # Setup query to raise exception
        self.mock_content.query.side_effect = Exception("Database error")
        
        # Execute search
        results = self.vector_store.search(query="test query")
        
        # Verify error result
        self.assertTrue(results.is_empty())
        self.assertIn("Search error", results.error)
        self.assertIn("Database error", results.error)
    
    def test_resolve_course_name(self):
        """Test course name resolution"""
        # Setup catalog query results
        self.mock_catalog.query.return_value = {
            "documents": [["Python Programming"]],
            "metadatas": [[{"title": "Python Programming Course"}]]
        }
        
        # Execute
        result = self.vector_store._resolve_course_name("Python")
        
        # Verify
        self.assertEqual(result, "Python Programming Course")
        self.mock_catalog.query.assert_called_once_with(
            query_texts=["Python"],
            n_results=1
        )
    
    def test_resolve_course_name_not_found(self):
        """Test course name resolution when not found"""
        # Setup empty results
        self.mock_catalog.query.return_value = {
            "documents": [[]],
            "metadatas": [[]]
        }
        
        # Execute
        result = self.vector_store._resolve_course_name("Unknown")
        
        # Verify
        self.assertIsNone(result)
    
    def test_build_filter_combinations(self):
        """Test filter building with different combinations"""
        # Test no filters
        filter_dict = self.vector_store._build_filter(None, None)
        self.assertIsNone(filter_dict)
        
        # Test course only
        filter_dict = self.vector_store._build_filter("Course Title", None)
        self.assertEqual(filter_dict, {"course_title": "Course Title"})
        
        # Test lesson only
        filter_dict = self.vector_store._build_filter(None, 5)
        self.assertEqual(filter_dict, {"lesson_number": 5})
        
        # Test both
        filter_dict = self.vector_store._build_filter("Course Title", 3)
        self.assertEqual(filter_dict, {"$and": [
            {"course_title": "Course Title"},
            {"lesson_number": 3}
        ]})
    
    def test_add_course_metadata(self):
        """Test adding course metadata"""
        # Create course
        course = Course(
            title="Test Course",
            instructor="Test Instructor",
            course_link="https://example.com/course",
            lessons=[
                Lesson(lesson_number=1, title="Lesson 1", lesson_link="https://example.com/lesson1"),
                Lesson(lesson_number=2, title="Lesson 2", lesson_link="https://example.com/lesson2")
            ]
        )
        
        # Execute
        self.vector_store.add_course_metadata(course)
        
        # Verify catalog add was called
        call_args = self.mock_catalog.add.call_args
        
        self.assertEqual(call_args[1]["documents"], ["Test Course"])
        self.assertEqual(call_args[1]["ids"], ["Test Course"])
        
        metadata = call_args[1]["metadatas"][0]
        self.assertEqual(metadata["title"], "Test Course")
        self.assertEqual(metadata["instructor"], "Test Instructor")
        self.assertEqual(metadata["course_link"], "https://example.com/course")
        self.assertEqual(metadata["lesson_count"], 2)
        
        # Verify lessons JSON
        lessons = json.loads(metadata["lessons_json"])
        self.assertEqual(len(lessons), 2)
        self.assertEqual(lessons[0]["lesson_number"], 1)
        self.assertEqual(lessons[0]["lesson_title"], "Lesson 1")
    
    def test_add_course_content(self):
        """Test adding course content chunks"""
        # Create chunks
        chunks = [
            CourseChunk(course_title="Course 1", lesson_number=1, chunk_index=0, content="Content 1"),
            CourseChunk(course_title="Course 1", lesson_number=1, chunk_index=1, content="Content 2"),
            CourseChunk(course_title="Course 1", lesson_number=2, chunk_index=0, content="Content 3")
        ]
        
        # Execute
        self.vector_store.add_course_content(chunks)
        
        # Verify content add was called
        call_args = self.mock_content.add.call_args
        
        self.assertEqual(call_args[1]["documents"], ["Content 1", "Content 2", "Content 3"])
        
        metadatas = call_args[1]["metadatas"]
        self.assertEqual(len(metadatas), 3)
        self.assertEqual(metadatas[0]["course_title"], "Course 1")
        self.assertEqual(metadatas[0]["lesson_number"], 1)
        self.assertEqual(metadatas[0]["chunk_index"], 0)
        
        ids = call_args[1]["ids"]
        self.assertEqual(ids[0], "Course_1_0")
        self.assertEqual(ids[1], "Course_1_1")
    
    def test_add_empty_course_content(self):
        """Test adding empty course content"""
        # Execute with empty list
        self.vector_store.add_course_content([])
        
        # Verify no add was called
        self.mock_content.add.assert_not_called()
    
    def test_clear_all_data(self):
        """Test clearing all data"""
        # Setup new mocks for recreated collections
        new_catalog = Mock()
        new_content = Mock()
        
        # Configure get_or_create_collection to return new mocks after initial setup
        self.mock_client.get_or_create_collection.side_effect = [
            new_catalog,
            new_content
        ]
        
        # Execute
        self.vector_store.clear_all_data()
        
        # Verify collections were deleted
        self.mock_client.delete_collection.assert_any_call("course_catalog")
        self.mock_client.delete_collection.assert_any_call("course_content")
        
        # Verify collections were recreated (2 additional calls after the initial 2)
        # Initial setup made 2 calls, clear_all_data should make 2 more
        self.assertEqual(self.mock_client.get_or_create_collection.call_count, 4)
    
    def test_get_existing_course_titles(self):
        """Test getting existing course titles"""
        # Setup mock results
        self.mock_catalog.get.return_value = {
            "ids": ["Course 1", "Course 2", "Course 3"]
        }
        
        # Execute
        titles = self.vector_store.get_existing_course_titles()
        
        # Verify
        self.assertEqual(titles, ["Course 1", "Course 2", "Course 3"])
    
    def test_get_course_count(self):
        """Test getting course count"""
        # Setup mock results
        self.mock_catalog.get.return_value = {
            "ids": ["Course 1", "Course 2"]
        }
        
        # Execute
        count = self.vector_store.get_course_count()
        
        # Verify
        self.assertEqual(count, 2)
    
    def test_get_course_link(self):
        """Test getting course link"""
        # Setup mock results
        self.mock_catalog.get.return_value = {
            "metadatas": [{"course_link": "https://example.com/course"}]
        }
        
        # Execute
        link = self.vector_store.get_course_link("Test Course")
        
        # Verify
        self.assertEqual(link, "https://example.com/course")
        self.mock_catalog.get.assert_called_once_with(ids=["Test Course"])
    
    def test_get_lesson_link(self):
        """Test getting lesson link"""
        # Setup mock results
        lessons_json = json.dumps([
            {"lesson_number": 1, "lesson_link": "https://example.com/lesson1"},
            {"lesson_number": 2, "lesson_link": "https://example.com/lesson2"}
        ])
        self.mock_catalog.get.return_value = {
            "metadatas": [{"lessons_json": lessons_json}]
        }
        
        # Execute
        link = self.vector_store.get_lesson_link("Test Course", 2)
        
        # Verify
        self.assertEqual(link, "https://example.com/lesson2")
    
    def test_get_all_courses_metadata(self):
        """Test getting all courses metadata"""
        # Setup mock results
        self.mock_catalog.get.return_value = {
            "metadatas": [
                {
                    "title": "Course 1",
                    "lessons_json": json.dumps([{"lesson_number": 1}])
                },
                {
                    "title": "Course 2",
                    "lessons_json": json.dumps([{"lesson_number": 1}])
                }
            ]
        }
        
        # Execute
        metadata = self.vector_store.get_all_courses_metadata()
        
        # Verify
        self.assertEqual(len(metadata), 2)
        self.assertEqual(metadata[0]["title"], "Course 1")
        self.assertIn("lessons", metadata[0])
        self.assertNotIn("lessons_json", metadata[0])


if __name__ == "__main__":
    unittest.main()