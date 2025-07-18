#!/usr/bin/env python3
"""
Pipeline validation script to check all audio/video components
"""
import os
import sys
import subprocess
import asyncio
import psutil
import json
from datetime import datetime
from pathlib import Path

class PipelineValidator:
    def __init__(self):
        self.results = []
        self.video_pipe = "/tmp/vtuber_video"
        self.test_duration = 5  # seconds
        
    def add_result(self, component, status, message):
        """Add a test result"""
        self.results.append({
            "component": component,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Print colored output
        color = "\033[92m" if status == "PASS" else "\033[91m"
        reset = "\033[0m"
        print(f"{color}[{status}]{reset} {component}: {message}")
    
    def check_environment(self):
        """Check basic environment requirements"""
        print("\n=== Checking Environment ===")
        
        # Check display
        display = os.environ.get('DISPLAY')
        if display:
            self.add_result("Display", "PASS", f"Display set to {display}")
        else:
            self.add_result("Display", "FAIL", "DISPLAY environment variable not set")
        
        # Check if running in Docker
        if os.path.exists('/.dockerenv'):
            self.add_result("Docker", "PASS", "Running inside Docker container")
        else:
            self.add_result("Docker", "WARN", "Not running in Docker container")
    
    def check_processes(self):
        """Check if required processes are running"""
        print("\n=== Checking Processes ===")
        
        required_processes = {
            "Xvfb": ["Xvfb"],
            "VNC Server": ["x11vnc"],
            "Window Manager": ["fluxbox"],
            "PulseAudio": ["pulseaudio"],
            "Supervisord": ["supervisord"]
        }
        
        for name, keywords in required_processes.items():
            found = False
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if any(kw in cmdline for kw in keywords):
                        found = True
                        self.add_result(name, "PASS", f"Process running (PID: {proc.pid})")
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            if not found:
                self.add_result(name, "FAIL", "Process not found")
    
    def check_pulseaudio(self):
        """Check PulseAudio virtual devices"""
        print("\n=== Checking PulseAudio ===")
        
        try:
            # List sinks
            result = subprocess.run(['pactl', 'list', 'sinks'], 
                                  capture_output=True, text=True)
            if 'vtuber_sink' in result.stdout:
                self.add_result("Virtual Sink", "PASS", "vtuber_sink found")
            else:
                self.add_result("Virtual Sink", "FAIL", "vtuber_sink not found")
            
            # List sources
            result = subprocess.run(['pactl', 'list', 'sources'], 
                                  capture_output=True, text=True)
            if 'vtuber_source' in result.stdout:
                self.add_result("Virtual Source", "PASS", "vtuber_source found")
            else:
                self.add_result("Virtual Source", "FAIL", "vtuber_source not found")
                
        except subprocess.CalledProcessError as e:
            self.add_result("PulseAudio", "FAIL", f"Command failed: {e}")
        except FileNotFoundError:
            self.add_result("PulseAudio", "FAIL", "pactl command not found")
    
    def check_video_pipe(self):
        """Check named pipe for video"""
        print("\n=== Checking Video Pipe ===")
        
        if os.path.exists(self.video_pipe):
            stat = os.stat(self.video_pipe)
            if stat.st_mode & 0o010000:  # Check if it's a FIFO
                self.add_result("Video Pipe", "PASS", f"Named pipe exists at {self.video_pipe}")
                
                # Check if pipe is writable
                if os.access(self.video_pipe, os.W_OK):
                    self.add_result("Pipe Access", "PASS", "Pipe is writable")
                else:
                    self.add_result("Pipe Access", "FAIL", "Pipe is not writable")
            else:
                self.add_result("Video Pipe", "FAIL", f"{self.video_pipe} exists but is not a pipe")
        else:
            self.add_result("Video Pipe", "FAIL", f"Named pipe not found at {self.video_pipe}")
    
    async def test_video_flow(self):
        """Test if video data flows through the pipe"""
        print("\n=== Testing Video Flow ===")
        
        if not os.path.exists(self.video_pipe):
            self.add_result("Video Flow", "SKIP", "Pipe doesn't exist")
            return
        
        # Start a test pattern generator
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'lavfi',
            '-i', 'testsrc=size=640x480:rate=30',
            '-t', str(self.test_duration),
            '-pix_fmt', 'yuv420p',
            '-f', 'rawvideo',
            '-y',
            self.video_pipe
        ]
        
        try:
            # Start FFmpeg in background
            proc = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Try to read from pipe
            read_task = asyncio.create_task(self._read_from_pipe())
            
            # Wait for FFmpeg to complete or timeout
            try:
                await asyncio.wait_for(proc.wait(), timeout=self.test_duration + 2)
            except asyncio.TimeoutError:
                proc.terminate()
                await proc.wait()
            
            # Check results
            bytes_read = await read_task
            if bytes_read > 0:
                self.add_result("Video Flow", "PASS", 
                              f"Successfully read {bytes_read} bytes from pipe")
            else:
                self.add_result("Video Flow", "FAIL", "No data read from pipe")
                
        except Exception as e:
            self.add_result("Video Flow", "FAIL", f"Error testing video flow: {e}")
    
    async def _read_from_pipe(self):
        """Read data from the pipe"""
        bytes_read = 0
        try:
            # Open pipe in non-blocking mode
            fd = os.open(self.video_pipe, os.O_RDONLY | os.O_NONBLOCK)
            
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < self.test_duration:
                try:
                    data = os.read(fd, 4096)
                    if data:
                        bytes_read += len(data)
                except BlockingIOError:
                    await asyncio.sleep(0.1)
                    
            os.close(fd)
        except Exception as e:
            print(f"Error reading from pipe: {e}")
            
        return bytes_read
    
    def check_chrome_flags(self):
        """Check if Chrome is running with correct flags"""
        print("\n=== Checking Chrome Configuration ===")
        
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                if 'chrome' in proc.info['name'].lower() or 'chromium' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    
                    # Check for fake video flag
                    if '--use-file-for-fake-video-capture' in cmdline:
                        self.add_result("Chrome Video Flag", "PASS", 
                                      "Chrome running with fake video capture flag")
                        
                        # Extract pipe path
                        for arg in proc.info['cmdline']:
                            if arg.startswith('--use-file-for-fake-video-capture='):
                                pipe_path = arg.split('=', 1)[1]
                                if pipe_path == self.video_pipe:
                                    self.add_result("Chrome Pipe Path", "PASS", 
                                                  f"Using correct pipe: {pipe_path}")
                                else:
                                    self.add_result("Chrome Pipe Path", "FAIL", 
                                                  f"Wrong pipe path: {pipe_path}")
                    else:
                        self.add_result("Chrome Video Flag", "WARN", 
                                      "Chrome running but without fake video flag")
                    
                    # Check for audio flag
                    if '--use-fake-ui-for-media-stream' in cmdline:
                        self.add_result("Chrome Audio Flag", "PASS", 
                                      "Auto-accept media permissions enabled")
                    
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    
    def generate_report(self):
        """Generate a summary report"""
        print("\n=== Pipeline Validation Report ===")
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        failed = sum(1 for r in self.results if r['status'] == 'FAIL')
        warned = sum(1 for r in self.results if r['status'] == 'WARN')
        
        print(f"\nTotal checks: {len(self.results)}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Warnings: {warned}")
        
        if failed > 0:
            print("\nFailed components:")
            for r in self.results:
                if r['status'] == 'FAIL':
                    print(f"  - {r['component']}: {r['message']}")
        
        # Save detailed report
        report_path = Path("pipeline_validation_report.json")
        with open(report_path, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total": len(self.results),
                    "passed": passed,
                    "failed": failed,
                    "warnings": warned
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_path}")
        
        return failed == 0
    
    async def run_validation(self):
        """Run all validation checks"""
        print("Starting VTuber Audio/Video Pipeline Validation")
        print("=" * 50)
        
        self.check_environment()
        self.check_processes()
        self.check_pulseaudio()
        self.check_video_pipe()
        await self.test_video_flow()
        self.check_chrome_flags()
        
        success = self.generate_report()
        
        if success:
            print("\n✅ Pipeline validation PASSED!")
        else:
            print("\n❌ Pipeline validation FAILED!")
            sys.exit(1)

def main():
    validator = PipelineValidator()
    asyncio.run(validator.run_validation())

if __name__ == "__main__":
    main()