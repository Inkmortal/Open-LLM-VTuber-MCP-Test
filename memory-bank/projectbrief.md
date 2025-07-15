# Project Brief: Open-LLM-VTuber MCP Integration

## Project Overview
This project aims to enhance the Open-LLM-VTuber application by integrating MCP (Model Context Protocol) to enable agentic capabilities for the AI VTuber, allowing it to access external tools and perform actions beyond conversation.

## Core Requirements

### 1. MCP Integration
- Integrate MCP protocol into the Open-LLM-VTuber architecture
- Enable the VTuber to access MCP servers for tool usage
- Support multiple MCP server connections simultaneously

### 2. Tool Access Requirements
The VTuber should be able to access:
- **Web Search**: Search the internet for current information
- **Jira Integration**: Create, update, and query Jira tickets
- **File System Access**: Read/write local files with proper permissions
- **Claude Code SDK**: Utilize Claude Code agentically for coding tasks
- **Future Extensions**: Architecture should support easy addition of new MCP tools

### 3. Technical Constraints
- Must maintain compatibility with existing VTuber features (voice, Live2D, etc.)
- Should work with all supported LLM backends
- Performance should not significantly degrade real-time conversation
- Tool usage should be interruptible like normal conversations

### 4. User Experience Goals
- Tool usage should feel natural within conversations
- Visual/audio feedback when tools are being used
- Clear indication of what actions the VTuber is taking
- Maintain the personality and character during tool usage

## Success Criteria
1. VTuber can successfully connect to and use MCP servers
2. At least 3 core tools (web search, file system, Claude Code) are functional
3. Tool usage integrates seamlessly with conversation flow
4. System remains stable and performant during tool operations
5. Configuration is simple and well-documented

## Out of Scope
- Modifying core Live2D rendering system
- Changing existing ASR/TTS functionality
- Creating new MCP servers (will use existing ones)
- Major UI/UX redesign