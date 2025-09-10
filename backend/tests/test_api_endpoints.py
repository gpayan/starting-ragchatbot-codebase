"""
Test suite for FastAPI endpoints.
Tests all API routes including query, courses, and session management.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


class TestQueryEndpoint:
    """Test the /api/query endpoint."""
    
    @pytest.mark.api
    def test_query_success_with_new_session(self, test_app):
        """Test successful query with new session creation."""
        response = test_app.post(
            "/api/query",
            json={"query": "What is unit testing?"}
        )
        
        # Debug output if test fails
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.json()}")
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data
        assert data["session_id"] == "test-session-id"
        assert isinstance(data["sources"], list)
    
    @pytest.mark.api
    def test_query_with_existing_session(self, test_app):
        """Test query with existing session ID."""
        session_id = "existing-session-123"
        response = test_app.post(
            "/api/query",
            json={
                "query": "Explain integration testing",
                "session_id": session_id
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id
    
    @pytest.mark.api
    def test_query_empty_string(self, test_app):
        """Test query with empty string."""
        response = test_app.post(
            "/api/query",
            json={"query": ""}
        )
        
        # Should still process but may return empty or default response
        assert response.status_code in [200, 422]
    
    @pytest.mark.api
    def test_query_missing_field(self, test_app):
        """Test query with missing required field."""
        response = test_app.post(
            "/api/query",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.api
    def test_query_long_text(self, test_app):
        """Test query with very long text."""
        long_query = "What is testing? " * 100
        response = test_app.post(
            "/api/query",
            json={"query": long_query}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
    
    @pytest.mark.api
    def test_query_special_characters(self, test_app):
        """Test query with special characters."""
        response = test_app.post(
            "/api/query",
            json={"query": "What about testing with @#$% special chars?"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
    
    @pytest.mark.api
    def test_query_response_structure(self, test_app):
        """Test the structure of query response."""
        response = test_app.post(
            "/api/query",
            json={"query": "Tell me about testing"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert isinstance(data, dict)
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert "sources" in data
        assert isinstance(data["sources"], list)
        assert "session_id" in data
        assert isinstance(data["session_id"], str)
        
        # Check sources structure if present
        if data["sources"]:
            source = data["sources"][0]
            assert isinstance(source, dict)
            expected_keys = {"title", "course_title", "lesson_number", "link"}
            assert expected_keys.issubset(source.keys())


class TestCoursesEndpoint:
    """Test the /api/courses endpoint."""
    
    @pytest.mark.api
    def test_get_courses_success(self, test_app):
        """Test successful retrieval of course statistics."""
        response = test_app.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_courses" in data
        assert "course_titles" in data
        assert isinstance(data["total_courses"], int)
        assert isinstance(data["course_titles"], list)
    
    @pytest.mark.api
    def test_courses_response_structure(self, test_app):
        """Test the structure of courses response."""
        response = test_app.get("/api/courses")
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response matches expected structure
        assert data["total_courses"] == 2
        assert len(data["course_titles"]) == 2
        assert "Test Course 1" in data["course_titles"]
        assert "Test Course 2" in data["course_titles"]
    
    @pytest.mark.api
    def test_courses_no_params(self, test_app):
        """Test that courses endpoint requires no parameters."""
        # Should work without any query params
        response = test_app.get("/api/courses")
        assert response.status_code == 200
        
        # Should ignore unexpected query params
        response = test_app.get("/api/courses?unexpected=param")
        assert response.status_code == 200


class TestSessionEndpoint:
    """Test the /api/session/clear endpoint."""
    
    @pytest.mark.api
    def test_clear_session_success(self, test_app):
        """Test successful session clearing."""
        response = test_app.post(
            "/api/session/clear",
            json={"session_id": "test-session-123"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "test-session-123" in data["message"]
    
    @pytest.mark.api  
    def test_clear_session_missing_id(self, test_app):
        """Test clearing session without ID."""
        response = test_app.post(
            "/api/session/clear",
            json={}
        )
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.api
    def test_clear_session_empty_id(self, test_app):
        """Test clearing session with empty ID."""
        response = test_app.post(
            "/api/session/clear",
            json={"session_id": ""}
        )
        
        # Should accept empty string but may fail internally
        assert response.status_code in [200, 500]
    
    @pytest.mark.api
    def test_clear_nonexistent_session(self, test_app):
        """Test clearing a session that doesn't exist."""
        response = test_app.post(
            "/api/session/clear",
            json={"session_id": "nonexistent-session-999"}
        )
        
        # Should succeed even if session doesn't exist (idempotent)
        assert response.status_code == 200


