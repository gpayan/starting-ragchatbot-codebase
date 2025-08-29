# User Query Flow Diagram

## Complete Query Processing Flow

```mermaid
graph TD
    %% Frontend Layer
    User[User] -->|Types query| Input[Input Field<br/>index.html:59-64]
    Input -->|Enter/Click| SendBtn[Send Button<br/>script.js:27-30]
    SendBtn -->|Triggers| SendMsg[sendMessage()<br/>script.js:45]
    
    %% Frontend Processing
    SendMsg -->|Creates POST| Request[POST /api/query<br/>script.js:63-72<br/>Body: {query, session_id}]
    SendMsg -->|Shows| Loading[Loading Animation<br/>script.js:58-60]
    
    %% Backend API Layer
    Request -->|FastAPI| QueryEndpoint[/api/query<br/>app.py:56]
    QueryEndpoint -->|Check session| SessionCheck{session_id<br/>exists?<br/>app.py:61}
    SessionCheck -->|No| CreateSession[session_manager.create_session()<br/>app.py:63]
    SessionCheck -->|Yes| UseSession[Use existing session]
    CreateSession -->|Generate ID| SessionID[session_123<br/>session_manager.py:20-21]
    SessionID --> RAGQuery
    UseSession --> RAGQuery
    
    %% RAG System Layer
    RAGQuery[rag_system.query()<br/>rag_system.py:102]
    RAGQuery -->|Get history| History[session_manager.get_conversation_history()<br/>rag_system.py:119]
    RAGQuery -->|Call AI| AIGen[ai_generator.generate_response()<br/>rag_system.py:122-127]
    
    %% AI Generation with Tools
    AIGen -->|Prepare| ClaudeCall[Claude API Call<br/>ai_generator.py:80]
    ClaudeCall -->|Tool decision| ToolCheck{Uses search<br/>tool?}
    
    %% Tool Execution Path
    ToolCheck -->|Yes| ToolExec[CourseSearchTool.execute()<br/>search_tools.py:52]
    ToolExec -->|Search| VectorSearch[vector_store.search()<br/>vector_store.py:61]
    VectorSearch -->|Query ChromaDB| ChromaDB[(ChromaDB<br/>Collections:<br/>- course_catalog<br/>- course_content)]
    ChromaDB -->|Results| SearchResults[SearchResults<br/>vector_store.py:17]
    SearchResults -->|Format| FormatResults[Format results<br/>search_tools.py:88]
    FormatResults -->|Return to AI| ToolResult[Tool results<br/>ai_generator.py:108-120]
    
    %% Direct Response Path
    ToolCheck -->|No| DirectResponse[Direct AI response<br/>ai_generator.py:87]
    
    %% Final Response Generation
    ToolResult -->|Second API call| FinalGen[Final Claude response<br/>ai_generator.py:134]
    DirectResponse --> ResponseGen
    FinalGen --> ResponseGen
    
    %% Response Processing
    ResponseGen[Generate Response<br/>+ Track sources]
    ResponseGen -->|Update history| UpdateSession[session_manager.add_exchange()<br/>rag_system.py:137]
    ResponseGen -->|Return| APIResponse[QueryResponse<br/>app.py:68-72<br/>{answer, sources, session_id}]
    
    %% Frontend Response Handling
    APIResponse -->|JSON response| JSReceive[JavaScript receives<br/>script.js:75]
    JSReceive -->|Remove loading| RemoveLoad[Remove loading<br/>script.js:84]
    JSReceive -->|Parse markdown| Markdown[marked.parse()<br/>script.js:120]
    JSReceive -->|Update session| StoreSession[currentSessionId<br/>script.js:80]
    Markdown -->|Display| ShowMsg[Display message<br/>script.js:113-136]
    ShowMsg -->|If sources exist| ShowSources[Show sources<br/>script.js:124-130]
    ShowMsg -->|Scroll view| ScrollView[Auto-scroll<br/>script.js:135]
    
    %% Styling
    classDef frontend fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef backend fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef ai fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef storage fill:#e8f5e9,stroke:#1b5e20,stroke-width:2px
    classDef process fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    
    class User,Input,SendBtn,SendMsg,Request,Loading,JSReceive,RemoveLoad,Markdown,ShowMsg,ShowSources,ScrollView,StoreSession frontend
    class QueryEndpoint,SessionCheck,CreateSession,UseSession,SessionID,RAGQuery,History,UpdateSession,APIResponse backend
    class AIGen,ClaudeCall,ToolCheck,DirectResponse,FinalGen,ResponseGen ai
    class ToolExec,VectorSearch,ChromaDB,SearchResults,FormatResults,ToolResult process
    class ChromaDB storage
```

## Key Components

### 1. **Frontend Layer** (Blue)
- User interface components
- JavaScript event handlers
- API communication
- Response rendering

### 2. **Backend API Layer** (Orange)
- FastAPI endpoints
- Session management
- Request/response handling
- RAG system orchestration

### 3. **AI Generation Layer** (Purple)
- Claude API integration
- Tool decision making
- Response generation
- Context management

### 4. **Processing Layer** (Pink)
- Tool execution
- Vector search operations
- Result formatting
- Source tracking

### 5. **Storage Layer** (Green)
- ChromaDB vector database
- Course catalog collection
- Course content collection
- Semantic search

## Data Flow Summary

1. **Query Input**: User types question → JavaScript captures input
2. **API Request**: Frontend sends POST to `/api/query` with query and session_id
3. **Session Management**: Backend creates/retrieves session for context
4. **RAG Processing**: Query processed through RAG system with conversation history
5. **AI Decision**: Claude decides whether to use search tool based on query
6. **Tool Execution**: If needed, searches vector database for relevant content
7. **Response Generation**: Claude generates final response using search results
8. **Session Update**: Conversation history updated with new exchange
9. **Frontend Display**: Response rendered as markdown with sources

## Key Files and Line References

- **Frontend entry**: `frontend/script.js:45` (sendMessage function)
- **API endpoint**: `backend/app.py:56` (/api/query route)
- **RAG orchestration**: `backend/rag_system.py:102` (query method)
- **AI generation**: `backend/ai_generator.py:43` (generate_response)
- **Tool execution**: `backend/search_tools.py:52` (execute method)
- **Vector search**: `backend/vector_store.py:61` (search method)
- **Session creation**: `backend/session_manager.py:18` (create_session)