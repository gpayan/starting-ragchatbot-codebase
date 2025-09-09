import anthropic
from typing import List, Optional, Dict, Any

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

Available Tools:
1. **search_course_content**: For finding specific information within course materials
   - Use for content-related questions, concepts, examples, and detailed explanations
   - Can filter by course name and lesson number
   
2. **get_course_outline**: For retrieving complete course structure
   - Use for questions about course organization, lesson lists, or course overview
   - Returns course title, link, instructor, and complete lesson listing
   - When asked about course outline/structure, ALWAYS return the full information including:
     - Course title
     - Course link
     - Lesson numbers and titles for all lessons

Tool Usage Guidelines:
- **Outline queries**: Use get_course_outline for questions about course structure, lesson lists, or what's covered
- **Content queries**: Use search_course_content for specific topics, concepts, or detailed information
- **Sequential searching**: You can make up to 2 rounds of tool calls to refine your search
- **Iterative refinement**: Use results from previous searches to inform subsequent searches
- If a tool yields no results, try a different search approach or state this clearly

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **No meta-commentary**: Provide direct answers only — no reasoning process or tool explanations


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Complete** - For outline queries, include all course structure details
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None,
                         max_tool_rounds: int = 2) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_tool_rounds: Maximum number of sequential tool calling rounds (default 2)
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }
        
        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}
        
        # Get response from Claude
        response = self.client.messages.create(**api_params)
        
        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            return self._handle_sequential_tool_execution(response, api_params, tool_manager, max_tool_rounds)
        
        # Return direct response
        return response.content[0].text
    
    def _handle_sequential_tool_execution(self, initial_response, base_params: Dict[str, Any], 
                                          tool_manager, max_rounds: int = 2):
        """
        Handle sequential execution of tool calls with up to max_rounds iterations.
        
        Args:
            initial_response: The response containing initial tool use requests
            base_params: Base API parameters including tools
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool calling rounds (default 2)
            
        Returns:
            Final response text after tool execution rounds
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        current_response = initial_response
        
        for round_num in range(1, max_rounds + 1):
            # Add AI's response with tool use
            messages.append({"role": "assistant", "content": current_response.content})
            
            # Execute all tool calls and collect results
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    tool_result = tool_manager.execute_tool(
                        content_block.name, 
                        **content_block.input
                    )
                    
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": content_block.id,
                        "content": tool_result
                    })
            
            # Add tool results as single message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})
            
            # Check if we've reached max rounds
            if round_num >= max_rounds:
                # Final call without tools to get response
                final_params = {
                    **self.base_params,
                    "messages": messages,
                    "system": base_params["system"]
                }
                final_response = self.client.messages.create(**final_params)
                return final_response.content[0].text
            
            # Otherwise, make next API call WITH tools still enabled
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                "tools": base_params.get("tools"),  # Keep tools available!
                "tool_choice": {"type": "auto"}
            }
            
            # Get next response
            current_response = self.client.messages.create(**next_params)
            
            # Check for natural termination (no more tool use)
            if current_response.stop_reason != "tool_use":
                # Natural termination - no more tools needed
                return current_response.content[0].text
        
        # Shouldn't reach here, but return last response just in case
        return current_response.content[0].text