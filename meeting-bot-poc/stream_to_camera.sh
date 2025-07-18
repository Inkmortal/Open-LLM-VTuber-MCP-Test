#!/bin/bash

# Wait for browser and named pipe to be ready
sleep 20

# More robust approach: capture the entire X display since we control what's shown
# The VTuber browser will be the main content on the virtual display
echo "Starting virtual camera stream..."
echo "Capturing entire virtual display :99"

# Check if named pipe exists
if [ ! -p /tmp/video_pipe/video_stream ]; then
    echo "Warning: Named pipe /tmp/video_pipe/video_stream not found."
    echo "Exiting video stream."
    exit 0
fi

# Capture the full virtual display and stream to named pipe
# Since we control the desktop, the VTuber will be the primary content
exec ffmpeg -f x11grab \
       -video_size 1280x720 \
       -framerate 30 \
       -i :99.0 \
       -pix_fmt yuv420p \
       -f yuv4mpegpipe \
       -y /tmp/video_pipe/video_stream