"""WebSocket connection manager with heartbeat mechanism"""
from fastapi import WebSocket
from typing import Dict, Set
import asyncio
import time
import json
from app.config import settings


class ConnectionManager:
    """Manages WebSocket connections with heartbeat monitoring"""
    
    def __init__(self):
        # Active connections: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Connection metadata: {connection_id: metadata}
        self.connection_metadata: Dict[str, dict] = {}
        
        # Subscription relationships: {task_id: set(connection_ids)}
        self.task_subscriptions: Dict[int, Set[str]] = {}
        
        # Heartbeat status: {connection_id: last_ping_time}
        self.heartbeats: Dict[str, float] = {}
        
        # Configuration
        self.HEARTBEAT_INTERVAL = settings.WS_HEARTBEAT_INTERVAL
        self.HEARTBEAT_TIMEOUT = settings.WS_HEARTBEAT_TIMEOUT
        self.CLEANUP_INTERVAL = settings.WS_CLEANUP_INTERVAL
        
        # Start background monitor
        self._monitor_task = None
    
    def start_monitor(self):
        """Start heartbeat monitor (call this once at app startup)"""
        if self._monitor_task is None:
            self._monitor_task = asyncio.create_task(self._heartbeat_monitor())
    
    async def connect(self, websocket: WebSocket, connection_id: str):
        """Accept new connection"""
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            'connected_at': time.time(),
            'subscribed_tasks': set()
        }
        self.heartbeats[connection_id] = time.time()
        
        # Send connection confirmation
        await self.send_personal_message(connection_id, {
            'type': 'connected',
            'connection_id': connection_id,
            'server_time': time.time()
        })
    
    def disconnect(self, connection_id: str):
        """Disconnect connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        if connection_id in self.connection_metadata:
            # Clean up subscriptions
            for task_id in self.connection_metadata[connection_id]['subscribed_tasks']:
                if task_id in self.task_subscriptions:
                    self.task_subscriptions[task_id].discard(connection_id)
            del self.connection_metadata[connection_id]
        if connection_id in self.heartbeats:
            del self.heartbeats[connection_id]
    
    async def handle_ping(self, connection_id: str, data: dict):
        """Handle heartbeat ping"""
        self.heartbeats[connection_id] = time.time()
        
        # Immediately reply with pong
        await self.send_personal_message(connection_id, {
            'type': 'pong',
            'timestamp': data.get('timestamp'),
            'server_time': time.time()
        })
    
    async def _heartbeat_monitor(self):
        """Background task: monitor heartbeat timeouts"""
        while True:
            await asyncio.sleep(self.CLEANUP_INTERVAL)
            
            current_time = time.time()
            expired_connections = []
            
            for conn_id, last_ping in list(self.heartbeats.items()):
                if current_time - last_ping > self.HEARTBEAT_TIMEOUT:
                    expired_connections.append(conn_id)
            
            # Clean up expired connections
            for conn_id in expired_connections:
                print(f"Connection {conn_id} timed out (no heartbeat)")
                if conn_id in self.active_connections:
                    try:
                        await self.active_connections[conn_id].close(
                            code=1000,
                            reason="Heartbeat timeout"
                        )
                    except:
                        pass
                self.disconnect(conn_id)
    
    async def subscribe_task(self, connection_id: str, task_id: int):
        """Subscribe to task updates"""
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        self.task_subscriptions[task_id].add(connection_id)
        
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]['subscribed_tasks'].add(task_id)
    
    async def unsubscribe_task(self, connection_id: str, task_id: int):
        """Unsubscribe from task"""
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(connection_id)
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]['subscribed_tasks'].discard(task_id)
    
    async def broadcast_task_update(self, task_id: int, data: dict):
        """Broadcast task update to all subscribers"""
        if task_id not in self.task_subscriptions:
            return
        
        dead_connections = []
        for conn_id in self.task_subscriptions[task_id]:
            if conn_id in self.active_connections:
                try:
                    await self.active_connections[conn_id].send_json(data)
                except Exception as e:
                    print(f"Failed to send to {conn_id}: {e}")
                    dead_connections.append(conn_id)
        
        # Clean up dead connections
        for conn_id in dead_connections:
            self.disconnect(conn_id)
    
    async def send_personal_message(self, connection_id: str, data: dict):
        """Send personal message"""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_json(data)
            except Exception as e:
                print(f"Failed to send to {connection_id}: {e}")


# Global connection manager instance
manager = ConnectionManager()
