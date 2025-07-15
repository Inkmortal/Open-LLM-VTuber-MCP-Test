# Product Context: Open-LLM-VTuber MCP Integration

## Why This Project Exists

### Current State
Open-LLM-VTuber is a voice-interactive AI companion with a Live2D avatar that can:
- Engage in real-time voice conversations
- Display emotions through Live2D expressions
- Process visual input (camera, screenshots)
- Run completely offline with local models
- Support multiple LLM backends

### The Gap
Currently, the VTuber is limited to conversational interactions. It cannot:
- Access real-time information from the web
- Interact with external systems or APIs
- Perform actions on behalf of the user
- Write or modify code autonomously
- Access and manage project management tools

### The Solution: MCP Integration
By integrating MCP (Model Context Protocol), we transform the VTuber from a conversational companion into an agentic assistant that can:
- Perform web searches during conversations
- Help manage Jira tickets while discussing projects
- Read and write files to assist with documentation
- Use Claude Code to help with programming tasks
- Extend capabilities through additional MCP servers

## User Experience Vision

### Before MCP Integration
```
User: "What's the weather like in Tokyo?"
VTuber: "I don't have access to current weather information."
```

### After MCP Integration
```
User: "What's the weather like in Tokyo?"
VTuber: *searches web* "Let me check that for you... Currently in Tokyo, it's 22°C with partly cloudy skies."
```

### Advanced Scenarios
```
User: "Can you help me fix the bug in my Python script?"
VTuber: *reads file* "I see the issue in your script. Let me fix it for you." *uses Claude Code to debug and fix*
```

## How It Should Work

### Architecture Flow
1. **User Input** → VTuber receives voice/text input
2. **Intent Recognition** → Agent determines if tools are needed
3. **Tool Selection** → Agent selects appropriate MCP server/tool
4. **Tool Execution** → MCP protocol handles tool interaction
5. **Response Integration** → Results integrated into conversation
6. **User Feedback** → Response delivered via voice/display

### Key Behaviors
- **Seamless Integration**: Tool usage should feel natural, not jarring
- **Transparency**: Users should understand what actions are being taken
- **Interruptibility**: Users can interrupt tool operations like conversations
- **Personality Preservation**: VTuber maintains character while using tools
- **Error Handling**: Graceful degradation when tools fail

## Target Users
1. **Developers**: Using VTuber as a coding assistant
2. **Project Managers**: Managing tasks through natural conversation
3. **Researchers**: Getting real-time information during discussions
4. **Power Users**: Automating workflows through voice commands

## Success Metrics
- Successful tool invocations per conversation
- User satisfaction with tool integration
- Reduction in "I can't do that" responses
- Increased session duration due to enhanced capabilities