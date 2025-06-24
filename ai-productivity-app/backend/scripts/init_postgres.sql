-- PostgreSQL initialization script for AI Productivity App
-- This script sets up the database with necessary extensions and configurations

-- Enable UUID extension for generating UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for cryptographic functions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Enable full-text search capabilities
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Enable vector similarity search (pgvector extension)
-- Uncomment when pgvector is available in your PostgreSQL instance
-- CREATE EXTENSION IF NOT EXISTS "vector";

-- Enable additional text search features
CREATE EXTENSION IF NOT EXISTS "unaccent";

-- Set timezone to UTC
SET timezone = 'UTC';

-- Configure search path for extensions
ALTER DATABASE ai_productivity SET search_path TO public, extensions;

-- Create custom text search configuration for better search
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS ai_english (COPY = english);

-- Add custom text processing functions
CREATE OR REPLACE FUNCTION normalize_code_text(text) 
RETURNS text AS $$
BEGIN
    -- Remove common code symbols and normalize for search
    RETURN regexp_replace(
        regexp_replace($1, '[(){}\[\]<>;,.]', ' ', 'g'),
        '\s+', ' ', 'g'
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Enable query performance monitoring
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Set recommended PostgreSQL configuration for AI workloads
ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
ALTER SYSTEM SET pg_stat_statements.track = 'all';
ALTER SYSTEM SET pg_stat_statements.max = 10000;
ALTER SYSTEM SET work_mem = '256MB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET random_page_cost = 1.1;

-- Reload configuration
SELECT pg_reload_conf();