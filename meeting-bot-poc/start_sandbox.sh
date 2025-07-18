#!/bin/bash

# Setup PulseAudio virtual devices
export PULSE_RUNTIME_PATH=/tmp/pulse-runtime
sudo -u vtuber pactl load-module module-null-sink sink_name=vtuber_sink
sudo -u vtuber pactl load-module module-remap-source source_name=vtuber_mic master=vtuber_sink.monitor

echo "Virtual audio devices ready"