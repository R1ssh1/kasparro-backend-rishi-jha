"""Quick script to check database migration status."""
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://kasparro_admin:KasparroSecure2024!@kasparro-postgres.cp8acayqwl5q.ap-south-2.rds.amazonaws.com:5432/kasparro"

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    # Check alembic version
    result = conn.execute(text("SELECT version_num FROM alembic_version"))
    version = result.scalar()
    print(f"Current alembic version: {version}")
    
    # List all tables
    result = conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename"))
    tables = [row[0] for row in result]
    print(f"\nTables in database ({len(tables)}):")
    for table in tables:
        print(f"  - {table}")
    
    # Check if master_entities exists
    has_master_entities = 'master_entities' in tables
    print(f"\nmaster_entities table exists: {has_master_entities}")
    
    if not has_master_entities:
        print("\n⚠️  Migration 'ae47cc2dd3ef' (master entities) needs to be run!")
