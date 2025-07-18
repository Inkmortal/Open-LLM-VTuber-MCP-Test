#!/bin/bash
set -e

# Start Xvfb
echo "Starting X server..."
Xvfb :99 -screen 0 1280x720x24 &
export DISPLAY=:99

# Wait for X server to start
sleep 2

# Start window manager
echo "Starting window manager..."
fluxbox &

# Start PulseAudio
echo "Starting PulseAudio..."
pulseaudio --start --exit-idle-time=-1

# Create virtual audio sink for VTuber audio
pactl load-module module-null-sink sink_name=vtuber_sink sink_properties=device.description="VTuber_Audio"
pactl load-module module-virtual-source source_name=vtuber_source master=vtuber_sink.monitor

# Create named pipe for video
echo "Creating video pipe..."
rm -f /tmp/vtuber_video
mkfifo /tmp/vtuber_video

# Start supervisord
echo "Starting supervisord..."
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf