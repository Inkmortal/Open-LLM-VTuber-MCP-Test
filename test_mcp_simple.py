#!/usr/bin/env python3
"""
Simple test to check if MCP servers are running and responsive
"""
import subprocess
import asyncio
import sys
import json

async def test_mcp_server():
    """Test MCP server by running it and sending a simple message"""
    
    # Test the filesystem MCP server first (it's simpler)
    cmd = ["cmd", "/c", "npx", "-y", "@modelcontextprotocol/server-filesystem", r"C:\Users\danhc\Documents"]
    
    print(f"Starting MCP server: {' '.join(cmd)}")
    
    try:
        # Start the process
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        print("Process started, PID:", proc.pid)
        
        # Give it a moment to start
        await asyncio.sleep(1)
        
        # Send a simple JSON-RPC message to see if it responds
        test_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",  # Try an older version
                "capabilities": {}
            }
        }
        
        message_str = json.dumps(test_message) + "\n"
        print(f"Sending: {message_str.strip()}")
        
        proc.stdin.write(message_str.encode())
        await proc.stdin.drain()
        
        # Try to read response with timeout
        try:
            response = await asyncio.wait_for(proc.stdout.readline(), timeout=5.0)
            print(f"Response: {response.decode().strip()}")
        except asyncio.TimeoutError:
            print("No response received within 5 seconds")
            
        # Check stderr
        try:
            stderr_data = await asyncio.wait_for(proc.stderr.read(1024), timeout=0.5)
            if stderr_data:
                print(f"Stderr: {stderr_data.decode()}")
        except asyncio.TimeoutError:
            pass
            
        # Terminate the process
        proc.terminate()
        await proc.wait()
        
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mcp_server())