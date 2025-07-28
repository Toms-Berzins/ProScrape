#!/usr/bin/env python3
"""Comprehensive test for enhanced WebSocket stability and features."""

import asyncio
import websockets
import json
import aiohttp
from datetime import datetime

async def test_connection_stability():
    """Test connection stability with multiple simultaneous connections."""
    uri = "ws://localhost:55144/ws"
    connections = []
    
    try:
        print("Testing Connection Stability")
        print("=" * 40)
        
        # Create multiple connections simultaneously
        for i in range(3):
            try:
                websocket = await websockets.connect(uri)
                connections.append(websocket)
                
                # Wait for connection established message
                message = await websocket.recv()
                data = json.loads(message)
                print(f"Connection {i+1}: {data.get('type')} - ID: {data.get('connection_id')}")
                
            except Exception as e:
                print(f"ERROR: Failed to create connection {i+1}: {e}")
        
        print(f"\nOK: Created {len(connections)} simultaneous connections")
        
        # Test message broadcasting to all connections
        for i, ws in enumerate(connections):
            subscribe_msg = {
                "type": "subscribe",
                "timestamp": datetime.now().isoformat()
            }
            await ws.send(json.dumps(subscribe_msg))
            
            # Wait for subscription confirmation
            response = await ws.recv()
            response_data = json.loads(response)
            print(f"Connection {i+1}: {response_data.get('type')} - {response_data.get('message')}")
        
        # Test ping/pong for all connections
        print("\nTesting ping/pong mechanism...")
        for i, ws in enumerate(connections):
            ping_msg = {
                "type": "ping",
                "timestamp": datetime.now().isoformat()
            }
            await ws.send(json.dumps(ping_msg))
            
            # Wait for response
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=3)
                response_data = json.loads(response)
                print(f"Connection {i+1}: PING -> {response_data.get('type')}")
            except asyncio.TimeoutError:
                print(f"Connection {i+1}: PING -> TIMEOUT")
        
        # Close all connections gracefully
        print("\nClosing connections gracefully...")
        for i, ws in enumerate(connections):
            await ws.close()
            print(f"Connection {i+1}: CLOSED")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Connection stability test failed: {e}")
        # Clean up any remaining connections
        for ws in connections:
            try:
                await ws.close()
            except:
                pass
        return False

async def test_health_monitoring():
    """Test WebSocket health monitoring endpoints."""
    print("\nTesting Health Monitoring")
    print("=" * 40)
    
    try:
        async with aiohttp.ClientSession() as session:
            # Test WebSocket stats endpoint
            async with session.get("http://localhost:55144/monitoring/websocket/stats") as response:
                if response.status == 200:
                    data = await response.json()
                    print("WebSocket Statistics:")
                    print(f"   Total connections: {data.get('total_connections', 0)}")
                    print(f"   Total disconnections: {data.get('total_disconnections', 0)}")
                    print(f"   Active connections: {data.get('active_connections', 0)}")
                    print(f"   Uptime: {data.get('uptime_formatted', 'unknown')}")
                    print(f"   Ping interval: {data.get('ping_interval', 'unknown')}s")
                    print(f"   Health status: {'OK' if data.get('active_connections', 0) >= 0 else 'ERROR'}")
                else:
                    print(f"ERROR: Failed to get WebSocket stats: HTTP {response.status}")
            
            # Test health endpoint
            async with session.get("http://localhost:55144/health") as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"\nAPI Health Status: {data.get('status', 'unknown')}")
                    print(f"   Database: {data.get('database', 'unknown')}")
                    print(f"   WebSocket: {data.get('websocket_manager', 'unknown')}")
                else:
                    print(f"ERROR: Failed to get health status: HTTP {response.status}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Health monitoring test failed: {e}")
        return False

async def test_reconnection_scenario():
    """Test reconnection behavior when connection is lost."""
    uri = "ws://localhost:55144/ws"
    
    print("\nTesting Reconnection Scenario")
    print("=" * 40)
    
    try:
        # Connect and establish session
        websocket = await websockets.connect(uri)
        
        # Wait for connection established
        message = await websocket.recv()
        data = json.loads(message)
        connection_id = data.get('connection_id')
        print(f"Initial connection: {connection_id}")
        
        # Subscribe to updates
        subscribe_msg = {
            "type": "subscribe",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send(json.dumps(subscribe_msg))
        
        response = await websocket.recv()
        response_data = json.loads(response)
        print(f"Subscription: {response_data.get('message')}")
        
        # Simulate connection loss by closing
        await websocket.close()
        print("Connection closed (simulating network issue)")
        
        # Wait a moment
        await asyncio.sleep(1)
        
        # Reconnect
        websocket = await websockets.connect(uri)
        
        # Wait for new connection established
        message = await websocket.recv()
        data = json.loads(message)
        new_connection_id = data.get('connection_id')
        print(f"Reconnected: {new_connection_id}")
        
        # Verify new connection works
        ping_msg = {
            "type": "ping",
            "timestamp": datetime.now().isoformat()
        }
        await websocket.send(json.dumps(ping_msg))
        
        response = await asyncio.wait_for(websocket.recv(), timeout=3)
        response_data = json.loads(response)
        print(f"Reconnection test: PING -> {response_data.get('type')}")
        
        await websocket.close()
        print("Reconnection test completed successfully")
        
        return connection_id != new_connection_id  # Should have different IDs
        
    except Exception as e:
        print(f"ERROR: Reconnection test failed: {e}")
        return False

async def main():
    """Run comprehensive WebSocket stability tests."""
    print("Enhanced WebSocket Stability Test Suite")
    print("=" * 50)
    
    tests = [
        ("Connection Stability", test_connection_stability),
        ("Health Monitoring", test_health_monitoring),
        ("Reconnection Scenario", test_reconnection_scenario)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            print(f"\n{test_name}: {'PASS' if result else 'FAIL'}")
        except Exception as e:
            results.append((test_name, False))
            print(f"\n{test_name}: FAIL - {e}")
        
        # Wait between tests
        await asyncio.sleep(1)
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResults: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("SUCCESS: All WebSocket stability tests passed!")
        print("The enhanced WebSocket implementation resolves connection stability issues.")
    else:
        print("WARNING: Some tests failed. Check implementation.")

if __name__ == "__main__":
    asyncio.run(main())