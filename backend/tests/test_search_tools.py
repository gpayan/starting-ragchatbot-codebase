"""Tests for search_tools.py - CourseSearchTool and CourseOutlineTool"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, MagicMock, patch
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool(unittest.TestCase):
    """Test CourseSearchTool functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_vector_store = Mock()
        self.search_tool = CourseSearchTool(self.mock_vector_store)
    
    def test_tool_definition(self):
        """Test that tool definition is properly structured"""
        tool_def = self.search_tool.get_tool_definition()
        
        self.assertEqual(tool_def["name"], "search_course_content")
        self.assertIn("description", tool_def)
        self.assertIn("input_schema", tool_def)
        self.assertIn("properties", tool_def["input_schema"])
        self.assertIn("query", tool_def["input_schema"]["properties"])
        self.assertIn("course_name", tool_def["input_schema"]["properties"])
        self.assertIn("lesson_number", tool_def["input_schema"]["properties"])
        self.assertEqual(tool_def["input_schema"]["required"], ["query"])
    
    def test_execute_with_valid_results(self):
        """Test execute method with valid search results"""
        # Setup mock results
        mock_results = SearchResults(
            documents=["This is course content about Python"],
            metadata=[{
                "course_title": "Introduction to Python",
                "lesson_number": 1
            }],
            distances=[0.5],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.return_value = "https://example.com/lesson1"
        
        # Execute search
        result = self.search_tool.execute(
            query="Python basics",
            course_name="Python",
            lesson_number=1
        )
        
        # Verify results
        self.assertIn("Introduction to Python", result)
        self.assertIn("Lesson 1", result)
        self.assertIn("This is course content about Python", result)
        
        # Check that sources were tracked
        self.assertEqual(len(self.search_tool.last_sources), 1)
        self.assertEqual(self.search_tool.last_sources[0], "Introduction to Python - Lesson 1")
        
        # Check structured source objects
        self.assertEqual(len(self.search_tool.last_source_objects), 1)
        source_obj = self.search_tool.last_source_objects[0]
        self.assertEqual(source_obj["course_title"], "Introduction to Python")
        self.assertEqual(source_obj["lesson_number"], 1)
        self.assertEqual(source_obj["link"], "https://example.com/lesson1")
    
    def test_execute_with_empty_results(self):
        """Test execute method when no results are found"""
        # Setup empty results
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        
        # Execute search
        result = self.search_tool.execute(
            query="nonexistent content",
            course_name="Python"
        )
        
        # Verify appropriate message
        self.assertIn("No relevant content found", result)
        self.assertIn("Python", result)
    
    def test_execute_with_error(self):
        """Test execute method when search returns an error"""
        # Setup error results
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Database connection failed"
        )
        self.mock_vector_store.search.return_value = mock_results
        
        # Execute search
        result = self.search_tool.execute(query="test query")
        
        # Verify error message is returned
        self.assertEqual(result, "Database connection failed")
    
    def test_execute_with_multiple_results(self):
        """Test execute with multiple search results"""
        # Setup multiple results
        mock_results = SearchResults(
            documents=[
                "Content from lesson 1",
                "Content from lesson 2",
                "Content from lesson 3"
            ],
            metadata=[
                {"course_title": "Python Course", "lesson_number": 1},
                {"course_title": "Python Course", "lesson_number": 2},
                {"course_title": "Java Course", "lesson_number": 1}
            ],
            distances=[0.3, 0.5, 0.7],
            error=None
        )
        self.mock_vector_store.search.return_value = mock_results
        self.mock_vector_store.get_lesson_link.side_effect = [
            "https://example.com/python/1",
            "https://example.com/python/2",
            "https://example.com/java/1"
        ]
        
        # Execute search
        result = self.search_tool.execute(query="programming basics")
        
        # Verify all results are included
        self.assertIn("Python Course", result)
        self.assertIn("Java Course", result)
        self.assertIn("Lesson 1", result)
        self.assertIn("Lesson 2", result)
        
        # Check sources
        self.assertEqual(len(self.search_tool.last_sources), 3)
        self.assertEqual(len(self.search_tool.last_source_objects), 3)
    
    def test_execute_calls_vector_store_correctly(self):
        """Test that execute calls vector store search with correct parameters"""
        mock_results = SearchResults(documents=[], metadata=[], distances=[], error=None)
        self.mock_vector_store.search.return_value = mock_results
        
        # Test with all parameters
        self.search_tool.execute(
            query="test query",
            course_name="Test Course",
            lesson_number=5
        )
        
        # Verify vector store was called correctly
        self.mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name="Test Course",
            lesson_number=5
        )


