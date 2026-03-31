### `src/data_processor.py`
```python
"""
data_processor.py

Refactored data processing module with improved structure,
type hints, error handling, and docstrings.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


class DataProcessorError(Exception):
    """Base exception for DataProcessor errors."""


class ValidationError(DataProcessorError):
    """Raised when input data fails validation."""


class TransformationError(DataProcessorError):
    """Raised when a data transformation step fails."""


@dataclass
class ProcessingResult:
    """Encapsulates the outcome of a processing pipeline run.

    Attributes:
        records:  Successfully processed records.
        errors:   Per-record error messages keyed by record index.
        total:    Total number of input records attempted.
    """

    records: list[dict[str, Any]] = field(default_factory=list)
    errors: dict[int, str] = field(default_factory=dict)
    total: int = 0

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------

    @property
    def success_count(self) -> int:
        """Number of records processed without error."""
        return len(self.records)

    @property
    def error_count(self) -> int:
        """Number of records that failed processing."""
        return len(self.errors)

    @property
    def success_rate(self) -> float:
        """Fraction of records processed successfully (0.0 – 1.0)."""
        if self.total == 0:
            return 0.0
        return self.success_count / self.total


class DataProcessor:
    """Validates, normalises, and transforms tabular records.

    Parameters
    ----------
    required_fields:
        Field names that *must* be present on every record.
    allowed_statuses:
        Whitelist of acceptable values for the ``status`` field.
        Defaults to ``{"active", "inactive", "pending"}``.
    """

    DEFAULT_STATUSES: frozenset[str] = frozenset({"active", "inactive", "pending"})

    def __init__(
        self,
        required_fields: list[str] | None = None,
        allowed_statuses: set[str] | None = None,
    ) -> None:
        self.required_fields: list[str] = required_fields or ["id", "name", "status"]
        self.allowed_statuses: frozenset[str] = (
            frozenset(allowed_statuses) if allowed_statuses else self.DEFAULT_STATUSES
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, data: list[dict[str, Any]]) -> ProcessingResult:
        """Run the full validation → normalisation → transformation pipeline.

        Parameters
        ----------
        data:
            List of raw record dictionaries.

        Returns
        -------
        ProcessingResult
            Aggregated result containing successful records and any errors.

        Raises
        ------
        DataProcessorError
            If *data* is not a list.
        """
        if not isinstance(data, list):
            raise DataProcessorError(
                f"Expected a list of records, got {type(data).__name__!r}."
            )

        result = ProcessingResult(total=len(data))

        for idx, record in enumerate(data):
            try:
                validated = self.validate(record)
                normalised = self.normalise(validated)
                transformed = self.transform(normalised)
                result.records.append(transformed)
            except (ValidationError, TransformationError) as exc:
                logger.warning("Record %d skipped: %s", idx, exc)
                result.errors[idx] = str(exc)

        logger.info(
            "Processing complete – %d/%d records succeeded (%.1f%%).",
            result.success_count,
            result.total,
            result.success_rate * 100,
        )
        return result

    def validate(self, record: dict[str, Any]) -> dict[str, Any]:
        """Assert that *record* contains all required fields with non-empty values.

        Parameters
        ----------
        record:
            A single raw record dictionary.

        Returns
        -------
        dict[str, Any]
            The same record, unchanged, if validation passes.

        Raises
        ------
        ValidationError
            On missing fields, empty values, or an invalid ``status``.
        """
        if not isinstance(record, dict):
            raise ValidationError(
                f"Record must be a dict, got {type(record).__name__!r}."
            )

        for field_name in self.required_fields:
            if field_name not in record:
                raise ValidationError(f"Missing required field: {field_name!r}.")
            if record[field_name] is None or str(record[field_name]).strip() == "":
                raise ValidationError(
                    f"Field {field_name!r} must not be empty or None."
                )

        status = str(record.get("status", "")).strip().lower()
        if status not in self.allowed_statuses:
            raise ValidationError(
                f"Invalid status {status!r}. "
                f"Allowed values: {sorted(self.allowed_statuses)}."
            )

        return record

    def normalise(self, record: dict[str, Any]) -> dict[str, Any]:
        """Standardise string fields: strip whitespace, lowercase ``status``.

        Parameters
        ----------
        record:
            A validated record dictionary.

        Returns
        -------
        dict[str, Any]
            A *new* dictionary with normalised values.
        """
        normalised: dict[str, Any] = {}
        for key, value in record.items():
            if isinstance(value, str):
                normalised[key] = value.strip()
            else:
                normalised[key] = value

        if "status" in normalised and isinstance(normalised["status"], str):
            normalised["status"] = normalised["status"].lower()

        return normalised

    def transform(self, record: dict[str, Any]) -> dict[str, Any]:
        """Apply business-level transformations to a normalised record.

        Current transformations
        -----------------------
        * ``name`` → title-cased.
        * ``id``   → coerced to ``int`` when possible.
        * ``tags`` → deduplicated list (if present).

        Parameters
        ----------
        record:
            A normalised record dictionary.

        Returns
        -------
        dict[str, Any]
            Transformed record.

        Raises
        ------
        TransformationError
            If a required transformation cannot be applied.
        """
        transformed = dict(record)

        # Coerce id to int
        try:
            transformed["id"] = int(transformed["id"])
        except (ValueError, TypeError) as exc:
            raise TransformationError(
                f"Cannot coerce id={transformed['id']!r} to int."
            ) from exc

        # Title-case name
        if "name" in transformed and isinstance(transformed["name"], str):
            transformed["name"] = transformed["name"].title()

        # Deduplicate tags while preserving order
        if "tags" in transformed and isinstance(transformed["tags"], list):
            seen: set[Any] = set()
            deduped: list[Any] = []
            for tag in transformed["tags"]:
                if tag not in seen:
                    seen.add(tag)
                    deduped.append(tag)
            transformed["tags"] = deduped

        return transformed
```

---

### `tests/__init__.py`
```python
```

---

### `tests/test_data_processor.py`
```python
"""
Unit tests for src/data_processor.py

Run with:
    pytest tests/test_data_