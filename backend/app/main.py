"""FastAPI application entry point"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.websocket.manager import manager
from app.database import engine
from sqlalchemy import text
import uuid

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Startup tasks"""
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    ensure_schema_updates()
    # Start WebSocket heartbeat monitor
    manager.start_monitor()


def ensure_schema_updates():
    """Apply lightweight idempotent schema updates for existing installations."""
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE scripts ADD COLUMN IF NOT EXISTS argument_schema JSONB"))


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.websocket("/ws/{connection_id}")
async def websocket_endpoint(websocket: WebSocket, connection_id: str):
    """WebSocket endpoint"""
    await manager.connect(websocket, connection_id)
    
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get('type')
            
            if msg_type == 'ping':
                await manager.handle_ping(connection_id, data)
            
            elif msg_type == 'subscribe':
                task_id = data.get('task_id')
                await manager.subscribe_task(connection_id, task_id)
                
                # Send current task status
                await manager.send_personal_message(connection_id, {
                    'type': 'task_update',
                    'task_id': task_id,
                    'data': {'status': 'subscribed'}
                })
            
            elif msg_type == 'unsubscribe':
                task_id = data.get('task_id')
                await manager.unsubscribe_task(connection_id, task_id)
    
    except WebSocketDisconnect:
        manager.disconnect(connection_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(connection_id)


# Import and include API routers
from app.api.v1 import models, datasets, scripts, batches, comparisons, task_groups, task_instances

app.include_router(models.router, prefix="/api/v1/models", tags=["models"])
app.include_router(datasets.router, prefix="/api/v1/datasets", tags=["datasets"])
app.include_router(scripts.router, prefix="/api/v1/scripts", tags=["scripts"])
app.include_router(batches.router, prefix="/api/v1/batches", tags=["batches"])
app.include_router(task_groups.router, prefix="/api/v1/task-groups", tags=["task-groups"])
app.include_router(task_instances.router, prefix="/api/v1/task-instances", tags=["task-instances"])
app.include_router(comparisons.router, prefix="/api/v1/comparisons", tags=["comparisons"])
