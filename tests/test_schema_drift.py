"""Tests for schema drift detection."""
import pytest
from core.schema_drift import SchemaDriftDetector


@pytest.mark.asyncio
async def test_schema_drift_exact_match(db_session):
    """Test no drift when schema matches exactly."""
    detector = SchemaDriftDetector("test_source", db_session)
    
    expected_fields = {"id", "name", "price", "volume"}
    detector.register_schema("test_schema", expected_fields)
    
    actual_data = {
        "id": "btc",
        "name": "Bitcoin",
        "price": 50000.0,
        "volume": 1000000.0
    }
    
    report = detector.detect_drift("test_schema", actual_data)
    
    assert report["drift_detected"] is False
    assert report["confidence"] == 1.0
    assert len(report["missing_fields"]) == 0
    assert len(report["extra_fields"]) == 0


@pytest.mark.asyncio
async def test_schema_drift_missing_fields(db_session):
    """Test drift detection when fields are missing."""
    detector = SchemaDriftDetector("test_source", db_session)
    
    expected_fields = {"id", "name", "price", "volume", "market_cap"}
    detector.register_schema("test_schema", expected_fields)
    
    actual_data = {
        "id": "btc",
        "name": "Bitcoin"
        # Missing: price, volume, market_cap
    }
    
    report = detector.detect_drift("test_schema", actual_data)
    
    assert report["drift_detected"] is True
    assert report["confidence"] < 1.0
    assert "price" in report["missing_fields"]
    assert "volume" in report["missing_fields"]
    assert "market_cap" in report["missing_fields"]
    assert len(report["warnings"]) > 0


@pytest.mark.asyncio
async def test_schema_drift_extra_fields(db_session):
    """Test drift detection when unexpected fields appear."""
    detector = SchemaDriftDetector("test_source", db_session)
    
    expected_fields = {"id", "name", "price"}
    detector.register_schema("test_schema", expected_fields)
    
    actual_data = {
        "id": "btc",
        "name": "Bitcoin",
        "price": 50000.0,
        "unexpected_field1": "value1",
        "unexpected_field2": "value2"
    }
    
    report = detector.detect_drift("test_schema", actual_data)
    
    assert report["drift_detected"] is True
    assert "unexpected_field1" in report["extra_fields"]
    assert "unexpected_field2" in report["extra_fields"]


@pytest.mark.asyncio
async def test_schema_drift_fuzzy_matching(db_session):
    """Test fuzzy matching for renamed fields."""
    detector = SchemaDriftDetector("test_source", db_session)
    
    expected_fields = {"current_price", "market_cap"}
    detector.register_schema("test_schema", expected_fields)
    
    # Field renamed: current_price -> currentPrice (camelCase)
    actual_data = {
        "currentPrice": 50000.0,
        "market_cap": 1000000.0
    }
    
    report = detector.detect_drift("test_schema", actual_data)
    
    assert report["drift_detected"] is True
    assert "current_price" in report["missing_fields"]
    assert "currentPrice" in report["extra_fields"]
    # Should detect fuzzy match
    assert len(report["fuzzy_matches"]) > 0
    assert len(report["warnings"]) > 0


@pytest.mark.asyncio
async def test_schema_drift_batch_analysis(db_session):
    """Test batch analysis across multiple records."""
    detector = SchemaDriftDetector("test_source", db_session)
    
    expected_fields = {"id", "name", "price"}
    detector.register_schema("test_schema", expected_fields)
    
    records = [
        {"id": "btc", "name": "Bitcoin", "price": 50000.0},
        {"id": "eth", "name": "Ethereum"},  # Missing price (33% < threshold)
        {"id": "ada", "extra1": "foo", "extra2": "bar"},  # Missing 2/3 fields (66% > 50% threshold)
    ]
    
    report = await detector.analyze_batch("test_schema", records, sample_size=10)
    
    assert report["sample_count"] == 3
    assert report["drift_count"] >= 1  # Third record has >50% missing
    assert report["drift_ratio"] > 0.0


@pytest.mark.asyncio
async def test_confidence_scoring(db_session):
    """Test confidence score calculation."""
    detector = SchemaDriftDetector("test_source", db_session)
    
    expected_fields = {"a", "b", "c", "d", "e"}  # 5 fields
    detector.register_schema("test_schema", expected_fields)
    
    # 3 out of 5 fields present (60% confidence)
    actual_data = {"a": 1, "b": 2, "c": 3}
    
    report = detector.detect_drift("test_schema", actual_data)
    
    assert 0.5 <= report["confidence"] <= 0.7
