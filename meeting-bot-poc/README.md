# VTuber Teams Meeting Bot

A containerized solution that enables the VTuber to join Microsoft Teams meetings with full audio/video capabilities.

## Architecture Overview

The meeting bot uses a cloud-deployable architecture with no host dependencies:
- **Video**: Chrome's `--use-file-for-fake-video-capture` reads from a named pipe
- **Audio**: PulseAudio virtual devices for TTS output
- **Automation**: Playwright for browser control
- **No kernel modules required** - fully userspace solution

## Quick Start

### Prerequisites

1. **VTuber Server**: Must be running on port 12393
2. **Docker**: Docker and Docker Compose installed
3. **Meeting URL**: Teams or Zoom meeting link

### Running Locally

```bash
# Start the VTuber server (in main directory)
cd ..
python run_server.py

# Run the meeting bot
cd meeting-bot-poc
export MEETING_URL="https://teams.microsoft.com/l/meetup-join/..."
docker-compose -f docker-compose.cloud.yml up --build
```

### Monitoring

Connect via VNC to see the browser:
- **URL**: `localhost:5900`
- **Password**: `vtuber123`

## Implementation Details

### Video Pipeline
```
VTuber Web UI → FFmpeg Screen Capture → Named Pipe → Chrome Fake Video
```

### Audio Pipeline  
```
VTuber TTS → WebSocket → PulseAudio Sink → Virtual Source → Browser Mic
```

### Key Components

1. **stream_vtuber_to_pipe.py**: Captures VTuber browser window with FFmpeg
2. **meeting_bot_cloud.py**: Launches Chrome with pipe video to join meetings
3. **Named Pipe**: `/tmp/vtuber_video` for video streaming
4. **PulseAudio**: Virtual audio devices for dynamic audio routing

## Cloud Deployment

This solution is designed for cloud deployment:

### AWS ECS
```bash
# Build and push to ECR
aws ecr get-login-password | docker login --username AWS --password-stdin $ECR_URI
docker build -f Dockerfile.cloud -t vtuber-bot .
docker tag vtuber-bot:latest $ECR_URI/vtuber-bot:latest
docker push $ECR_URI/vtuber-bot:latest
```

### Google Cloud Run
```bash
gcloud builds submit --tag gcr.io/$PROJECT_ID/vtuber-bot
gcloud run deploy --image gcr.io/$PROJECT_ID/vtuber-bot
```

### Environment Variables

- `VTUBER_URL`: VTuber server WebSocket URL (default: `http://host.docker.internal:12393`)
- `MEETING_URL`: Full Teams/Zoom meeting URL
- `VNC_PASSWORD`: Password for VNC access

## Development

### Local Testing

For local development without the full VTuber:
```bash
docker-compose -f docker-compose.sandbox.yml up --build
```

### Architecture Documentation

See [README-CLOUD.md](README-CLOUD.md) for detailed technical documentation.

## Troubleshooting

1. **No video in meeting**: Check FFmpeg is capturing the correct screen area
2. **No audio**: Verify PulseAudio virtual devices are created
3. **Chrome won't start**: Ensure the named pipe exists before Chrome launches
4. **VTuber not connecting**: Check VTUBER_URL is accessible from container

## Future Enhancements

- [ ] Multiple meeting platform support (Zoom, Google Meet)
- [ ] Automatic meeting join from calendar
- [ ] Advanced caption analysis
- [ ] Multi-meeting support
- [ ] Health monitoring and auto-recovery