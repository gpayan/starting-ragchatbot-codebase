"""Tests for ai_generator.py - AIGenerator class"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import Mock, MagicMock, patch, call
from ai_generator import AIGenerator


class TestAIGenerator(unittest.TestCase):
    """Test AIGenerator functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock the anthropic client
        with patch('ai_generator.anthropic.Anthropic') as mock_anthropic:
            self.mock_client = Mock()
            mock_anthropic.return_value = self.mock_client
            self.ai_generator = AIGenerator(api_key="test_key", model="test_model")
    
    def test_initialization(self):
        """Test AIGenerator initialization"""
        self.assertEqual(self.ai_generator.model, "test_model")
        self.assertEqual(self.ai_generator.base_params["model"], "test_model")
        self.assertEqual(self.ai_generator.base_params["temperature"], 0)
        self.assertEqual(self.ai_generator.base_params["max_tokens"], 800)
    
    def test_generate_response_without_tools(self):
        """Test generating response without tools"""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="This is the AI response")]
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response
        
        # Generate response
        result = self.ai_generator.generate_response(
            query="What is Python?",
            conversation_history=None,
            tools=None,
            tool_manager=None
        )
        
        # Verify result
        self.assertEqual(result, "This is the AI response")
        
        # Verify API call
        self.mock_client.messages.create.assert_called_once()
        call_args = self.mock_client.messages.create.call_args[1]
        self.assertEqual(call_args["model"], "test_model")
        self.assertEqual(call_args["messages"][0]["content"], "What is Python?")
        self.assertIn("system", call_args)
    
    def test_generate_response_with_conversation_history(self):
        """Test generating response with conversation history"""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Response with context")]
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response
        
        # Generate response with history
        result = self.ai_generator.generate_response(
            query="Tell me more",
            conversation_history="Previous: User asked about Python. AI explained it's a programming language.",
            tools=None,
            tool_manager=None
        )
        
        # Verify result
        self.assertEqual(result, "Response with context")
        
        # Verify system prompt includes history
        call_args = self.mock_client.messages.create.call_args[1]
        self.assertIn("Previous conversation", call_args["system"])
        self.assertIn("User asked about Python", call_args["system"])
    
    def test_generate_response_with_single_tool_call(self):
        """Test generating response with single tool usage (backward compatibility)"""
        # Setup mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool execution result: Found course content"
        
        # Setup mock tools
        tools = [
            {
                "name": "search_course_content",
                "description": "Search course materials",
                "input_schema": {}
            }
        ]
        
        # Setup initial response with tool use
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "search_course_content"
        mock_tool_use.input = {"query": "Python basics"}
        mock_tool_use.id = "tool_123"
        
        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_use]
        mock_initial_response.stop_reason = "tool_use"
        
        # Setup second response (no more tools needed)
        mock_second_response = Mock()
        mock_second_response.content = [Mock(text="Based on the course content, Python is...")]
        mock_second_response.stop_reason = "end_turn"  # Natural termination
        
        # Configure mock client to return both responses
        self.mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_second_response
        ]
        
        # Generate response
        result = self.ai_generator.generate_response(
            query="What is Python?",
            conversation_history=None,
            tools=tools,
            tool_manager=mock_tool_manager
        )
        
        # Verify result
        self.assertEqual(result, "Based on the course content, Python is...")
        
        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content",
            query="Python basics"
        )
        
        # Verify two API calls were made
        self.assertEqual(self.mock_client.messages.create.call_count, 2)
        
        # Verify first call included tools
        first_call = self.mock_client.messages.create.call_args_list[0][1]
        self.assertIn("tools", first_call)
        self.assertEqual(first_call["tools"], tools)
        self.assertEqual(first_call["tool_choice"], {"type": "auto"})
        
        # Verify second call still has tools enabled (key change!)
        second_call = self.mock_client.messages.create.call_args_list[1][1]
        self.assertIn("tools", second_call)
        self.assertEqual(second_call["tools"], tools)
        messages = second_call["messages"]
        self.assertEqual(len(messages), 3)  # user, assistant with tool use, user with tool result
        self.assertEqual(messages[2]["role"], "user")
        tool_result = messages[2]["content"][0]
        self.assertEqual(tool_result["type"], "tool_result")
        self.assertEqual(tool_result["tool_use_id"], "tool_123")
        self.assertEqual(tool_result["content"], "Tool execution result: Found course content")
    
    def test_sequential_tool_calls_two_rounds(self):
        """Test AI making two sequential rounds of tool calls"""
        # Setup mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Course X outline: Lesson 4: Advanced Python Concepts",
            "Found 3 courses discussing Advanced Python Concepts"
        ]
        
        # Setup tools
        tools = [
            {"name": "get_course_outline", "description": "Get course outline"},
            {"name": "search_course_content", "description": "Search content"}
        ]
        
        # First response: get course outline
        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "get_course_outline"
        tool_use_1.input = {"course_name": "Course X"}
        tool_use_1.id = "tool_1"
        
        mock_first_response = Mock()
        mock_first_response.content = [tool_use_1]
        mock_first_response.stop_reason = "tool_use"
        
        # Second response: search based on first result
        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "search_course_content"
        tool_use_2.input = {"query": "Advanced Python Concepts"}
        tool_use_2.id = "tool_2"
        
        mock_second_response = Mock()
        mock_second_response.content = [tool_use_2]
        mock_second_response.stop_reason = "tool_use"
        
        # Third response: final answer after 2 rounds
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Based on my search, the following courses discuss the same topic as lesson 4...")]
        mock_final_response.stop_reason = "end_turn"
        
        # Configure mock client
        self.mock_client.messages.create.side_effect = [
            mock_first_response,
            mock_second_response,
            mock_final_response  # After max rounds, makes final call without tools
        ]
        
        # Generate response
        result = self.ai_generator.generate_response(
            query="Find courses discussing the same topic as lesson 4 of Course X",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2
        )
        
        # Verify result
        self.assertIn("courses discuss the same topic", result)
        
        # Verify both tools were executed
        self.assertEqual(mock_tool_manager.execute_tool.call_count, 2)
        mock_tool_manager.execute_tool.assert_any_call("get_course_outline", course_name="Course X")
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="Advanced Python Concepts")
        
        # Verify three API calls were made
        self.assertEqual(self.mock_client.messages.create.call_count, 3)
        
        # Verify first two calls have tools enabled
        first_call = self.mock_client.messages.create.call_args_list[0][1]
        self.assertIn("tools", first_call)
        
        second_call = self.mock_client.messages.create.call_args_list[1][1]
        self.assertIn("tools", second_call)  # Tools still enabled in round 2!
        
        # Verify third call (after max rounds) has NO tools
        third_call = self.mock_client.messages.create.call_args_list[2][1]
        self.assertNotIn("tools", third_call)  # Final call without tools
    
    def test_sequential_tool_calls_natural_termination(self):
        """Test natural termination when AI doesn't need more tools"""
        # Setup mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Found comprehensive course information"
        
        # Setup tools
        tools = [{"name": "search_course_content", "description": "Search"}]
        
        # First response: tool use
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.name = "search_course_content"
        tool_use.input = {"query": "Python"}
        tool_use.id = "tool_1"
        
        mock_first_response = Mock()
        mock_first_response.content = [tool_use]
        mock_first_response.stop_reason = "tool_use"
        
        # Second response: no more tools needed (natural termination)
        mock_second_response = Mock()
        mock_second_response.content = [Mock(text="I found all the information needed.")]
        mock_second_response.stop_reason = "end_turn"  # No more tool use
        
        # Configure mock client
        self.mock_client.messages.create.side_effect = [
            mock_first_response,
            mock_second_response
        ]
        
        # Generate response
        result = self.ai_generator.generate_response(
            query="Search for Python courses",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2  # Could do 2 rounds but stops after 1
        )
        
        # Verify result
        self.assertEqual(result, "I found all the information needed.")
        
        # Verify only one tool was executed
        self.assertEqual(mock_tool_manager.execute_tool.call_count, 1)
        
        # Verify only two API calls (not three)
        self.assertEqual(self.mock_client.messages.create.call_count, 2)
    
    def test_handle_tool_execution_multiple_tools(self):
        """Test handling multiple tool calls in one response"""
        # Setup mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Search result 1",
            "Search result 2"
        ]
        
        # Setup response with multiple tool uses
        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "search_course_content"
        tool_use_1.input = {"query": "Python"}
        tool_use_1.id = "tool_1"
        
        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "get_course_outline"
        tool_use_2.input = {"course_name": "Python"}
        tool_use_2.id = "tool_2"
        
        text_content = Mock()
        text_content.type = "text"
        text_content.text = "Let me search for that..."
        
        mock_initial_response = Mock()
        mock_initial_response.content = [text_content, tool_use_1, tool_use_2]
        
        # Setup final response
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Combined results")]
        
        # Setup base params
        base_params = {
            "messages": [{"role": "user", "content": "test"}],
            "system": "test system",
            "tools": [{"name": "search_tool"}, {"name": "get_outline"}]  # Need tools in base_params
        }
        
        # Configure mock client
        self.mock_client.messages.create.return_value = mock_final_response
        
        # Execute (using new method name)
        result = self.ai_generator._handle_sequential_tool_execution(
            mock_initial_response,
            base_params,
            mock_tool_manager,
            max_rounds=2
        )
        
        # Verify result
        self.assertEqual(result, "Combined results")
        
        # Verify both tools were executed
        self.assertEqual(mock_tool_manager.execute_tool.call_count, 2)
        mock_tool_manager.execute_tool.assert_any_call("search_course_content", query="Python")
        mock_tool_manager.execute_tool.assert_any_call("get_course_outline", course_name="Python")
    
    def test_sequential_tool_calls_max_rounds_limit(self):
        """Test that tool calling stops after max_rounds even if AI wants more"""
        # Setup mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "First tool result",
            "Second tool result"
        ]
        
        # Setup tools
        tools = [{"name": "search_tool", "description": "Search"}]
        
        # All responses want to use tools
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.name = "search_tool"
        tool_use.input = {"query": "test"}
        tool_use.id = "tool_id"
        
        mock_tool_response = Mock()
        mock_tool_response.content = [tool_use]
        mock_tool_response.stop_reason = "tool_use"
        
        # Final response after forced termination
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final answer after 2 rounds")]
        
        # Configure mock client
        self.mock_client.messages.create.side_effect = [
            mock_tool_response,  # Round 1
            mock_tool_response,  # Round 2 (still wants tools)
            mock_final_response  # Forced final call without tools
        ]
        
        # Generate response with max_rounds=2
        result = self.ai_generator.generate_response(
            query="Complex query",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=2
        )
        
        # Verify result
        self.assertEqual(result, "Final answer after 2 rounds")
        
        # Verify exactly 2 tools were executed (not more)
        self.assertEqual(mock_tool_manager.execute_tool.call_count, 2)
        
        # Verify exactly 3 API calls
        self.assertEqual(self.mock_client.messages.create.call_count, 3)
        
        # Verify last call has no tools
        last_call = self.mock_client.messages.create.call_args_list[2][1]
        self.assertNotIn("tools", last_call)
    
    def test_generate_response_tool_error_handling(self):
        """Test error handling when tool execution fails"""
        # Setup mock tool manager that raises exception
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool execution failed")
        
        # Setup tools
        tools = [{"name": "search_tool", "description": "Search", "input_schema": {}}]
        
        # Setup response with tool use
        mock_tool_use = Mock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.name = "search_tool"
        mock_tool_use.input = {"query": "test"}
        mock_tool_use.id = "tool_123"
        
        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_use]
        mock_initial_response.stop_reason = "tool_use"
        
        self.mock_client.messages.create.return_value = mock_initial_response
        
        # Generate response and expect exception to propagate
        with self.assertRaises(Exception) as context:
            self.ai_generator.generate_response(
                query="Test query",
                conversation_history=None,
                tools=tools,
                tool_manager=mock_tool_manager
            )
        
        self.assertIn("Tool execution failed", str(context.exception))
    
    def test_system_prompt_structure(self):
        """Test that system prompt is correctly structured"""
        # Verify system prompt constant
        self.assertIn("AI assistant specialized in course materials", AIGenerator.SYSTEM_PROMPT)
        self.assertIn("search_course_content", AIGenerator.SYSTEM_PROMPT)
        self.assertIn("get_course_outline", AIGenerator.SYSTEM_PROMPT)
        self.assertIn("Tool Usage Guidelines", AIGenerator.SYSTEM_PROMPT)
    
    def test_backward_compatibility_max_rounds_one(self):
        """Test that setting max_tool_rounds=1 behaves like old implementation"""
        # Setup mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"
        
        # Setup tools
        tools = [{"name": "tool", "description": "Tool"}]
        
        # First response: tool use
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.name = "tool"
        tool_use.input = {"param": "value"}
        tool_use.id = "tool_1"
        
        mock_first_response = Mock()
        mock_first_response.content = [tool_use]
        mock_first_response.stop_reason = "tool_use"
        
        # Second response: forced final without tools
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final response")]
        
        # Configure mock client
        self.mock_client.messages.create.side_effect = [
            mock_first_response,
            mock_final_response
        ]
        
        # Generate response with max_tool_rounds=1 (old behavior)
        result = self.ai_generator.generate_response(
            query="Query",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_tool_rounds=1  # Explicitly set to 1
        )
        
        # Verify result
        self.assertEqual(result, "Final response")
        
        # Verify only one tool executed
        self.assertEqual(mock_tool_manager.execute_tool.call_count, 1)
        
        # Verify second call has NO tools (matches old behavior)
        second_call = self.mock_client.messages.create.call_args_list[1][1]
        self.assertNotIn("tools", second_call)
    
    def test_api_params_structure(self):
        """Test API parameters are correctly structured"""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Response")]
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response
        
        # Generate response with tools
        tools = [{"name": "test_tool"}]
        self.ai_generator.generate_response(
            query="Test",
            tools=tools,
            tool_manager=None
        )
        
        # Check API call structure
        call_args = self.mock_client.messages.create.call_args[1]
        
        # Verify base params are included
        self.assertEqual(call_args["model"], "test_model")
        self.assertEqual(call_args["temperature"], 0)
        self.assertEqual(call_args["max_tokens"], 800)
        
        # Verify message structure
        self.assertEqual(call_args["messages"][0]["role"], "user")
        self.assertEqual(call_args["messages"][0]["content"], "Test")
        
        # Verify tools are included
        self.assertEqual(call_args["tools"], tools)
        self.assertEqual(call_args["tool_choice"], {"type": "auto"})


if __name__ == "__main__":
    unittest.main()