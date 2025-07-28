#!/usr/bin/env python3
"""Test WebSocket client to validate enhanced stability features."""

import asyncio
import websockets
import json
import time
from datetime import datetime

class WebSocketTestClient:
    def __init__(self, uri="ws://localhost:8005/ws"):
        self.uri = uri
        self.websocket = None
        self.connection_id = None
        self.connected = False
        self.messages_received = 0
        self.messages_sent = 0
        
    async def connect(self):
        """Connect to WebSocket server."""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print(f"Connected to {self.uri}")
            
            # Wait for connection established message
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "connection_established":
                self.connection_id = data.get("connection_id")
                print(f"Connection ID: {self.connection_id}")
                print(f"Server ping interval: {data.get('ping_interval', 'unknown')} seconds")
            
            return True
            
        except Exception as e:
            print(f"Failed to connect: {e}")
            return False
    
    async def send_message(self, message_dict):
        """Send a message to the server."""
        if not self.connected or not self.websocket:
            return False
            
        try:
            message_json = json.dumps(message_dict)
            await self.websocket.send(message_json)
            self.messages_sent += 1
            print(f"Sent: {message_dict.get('type', 'unknown')}")
            return True
            
        except Exception as e:
            print(f"Failed to send message: {e}")
            return False
    
    async def listen_for_messages(self):
        """Listen for incoming messages."""
        while self.connected and self.websocket:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
                self.messages_received += 1
                
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    if message_type == "ping":
                        # Respond to ping with pong
                        await self.send_message({"type": "pong"})
                        print("Received ping, sent pong")
                        
                    elif message_type == "pong":
                        print("Received pong response")
                        
                    else:
                        print(f"Received: {message_type} - {data.get('message', '')}")
                        
                except json.JSONDecodeError:
                    print(f"Received non-JSON message: {message}")
                    
            except asyncio.TimeoutError:
                # No message received in timeout period, continue
                continue
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by server")
                self.connected = False
                break
            except Exception as e:
                print(f"Error receiving message: {e}")
                break
    
    async def test_features(self):
        """Test various WebSocket features."""
        if not self.connected:
            return
        
        print("\n=== Testing WebSocket Features ===")
        
        # Test 1: Subscribe to updates
        await self.send_message({"type": "subscribe"})
        await asyncio.sleep(1)
        
        # Test 2: Set language
        await self.send_message({"type": "set_language", "language": "en"})
        await asyncio.sleep(1)
        
        # Test 3: Get status
        await self.send_message({"type": "get_status"})
        await asyncio.sleep(1)
        
        # Test 4: Send invalid message
        await self.send_message({"type": "invalid_type", "data": "test"})
        await asyncio.sleep(1)
        
        # Test 5: Send plain text (should trigger error handling)
        try:
            await self.websocket.send("This is not JSON")
            self.messages_sent += 1
        except Exception as e:
            print(f"Failed to send plain text: {e}")
        
        await asyncio.sleep(2)
        
        print(f"Test completed. Sent: {self.messages_sent}, Received: {self.messages_received}")
    
    async def disconnect(self):
        """Disconnect from server."""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            print("Disconnected from server")

async def test_connection_stability():
    """Test connection stability with multiple scenarios."""
    print("=== WebSocket Connection Stability Test ===")
    
    client = WebSocketTestClient()
    
    try:
        # Connect
        if not await client.connect():
            return
        
        # Start listening task
        listen_task = asyncio.create_task(client.listen_for_messages())
        
        # Test features
        await client.test_features()
        
        # Let it run for a bit to test ping/pong
        print("\nTesting ping/pong mechanism...")
        await asyncio.sleep(10)
        
        # Cancel listening task
        listen_task.cancel()
        
        # Disconnect
        await client.disconnect()
        
        print(f"\nFinal stats:")
        print(f"Messages sent: {client.messages_sent}")
        print(f"Messages received: {client.messages_received}")
        print(f"Connection ID: {client.connection_id}")
        
    except Exception as e:
        print(f"Test failed: {e}")

async def test_multiple_connections():
    """Test multiple simultaneous connections."""
    print("\n=== Testing Multiple Connections ===")
    
    clients = []
    
    # Create multiple clients
    for i in range(3):
        client = WebSocketTestClient()
        if await client.connect():
            clients.append(client)
            print(f"Client {i+1} connected")
    
    # Let them all listen
    listen_tasks = []
    for client in clients:
        task = asyncio.create_task(client.listen_for_messages())
        listen_tasks.append(task)
    
    # Send some messages
    for i, client in enumerate(clients):
        await client.send_message({
            "type": "set_language", 
            "language": ["en", "lv", "ru"][i % 3]
        })
        await asyncio.sleep(0.5)
    
    # Wait a bit
    await asyncio.sleep(5)
    
    # Clean up
    for task in listen_tasks:
        task.cancel()
    
    for i, client in enumerate(clients):
        await client.disconnect()
        print(f"Client {i+1} disconnected")

async def main():
    """Main test function."""
    # Test single connection stability
    await test_connection_stability()
    
    # Wait a bit
    await asyncio.sleep(2)
    
    # Test multiple connections
    await test_multiple_connections()

if __name__ == "__main__":
    print("Starting WebSocket client tests...")
    asyncio.run(main())