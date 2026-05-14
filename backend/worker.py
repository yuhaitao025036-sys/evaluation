"""RQ Worker startup script"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from redis import Redis
from rq import Worker, Queue, Connection
from app.config import settings

# Connect to Redis
redis_conn = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None
)

if __name__ == '__main__':
    # Listen to the default queue
    with Connection(redis_conn):
        worker = Worker([settings.RQ_QUEUE_NAME], connection=redis_conn)
        print(f"Worker started, listening to queue: {settings.RQ_QUEUE_NAME}")
        worker.work()
