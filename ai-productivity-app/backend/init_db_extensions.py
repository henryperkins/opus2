#!/usr/bin/env python3
"""Initialize PostgreSQL extensions required by the application"""

import os
import sys
from sqlalchemy import create_engine, text

def init_extensions():
    """Create required PostgreSQL extensions"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)
    
    print(f"Connecting to database...")
    
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            # Test connection
            result = conn.execute(text("SELECT version()"))
            print(f"PostgreSQL version: {result.fetchone()[0]}")
            
            # Create extensions
            extensions = ['pg_trgm', 'uuid-ossp']
            for ext in extensions:
                try:
                    conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {ext}"))
                    conn.commit()
                    print(f"✓ Extension '{ext}' created/verified")
                except Exception as e:
                    print(f"✗ Error creating extension '{ext}': {e}")
                    raise
            
            # Verify extensions
            result = conn.execute(text("SELECT extname FROM pg_extension WHERE extname IN ('pg_trgm', 'uuid-ossp')"))
            installed = [row[0] for row in result]
            print(f"\nInstalled extensions: {', '.join(installed)}")
            
            if 'pg_trgm' not in installed:
                print("\nERROR: pg_trgm extension is required but not installed.")
                print("Please run: CREATE EXTENSION pg_trgm; in your PostgreSQL database")
                sys.exit(1)
                
    except Exception as e:
        print(f"\nERROR: Failed to initialize database extensions: {e}")
        sys.exit(1)

if __name__ == "__main__":
    init_extensions()