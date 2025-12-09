"""Tests for failure injection and recovery."""
import pytest
from core.failure_injector import FailureInjector, FailureType


def test_failure_injector_disabled():
    """Test that injector does nothing when disabled."""
    injector = FailureInjector(enabled=False)
    injector.configure(probability=1.0, failure_type=FailureType.NETWORK_ERROR)
    
    # Should not fail even with 100% probability
    assert injector.should_fail() is False


def test_failure_injector_specific_record():
    """Test failure at specific record index."""
    injector = FailureInjector(enabled=True)
    injector.configure(fail_at_record=5)
    
    # Should not fail at other records
    assert injector.should_fail(record_index=1) is False
    assert injector.should_fail(record_index=4) is False
    
    # Should fail at record 5
    assert injector.should_fail(record_index=5) is True


def test_failure_injector_probability():
    """Test probabilistic failure injection."""
    injector = FailureInjector(enabled=True)
    injector.configure(probability=1.0)  # 100% failure
    
    # Should always fail with 100% probability
    assert injector.should_fail() is True


def test_failure_injector_raises_correct_error():
    """Test that correct exception types are raised."""
    injector = FailureInjector(enabled=True)
    
    # Network error
    injector.configure(failure_type=FailureType.NETWORK_ERROR)
    with pytest.raises(ConnectionError):
        injector.raise_failure("Test network error")
    
    # Database error
    injector.configure(failure_type=FailureType.DATABASE_ERROR)
    with pytest.raises(RuntimeError):
        injector.raise_failure("Test database error")
    
    # Timeout
    injector.configure(failure_type=FailureType.TIMEOUT)
    with pytest.raises(TimeoutError):
        injector.raise_failure("Test timeout")


def test_failure_injector_inject_if_enabled():
    """Test the combined check and inject method."""
    injector = FailureInjector(enabled=True)
    injector.configure(
        probability=1.0,
        failure_type=FailureType.VALIDATION_ERROR
    )
    
    with pytest.raises(ValueError):
        injector.inject_if_enabled(message="Test injection")


def test_failure_injector_configuration():
    """Test configuration method."""
    injector = FailureInjector(enabled=True)
    
    injector.configure(
        probability=0.5,
        failure_type=FailureType.RATE_LIMIT,
        fail_at_record=10
    )
    
    assert injector.failure_probability == 0.5
    assert injector.failure_type == FailureType.RATE_LIMIT
    assert injector.fail_at_record == 10


def test_failure_injector_probability_bounds():
    """Test probability is clamped to [0, 1]."""
    injector = FailureInjector(enabled=True)
    
    # Test lower bound
    injector.configure(probability=-0.5)
    assert injector.failure_probability == 0.0
    
    # Test upper bound
    injector.configure(probability=2.0)
    assert injector.failure_probability == 1.0
