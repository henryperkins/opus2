#!/usr/bin/env python3
"""Simple migration runner"""
import sqlite3
import os

def run_migration():
    db_path = "data/app.db"

    if not os.path.exists(db_path):
        print("Database not found - run the app first to create it")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(projects)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'color' not in columns:
        print("Adding color column...")
        cursor.execute("ALTER TABLE projects ADD COLUMN color VARCHAR(7) DEFAULT '#3B82F6'")

    if 'emoji' not in columns:
        print("Adding emoji column...")
        cursor.execute("ALTER TABLE projects ADD COLUMN emoji VARCHAR(10) DEFAULT '📁'")

    if 'tags' not in columns:
        print("Adding tags column...")
        cursor.execute("ALTER TABLE projects ADD COLUMN tags JSON DEFAULT '[]'")

    conn.commit()
    conn.close()
    print("Migration complete!")

if __name__ == "__main__":
    run_migration()
