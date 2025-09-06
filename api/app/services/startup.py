"""
Service startup and initialization tasks
"""

import os
import logging
from typing import Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import redis
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

logger = logging.getLogger(__name__)

def init_qdrant_collections():
    """Initialize Qdrant collections if they don't exist"""
    try:
        client = QdrantClient(
            url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        
        collections = ["brand_assets", "design_references", "generated_images"]
        
        for collection_name in collections:
            try:
                # Check if collection exists
                client.get_collection(collection_name)
                logger.info(f"Collection {collection_name} already exists")
            except Exception:
                # Create collection if it doesn't exist
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
                )
                logger.info(f"Created collection {collection_name}")
                
                # Add a dummy vector to initialize the collection
                import uuid
                client.upsert(
                    collection_name=collection_name,
                    points=[
                        PointStruct(
                            id=str(uuid.uuid4()),
                            vector=[0.0] * 768,
                            payload={
                                "type": "initialization",
                                "content": "Initial placeholder vector"
                            }
                        )
                    ]
                )
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant collections: {e}")
        return False

def init_redis():
    """Test Redis connection"""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url)
        r.ping()
        logger.info("Redis connection successful")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        return False

def init_postgres():
    """Initialize PostgreSQL database and run migrations"""
    try:
        # Parse DATABASE_URL
        db_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sgd_db")
        
        # Extract components
        import urllib.parse
        parsed = urllib.parse.urlparse(db_url)
        
        # First connect to postgres database to create sgd_db if needed
        try:
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                user=parsed.username,
                password=parsed.password,
                database="postgres"
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            
            # Check if database exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'sgd_db'")
            if not cur.fetchone():
                cur.execute("CREATE DATABASE sgd_db")
                logger.info("Created database sgd_db")
            
            cur.close()
            conn.close()
        except Exception as e:
            logger.warning(f"Could not create database (may already exist): {e}")
        
        # Now connect to sgd_db and run migrations
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        # Check if migrations have been run
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'projects'
            )
        """)
        
        if not cur.fetchone()[0]:
            # Run migrations
            migration_path = "/app/infra/migrations/001_initial.sql"
            if os.path.exists(migration_path):
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                cur.execute(migration_sql)
                conn.commit()
                logger.info("Database migrations completed")
            else:
                logger.warning(f"Migration file not found: {migration_path}")
        else:
            logger.info("Database already initialized")
        
        cur.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize PostgreSQL: {e}")
        return False

def run_startup_tasks():
    """Run all startup initialization tasks"""
    logger.info("Running startup tasks...")
    
    tasks = [
        ("PostgreSQL", init_postgres),
        ("Redis", init_redis),
        ("Qdrant", init_qdrant_collections)
    ]
    
    results = []
    for name, task in tasks:
        try:
            success = task()
            results.append((name, success))
            if success:
                logger.info(f"✓ {name} initialized successfully")
            else:
                logger.warning(f"✗ {name} initialization failed")
        except Exception as e:
            logger.error(f"✗ {name} initialization error: {e}")
            results.append((name, False))
    
    # Return True if all critical services are ready
    critical_services = ["Redis", "Qdrant"]
    all_critical_ready = all(
        success for name, success in results 
        if name in critical_services
    )
    
    if all_critical_ready:
        logger.info("All critical services initialized successfully")
    else:
        logger.warning("Some critical services failed to initialize")
    
    return all_critical_ready