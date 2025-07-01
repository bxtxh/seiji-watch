-- Initialize pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Grant permissions to user
GRANT ALL PRIVILEGES ON DATABASE seiji_watch TO seiji_watch_user;
GRANT ALL ON SCHEMA public TO seiji_watch_user;

-- Create basic tables (will be managed by Alembic migrations later)
-- This is just for initial development setup

-- Test table to verify pgvector is working
CREATE TABLE IF NOT EXISTS test_embeddings (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    embedding vector(1536),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert test data
INSERT INTO test_embeddings (content, embedding) VALUES 
('テスト用データ1', '[0.1, 0.2, 0.3]'::vector),
('テスト用データ2', '[0.4, 0.5, 0.6]'::vector)
ON CONFLICT DO NOTHING;