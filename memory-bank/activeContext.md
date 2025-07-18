# Active Context: MCP Integration Development

## Current Status
- ✅ Explored and understood Open-LLM-VTuber architecture
- ✅ Learned about MCP (Model Context Protocol) capabilities
- ✅ Identified integration points in the codebase
- ✅ Created initial memory bank documentation
- ✅ **Implemented core MCP integration** (2025-07-09)
- ✅ **Fixed all major issues and improved UX** (2025-07-09)
- ✅ **MCP Integration at Acceptable Levels** (2025-07-09)
- Room for improvement in autonomous tool usage

## Recent Fixes & Improvements (2025-07-09)

### Major Issues Resolved
1. **MCP Server Connection Hanging** ✅
   - Fixed: ClientSession needs to be used as context manager
   - Added: `await self.exit_stack.enter_async_context(ClientSession(read, write))`

2. **Tool Attribute Compatibility** ✅
   - Fixed: Handle both `input_schema` and `inputSchema`
   - Changed WSL paths to Windows paths in config

3. **CallToolResult Serialization** ✅
   - Fixed: Extract content from MCP SDK's CallToolResult objects
   - Added proper content extraction logic

4. **Empty Tool Call IDs** ✅
   - Fixed: Generate IDs when Gemini API provides empty strings
   - Format: `call_{index}_{tool_name}`

5. **Multi-Turn Tool Calling** ✅
   - Fixed: Pass tools parameter in summary phase
   - Enabled recursive tool execution

### UX Improvements
1. **Tag-Based Content Separation** ✅
   - Added `<thought>` tags for internal reasoning (not spoken)
   - Added `<speak>` tags for user-facing content (spoken)
   - Modified transformers to handle new tags

2. **Proactive Agent Behavior** ✅
   - Updated system prompt with "Proactive Mandate"
   - Added ALWAYS/NEVER behavioral principles
   - Changed thought formatting to bullet points
   - Removed third-person narration

3. **Display & Formatting Fixes** ✅
   - Fixed thought tag display by adding "thought" and "speak" to valid_tags
   - Removed action descriptions (::action::) as they were non-functional
   - Fixed asterisk filtering to preserve content while removing asterisk characters
   - Ensured thought content is completely hidden from users

### Architecture Understanding
1. **Agent System**: The VTuber uses an agent-based architecture with `AgentInterface` as the base
2. **Message Flow**: WebSocket → MessageHandler → Agent → LLM → Response Pipeline
3. **Extensibility**: System designed for modularity through interfaces and factories
4. **Configuration**: YAML-based config with support for multiple providers

### MCP Integration Strategy
Decided on agent-level integration approach:
- Create `MCPAgent` extending `BasicMemoryAgent`
- Add MCP configuration to YAML structure
- Implement tool decision and execution logic
- Maintain streaming and interrupt capabilities

## Implementation Complete

### What Was Built
1. **Enhanced OpenAI-Compatible LLM** ✅
   - Added function calling support to interface
   - Streaming tool call aggregation
   - Graceful fallback for unsupported providers

2. **MCP Client Manager** ✅
   - Generic support for all MCP servers
   - Tool namespacing (server.tool_name)
   - Proper session lifecycle management

3. **MCPAgent** ✅
   - Seamless extension of BasicMemoryAgent
   - Two-phase interaction (tools then summary)
   - Natural language responses for tool results

4. **Integration** ✅
   - Agent factory registration
   - Service context initialization
   - Configuration already in place

## Remaining Improvements

### Agent Intelligence
While the MCP integration is functional, the agent could be smarter in:
1. **Tool Discovery**: Agent should explore available tools more proactively
2. **Query Construction**: Better at inferring parameters and constructing queries
3. **Error Recovery**: Try alternative approaches when first attempt fails
4. **Context Inference**: Better at understanding implicit context from user requests
5. **Multi-Step Planning**: Plan complex sequences without user guidance

### Examples of Current Limitations
- Agent asks for clarification instead of trying different queries
- Doesn't always chain tools effectively (e.g., get user info then search)
- Could be more creative in problem-solving approaches
- Sometimes gives up too easily when initial approach fails

## Next Steps

### Enhancement Opportunities
1. **Install Dependencies**
   - Install mcp Python package
   - Verify Node.js and npx are available

