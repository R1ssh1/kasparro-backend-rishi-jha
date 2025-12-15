#!/usr/bin/env python3
"""Script to manually create master_entities tables if they don't exist."""
import os
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL_SYNC",
    "postgresql://kasparro_admin:KasparroSecure2024!@kasparro-postgres.cp8acayqwl5q.ap-south-2.rds.amazonaws.com:5432/kasparro"
)

print("=" * 60)
print("Creating master_entities tables")
print("=" * 60)

engine = create_engine(DATABASE_URL)

SQL_STATEMENTS = """
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
"""

try:
    with engine.connect() as conn:
        # Execute each statement
        for statement in SQL_STATEMENTS.strip().split(';'):
            if statement.strip():
                conn.execute(text(statement.strip()))
                conn.commit()
        
        # Verify tables exist
        result = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('master_entities', 'entity_mappings')
            ORDER BY table_name
        """))
        tables = [row[0] for row in result]
        
        print("\n✅ Tables created successfully:")
        for table in tables:
            print(f"   - {table}")
        
        if len(tables) == 2:
            print("\n🎉 All master entity tables are now ready!")
        else:
            print(f"\n⚠️  Only {len(tables)}/2 tables found. Please check for errors.")
            
except Exception as e:
    print(f"\n❌ Error creating tables: {e}")
    raise
finally:
    engine.dispose()
