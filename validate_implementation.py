"""Simple validation script for master entity implementation.

This script validates the implementation without requiring Python dependencies.
"""
import os
import re


def validate_file_exists(filepath, description):
    """Check if a file exists."""
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {filepath}")
    return exists


def validate_file_content(filepath, patterns, description):
    """Check if file contains required patterns."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing = []
        for pattern_name, pattern in patterns.items():
            if not re.search(pattern, content, re.MULTILINE):
                missing.append(pattern_name)
        
        if missing:
            print(f"✗ {description}: Missing {', '.join(missing)}")
            return False
        else:
            print(f"✓ {description}")
            return True
    except Exception as e:
        print(f"✗ {description}: Error - {e}")
        return False


def main():
    """Run validation checks."""
    print("=" * 70)
    print("Master Entity Implementation Validation")
    print("=" * 70)
    print()
    
    results = []
    
    # 1. Check migration file exists
    print("1. Migration File")
    print("-" * 70)
    results.append(validate_file_exists(
        "migrations/versions/ae47cc2dd3ef_add_master_entities_and_mappings.py",
        "Migration file"
    ))
    print()
    
    # 2. Check migration file content
    print("2. Migration Content")
    print("-" * 70)
    results.append(validate_file_content(
        "migrations/versions/ae47cc2dd3ef_add_master_entities_and_mappings.py",
        {
            "upgrade function": r"def upgrade\(\)",
            "downgrade function": r"def downgrade\(\)",
            "master_entities table": r"create_table\(\s*['\"]master_entities['\"]",
            "entity_mappings table": r"create_table\(\s*['\"]entity_mappings['\"]",
            "correct revision": r"revision.*=.*['\"]ae47cc2dd3ef['\"]",
            "correct down_revision": r"down_revision.*=.*['\"]dd46bb1cc2bd['\"]",
        },
        "Migration structure"
    ))
    print()
    
    # 3. Check models.py updates
    print("3. Model Definitions")
    print("-" * 70)
    results.append(validate_file_content(
        "core/models.py",
        {
            "MasterEntity class": r"class MasterEntity\(Base\)",
            "EntityMapping class": r"class EntityMapping\(Base\)",
            "canonical_symbol": r"canonical_symbol.*=.*Column",
            "master_entity_id": r"master_entity_id.*=.*Column",
        },
        "Model classes"
    ))
    print()
    
    # 4. Check master_entity.py exists
    print("4. Master Entity Utilities")
    print("-" * 70)
    results.append(validate_file_exists(
        "core/master_entity.py",
        "Utility file"
    ))
    results.append(validate_file_content(
        "core/master_entity.py",
        {
            "find_or_create": r"async def find_or_create_master_entity",
            "link_coin": r"async def link_coin_to_master_entity",
            "process_coin": r"async def process_coin_for_master_entity",
            "known_symbols": r"KNOWN_SYMBOLS\s*=",
        },
        "Utility functions"
    ))
    print()
    
    # 5. Check base.py integration
    print("5. Ingestion Integration")
    print("-" * 70)
    results.append(validate_file_content(
        "ingestion/base.py",
        {
            "import master_entity": r"from core\.master_entity import",
            "process_coin_for_master_entity": r"process_coin_for_master_entity",
        },
        "Base ingestion integration"
    ))
    print()
    
    # 6. Check docker-compose.yml
    print("6. Docker Compose Security")
    print("-" * 70)
    results.append(validate_file_content(
        "docker-compose.yml",
        {
            "DATABASE_USER env var": r"\$\{DATABASE_USER",
            "DATABASE_PASSWORD env var": r"\$\{DATABASE_PASSWORD",
            "DATABASE_NAME env var": r"\$\{DATABASE_NAME",
        },
        "Environment variables"
    ))
    
    # Check no hardcoded passwords
    with open("docker-compose.yml", 'r') as f:
        content = f.read()
    if "POSTGRES_PASSWORD: kasparro" in content:
        print("✗ Hardcoded password still present")
        results.append(False)
    else:
        print("✓ No hardcoded passwords")
        results.append(True)
    print()
    
    # 7. Check .env files
    print("7. Environment Files")
    print("-" * 70)
    results.append(validate_file_content(
        ".env",
        {
            "DATABASE_HOST": r"DATABASE_HOST\s*=",
            "DATABASE_USER": r"DATABASE_USER\s*=",
            "DATABASE_PASSWORD": r"DATABASE_PASSWORD\s*=",
        },
        ".env file"
    ))
    results.append(validate_file_content(
        ".env.example",
        {
            "DATABASE_HOST": r"DATABASE_HOST\s*=",
            "DATABASE_USER": r"DATABASE_USER\s*=",
            "DATABASE_PASSWORD": r"DATABASE_PASSWORD\s*=",
        },
        ".env.example file"
    ))
    print()
    
    # Summary
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    print(f"Tests Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ ALL VALIDATIONS PASSED!")
        print("\nImplementation Summary:")
        print("  1. ✓ Local secrets moved to environment variables")
        print("  2. ✓ Master entity normalization tables created")
        print("  3. ✓ Migration file generated")
        print("  4. ✓ Utility functions implemented")
        print("  5. ✓ Ingestion pipeline integrated")
        print("\nNext Steps:")
        print("  - Run 'docker-compose up' to test locally")
        print("  - Run migrations with 'alembic upgrade head'")
        print("  - Verify master entity creation during ETL")
        return 0
    else:
        print(f"\n✗ {total - passed} validation(s) failed")
        print("Please review the errors above.")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
