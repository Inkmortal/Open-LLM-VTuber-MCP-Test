FROM mcr.microsoft.com/playwright/chromium:latest

# Install necessary packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    pulseaudio \
    pulseaudio-utils \
    alsa-utils \
    ffmpeg \
    v4l2loopback-utils \
    dbus-x11 \
    python3-pip \
    python3-websocket \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies for WebSocket client
RUN pip3 install websockets aiofiles

# Create a non-root user and add to audio/video groups
ARG USERNAME=vtuber
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && usermod -aG audio $USERNAME \
    && usermod -aG video $USERNAME \
    && chown -R $USERNAME:$USERNAME /home/$USERNAME

USER $USERNAME
WORKDIR /home/$USERNAME

# Copy the meeting bot scripts
COPY --chown=$USERNAME:$USERNAME start_meeting_bot.sh ./
COPY --chown=$USERNAME:$USERNAME meeting_bot_client.py ./
COPY --chown=$USERNAME:$USERNAME browser_automation.js ./

# Make scripts executable
RUN chmod +x start_meeting_bot.sh

# Set the entrypoint
CMD ["./start_meeting_bot.sh"]