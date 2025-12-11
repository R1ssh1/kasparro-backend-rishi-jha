"""Test script to validate master entity implementation.

This script checks:
1. Migration file syntax
2. Model definitions
3. Master entity utility functions
"""
import sys
import importlib.util


def test_migration_syntax():
    """Test that the migration file has valid syntax."""
    print("Testing migration file syntax...")
    try:
        spec = importlib.util.spec_from_file_location(
            "migration",
            "migrations/versions/ae47cc2dd3ef_add_master_entities_and_mappings.py"
        )
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        
        # Check required functions exist
        assert hasattr(migration, 'upgrade'), "Migration missing upgrade function"
        assert hasattr(migration, 'downgrade'), "Migration missing downgrade function"
        assert migration.revision == 'ae47cc2dd3ef', "Invalid revision ID"
        assert migration.down_revision == 'dd46bb1cc2bd', "Invalid down_revision"
        
        print("✓ Migration file syntax is valid")
        return True
    except Exception as e:
        print(f"✗ Migration file syntax error: {e}")
        return False


def test_model_definitions():
    """Test that model definitions are valid."""
    print("\nTesting model definitions...")
    try:
        from core.models import MasterEntity, EntityMapping, Coin
        
        # Check MasterEntity attributes
        assert hasattr(MasterEntity, '__tablename__'), "MasterEntity missing __tablename__"
        assert MasterEntity.__tablename__ == "master_entities", "Wrong table name"
        
        # Check EntityMapping attributes
        assert hasattr(EntityMapping, '__tablename__'), "EntityMapping missing __tablename__"
        assert EntityMapping.__tablename__ == "entity_mappings", "Wrong table name"
        
        print("✓ Model definitions are valid")
        return True
    except Exception as e:
        print(f"✗ Model definition error: {e}")
        return False


def test_master_entity_utilities():
    """Test that master entity utility functions exist."""
    print("\nTesting master entity utilities...")
    try:
        from core.master_entity import (
            find_or_create_master_entity,
            link_coin_to_master_entity,
            process_coin_for_master_entity,
            KNOWN_SYMBOLS
        )
        
        # Check known symbols
        assert 'BTC' in KNOWN_SYMBOLS, "BTC not in KNOWN_SYMBOLS"
        assert 'ETH' in KNOWN_SYMBOLS, "ETH not in KNOWN_SYMBOLS"
        assert KNOWN_SYMBOLS['BTC']['name'] == 'Bitcoin', "Wrong BTC name"
        
        print("✓ Master entity utilities are valid")
        print(f"  - Known symbols: {len(KNOWN_SYMBOLS)} cryptocurrencies")
        return True
    except Exception as e:
        print(f"✗ Master entity utility error: {e}")
        return False


def test_docker_compose_env_vars():
    """Test that docker-compose.yml uses environment variables."""
    print("\nTesting docker-compose.yml...")
    try:
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
        
        # Check for environment variable usage
        assert '${DATABASE_USER' in content, "DATABASE_USER not using env var"
        assert '${DATABASE_PASSWORD' in content, "DATABASE_PASSWORD not using env var"
        assert '${DATABASE_NAME' in content, "DATABASE_NAME not using env var"
        
        # Check that hardcoded passwords are removed
        assert 'POSTGRES_PASSWORD: kasparro' not in content, "Hardcoded password still present"
        
        print("✓ docker-compose.yml uses environment variables")
        return True
    except Exception as e:
        print(f"✗ docker-compose.yml error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("Master Entity Implementation Validation")
    print("=" * 60)
    
    results = []
    results.append(("Migration Syntax", test_migration_syntax()))
    results.append(("Model Definitions", test_model_definitions()))
    results.append(("Utility Functions", test_master_entity_utilities()))
    results.append(("Docker Compose", test_docker_compose_env_vars()))
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    
    for name, passed in results:
        status = "PASS" if passed else "FAIL"
        symbol = "✓" if passed else "✗"
        print(f"{symbol} {name:<30} {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✓ All tests passed! Implementation is ready.")
        return 0
    else:
        print("✗ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
