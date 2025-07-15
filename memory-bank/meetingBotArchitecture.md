# Teams Meeting Bot Architecture

## Overview
The Teams Meeting Bot enables the VTuber (Mili) to join Microsoft Teams meetings as a full participant with video avatar, audio capabilities, and intelligent interaction. The bot leverages the existing VTuber infrastructure as a WebSocket client while adding meeting-specific capabilities.

## Core Architecture

### 1. Meeting Bot as WebSocket Client
The meeting bot connects to the existing VTuber server as a specialized client, reusing all existing infrastructure:
- MCPAgent for tool execution
- TTS/ASR engines for speech
- Conversation management
- Message routing

```
Teams Meeting ←→ Meeting Bot Container ←→ VTuber Server
                  (Docker + Playwright)     (Existing)
```

### 2. Three-Channel Monitoring System

#### Audio Channel (Activation Detection)
- **Purpose**: Wake word detection only (not full transcription)
- **Technology**: OpenWakeWord (FOSS, Apache 2.0 license)
- **Audio Source**: Browser tab audio via PulseAudio virtual sink
- **Activation**: Detects character name variations ("Mili", "Millie", etc.)

#### Chat Channel (Reliable Commands)
- **Purpose**: Monitor @mentions and text commands
- **Technology**: Microsoft Graph API
- **Authentication**: Service principal with delegated permissions
- **Polling**: Every 2 seconds (webhooks for future optimization)

#### Caption Channel (Meeting Context)
- **Purpose**: Capture meeting transcript with speaker names
- **Technology**: DOM scraping of Teams live captions
- **Selectors**: Resilient selectors (aria-labels, data-testid)
- **Storage**: Rolling 15-minute buffer + key points extraction

### 3. Audio/Video Pipeline

#### Audio Flow (TTS Output)
```
TTS Engine → Audio File → PulseAudio Sink → module-loopback → Virtual Source → Browser Mic
```

#### Video Flow (Avatar Display)
```
Avatar Renderer → HTML Canvas → Frame Capture → v4l2loopback → Virtual Camera → Browser
```

## Technical Components

### Docker Container Setup
- Base: Playwright Python image
- Audio: PulseAudio with virtual devices
- Video: v4l2loopback kernel module
- Access: VNC server for debugging/monitoring

### PulseAudio Configuration
```bash
# Create virtual audio sink for TTS output
load-module module-null-sink sink_name=vtuber_audio_sink

# Create virtual microphone from sink monitor
load-module module-remap-source source_name=vtuber_mic master=vtuber_audio_sink.monitor
```

### Video Pipeline
1. Local HTML page renders avatar via WebSocket commands
2. ffmpeg captures browser window
3. Pipes frames to v4l2loopback device (/dev/video9)
4. Browser uses virtual camera for Teams

### DOM Scraping Strategy
- Selector configuration in YAML/JSON
- Fallback selector chains
- Health monitoring for UI changes
- MutationObserver for real-time updates

## Implementation Phases

### Phase 1: Audio/Video POC (Highest Risk)
- Build Docker container with PulseAudio + v4l2loopback
- Test audio routing: TTS file → Virtual mic → Browser
- Test video routing: HTML canvas → Virtual camera → Browser
- Validate on https://webcammictest.com/

### Phase 2: Caption Scraping
- Analyze Teams DOM structure
- Implement resilient selector strategy
- Build MutationObserver-based monitor
- Test caption extraction accuracy

### Phase 3: WebSocket Integration
- Connect meeting bot to VTuber server
- Implement meeting-specific message types
- Handle context passing and activation

### Phase 4: TTS/Audio Integration
- Connect real TTS output to PulseAudio pipeline
- Implement atomic file operations
- Handle audio synchronization

### Phase 5: Complete Integration
- Live avatar rendering with WebSocket control
- Graph API webhooks for chat
- Calendar monitoring for auto-join
- Multi-meeting support

## Key Design Decisions

### Why Not Native Bot Framework?
- Requires Windows Server + complex infrastructure
- Needs admin consent + high privileges
- Cannot record/persist media
- Too complex for side project

### Why Three Channels?
- **Audio**: Fast, natural activation
- **Chat**: Reliable, explicit commands
- **Captions**: Context without processing overhead

### Why Browser Automation?
- Universal solution (Teams, Zoom, Meet)
- No API limitations
- Appears as normal participant
- Simpler than native integration

## Critical Discoveries

### Audio/Video Injection
- Chrome's `--use-file-for-fake-audio-capture` loads file ONCE
- Must use PulseAudio for dynamic audio
- v4l2loopback required for live video

### DOM Scraping Resilience
- Avoid CSS classes (change frequently)
- Prefer data-testid, aria-labels
- Implement health checks
- Use configuration files for selectors

### Graph API Limitations
- Only POST-meeting transcripts available
- No real-time transcript API
- Chat polling has 2-3 second delay
- Webhooks better than polling

## Security Considerations

### Authentication
- Dedicated Teams account for bot
- Limited permissions (no recording)
- Credential management via environment variables

### Data Privacy
- No transcript storage by default
- Process in-memory only
- Clear data retention policies
- Encrypted communications

## Resource Requirements

### Container Resources
- CPU: 2+ cores (browser + processing)
- RAM: 4GB minimum
- Storage: 10GB for dependencies

### Network
- Stable internet for Teams
- WebSocket to VTuber server
- Graph API access

## Future Enhancements

### Multi-Platform Support
- Zoom SDK integration
- Google Meet automation
- Platform detection logic

### Advanced Features
- Screen sharing capabilities
- Meeting recording playback
- Proactive action suggestions
- Dashboard generation

### Scalability
- Kubernetes deployment
- Multiple meeting instances
- Load balancing
- Monitoring/alerting

## Conclusion
This architecture provides a pragmatic solution for adding meeting capabilities to the VTuber while maximizing code reuse and minimizing complexity. The three-channel approach ensures reliable interaction while the container-based deployment enables easy scaling and management.