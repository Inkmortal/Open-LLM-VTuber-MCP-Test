#!/bin/bash
set -e

echo "=== VTuber Sandbox Starting ==="

# Create named pipe directory and pipe
echo "Creating named pipe for video..."
mkdir -p /tmp/video_pipe
mkfifo /tmp/video_pipe/video_stream
chmod 666 /tmp/video_pipe/video_stream

# Start Xvfb first
echo "Starting X server..."
Xvfb :99 -screen 0 1280x720x24 &
export DISPLAY=:99

# Wait for X server to be ready
echo "Waiting for X server..."
for i in {1..30}; do
    if xdpyinfo >/dev/null 2>&1; then
        echo "X server ready!"
        break
    fi
    sleep 1
done

# Start supervisord to manage all services
echo "Starting supervisord..."
exec /usr/bin/supervisord -n -c /etc/supervisor/conf.d/supervisord.conf