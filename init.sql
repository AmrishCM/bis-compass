-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create schemas if needed
DO $$ BEGIN
    CREATE SCHEMA IF NOT EXISTS bis_compass;
EXCEPTION
    WHEN duplicate_schema THEN null;
END $$;

-- Set search path
SET search_path TO bis_compass, public;