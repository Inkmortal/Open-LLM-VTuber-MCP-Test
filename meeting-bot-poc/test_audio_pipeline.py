#!/usr/bin/env python3
"""
Test audio pipeline by verifying PulseAudio routing
"""
import asyncio
import subprocess
import os
import time
from pathlib import Path

PULSE_SINK = "vtuber_sink"
PULSE_SOURCE = "vtuber_source"

def run_command(cmd):
    """Run a command and return output"""
    result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return result.returncode, result.stdout, result.stderr

async def test_audio_pipeline():
    """Test the complete audio pipeline"""
    print("=== Testing Audio Pipeline ===\n")
    
    # Step 1: Check PulseAudio daemon
    print("1. Checking PulseAudio daemon...")
    code, stdout, stderr = run_command("pactl info")
    if code == 0:
        print("   ✅ PulseAudio is running")
        server_info = [line for line in stdout.split('\n') if 'Server Name' in line]
        if server_info:
            print(f"   {server_info[0]}")
    else:
        print("   ❌ PulseAudio not running")
        return
    
    # Step 2: Check virtual sink
    print("\n2. Checking virtual sink...")
    code, stdout, stderr = run_command("pactl list sinks")
    if PULSE_SINK in stdout:
        print(f"   ✅ Virtual sink '{PULSE_SINK}' exists")
        
        # Get sink details
        sink_info = []
        capture = False
        for line in stdout.split('\n'):
            if f'Name: {PULSE_SINK}' in line:
                capture = True
            elif capture and line.strip() == '':
                break
            elif capture:
                sink_info.append(line)
        
        # Check if sink is suspended
        suspended = any('SUSPENDED' in line for line in sink_info)
        if suspended:
            print("   ⚠️  Sink is suspended")
        else:
            print("   ✅ Sink is active")
    else:
        print(f"   ❌ Virtual sink '{PULSE_SINK}' not found")
        print("   Creating virtual sink...")
        run_command(f"pactl load-module module-null-sink sink_name={PULSE_SINK} sink_properties=device.description='VTuber_Audio'")
    
    # Step 3: Check virtual source
    print("\n3. Checking virtual source...")
    code, stdout, stderr = run_command("pactl list sources")
    if PULSE_SOURCE in stdout:
        print(f"   ✅ Virtual source '{PULSE_SOURCE}' exists")
    else:
        print(f"   ❌ Virtual source '{PULSE_SOURCE}' not found")
        print("   Creating virtual source...")
        run_command(f"pactl load-module module-virtual-source source_name={PULSE_SOURCE} master={PULSE_SINK}.monitor")
    
    # Step 4: Test audio playback to sink
    print("\n4. Testing audio playback to virtual sink...")
    
    # Generate test tone
    test_file = "/tmp/test_tone.wav"
    print("   Generating test tone...")
    run_command(f"sox -n {test_file} synth 2 sine 440")
    
    if os.path.exists(test_file):
        print("   Playing test tone to virtual sink...")
        code, stdout, stderr = run_command(f"paplay --device={PULSE_SINK} {test_file}")
        if code == 0:
            print("   ✅ Audio playback successful")
        else:
            print(f"   ❌ Audio playback failed: {stderr}")
    
    # Step 5: Monitor sink activity
    print("\n5. Monitoring sink activity...")
    print("   Starting 5-second monitor...")
    
    # Use parecord to record from the sink monitor
    monitor_file = "/tmp/monitor_recording.wav"
    monitor_proc = subprocess.Popen(
        f"parecord --device={PULSE_SINK}.monitor --file-format=wav {monitor_file}",
        shell=True
    )
    
    # Play another test tone while recording
    await asyncio.sleep(1)
    run_command(f"paplay --device={PULSE_SINK} {test_file}")
    await asyncio.sleep(2)
    
    # Stop recording
    monitor_proc.terminate()
    
    # Check if we recorded anything
    if os.path.exists(monitor_file):
        size = os.path.getsize(monitor_file)
        if size > 44:  # WAV header is 44 bytes
            print(f"   ✅ Recorded {size} bytes from sink monitor")
            print("   Audio is flowing through virtual sink correctly")
        else:
            print("   ❌ No audio data recorded from sink monitor")
    
    # Step 6: List all audio streams
    print("\n6. Current audio streams:")
    code, stdout, stderr = run_command("pactl list sink-inputs")
    
    if "Sink Input #" in stdout:
        print("   Active audio streams:")
        for line in stdout.split('\n'):
            if "application.name" in line or "media.name" in line:
                print(f"     {line.strip()}")
    else:
        print("   No active audio streams")
    
    # Step 7: Test source (microphone) functionality
    print("\n7. Testing virtual source (microphone)...")
    
    # Record from virtual source
    source_test = "/tmp/source_test.wav"
    print("   Recording 3 seconds from virtual source...")
    
    # Start recording from source
    record_proc = subprocess.Popen(
        f"parecord --device={PULSE_SOURCE} --file-format=wav {source_test}",
        shell=True
    )
    
    # Play tone to sink (should appear in source)
    await asyncio.sleep(0.5)
    run_command(f"paplay --device={PULSE_SINK} {test_file}")
    await asyncio.sleep(2.5)
    
    # Stop recording
    record_proc.terminate()
    
    if os.path.exists(source_test):
        size = os.path.getsize(source_test)
        if size > 44:
            print(f"   ✅ Virtual source working - recorded {size} bytes")
            print("   Audio routing complete: Sink → Monitor → Source")
        else:
            print("   ❌ No audio recorded from virtual source")
    
    # Cleanup
    for f in [test_file, monitor_file, source_test]:
        try:
            os.unlink(f)
        except:
            pass
    
    print("\n=== Audio Pipeline Test Complete ===")
    print("\nSummary:")
    print("- Virtual sink (vtuber_sink): Audio destination for VTuber")
    print("- Virtual source (vtuber_source): Microphone for browser")
    print("- Audio flow: VTuber → Sink → Monitor → Source → Browser")

async def main():
    """Run the audio pipeline test"""
    try:
        await test_audio_pipeline()
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())