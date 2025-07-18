#!/bin/bash
set -e

echo "Starting test environment..."

# Start PulseAudio
echo "Starting PulseAudio..."
pulseaudio --start --exit-idle-time=-1

# Create virtual audio devices
echo "Creating virtual audio devices..."
pactl load-module module-null-sink sink_name=vtuber_sink sink_properties=device.description='VTuber_Audio'
pactl load-module module-virtual-source source_name=vtuber_source master=vtuber_sink.monitor

# Wait a bit for audio to start
sleep 2

# Run the virtual camera service with xvfb-run
echo -e "\n=== Starting VTuber Virtual Camera Service with xvfb-run ==="
xvfb-run --auto-servernum --server-args="-screen 0 1920x1080x24" \
    bash -c "
        # Start VNC server inside xvfb-run context to use same display
        x11vnc -display \$DISPLAY -forever -passwd test123 -rfbport 5900 &
        
        # Start window manager
        fluxbox &
        
        # Run the virtual camera with proper HTTP proxy
        python3 /run_virtual_camera_http_proxy.py
    " &
CAMERA_PID=$!

# Keep container running
echo -e "\nVirtual camera service started (PID: $CAMERA_PID)"
echo "VNC available at localhost:5900 (password: test123)"
echo "You should see:"
echo "  - VTuber browser on the left"
echo "  - Demo browser with virtual camera feed on the right"
echo "Container will keep running. Press Ctrl+C to stop."

# Keep the container alive
while true; do
    sleep 60
    echo "Container still running... VNC: localhost:5900"
done