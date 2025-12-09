"""
Schema Drift Detection Module

Automatically detects schema changes in incoming data using:
- Fuzzy field matching (Levenshtein distance)
- Confidence scoring
- Warning logs for potential schema drift
"""
import structlog
from typing import Dict, Any, List, Set, Optional, Tuple
from difflib import SequenceMatcher
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from core.models import SchemaDriftLog

logger = structlog.get_logger()


class SchemaDriftDetector:
    """Detects schema changes in data sources."""
    
    # Thresholds for drift detection
    FUZZY_MATCH_THRESHOLD = 0.7  # 70% similarity for field name matching
    MISSING_FIELD_THRESHOLD = 0.5  # Warn if >50% of expected fields missing
    NEW_FIELD_THRESHOLD = 0.3  # Warn if >30% unexpected fields appear
    
    def __init__(self, source: str, session: AsyncSession):
        """
        Initialize drift detector.
        
        Args:
            source: Data source name
            session: Database session for logging
        """
        self.source = source
        self.session = session
        self.logger = logger.bind(source=source, component="schema_drift")
        self.expected_schemas: Dict[str, Set[str]] = {}
    
    def register_schema(self, schema_name: str, fields: Set[str]) -> None:
        """
        Register expected schema for a data type.
        
        Args:
            schema_name: Name of the schema (e.g., "CoinGeckoRecord")
            fields: Set of expected field names
        """
        self.expected_schemas[schema_name] = fields
        self.logger.info(
            f"Registered schema: {schema_name}",
            field_count=len(fields),
            fields=sorted(list(fields))
        )
    
    def _fuzzy_match_field(self, field: str, candidates: Set[str]) -> Tuple[Optional[str], float]:
        """
        Find best fuzzy match for a field name.
        
        Args:
            field: Field name to match
            candidates: Set of candidate field names
            
        Returns:
            Tuple of (best_match, confidence_score)
        """
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            # Use SequenceMatcher for similarity ratio
            score = SequenceMatcher(None, field.lower(), candidate.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = candidate
        
        return (best_match, best_score)
    
    def detect_drift(
        self,
        schema_name: str,
        actual_data: Dict[str, Any],
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect schema drift in incoming data.
        
        Args:
            schema_name: Name of expected schema
            actual_data: Actual data record received
            run_id: Optional ETL run ID for logging
            
        Returns:
            Drift analysis report with warnings
        """
        if schema_name not in self.expected_schemas:
            self.logger.warning(
                f"Schema not registered: {schema_name}",
                schema_name=schema_name
            )
            return {
                "drift_detected": False,
                "confidence": 0.0,
                "warnings": [f"Schema {schema_name} not registered"]
            }
        
        expected_fields = self.expected_schemas[schema_name]
        actual_fields = set(actual_data.keys())
        
        # Calculate drift metrics
        missing_fields = expected_fields - actual_fields
        extra_fields = actual_fields - expected_fields
        common_fields = expected_fields & actual_fields
        
        # Attempt fuzzy matching for missing fields
        fuzzy_matches = {}
        for missing in missing_fields:
            match, score = self._fuzzy_match_field(missing, extra_fields)
            if match and score >= self.FUZZY_MATCH_THRESHOLD:
                fuzzy_matches[missing] = {"matched_to": match, "confidence": score}
        
        # Calculate confidence score
        total_expected = len(expected_fields)
        matched_count = len(common_fields) + len(fuzzy_matches)
        confidence = matched_count / total_expected if total_expected > 0 else 0.0
        
        # Determine if drift is significant
        missing_ratio = len(missing_fields) / total_expected if total_expected > 0 else 0.0
        extra_ratio = len(extra_fields) / total_expected if total_expected > 0 else 0.0
        
        drift_detected = (
            missing_ratio > self.MISSING_FIELD_THRESHOLD or
            extra_ratio > self.NEW_FIELD_THRESHOLD or
            len(fuzzy_matches) > 0
        )
        
        # Generate warnings
        warnings = []
        if missing_ratio > self.MISSING_FIELD_THRESHOLD:
            warnings.append(
                f"High missing field ratio: {missing_ratio:.1%} "
                f"({len(missing_fields)}/{total_expected} fields missing)"
            )
        
        if extra_ratio > self.NEW_FIELD_THRESHOLD:
            warnings.append(
                f"High new field ratio: {extra_ratio:.1%} "
                f"({len(extra_fields)} unexpected fields)"
            )
        
        if fuzzy_matches:
            for old, match_info in fuzzy_matches.items():
                warnings.append(
                    f"Possible field rename: '{old}' → '{match_info['matched_to']}' "
                    f"(confidence: {match_info['confidence']:.1%})"
                )
        
        # Build drift report
        report = {
            "drift_detected": drift_detected,
            "confidence": round(confidence, 3),
            "schema_name": schema_name,
            "expected_fields": total_expected,
            "matched_fields": len(common_fields),
            "missing_fields": list(missing_fields),
            "extra_fields": list(extra_fields),
            "fuzzy_matches": fuzzy_matches,
            "warnings": warnings,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Log warnings
        if drift_detected:
            self.logger.warning(
                "Schema drift detected",
                **report,
                run_id=run_id
            )
        else:
            self.logger.debug(
                "No schema drift",
                confidence=confidence,
                run_id=run_id
            )
        
        return report
    
    async def log_drift_to_db(
        self,
        drift_report: Dict[str, Any],
        run_id: Optional[str] = None
    ) -> None:
        """
        Persist drift detection to database.
        
        Args:
            drift_report: Drift analysis report
            run_id: ETL run ID
        """
        if not drift_report.get("drift_detected"):
            return  # Only log actual drift events
        
        try:
            await self.session.execute(
                insert(SchemaDriftLog).values(
                    source=self.source,
                    run_id=run_id,
                    schema_name=drift_report["schema_name"],
                    confidence_score=drift_report["confidence"],
                    missing_fields=drift_report["missing_fields"],
                    extra_fields=drift_report["extra_fields"],
                    fuzzy_matches=drift_report["fuzzy_matches"],
                    warnings=drift_report["warnings"],
                    detected_at=datetime.now(timezone.utc)
                )
            )
            await self.session.commit()
            self.logger.info("Drift logged to database", run_id=run_id)
        except Exception as e:
            self.logger.error(
                f"Failed to log drift to DB: {e}",
                run_id=run_id,
                error=str(e)
            )
    
    async def analyze_batch(
        self,
        schema_name: str,
        records: List[Dict[str, Any]],
        run_id: Optional[str] = None,
        sample_size: int = 10
    ) -> Dict[str, Any]:
        """
        Analyze schema drift across a batch of records.
        
        Args:
            schema_name: Expected schema name
            records: List of data records
            run_id: ETL run ID
            sample_size: Number of records to sample for analysis
            
        Returns:
            Aggregated drift analysis
        """
        if not records:
            return {"drift_detected": False, "sample_count": 0}
        
        # Sample records for analysis (avoid analyzing entire batch)
        sample = records[:min(sample_size, len(records))]
        
        drift_reports = []
        for record in sample:
            report = self.detect_drift(schema_name, record, run_id)
            drift_reports.append(report)
        
        # Aggregate results
        drift_count = sum(1 for r in drift_reports if r["drift_detected"])
        avg_confidence = sum(r["confidence"] for r in drift_reports) / len(drift_reports)
        
        all_warnings = []
        for r in drift_reports:
            all_warnings.extend(r.get("warnings", []))
        
        # Get unique warnings
        unique_warnings = list(set(all_warnings))
        
        aggregated = {
            "drift_detected": drift_count > 0,
            "sample_count": len(sample),
            "drift_count": drift_count,
            "drift_ratio": drift_count / len(sample) if sample else 0.0,
            "average_confidence": round(avg_confidence, 3),
            "warnings": unique_warnings,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Log to database if drift detected
        if drift_count > 0 and drift_reports[0].get("drift_detected"):
            await self.log_drift_to_db(drift_reports[0], run_id)
        
        self.logger.info(
            "Batch drift analysis complete",
            **aggregated,
            run_id=run_id
        )
        
        return aggregated
