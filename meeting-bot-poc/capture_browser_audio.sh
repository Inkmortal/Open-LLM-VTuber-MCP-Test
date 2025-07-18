#!/bin/bash
# Capture browser audio and route to virtual sink

echo "Setting up browser audio capture..."

# Wait for browser to start
sleep 10

# Find the browser's PulseAudio sink input
get_browser_sink_input() {
    pactl list sink-inputs | grep -B 20 -E "(Chromium|Chrome|application.name.*chrom)" | grep "Sink Input #" | head -1 | cut -d'#' -f2
}

# Wait for browser audio to appear
echo "Waiting for browser audio stream..."
for i in {1..30}; do
    SINK_INPUT=$(get_browser_sink_input)
    if [ -n "$SINK_INPUT" ]; then
        echo "Found browser audio stream: Sink Input #$SINK_INPUT"
        break
    fi
    sleep 1
done

if [ -z "$SINK_INPUT" ]; then
    echo "ERROR: Could not find browser audio stream"
    exit 1
fi

# Move browser audio to our virtual sink
echo "Routing browser audio to virtual sink..."
pactl move-sink-input $SINK_INPUT vtuber_sink

# Monitor the connection
while true; do
    # Check if sink input still exists
    if ! pactl list sink-inputs | grep -q "Sink Input #$SINK_INPUT"; then
        echo "Browser audio stream disappeared, searching for new one..."
        SINK_INPUT=$(get_browser_sink_input)
        if [ -n "$SINK_INPUT" ]; then
            echo "Found new browser audio stream: Sink Input #$SINK_INPUT"
            pactl move-sink-input $SINK_INPUT vtuber_sink
        fi
    fi
    
    sleep 5
done