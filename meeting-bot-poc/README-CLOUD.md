# VTuber Teams Meeting Bot - Cloud Deployable Version

This is a fully containerized, cloud-deployable version of the VTuber Teams Meeting Bot that requires NO host dependencies.

## Architecture

The solution uses Chrome's `--use-file-for-fake-video-capture` flag with a named pipe to stream the VTuber avatar as a virtual camera. This approach works entirely in userspace without requiring kernel modules like v4l2loopback.

### Components:

1. **VTuber Stream Capture**: Captures the VTuber web interface using FFmpeg screen capture
2. **Named Pipe Video Feed**: Streams video through a FIFO pipe in Y4M format  
3. **Chrome with Fake Video**: Chrome reads from the pipe as its camera source
4. **Meeting Automation**: Playwright automates joining and camera/mic controls

## Prerequisites

- Docker and Docker Compose
- VTuber server running on host machine (port 12393)
- Meeting URL (Teams or Zoom)

## Quick Start

1. **Start the VTuber server** on your host machine:
   ```bash
   cd ..  # Go to main VTuber directory
   python run_server.py
   ```

2. **Run the meeting bot**:
   ```bash
   # Set the meeting URL
   export MEETING_URL="https://teams.microsoft.com/l/meetup-join/..."
   
   # Start the container
   docker-compose -f docker-compose.cloud.yml up --build
   ```

3. **Monitor via VNC** (optional):
   - Connect to `localhost:5900` 
   - Password: `vtuber123`
   - You'll see the browser with VTuber avatar in the meeting

## Configuration

### Environment Variables:
- `VTUBER_URL`: URL of VTuber server (default: http://host.docker.internal:12393)
- `MEETING_URL`: Full URL of the Teams/Zoom meeting to join
- `VNC_PASSWORD`: Password for VNC access (default: vtuber123)

### Customization:
- Edit `conf.yaml` in the main VTuber directory to change avatar/character
- Modify `stream_vtuber_to_pipe.py` to adjust video capture area
- Update `meeting_bot_cloud.py` to add more meeting platform support

## Cloud Deployment

This solution can be deployed to any cloud platform that supports Docker:

### AWS ECS/Fargate:
```bash
# Build and push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_URI
docker build -f Dockerfile.cloud -t vtuber-bot .
docker tag vtuber-bot:latest $ECR_URI/vtuber-bot:latest
docker push $ECR_URI/vtuber-bot:latest
```

### Google Cloud Run:
```bash
# Build and push to GCR
gcloud builds submit --tag gcr.io/$PROJECT_ID/vtuber-bot
gcloud run deploy vtuber-bot --image gcr.io/$PROJECT_ID/vtuber-bot --port 5900
```

### Azure Container Instances:
```bash
# Push to ACR
az acr build --registry $ACR_NAME --image vtuber-bot .
az container create --resource-group $RG --name vtuber-bot --image $ACR_NAME.azurecr.io/vtuber-bot:latest
```

## Technical Details

### Why This Works:
- Chrome's `--use-file-for-fake-video-capture` can read from named pipes (FIFOs)
- FFmpeg captures the VTuber browser window and outputs Y4M format to the pipe
- Chrome continuously reads frames from the pipe as its camera feed
- Everything runs in userspace - no kernel modules required

### Limitations:
- Video quality depends on screen capture (not direct canvas access)
- Some latency due to the capture -> pipe -> Chrome pipeline
- Requires the VTuber server to be accessible from the container

## Troubleshooting

1. **Chrome won't start**: Check that the pipe exists and FFmpeg is writing to it
2. **No video in meeting**: Ensure FFmpeg is capturing the correct screen area
3. **VTuber not showing**: Verify VTUBER_URL is accessible from container
4. **Audio issues**: Check PulseAudio virtual sink is created properly

## Next Steps

For production use, consider:
- Adding health checks and auto-restart logic
- Implementing proper error handling and logging
- Using a message queue for meeting URL distribution
- Adding support for multiple simultaneous meetings
- Implementing avatar switching based on meeting context