class TestRootEndpoint:
    """Test the root endpoint."""
    
    @pytest.mark.api
    def test_root_endpoint(self, test_app):
        """Test the root endpoint returns expected message."""
        response = test_app.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Test RAG System API" in data["message"]


class TestErrorHandling:
    """Test error handling across endpoints."""
    
    @pytest.mark.api
    def test_query_internal_error(self, test_app, mock_rag_system):
        """Test handling of internal server errors in query endpoint."""
        # Make the query method raise an exception
        mock_rag_system.query = MagicMock(side_effect=Exception("Internal error"))
        
        response = test_app.post(
            "/api/query",
            json={"query": "This will fail"}
        )
        
        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Internal error" in data["detail"]
    
    @pytest.mark.api
    def test_invalid_json_payload(self, test_app):
        """Test handling of invalid JSON in request body."""
        response = test_app.post(
            "/api/query",
            data="This is not JSON",
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 422
    
    @pytest.mark.api
    def test_wrong_http_method(self, test_app):
        """Test using wrong HTTP method on endpoints."""
        # GET on POST-only endpoint
        response = test_app.get("/api/query")
        assert response.status_code == 405  # Method not allowed
        
        # POST on GET-only endpoint  
        response = test_app.post("/api/courses")
        assert response.status_code == 405


class TestConcurrentRequests:
    """Test handling of concurrent requests."""
    
    @pytest.mark.api
    def test_multiple_queries_same_session(self, test_app):
        """Test multiple queries using the same session."""
        session_id = "shared-session-456"
        
        # First query
        response1 = test_app.post(
            "/api/query",
            json={"query": "First question", "session_id": session_id}
        )
        assert response1.status_code == 200
        
        # Second query with same session
        response2 = test_app.post(
            "/api/query",
            json={"query": "Second question", "session_id": session_id}
        )
        assert response2.status_code == 200
        
        # Both should return the same session ID
        assert response1.json()["session_id"] == session_id
        assert response2.json()["session_id"] == session_id
    
    @pytest.mark.api
    def test_multiple_queries_different_sessions(self, test_app):
        """Test multiple queries with different sessions."""
        # Query 1 with session A
        response1 = test_app.post(
            "/api/query",
            json={"query": "Question A", "session_id": "session-A"}
        )
        
        # Query 2 with session B
        response2 = test_app.post(
            "/api/query",
            json={"query": "Question B", "session_id": "session-B"}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["session_id"] == "session-A"
        assert response2.json()["session_id"] == "session-B"


class TestContentTypes:
    """Test content type handling."""
    
    @pytest.mark.api
    def test_json_content_type(self, test_app):
        """Test that API accepts proper JSON content type."""
        response = test_app.post(
            "/api/query",
            json={"query": "Test query"},
            headers={"Content-Type": "application/json"}
        )
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
    
    @pytest.mark.api
    def test_response_encoding(self, test_app):
        """Test response encoding for special characters."""
        response = test_app.post(
            "/api/query",
            json={"query": "Test with émojis 🎯 and unicode ñ"}
        )
        
        assert response.status_code == 200
        # Response should handle unicode properly
        data = response.json()
        assert isinstance(data["answer"], str)