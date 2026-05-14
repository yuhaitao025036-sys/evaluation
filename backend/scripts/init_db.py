#!/usr/bin/env python3
"""
Database initialization script
Creates all tables and indexes
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import engine, Base
from app.models import *
from sqlalchemy import text


def init_database():
    """Initialize database tables"""
    print("🔧 Initializing DUCC Evaluation System Database...")
    print("")
    
    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✓ Connected to PostgreSQL")
            print(f"  Version: {version.split(',')[0]}")
            print("")
        
        # Create all tables
        print("📋 Creating tables...")
        Base.metadata.create_all(bind=engine)
        print("✓ All tables created successfully")
        print("")
        
        # List created tables
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            tables = [row[0] for row in result]
            
            print(f"📊 Created {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
            print("")
        
        # List created indexes
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE schemaname = 'public'
                AND indexname NOT LIKE '%_pkey'
                ORDER BY indexname
            """))
            indexes = [row[0] for row in result]
            
            print(f"🔍 Created {len(indexes)} indexes:")
            for index in indexes:
                print(f"   - {index}")
            print("")
        
        print("✅ Database initialization complete!")
        return 0
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(init_database())
