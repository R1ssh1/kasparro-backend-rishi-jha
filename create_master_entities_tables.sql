-- SQL to manually create master_entities and entity_mappings tables
-- Based on migration ae47cc2dd3ef_add_master_entities_and_mappings.py

-- Create master_entities table
CREATE TABLE IF NOT EXISTS master_entities (
    id SERIAL PRIMARY KEY,
    canonical_symbol VARCHAR(20) NOT NULL UNIQUE,
    canonical_name VARCHAR(200) NOT NULL,
    entity_type VARCHAR(50),
    primary_source VARCHAR(50) NOT NULL,
    primary_coin_id INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_master_entities_symbol_name ON master_entities (canonical_symbol, canonical_name);
CREATE UNIQUE INDEX IF NOT EXISTS ix_master_entities_canonical_symbol ON master_entities (canonical_symbol);

-- Create entity_mappings table
CREATE TABLE IF NOT EXISTS entity_mappings (
    id SERIAL PRIMARY KEY,
    master_entity_id INTEGER NOT NULL,
    coin_id INTEGER NOT NULL UNIQUE,
    source VARCHAR(50) NOT NULL,
    confidence NUMERIC(5, 3),
    is_primary INTEGER,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    CONSTRAINT uq_coin_id UNIQUE (coin_id)
);

CREATE INDEX IF NOT EXISTS ix_entity_mappings_master_entity ON entity_mappings (master_entity_id);

-- Verify tables were created
SELECT 'master_entities' as table_name, COUNT(*) as exists FROM information_schema.tables WHERE table_name = 'master_entities'
UNION ALL
SELECT 'entity_mappings' as table_name, COUNT(*) as exists FROM information_schema.tables WHERE table_name = 'entity_mappings';
