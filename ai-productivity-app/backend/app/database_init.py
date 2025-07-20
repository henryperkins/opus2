"""Initialize database extensions before starting the application"""
import os
import sys
import logging

logger = logging.getLogger(__name__)

def init_database_extensions():
    """Create required PostgreSQL extensions"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL not set")
        return False
    
    try:
        # Import here to avoid circular imports
        from sqlalchemy import create_engine, text
        
        # Use psycopg dialect explicitly
        if 'postgresql://' in db_url:
            db_url = db_url.replace('postgresql://', 'postgresql+psycopg://')
            
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Create extensions
            extensions = ['pg_trgm', 'uuid-ossp']
            for ext in extensions:
                try:
                    conn.execute(text(f'CREATE EXTENSION IF NOT EXISTS "{ext}"'))
                    conn.commit()
                    logger.info(f"Extension '{ext}' created/verified")
                except Exception as e:
                    logger.warning(f"Could not create extension '{ext}': {e}")
                    # Continue anyway - the extension might already exist
            
            # Verify pg_trgm is available
            result = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'"))
            if result.fetchone():
                logger.info("pg_trgm extension is available")
                return True
            else:
                logger.error("pg_trgm extension is not available")
                return False
                
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        return False

if __name__ == "__main__":
    if not init_database_extensions():
        sys.exit(1)