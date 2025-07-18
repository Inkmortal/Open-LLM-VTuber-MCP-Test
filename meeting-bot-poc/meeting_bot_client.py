#!/usr/bin/env python3
"""
Meeting Bot WebSocket Client
Connects to the VTuber server and handles audio/video routing
"""
import asyncio
import websockets
import json
import subprocess
import os
import tempfile
from pathlib import Path

class MeetingBotClient:
    def __init__(self, vtuber_url="ws://host.docker.internal:12393/client-ws"):
        self.vtuber_url = vtuber_url
        self.audio_cache = Path("/tmp/vtuber_audio_cache")
        self.audio_cache.mkdir(exist_ok=True)
        
    async def handle_audio(self, audio_file_path):
        """Route TTS audio to PulseAudio virtual sink"""
        # The VTuber server sends audio file paths
        # We need to play them through PulseAudio
        cmd = [
            "ffmpeg", "-i", audio_file_path,
            "-f", "pulse", "vtuber_sink",
            "-y"  # Overwrite without asking
        ]
        subprocess.run(cmd, check=True)
        print(f"Played audio: {audio_file_path}")
        
    async def handle_message(self, websocket):
        """Handle messages from VTuber server"""
        async for message in websocket:
            try:
                data = json.loads(message)
                
                # Handle different message types
                if data.get("type") == "audio_chunk":
                    # Audio data from TTS
                    audio_data = data.get("audio")
                    if audio_data:
                        # Save to temp file and play
                        temp_file = tempfile.NamedTemporaryFile(
                            delete=False, 
                            suffix=".wav",
                            dir=self.audio_cache
                        )
                        temp_file.write(audio_data.encode('latin-1'))
                        temp_file.close()
                        await self.handle_audio(temp_file.name)
                        
                elif data.get("type") == "tts_response":
                    # File path to audio
                    audio_path = data.get("audio_file_path")
                    if audio_path and os.path.exists(audio_path):
                        await self.handle_audio(audio_path)
                        
                elif data.get("type") == "expression":
                    # Live2D expression changes
                    expression = data.get("expression")
                    print(f"Expression change: {expression}")
                    # TODO: Update avatar display
                    
                elif data.get("type") == "message":
                    # Text messages
                    print(f"VTuber says: {data.get('text', '')}")
                    
            except Exception as e:
                print(f"Error handling message: {e}")
                
    async def send_message(self, websocket, text):
        """Send a message to the VTuber"""
        message = {
            "type": "user_message",
            "text": text,
            "metadata": {
                "source": "teams_meeting",
                "require_audio": True
            }
        }
        await websocket.send(json.dumps(message))
        
    async def run(self):
        """Main client loop"""
        print(f"Connecting to VTuber server at {self.vtuber_url}")
        
        try:
            async with websockets.connect(self.vtuber_url) as websocket:
                print("Connected to VTuber server!")
                
                # Send initial greeting
                await self.send_message(websocket, "Meeting bot connected and ready.")
                
                # Handle incoming messages
                await self.handle_message(websocket)
                
        except Exception as e:
            print(f"Connection error: {e}")
            # Retry after delay
            await asyncio.sleep(5)
            await self.run()

if __name__ == "__main__":
    client = MeetingBotClient()
    asyncio.run(client.run())