# System Patterns: Open-LLM-VTuber Architecture

## Current Architecture Overview

### Core Components

#### 1. WebSocket Server (`server.py`, `websocket_handler.py`)
- FastAPI-based WebSocket server
- Handles client connections and message routing
- Manages conversation state and audio streaming
- Routes: health check, WebSocket endpoint, static files

#### 2. Agent System (`agent/`)
- **AgentInterface**: Base interface for all agents
- **BasicMemoryAgent**: Default agent with conversation memory
- **Stateless LLMs**: Modular LLM providers (OpenAI, Claude, Ollama, etc.)
- Transformer pipeline for text processing

#### 3. Message Flow
```
User Input → WebSocket → Message Handler → Agent → LLM → Response Pipeline → TTS → Audio Stream
```

#### 4. Processing Pipeline (`transformers.py`)
- **sentence_divider**: Splits LLM output into sentences (must include all valid tags)
- **actions_extractor**: Extracts Live2D expressions ([emotion] format only)
- **display_processor**: Formats text for display (tag precedence is critical)
- **tts_filter**: Prepares text for speech synthesis (filters angle brackets, asterisks, etc.)

## MCP Integration Points

### 1. Agent Layer Integration
The most natural integration point is within the Agent system:
- Extend `AgentInterface` to support tool usage
- Create `MCPAgent` that inherits from `BasicMemoryAgent`
- Add MCP client initialization and management
- Integrate tool calls into the chat pipeline

### 2. Message Handler Extension
Extend message types to support MCP operations:
- Add MCP-specific message types (tool-request, tool-response)
- Handle async tool execution
- Provide feedback during long-running operations

### 3. Configuration Integration
Add MCP configuration to the YAML structure:
```yaml
mcp_config:
  enabled: true
  servers:
    - name: filesystem
      command: "mcp-server-filesystem"
      args: ["--root", "/permitted/path"]
    - name: web_search
      url: "http://localhost:8080"
```

## Design Patterns for MCP Integration

### 1. Tool Decision Pattern
```python
class MCPAgent(BasicMemoryAgent):
    async def _should_use_tool(self, message: str) -> Optional[ToolDecision]:
        # Analyze message for tool requirements
        # Return tool name and parameters if needed
```

### 2. Async Tool Execution Pattern
```python
async def _execute_tool(self, tool: str, params: dict) -> ToolResult:
    # Execute MCP tool asynchronously
    # Handle timeouts and errors
    # Return structured result
```

### 3. Response Integration Pattern
- Tool results should be integrated into the conversation naturally
- Maintain streaming capability for real-time feedback
- Preserve Live2D expressions during tool usage

### 4. Interrupt Handling Pattern
- Tool operations should be interruptible
- Clean up resources on interruption
- Inform user of interrupted operations

## Component Relationships

### Current Flow
```
WebSocketHandler
    ↓
MessageHandler
    ↓
ConversationHandler
    ↓
Agent (BasicMemoryAgent)
    ↓
StatelessLLM
    ↓
Response Pipeline
```

### With MCP Integration
```
WebSocketHandler
    ↓
MessageHandler
    ↓
ConversationHandler
    ↓
MCPAgent (extends BasicMemoryAgent)
    ↓                    ↓
StatelessLLM         MCP Client
    ↓                    ↓
    └──── Tool Decision ──┘
             ↓
      Response Pipeline
```

## Key Architectural Decisions

### 1. Agent-Level Integration
- MCP functionality lives in a specialized agent
- Preserves modularity and backward compatibility
- Allows easy enable/disable of MCP features

### 2. Async-First Design
- All MCP operations are async
- Non-blocking tool execution
- Maintains real-time conversation flow

### 3. Configuration-Driven
- MCP servers configured in YAML
- No hardcoded tool dependencies
- Easy addition/removal of capabilities

### 4. Graceful Degradation
- System continues working if MCP fails
- Clear error messages to users
- Fallback to conversation-only mode

## Implementation Learnings

### Critical Discoveries
1. **Tag Processing Order Matters**
   - Display processor must check thought tags BEFORE other tags
   - Tag precedence prevents display override issues
   - All tags must be registered in sentence_divider's valid_tags

2. **Live2D vs Action Descriptions**
   - Live2D uses [emotion] format, not asterisks
   - Action descriptions (*action* or ::action::) are non-functional
   - Only emotions in emotionMap actually trigger model expressions

3. **MCP Session Management**
   - ClientSession must be used as async context manager
   - Message loop won't start without proper initialization
   - Tool results need careful serialization handling

4. **Streaming vs Tool Execution**
   - Multi-turn tool calling requires passing tools in summary phase
   - Empty tool_call_id from Gemini needs ID generation
   - Recursive tool execution enables complex workflows

### Best Practices
- Keep thoughts extremely brief to avoid verbose output
- Use tag-based separation for clean content filtering
- Prioritize functional behavior over perfect autonomy
- Test with real MCP servers early to catch integration issues

## MCP Server Integration Patterns

### Schema Compatibility
1. **Gemini API Limitations**
   - Cannot handle FastMCP's anyOf schemas directly
   - Requires schema simplification before sending to API
   - Solution: Extract non-null option from anyOf arrays

2. **Enum Handling**
   - Avoid empty strings in Literal types
   - Use Optional[Literal[...]] instead of Literal[..., ""]
   - Update logic to check for None instead of empty strings

### Configuration Patterns
1. **Path Handling**
   - Always use forward slashes in YAML, even on Windows
   - MCP servers need absolute paths to executables
   - Environment variables can be empty dict {} or specific values

2. **Server Types**
   - stdio: Local executables (npx, python scripts, node)
   - sse: HTTP-based servers (not yet tested)

### Debug Patterns
1. **Tool Execution Verification**
   - Log tool names, arguments, and results
   - Track execution flow through MCP client manager
   - Distinguish between model hallucination and actual execution

2. **Connection Debugging**
   - 10-second timeout indicates server not responding
   - Check if command exists and is executable
   - Verify server implements MCP protocol correctly