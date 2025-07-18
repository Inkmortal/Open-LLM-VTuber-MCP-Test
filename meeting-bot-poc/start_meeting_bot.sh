#!/bin/bash

# Start PulseAudio daemon
echo "Starting PulseAudio..."
pulseaudio -D --exit-idle-time=-1 --log-target=stderr
sleep 2

# Configure PulseAudio virtual devices
echo "Setting up virtual audio devices..."

# Create a virtual sink for VTuber audio output
pactl load-module module-null-sink sink_name=vtuber_sink sink_properties=device.description="VTuber_Audio_Sink"

# Create a virtual microphone from the sink's monitor
pactl load-module module-remap-source source_name=vtuber_mic master=vtuber_sink.monitor source_properties=device.description="VTuber_Virtual_Microphone"

# Set default devices
pactl set-default-sink vtuber_sink
pactl set-default-source vtuber_mic

echo "Audio devices configured:"
pactl list short sinks
pactl list short sources

# Start the VTuber avatar renderer (serves HTML page on localhost:3000)
echo "Starting avatar renderer..."
python3 -m http.server 3000 --directory /home/vtuber/avatar &
AVATAR_PID=$!

# Start ffmpeg to capture avatar window and stream to virtual camera
# This captures the Chromium window showing the avatar and pipes to v4l2loopback
echo "Starting virtual camera stream..."
# Wait for browser to start first
sleep 10
# Use xwininfo to find the browser window, then ffmpeg to capture and stream
# For now, we'll use a placeholder - in production we'd capture the actual window
ffmpeg -f x11grab -video_size 640x480 -i :0.0 -f v4l2 -pix_fmt yuv420p /dev/video0 &
FFMPEG_PID=$!

# Start the WebSocket client that connects to VTuber server
echo "Starting VTuber WebSocket client..."
python3 meeting_bot_client.py &
VTUBER_PID=$!

# Give everything time to initialize
sleep 5

# Start Playwright browser automation
echo "Starting browser automation..."
node browser_automation.js

# Keep the script running
wait $VTUBER_PID