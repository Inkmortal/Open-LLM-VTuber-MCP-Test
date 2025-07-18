#!/bin/bash
set -e

echo "Starting diagnostic test environment..."

# Start PulseAudio
echo "Starting PulseAudio..."
pulseaudio --start --exit-idle-time=-1

# Run the diagnostic with xvfb-run
echo -e "\n=== Starting Live2D Diagnostic with xvfb-run ==="
xvfb-run --auto-servernum --server-args="-screen 0 1920x1080x24" \
    bash -c "
        # Start VNC server for monitoring
        x11vnc -display \$DISPLAY -forever -passwd test123 -rfbport 5900 &
        
        # Start window manager
        fluxbox &
        
        # Run the diagnostic
        python3 /run_virtual_camera_diagnostic_v2.py
    "

echo -e "\nDiagnostic complete!"