#!/usr/bin/env python
"""Comprehensive diagnostic tests for the RAG system - combines API, content, and system tests"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
import requests
import json
from typing import List, Dict, Any
from unittest.mock import patch

# Import system components
from config import Config
from rag_system import RAGSystem
from vector_store import VectorStore
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager


class TestSystemDiagnostics(unittest.TestCase):
    """Diagnostic tests for the live RAG system"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.config = Config()
        cls.base_url = "http://localhost:8000"
    
    def test_01_api_configuration(self):
        """Test API configuration"""
        self.assertIsNotNone(self.config.ANTHROPIC_API_KEY, "API key not set")
        self.assertNotEqual(self.config.ANTHROPIC_API_KEY, "", "API key is empty")
        self.assertNotEqual(self.config.ANTHROPIC_API_KEY, "test_key", "API key is test placeholder")
    
    def test_02_vector_store_connectivity(self):
        """Test vector store connectivity and data"""
        vector_store = VectorStore(
            self.config.CHROMA_PATH,
            self.config.EMBEDDING_MODEL,
            self.config.MAX_RESULTS
        )
        
        # Check existing data
        course_count = vector_store.get_course_count()
        self.assertGreater(course_count, 0, "No courses loaded in vector store")
        
        # Test search
        results = vector_store.search("Python")
        self.assertFalse(results.is_empty(), "Search returned no results")
        self.assertIsNone(results.error, f"Search error: {results.error}")
    
    def test_03_search_tool_execution(self):
        """Test search tool execution"""
        vector_store = VectorStore(
            self.config.CHROMA_PATH,
            self.config.EMBEDDING_MODEL,
            self.config.MAX_RESULTS
        )
        
        search_tool = CourseSearchTool(vector_store)
        
        # Test basic search
        result = search_tool.execute(query="programming")
        self.assertIsNotNone(result, "Search tool returned None")
        self.assertGreater(len(result), 0, "Search tool returned empty result")
        self.assertNotIn("error", result.lower(), f"Search tool returned error: {result}")
        
        # Test with course filter
        result = search_tool.execute(query="lesson", course_name="MCP")
        self.assertIsNotNone(result, "Filtered search returned None")
    
    def test_04_outline_tool_execution(self):
        """Test outline tool execution"""
        vector_store = VectorStore(
            self.config.CHROMA_PATH,
            self.config.EMBEDDING_MODEL,
            self.config.MAX_RESULTS
        )
        
        outline_tool = CourseOutlineTool(vector_store)
        
        # Test getting course outline
        result = outline_tool.execute(course_name="MCP")
        self.assertIsNotNone(result, "Outline tool returned None")
        self.assertNotIn("No course found", result, "Course not found")
        self.assertIn("Course Title", result, "Outline missing course title")
    
    def test_05_rag_system_initialization(self):
        """Test RAG system initialization"""
        try:
            rag_system = RAGSystem(self.config)
            self.assertIsNotNone(rag_system, "RAG system initialization failed")
            
            # Check components
            self.assertIsNotNone(rag_system.vector_store)
            self.assertIsNotNone(rag_system.ai_generator)
            self.assertIsNotNone(rag_system.tool_manager)
            
            # Check tools registration
            tools = rag_system.tool_manager.tools
            self.assertIn("search_course_content", tools)
            self.assertIn("get_course_outline", tools)
            
        except Exception as e:
            self.fail(f"RAG system initialization failed: {e}")
    
    def test_06_rag_system_query(self):
        """Test RAG system query processing"""
        if not self.config.ANTHROPIC_API_KEY or self.config.ANTHROPIC_API_KEY == "test_key":
            self.skipTest("Valid API key required for query test")
        
        rag_system = RAGSystem(self.config)
        
        # Test simple query
        response, sources = rag_system.query("What courses are available?")
        
        self.assertIsNotNone(response, "Query returned None response")
        self.assertGreater(len(response), 0, "Query returned empty response")
        self.assertNotIn("query failed", response.lower(), "Query failed")
        self.assertIsInstance(sources, list, "Sources not a list")