2. **Test Basic Functionality**
   - File system access via filesystem server
   - Jira access via atlassian server
   - Verify tool calls don't reach TTS

3. **Error Scenarios**
   - Test with unavailable MCP servers
   - Test with invalid tool arguments
   - Verify graceful degradation

### Design Decisions Made
1. **Agent-Level Integration**: MCP functionality lives in specialized agent to maintain modularity
2. **Async-First**: All MCP operations will be async to maintain real-time flow
3. **Configuration-Driven**: MCP servers defined in YAML for flexibility
4. **Graceful Degradation**: System continues working if MCP fails

## Key Insights

### Technical Patterns
- The codebase uses decorators extensively for pipeline processing
- Async generators are used for streaming responses
- Factory pattern used for creating different implementations
- Strong separation between stateless LLMs and stateful agents

### Integration Opportunities
- Can leverage existing transformer pipeline for tool responses
- WebSocket infrastructure supports additional message types
- Configuration system easily extends for MCP settings
- Interrupt handling mechanism can be reused for tool cancellation

### Potential Challenges
1. **Streaming vs Tool Execution**: Need to maintain streaming while executing tools
2. **Context Length**: Tool results might increase context significantly
3. **UI Feedback**: Need clear indication of tool usage in Live2D model
4. **Error Recovery**: Complex error scenarios with multiple tool failures

## Project Context
This is a personal project to enhance the Open-LLM-VTuber with agentic capabilities. The main goal is to transform the VTuber from a conversational companion into an AI assistant that can perform actions through MCP tools while maintaining its personality and real-time interaction capabilities.

## Teams Meeting Bot Development (2025-01-15)

### Architecture Finalized
After extensive research and consultation:
1. **Three-Channel Monitoring**
   - Audio: OpenWakeWord for activation only
   - Chat: Graph API for @mentions
   - Captions: DOM scraping for context

2. **Audio/Video Pipeline**
   - PulseAudio for dynamic audio routing
   - v4l2loopback for virtual camera
   - Live avatar rendering via HTML/WebSocket

3. **Implementation Approach**
   - Meeting bot as WebSocket client to existing server
   - Docker container with Playwright
   - Phased implementation starting with audio/video POC

See `meetingBotArchitecture.md` for complete details.

## Meeting Bot POC - Virtual Camera Implementation (2025-07-17)

### WebGL Rendering Issue Resolved ✅
Successfully fixed the VTuber character rendering issue in Docker container:

1. **Problem**: VTuber background rendered but Live2D character model was missing
   - Root cause: WebGL context failed without GPU in containerized environment
   - Live2D requires WebGL for character model rendering

2. **Solution**: Hybrid approach combining Mesa environment variables and Chrome flags
   - Environment variables:
     - `LIBGL_ALWAYS_SOFTWARE=1` - Forces software rendering
     - `GALLIUM_DRIVER=llvmpipe` - Uses Mesa's software rasterizer
     - `MESA_GL_VERSION_OVERRIDE=4.5` - Specifies OpenGL version
   - Chrome flags:
     - `--use-gl=swiftshader` - Force SwiftShader software renderer
     - `--enable-webgl` - Explicitly enable WebGL
     - `--ignore-gpu-blocklist` - Override GPU detection

3. **Implementation**: Created `run_virtual_camera_hybrid.py`
   - Combines Mesa environment setup with comprehensive Chrome flags
   - Successfully enables WebGL 1.0 and 2.0 in containerized environment
   - Virtual camera now streams VTuber with fully rendered character

### Virtual Camera POC Complete ✅
Successfully implemented canvas-based virtual camera injection:
1. **No kernel modules needed** - Pure JavaScript injection approach
2. **WebSocket proxy** - Forwards localhost:12393 to Windows host
3. **Frame streaming** - 30 FPS JPEG frames via base64 encoding
4. **Full viewport capture** - 1280x720 VTuber page scaled to 640x480
5. **HTTP server** - Serves demo page for secure context (navigator.mediaDevices)

### Key Learnings
1. **Secure context required** - navigator.mediaDevices needs HTTPS or localhost
2. **WebGL in containers** - Requires careful configuration of software rendering
3. **SwiftShader** - Google's software renderer works well for WebGL in headless environments
4. **Mesa libraries** - Already included in Ubuntu base image, just need proper environment setup