#!/usr/bin/env python3
"""
Route VTuber audio from WebSocket to PulseAudio virtual sink
"""
import asyncio
import websockets
import json
import os
import subprocess
import tempfile
from pathlib import Path

VTUBER_WS_URL = os.environ.get('VTUBER_WS_URL', 'ws://host.docker.internal:12393/client-ws')
PULSE_SINK = 'vtuber_sink'

class VTuberAudioRouter:
    def __init__(self):
        self.ws = None
        self.audio_dir = tempfile.mkdtemp(prefix='vtuber_audio_')
        self.current_audio = None
        
    async def connect(self):
        """Connect to VTuber WebSocket"""
        print(f"Connecting to VTuber at {VTUBER_WS_URL}")
        self.ws = await websockets.connect(VTUBER_WS_URL)
        print("Connected successfully")
        
    async def handle_message(self, message):
        """Process messages from VTuber server"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'audio':
                # Audio data from TTS
                audio_data = data.get('audio')
                if audio_data:
                    await self.play_audio(audio_data)
                    
            elif msg_type == 'tts_response':
                # Alternative audio format
                audio_path = data.get('audio_path')
                if audio_path:
                    await self.play_audio_file(audio_path)
                    
        except json.JSONDecodeError:
            print(f"Failed to parse message: {message}")
        except Exception as e:
            print(f"Error handling message: {e}")
    
    async def play_audio(self, audio_data):
        """Play audio data through PulseAudio"""
        # Save audio data to temporary file
        audio_file = Path(self.audio_dir) / f"tts_{asyncio.get_event_loop().time()}.wav"
        
        # Assuming audio_data is base64 encoded
        import base64
        audio_bytes = base64.b64decode(audio_data)
        
        with open(audio_file, 'wb') as f:
            f.write(audio_bytes)
            
        await self.play_audio_file(str(audio_file))
        
        # Clean up old file after playing
        await asyncio.sleep(5)
        try:
            audio_file.unlink()
        except:
            pass
    
    async def play_audio_file(self, audio_path):
        """Play audio file through PulseAudio sink"""
        print(f"Playing audio: {audio_path}")
        
        # Use paplay to play through specific sink
        cmd = [
            'paplay',
            '--device=' + PULSE_SINK,
            audio_path
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await proc.communicate()
            
            if proc.returncode != 0:
                print(f"Error playing audio: {stderr.decode()}")
            else:
                print("Audio playback completed")
                
        except Exception as e:
            print(f"Failed to play audio: {e}")
    
    async def run(self):
        """Main loop to receive and route audio"""
        try:
            await self.connect()
            
            # Send initial connection message
            await self.ws.send(json.dumps({
                "type": "client_info",
                "client_type": "audio_router",
                "version": "1.0"
            }))
            
            # Listen for messages
            async for message in self.ws:
                await self.handle_message(message)
                
        except websockets.exceptions.ConnectionClosed:
            print("WebSocket connection closed")
        except Exception as e:
            print(f"Error in audio router: {e}")
        finally:
            if self.ws:
                await self.ws.close()
            
            # Clean up temp directory
            try:
                import shutil
                shutil.rmtree(self.audio_dir)
            except:
                pass

def setup_pulseaudio():
    """Ensure PulseAudio virtual devices are set up"""
    print("Setting up PulseAudio virtual devices...")
    
    # Check if sink exists
    result = subprocess.run(['pactl', 'list', 'sinks'], 
                          capture_output=True, text=True)
    
    if PULSE_SINK not in result.stdout:
        print(f"Creating virtual sink: {PULSE_SINK}")
        subprocess.run([
            'pactl', 'load-module', 'module-null-sink',
            f'sink_name={PULSE_SINK}',
            'sink_properties=device.description="VTuber_Audio"'
        ])
    
    # Check if source exists
    result = subprocess.run(['pactl', 'list', 'sources'], 
                          capture_output=True, text=True)
    
    if 'vtuber_source' not in result.stdout:
        print("Creating virtual source from sink monitor")
        subprocess.run([
            'pactl', 'load-module', 'module-virtual-source',
            'source_name=vtuber_source',
            f'master={PULSE_SINK}.monitor'
        ])
    
    print("PulseAudio setup complete")

async def main():
    # Setup PulseAudio first
    setup_pulseaudio()
    
    # Run audio router
    router = VTuberAudioRouter()
    
    while True:
        try:
            await router.run()
        except Exception as e:
            print(f"Router error: {e}")
            print("Retrying in 5 seconds...")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())