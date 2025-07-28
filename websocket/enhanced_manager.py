"""
Enhanced WebSocket connection manager with improved stability and error handling.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from enum import Enum
from fastapi import WebSocket, WebSocketDisconnect
import weakref

logger = logging.getLogger(__name__)


class ConnectionState(str, Enum):
    """Connection state enumeration."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ConnectionInfo:
    """Information about a WebSocket connection."""
    websocket: WebSocket
    connection_id: str
    connected_at: datetime
    last_ping: Optional[datetime] = None
    last_pong: Optional[datetime] = None
    language: str = "lv"
    state: ConnectionState = ConnectionState.CONNECTED
    ping_failures: int = 0
    total_messages_sent: int = 0
    total_messages_received: int = 0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "connection_id": self.connection_id,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat() if self.last_ping else None,
            "last_pong": self.last_pong.isoformat() if self.last_pong else None,
            "language": self.language,
            "state": self.state.value,
            "ping_failures": self.ping_failures,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_received": self.total_messages_received,
            "uptime_seconds": (datetime.utcnow() - self.connected_at).total_seconds()
        }


class EnhancedConnectionManager:
    """Enhanced WebSocket connection manager with stability improvements."""
    
    def __init__(self, 
                 ping_interval: int = 30,
                 ping_timeout: int = 10,
                 max_ping_failures: int = 3,
                 cleanup_interval: int = 60):
        """
        Initialize the enhanced connection manager.
        
        Args:
            ping_interval: Seconds between ping messages
            ping_timeout: Seconds to wait for pong response
            max_ping_failures: Max consecutive ping failures before disconnect
            cleanup_interval: Seconds between connection cleanup runs
        """
        self.connections: Dict[str, ConnectionInfo] = {}
        self.ping_interval = ping_interval
        self.ping_timeout = ping_timeout
        self.max_ping_failures = max_ping_failures
        self.cleanup_interval = cleanup_interval
        
        # Statistics
        self.total_connections = 0
        self.total_disconnections = 0
        self.total_messages_broadcast = 0
        self.started_at = datetime.utcnow()
        
        # Background tasks
        self._ping_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._running = False
        
    async def start(self):
        """Start background tasks for connection management."""
        if self._running:
            return
            
        self._running = True
        self._ping_task = asyncio.create_task(self._ping_loop())
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("Enhanced WebSocket manager started")
        
    async def stop(self):
        """Stop background tasks and close all connections."""
        self._running = False
        
        # Cancel background tasks
        if self._ping_task:
            self._ping_task.cancel()
        if self._cleanup_task:
            self._cleanup_task.cancel()
            
        # Close all connections
        await self._close_all_connections()
        logger.info("Enhanced WebSocket manager stopped")
        
    async def connect(self, websocket: WebSocket, connection_id: Optional[str] = None) -> str:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            connection_id: Optional custom connection ID
            
        Returns:
            The connection ID assigned to this connection
        """
        try:
            await websocket.accept()
            
            # Generate connection ID if not provided
            if not connection_id:
                connection_id = f"ws_{int(time.time() * 1000)}_{len(self.connections)}"
            
            # Create connection info
            conn_info = ConnectionInfo(
                websocket=websocket,
                connection_id=connection_id,
                connected_at=datetime.utcnow(),
                state=ConnectionState.CONNECTED
            )
            
            self.connections[connection_id] = conn_info
            self.total_connections += 1
            
            logger.info(f"WebSocket connected: {connection_id} (Total: {len(self.connections)})")
            
            # Send welcome message
            await self._send_to_connection(connection_id, {
                "type": "connection_established",
                "connection_id": connection_id,
                "server_time": datetime.utcnow().isoformat(),
                "ping_interval": self.ping_interval
            })
            
            return connection_id
            
        except Exception as e:
            logger.error(f"Error accepting WebSocket connection: {e}")
            raise
    
    async def disconnect(self, connection_id: str, reason: str = "client_disconnect"):
        """
        Disconnect and clean up a WebSocket connection.
        
        Args:
            connection_id: The connection ID to disconnect
            reason: Reason for disconnection
        """
        if connection_id not in self.connections:
            return
            
        conn_info = self.connections[connection_id]
        conn_info.state = ConnectionState.DISCONNECTING
        
        try:
            # Send goodbye message if connection is still active
            if conn_info.websocket.client_state.name == "CONNECTED":
                await self._send_to_connection(connection_id, {
                    "type": "connection_closing",
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except Exception as e:
            logger.debug(f"Could not send goodbye message to {connection_id}: {e}")
        
        # Remove from connections
        del self.connections[connection_id]
        self.total_disconnections += 1
        
        logger.info(f"WebSocket disconnected: {connection_id} (Reason: {reason}, Remaining: {len(self.connections)})")
    
    async def send_personal_message(self, connection_id: str, message: Dict) -> bool:
        """
        Send a message to a specific connection.
        
        Args:
            connection_id: Target connection ID  
            message: Message dictionary to send
            
        Returns:
            True if message was sent successfully, False otherwise
        """
        return await self._send_to_connection(connection_id, message)
    
    async def broadcast_message(self, message: Dict, exclude_connections: Optional[Set[str]] = None) -> int:
        """
        Broadcast a message to all connected clients.
        
        Args:
            message: Message dictionary to broadcast
            exclude_connections: Set of connection IDs to exclude
            
        Returns:
            Number of connections that received the message
        """
        if not self.connections:
            return 0
            
        exclude_connections = exclude_connections or set()
        successful_sends = 0
        failed_connections = []
        
        # Add broadcast metadata
        message.update({
            "broadcast_timestamp": datetime.utcnow().isoformat(),
            "total_recipients": len(self.connections) - len(exclude_connections)
        })
        
        # Send to all connections
        for connection_id, conn_info in self.connections.items():
            if connection_id in exclude_connections:
                continue
                
            if await self._send_to_connection(connection_id, message):
                successful_sends += 1
            else:
                failed_connections.append(connection_id)
        
        # Clean up failed connections
        for connection_id in failed_connections:
            await self.disconnect(connection_id, "broadcast_failure")
        
        self.total_messages_broadcast += 1
        logger.debug(f"Broadcast sent to {successful_sends} connections")
        
        return successful_sends
    
    async def set_connection_language(self, connection_id: str, language: str):
        """Set the language preference for a connection."""
        if connection_id in self.connections:
            self.connections[connection_id].language = language
            logger.debug(f"Set language for {connection_id}: {language}")
    
    def get_connection_info(self, connection_id: str) -> Optional[Dict]:
        """Get connection information."""
        if connection_id in self.connections:
            return self.connections[connection_id].to_dict()
        return None
    
    def get_all_connections(self) -> Dict[str, Dict]:
        """Get information about all connections."""
        return {
            conn_id: conn_info.to_dict() 
            for conn_id, conn_info in self.connections.items()
        }
    
    def get_statistics(self) -> Dict:
        """Get manager statistics."""
        now = datetime.utcnow()
        uptime = (now - self.started_at).total_seconds()
        
        return {
            "active_connections": len(self.connections),
            "total_connections": self.total_connections,
            "total_disconnections": self.total_disconnections,
            "total_messages_broadcast": self.total_messages_broadcast,
            "uptime_seconds": uptime,
            "uptime_formatted": str(timedelta(seconds=int(uptime))),
            "started_at": self.started_at.isoformat(),
            "ping_interval": self.ping_interval,
            "ping_timeout": self.ping_timeout,
            "max_ping_failures": self.max_ping_failures,
            "connections_by_language": self._get_language_stats(),
            "connections_by_state": self._get_state_stats()
        }
    
    async def _send_to_connection(self, connection_id: str, message: Dict) -> bool:
        """
        Internal method to send message to a specific connection.
        
        Returns:
            True if successful, False if failed
        """
        if connection_id not in self.connections:
            return False
            
        conn_info = self.connections[connection_id]
        
        try:
            # Add connection metadata to message
            message.update({
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            json_message = json.dumps(message)
            await conn_info.websocket.send_text(json_message)
            
            conn_info.total_messages_sent += 1
            return True
            
        except WebSocketDisconnect:
            await self.disconnect(connection_id, "websocket_disconnect")
            return False
        except Exception as e:
            logger.error(f"Error sending message to {connection_id}: {e}")
            await self.disconnect(connection_id, "send_error")
            return False
    
    async def _ping_loop(self):
        """Background task to ping all connections periodically."""
        while self._running:
            try:
                await asyncio.sleep(self.ping_interval)
                
                if not self.connections:
                    continue
                
                # Send ping to all connections
                ping_tasks = []
                for connection_id in list(self.connections.keys()):
                    ping_tasks.append(self._ping_connection(connection_id))
                
                if ping_tasks:
                    await asyncio.gather(*ping_tasks, return_exceptions=True)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ping loop: {e}")
    
    async def _ping_connection(self, connection_id: str):
        """Ping a specific connection and handle response."""
        if connection_id not in self.connections:
            return
            
        conn_info = self.connections[connection_id]
        conn_info.last_ping = datetime.utcnow()
        
        # Send ping
        ping_sent = await self._send_to_connection(connection_id, {
            "type": "ping",
            "expects_pong": True
        })
        
        if not ping_sent:
            return
        
        # Wait for pong response
        try:
            await asyncio.sleep(self.ping_timeout)
            
            # Check if pong was received
            if (conn_info.last_pong is None or 
                conn_info.last_pong < conn_info.last_ping):
                
                conn_info.ping_failures += 1
                logger.warning(f"Ping timeout for {connection_id} (failures: {conn_info.ping_failures})")
                
                if conn_info.ping_failures >= self.max_ping_failures:
                    await self.disconnect(connection_id, "ping_timeout")
            else:
                # Reset failure count on successful pong
                conn_info.ping_failures = 0
                
        except Exception as e:
            logger.error(f"Error pinging connection {connection_id}: {e}")
    
    async def _cleanup_loop(self):
        """Background task to clean up stale connections."""
        while self._running:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                # Check for stale connections
                stale_connections = []
                cutoff_time = datetime.utcnow() - timedelta(minutes=5)
                
                for connection_id, conn_info in self.connections.items():
                    # Check if connection is unresponsive
                    if (conn_info.last_ping and 
                        not conn_info.last_pong and 
                        conn_info.last_ping < cutoff_time):
                        stale_connections.append(connection_id)
                
                # Clean up stale connections
                for connection_id in stale_connections:
                    await self.disconnect(connection_id, "stale_connection")
                
                if stale_connections:
                    logger.info(f"Cleaned up {len(stale_connections)} stale connections")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _close_all_connections(self):
        """Close all active connections."""
        connection_ids = list(self.connections.keys())
        
        for connection_id in connection_ids:
            await self.disconnect(connection_id, "server_shutdown")
    
    def _get_language_stats(self) -> Dict[str, int]:
        """Get statistics by language."""
        stats = {}
        for conn_info in self.connections.values():
            lang = conn_info.language
            stats[lang] = stats.get(lang, 0) + 1
        return stats
    
    def _get_state_stats(self) -> Dict[str, int]:
        """Get statistics by connection state."""
        stats = {}
        for conn_info in self.connections.values():
            state = conn_info.state.value
            stats[state] = stats.get(state, 0) + 1
        return stats
    
    async def handle_client_message(self, connection_id: str, message_data: str):
        """
        Handle incoming client message with proper error handling.
        
        Args:
            connection_id: Connection ID that sent the message
            message_data: Raw message data from client
        """
        if connection_id not in self.connections:
            return
            
        conn_info = self.connections[connection_id]
        conn_info.total_messages_received += 1
        
        try:
            # Parse JSON message
            message = json.loads(message_data)
            message_type = message.get("type", "")
            
            # Handle pong responses
            if message_type == "pong":
                conn_info.last_pong = datetime.utcnow()
                logger.debug(f"Received pong from {connection_id}")
                return
            
            # Handle other message types
            response = await self._process_client_message(connection_id, message)
            if response:
                await self._send_to_connection(connection_id, response)
                
        except json.JSONDecodeError:
            # Handle non-JSON messages
            await self._send_to_connection(connection_id, {
                "type": "error",
                "message": "Invalid JSON format",
                "received_data": message_data[:100]  # Limit for security
            })
        except Exception as e:
            logger.error(f"Error handling message from {connection_id}: {e}")
            await self._send_to_connection(connection_id, {
                "type": "error", 
                "message": "Internal server error"
            })
    
    async def _process_client_message(self, connection_id: str, message: Dict) -> Optional[Dict]:
        """
        Process a parsed client message and return response if needed.
        
        Args:
            connection_id: Connection ID
            message: Parsed message dictionary
            
        Returns:
            Response dictionary or None
        """
        message_type = message.get("type", "")
        conn_info = self.connections[connection_id]
        
        if message_type == "set_language":
            # Handle language switching
            new_language = message.get("language", "lv")
            if new_language in ["en", "lv", "ru"]:
                old_language = conn_info.language
                conn_info.language = new_language
                
                return {
                    "type": "language_changed",
                    "old_language": old_language,
                    "new_language": new_language,
                    "message": f"Language switched to {new_language}"
                }
            else:
                return {
                    "type": "error",
                    "message": f"Unsupported language: {new_language}"
                }
        
        elif message_type == "subscribe":
            # Handle subscription requests
            return {
                "type": "subscribed",
                "message": "Subscribed to real-time updates",
                "language": conn_info.language
            }
        
        elif message_type == "get_status":
            # Handle status requests
            return {
                "type": "status",
                "connection_info": conn_info.to_dict(),
                "server_stats": self.get_statistics()
            }
        
        else:
            return {
                "type": "echo",
                "original_message": message,
                "message": f"Received message type: {message_type}"
            }


# Global enhanced manager instance
enhanced_manager = EnhancedConnectionManager()