class TestAPIEndpoints(unittest.TestCase):
    """Test API endpoints (requires running server)"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.base_url = "http://localhost:8000"
        cls.server_running = cls._check_server()
    
    @classmethod
    def _check_server(cls):
        """Check if server is running"""
        try:
            response = requests.get(f"{cls.base_url}/docs", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def setUp(self):
        """Skip tests if server not running"""
        if not self.server_running:
            self.skipTest("Server not running. Start with: uv run uvicorn app:app --reload")
    
    def test_01_courses_endpoint(self):
        """Test GET /api/courses endpoint"""
        response = requests.get(f"{self.base_url}/api/courses")
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("total_courses", data)
        self.assertIn("course_titles", data)
        self.assertGreater(data["total_courses"], 0)
    
    def test_02_query_endpoint(self):
        """Test POST /api/query endpoint"""
        payload = {
            "query": "What is machine learning?",
            "session_id": None
        }
        
        response = requests.post(
            f"{self.base_url}/api/query",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        self.assertIn("answer", data)
        self.assertIn("sources", data)
        self.assertIn("session_id", data)
        
        # Check response quality
        answer = data["answer"]
        self.assertGreater(len(answer), 50, "Answer too short")
        self.assertNotIn("query failed", answer.lower())
    
    def test_03_query_with_sources(self):
        """Test that queries return proper sources"""
        payload = {
            "query": "Tell me about the MCP course",
            "session_id": None
        }
        
        response = requests.post(f"{self.base_url}/api/query", json=payload)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        sources = data.get("sources", [])
        
        # Should have sources for course-specific query
        if sources:
            first_source = sources[0]
            self.assertIsInstance(first_source, dict)
            # Check for expected keys in source
            if "title" in first_source:
                self.assertIsNotNone(first_source["title"])
    
    def test_04_session_management(self):
        """Test session management endpoints"""
        # Create initial query
        response = requests.post(
            f"{self.base_url}/api/query",
            json={"query": "What is Python?", "session_id": None}
        )
        
        self.assertEqual(response.status_code, 200)
        session_id = response.json()["session_id"]
        self.assertIsNotNone(session_id)
        
        # Use same session
        response = requests.post(
            f"{self.base_url}/api/query",
            json={"query": "Tell me more", "session_id": session_id}
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Clear session
        response = requests.post(
            f"{self.base_url}/api/session/clear",
            json={"session_id": session_id}
        )
        
        self.assertEqual(response.status_code, 200)


class TestContentQueries(unittest.TestCase):
    """Test various content queries"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.config = Config()
        if cls.config.ANTHROPIC_API_KEY and cls.config.ANTHROPIC_API_KEY != "test_key":
            cls.rag_system = RAGSystem(cls.config)
        else:
            cls.rag_system = None
    
    def setUp(self):
        """Skip if no valid API key"""
        if not self.rag_system:
            self.skipTest("Valid API key required for content query tests")
    
    def test_general_query(self):
        """Test general knowledge query"""
        response, sources = self.rag_system.query("What is Python?")
        
        self.assertIsNotNone(response)
        self.assertGreater(len(response), 50)
        self.assertNotIn("query failed", response.lower())
    
    def test_course_specific_query(self):
        """Test course-specific query"""
        response, sources = self.rag_system.query("What is covered in the MCP course?")
        
        self.assertIsNotNone(response)
        self.assertIn("MCP", response)
        self.assertGreater(len(sources), 0, "No sources returned for course query")
    
    def test_technical_query(self):
        """Test technical content query"""
        response, sources = self.rag_system.query("How do I use ChromaDB?")
        
        self.assertIsNotNone(response)
        self.assertGreater(len(response), 100)
        # Should return sources from course content
        if sources:
            self.assertIsInstance(sources[0], dict)


def run_diagnostics():
    """Run all diagnostic tests"""
    print("\n" + "="*60)
    print("RAG CHATBOT DIAGNOSTIC TESTS")
    print("="*60)
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestSystemDiagnostics))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestAPIEndpoints))
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(TestContentQueries))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "="*60)
    print("DIAGNOSTIC SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL DIAGNOSTIC TESTS PASSED - System is working correctly!")
    else:
        print("\n❌ Some tests failed - Review the output above for details")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    # Run as diagnostic tool
    import sys
    success = run_diagnostics()
    sys.exit(0 if success else 1)