class TestCourseOutlineTool(unittest.TestCase):
    """Test CourseOutlineTool functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_vector_store = Mock()
        self.outline_tool = CourseOutlineTool(self.mock_vector_store)
    
    def test_tool_definition(self):
        """Test that tool definition is properly structured"""
        tool_def = self.outline_tool.get_tool_definition()
        
        self.assertEqual(tool_def["name"], "get_course_outline")
        self.assertIn("description", tool_def)
        self.assertIn("input_schema", tool_def)
        self.assertIn("properties", tool_def["input_schema"])
        self.assertIn("course_name", tool_def["input_schema"]["properties"])
        self.assertEqual(tool_def["input_schema"]["required"], ["course_name"])
    
    def test_execute_with_valid_course(self):
        """Test execute method with valid course data"""
        # Setup mock course resolution
        self.mock_vector_store._resolve_course_name.return_value = "Introduction to Python"
        
        # Setup mock course metadata
        self.mock_vector_store.course_catalog.get.return_value = {
            "metadatas": [{
                "course_link": "https://example.com/python-course",
                "instructor": "John Doe",
                "lesson_count": 3,
                "lessons_json": '[{"lesson_number": 1, "lesson_title": "Getting Started"}, {"lesson_number": 2, "lesson_title": "Variables"}, {"lesson_number": 3, "lesson_title": "Functions"}]'
            }]
        }
        
        # Execute
        result = self.outline_tool.execute(course_name="Python")
        
        # Verify output
        self.assertIn("Introduction to Python", result)
        self.assertIn("https://example.com/python-course", result)
        self.assertIn("John Doe", result)
        self.assertIn("Total Lessons:", result)
        self.assertIn("3", result)
        self.assertIn("Lesson 1: Getting Started", result)
        self.assertIn("Lesson 2: Variables", result)
        self.assertIn("Lesson 3: Functions", result)
        
        # Check sources
        self.assertEqual(len(self.outline_tool.last_sources), 1)
        self.assertEqual(self.outline_tool.last_sources[0], "Introduction to Python")
    
    def test_execute_with_nonexistent_course(self):
        """Test execute method when course doesn't exist"""
        # Setup mock to return None for unknown course
        self.mock_vector_store._resolve_course_name.return_value = None
        
        # Execute
        result = self.outline_tool.execute(course_name="Nonexistent Course")
        
        # Verify error message
        self.assertIn("No course found matching", result)
        self.assertIn("Nonexistent Course", result)
    
    def test_execute_with_database_error(self):
        """Test execute method when database error occurs"""
        # Setup mock course resolution
        self.mock_vector_store._resolve_course_name.return_value = "Test Course"
        
        # Setup mock to raise exception
        self.mock_vector_store.course_catalog.get.side_effect = Exception("Database error")
        
        # Execute
        result = self.outline_tool.execute(course_name="Test")
        
        # Verify error message
        self.assertIn("Error retrieving course outline", result)
        self.assertIn("Database error", result)


class TestToolManager(unittest.TestCase):
    """Test ToolManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.tool_manager = ToolManager()
        self.mock_tool = Mock()
        self.mock_tool.get_tool_definition.return_value = {
            "name": "test_tool",
            "description": "Test tool"
        }
    
    def test_register_tool(self):
        """Test tool registration"""
        self.tool_manager.register_tool(self.mock_tool)
        
        self.assertIn("test_tool", self.tool_manager.tools)
        self.assertEqual(self.tool_manager.tools["test_tool"], self.mock_tool)
    
    def test_get_tool_definitions(self):
        """Test getting all tool definitions"""
        # Register multiple tools
        tool1 = Mock()
        tool1.get_tool_definition.return_value = {"name": "tool1"}
        tool2 = Mock()
        tool2.get_tool_definition.return_value = {"name": "tool2"}
        
        self.tool_manager.register_tool(tool1)
        self.tool_manager.register_tool(tool2)
        
        definitions = self.tool_manager.get_tool_definitions()
        
        self.assertEqual(len(definitions), 2)
        self.assertIn({"name": "tool1"}, definitions)
        self.assertIn({"name": "tool2"}, definitions)
    
    def test_execute_tool(self):
        """Test tool execution"""
        self.mock_tool.execute.return_value = "Tool result"
        self.tool_manager.register_tool(self.mock_tool)
        
        result = self.tool_manager.execute_tool("test_tool", param1="value1")
        
        self.assertEqual(result, "Tool result")
        self.mock_tool.execute.assert_called_once_with(param1="value1")
    
    def test_execute_nonexistent_tool(self):
        """Test executing a tool that doesn't exist"""
        result = self.tool_manager.execute_tool("nonexistent_tool")
        
        self.assertIn("Tool 'nonexistent_tool' not found", result)
    
    def test_get_last_sources(self):
        """Test getting last sources from tools"""
        # Create tool with last_sources
        tool_with_sources = Mock()
        tool_with_sources.get_tool_definition.return_value = {"name": "search_tool"}
        tool_with_sources.last_sources = ["Source 1", "Source 2"]
        
        self.tool_manager.register_tool(tool_with_sources)
        
        sources = self.tool_manager.get_last_sources()
        
        self.assertEqual(sources, ["Source 1", "Source 2"])
    
    def test_reset_sources(self):
        """Test resetting sources in all tools"""
        # Create tools with sources
        tool1 = Mock()
        tool1.get_tool_definition.return_value = {"name": "tool1"}
        tool1.last_sources = ["Source 1"]
        tool1.last_source_objects = [{"title": "Source 1"}]
        
        tool2 = Mock()
        tool2.get_tool_definition.return_value = {"name": "tool2"}
        tool2.last_sources = ["Source 2"]
        tool2.last_source_objects = [{"title": "Source 2"}]
        
        self.tool_manager.register_tool(tool1)
        self.tool_manager.register_tool(tool2)
        
        # Reset sources
        self.tool_manager.reset_sources()
        
        # Verify sources were reset
        self.assertEqual(tool1.last_sources, [])
        self.assertEqual(tool1.last_source_objects, [])
        self.assertEqual(tool2.last_sources, [])
        self.assertEqual(tool2.last_source_objects, [])


if __name__ == "__main__":
    unittest.main()