"""
Failure Injection Module for Testing ETL Recovery

Provides controlled failure mechanisms to test:
- Checkpoint resume functionality
- Duplicate prevention
- Error metadata recording
"""
import structlog
import random
from typing import Optional
from enum import Enum

logger = structlog.get_logger()


class FailureType(Enum):
    """Types of failures that can be injected."""
    NETWORK_ERROR = "network_error"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT = "timeout"
    RATE_LIMIT = "rate_limit"


class FailureInjector:
    """Inject controlled failures for testing ETL recovery."""
    
    def __init__(self, enabled: bool = False):
        """
        Initialize failure injector.
        
        Args:
            enabled: Whether failure injection is enabled
        """
        self.enabled = enabled
        self.failure_probability = 0.0
        self.failure_type: Optional[FailureType] = None
        self.fail_at_record: Optional[int] = None
        self.logger = logger.bind(component="failure_injector")
    
    def configure(
        self,
        probability: float = 0.0,
        failure_type: FailureType = FailureType.NETWORK_ERROR,
        fail_at_record: Optional[int] = None
    ) -> None:
        """
        Configure failure injection parameters.
        
        Args:
            probability: Probability of failure (0.0 to 1.0)
            failure_type: Type of failure to inject
            fail_at_record: Specific record number to fail at (1-indexed)
        """
        self.failure_probability = max(0.0, min(1.0, probability))
        self.failure_type = failure_type
        self.fail_at_record = fail_at_record
        
        self.logger.info(
            "Failure injection configured",
            enabled=self.enabled,
            probability=self.failure_probability,
            failure_type=failure_type.value if failure_type else None,
            fail_at_record=fail_at_record
        )
    
    def should_fail(self, record_index: Optional[int] = None) -> bool:
        """
        Determine if a failure should occur.
        
        Args:
            record_index: Current record index (1-indexed)
            
        Returns:
            True if failure should be injected
        """
        if not self.enabled:
            return False
        
        # Fail at specific record if configured
        if self.fail_at_record is not None and record_index == self.fail_at_record:
            self.logger.warning(
                f"Injecting failure at record {record_index}",
                failure_type=self.failure_type.value if self.failure_type else None
            )
            return True
        
        # Fail with configured probability
        if random.random() < self.failure_probability:
            self.logger.warning(
                "Injecting random failure",
                record_index=record_index,
                failure_type=self.failure_type.value if self.failure_type else None
            )
            return True
        
        return False
    
    def raise_failure(self, message: str = "Injected failure") -> None:
        """
        Raise an appropriate exception based on configured failure type.
        
        Args:
            message: Error message
            
        Raises:
            Exception appropriate to the configured failure type
        """
        if not self.enabled or not self.failure_type:
            return
        
        error_map = {
            FailureType.NETWORK_ERROR: ConnectionError(f"{message}: Network error"),
            FailureType.DATABASE_ERROR: RuntimeError(f"{message}: Database error"),
            FailureType.VALIDATION_ERROR: ValueError(f"{message}: Validation error"),
            FailureType.TIMEOUT: TimeoutError(f"{message}: Operation timeout"),
            FailureType.RATE_LIMIT: RuntimeError(f"{message}: Rate limit exceeded")
        }
        
        exception = error_map.get(self.failure_type, RuntimeError(message))
        self.logger.error(
            "Raising injected failure",
            failure_type=self.failure_type.value,
            message=message
        )
        raise exception
    
    def inject_if_enabled(self, record_index: Optional[int] = None, message: str = "Injected failure") -> None:
        """
        Check and inject failure if conditions are met.
        
        Args:
            record_index: Current record index
            message: Error message
            
        Raises:
            Exception if failure should be injected
        """
        if self.should_fail(record_index):
            self.raise_failure(message)


# Global failure injector instance
failure_injector = FailureInjector(enabled=False)
