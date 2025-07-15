# Technical Context: Open-LLM-VTuber Development Environment

## Technology Stack

### Core Technologies
- **Python 3.11+**: Primary language
- **FastAPI**: WebSocket server framework
- **Uvicorn**: ASGI server
- **asyncio**: Async programming
- **Pydantic**: Data validation
- **Loguru**: Logging

### Package Management
- **UV**: Fast Python package manager (replaced pip)
- **pyproject.toml**: Project configuration
- **uv.lock**: Dependency lock file

### Frontend
- **HTML/JavaScript**: Web interface
- **WebSocket API**: Real-time communication
- **Live2D SDK**: Avatar rendering
- **Web Audio API**: Audio processing

## Development Setup

### Directory Structure
```
Open-LLM-VTuber-MCP-Test/
├── src/open_llm_vtuber/    # Main source code
│   ├── agent/              # Agent implementations
│   ├── asr/                # Speech recognition
│   ├── tts/                # Text-to-speech
│   ├── config_manager/     # Configuration handling
│   └── conversations/      # Conversation management
├── memory-bank/            # Project documentation
├── characters/             # Character configurations
├── live2d-models/          # Live2D model files
├── web_tool/              # Frontend files
├── conf.yaml              # Main configuration
└── run_server.py          # Entry point
```

### Configuration System
- YAML-based configuration
- Hot-swappable character configs
- Environment variable support
- Config validation on startup

## MCP Technical Requirements

### MCP SDK
- Need to integrate MCP Python SDK
- Support for MCP server discovery
- Handle MCP protocol messages
- Manage server lifecycle

### Dependencies to Add
```toml
[dependencies]
mcp-sdk = "^0.1.0"  # Or appropriate version
httpx = "^0.24.0"   # For HTTP-based MCP servers
```

### Integration Considerations

#### 1. Async Compatibility
- MCP operations must be async
- Integrate with existing asyncio event loop
- Handle concurrent tool requests

#### 2. Error Handling
- Timeout handling for tool operations
- Graceful failure recovery
- User-friendly error messages

#### 3. Security
- Sandbox file system access
- Validate tool permissions
- Audit tool usage

#### 4. Performance
- Tool calls shouldn't block conversation
- Efficient message serialization
- Connection pooling for MCP servers

## Development Tools

### Current Tools
- **Git**: Version control
- **Ruff**: Python linter/formatter
- **Pre-commit**: Git hooks
- **GitHub Actions**: CI/CD

### Testing Approach
- Unit tests for MCP client
- Integration tests for tool usage
- Mock MCP servers for testing
- End-to-end conversation tests

## Deployment Considerations

### Local Development
```bash
uv run run_server.py --verbose
```

### Production
- Docker support available
- HTTPS configuration for remote access
- Environment-specific configs

## Technical Constraints

### Performance Requirements
- Sub-second response for tool decisions
- Streaming responses during tool execution
- Memory efficient for long conversations

### Compatibility
- Must work with all existing LLM providers
- Support all current ASR/TTS modules
- Maintain WebSocket protocol compatibility

### Security Boundaries
- File system access restrictions
- Network request limitations
- Credential management for MCP servers