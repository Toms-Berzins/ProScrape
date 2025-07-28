#!/usr/bin/env python3
"""Test WebSocket connection that simulates frontend behavior."""

import asyncio
import websockets
import json
from datetime import datetime

async def test_frontend_websocket():
    """Test WebSocket connection as the frontend would."""
    uri = "ws://localhost:8000/ws"
    
    try:
        print(f"Connecting to {uri}...")
        
        async with websockets.connect(uri) as websocket:
            print("OK WebSocket connected successfully!")
            
            # Wait for connection established message
            message = await websocket.recv()
            data = json.loads(message)
            print(f"RECV: {data.get('type')} - Connection ID: {data.get('connection_id')}")
            
            # Simulate frontend behavior - subscribe to updates
            subscribe_msg = {
                "type": "subscribe",
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(subscribe_msg))
            print("SENT: subscribe message")
            
            # Wait for subscription confirmation
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"RECV: {response_data.get('type')} - {response_data.get('message')}")
            
            # Test language switching (like frontend would)
            lang_msg = {
                "type": "set_language",
                "language": "en",
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(lang_msg))
            print("SENT: language switch to English")
            
            # Wait for language switch confirmation
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"RECV: {response_data.get('type')} - {response_data.get('message')}")
            
            # Test heartbeat/ping mechanism
            ping_msg = {
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            }
            
            await websocket.send(json.dumps(ping_msg))
            print("SENT: ping")
            
            # Listen for a few seconds to see ping/pong
            try:
                for i in range(3):
                    message = await asyncio.wait_for(websocket.recv(), timeout=2)
                    data = json.loads(message)
                    print(f"RECV: {data.get('type')} - {data.get('message', data.get('timestamp', 'No message'))}")
            except asyncio.TimeoutError:
                print("TIMEOUT: No more messages received")
            
            print("SUCCESS: WebSocket test completed successfully!")
            
    except Exception as e:
        print(f"ERROR: WebSocket connection failed: {e}")
        return False
    
    return True

async def check_server_stats():
    """Check server statistics after connection."""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/monitoring/websocket/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    
                    print("\nServer Statistics:")
                    print(f"   Active connections: {data.get('active_connections', 0)}")
                    print(f"   Total connections: {data.get('total_connections', 0)}")
                    print(f"   Total disconnections: {data.get('total_disconnections', 0)}")
                    print(f"   Uptime: {data.get('uptime_formatted', 'unknown')}")
                    print(f"   Ping interval: {data.get('ping_interval', 'unknown')}s")
                    
                else:
                    print(f"ERROR: Failed to get server stats: HTTP {response.status}")
                    
    except Exception as e:
        print(f"ERROR: Failed to get server stats: {e}")

async def main():
    """Main test function."""
    print("Testing Frontend WebSocket Connection")
    print("=" * 50)
    
    # Test WebSocket connection
    success = await test_frontend_websocket()
    
    # Wait a moment for server to process
    await asyncio.sleep(1)
    
    # Check server stats
    await check_server_stats()
    
    if success:
        print("\nSUCCESS: Frontend WebSocket connection is working!")
    else:
        print("\nWARNING: Frontend WebSocket connection has issues.")

if __name__ == "__main__":
    asyncio.run(main())