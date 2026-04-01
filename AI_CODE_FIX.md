### `src/utils/data_processor.py`
```python
"""
Data processing utilities module.

Provides validated, type-safe helpers for common data transformation
and validation operations used throughout the application.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class DataProcessorError(Exception):
    """Base exception for DataProcessor errors."""


class ValidationError(DataProcessorError):
    """Raised when input data fails validation."""


class TransformationError(DataProcessorError):
    """Raised when a data transformation operation fails."""


@dataclass
class ProcessingResult:
    """Encapsulates the outcome of a processing operation."""

    success: bool
    data: Any = None
    errors: list[str] = field(default_factory=list)
    processed_at: datetime = field(default_factory=datetime.utcnow)

    def add_error(self, message: str) -> None:
        """Append an error message and mark result as failed."""
        self.errors.append(message)
        self.success = False

    def to_dict(self) -> dict[str, Any]:
        """Serialize result to a plain dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "errors": self.errors,
            "processed_at": self.processed_at.isoformat(),
        }


class DataProcessor:
    """
    Handles validation and transformation of input data.

    Example
    -------
    >>> processor = DataProcessor(strict_mode=True)
    >>> result = processor.process({"name": "Alice", "age": 30})
    >>> result.success
    True
    """

    # Compile once at class level for performance
    _EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
    _SAFE_STRING_RE = re.compile(r"^[\w\s\-.,@]+$")

    def __init__(self, strict_mode: bool = False) -> None:
        """
        Parameters
        ----------
        strict_mode:
            When *True*, any validation warning is treated as an error.
        """
        self.strict_mode = strict_mode
        self._processed_count: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, data: dict[str, Any]) -> ProcessingResult:
        """
        Validate and transform *data*.

        Parameters
        ----------
        data:
            Arbitrary key/value payload to process.

        Returns
        -------
        ProcessingResult
            Always returns a result object; never raises on bad input.
        """
        result = ProcessingResult(success=True)

        try:
            self._validate(data, result)
            if result.success:
                result.data = self._transform(data)
                self._processed_count += 1
                logger.info(
                    "Record processed successfully (total=%d).",
                    self._processed_count,
                )
        except TransformationError as exc:
            result.add_error(f"Transformation failed: {exc}")
            logger.error("Transformation error for data=%r: %s", data, exc)
        except Exception as exc:  # pragma: no cover – unexpected path
            result.add_error(f"Unexpected error: {exc}")
            logger.exception("Unexpected error while processing data=%r", data)

        return result

    def process_batch(
        self, records: list[dict[str, Any]]
    ) -> list[ProcessingResult]:
        """
        Process a collection of records.

        Parameters
        ----------
        records:
            List of payloads forwarded individually to :meth:`process`.

        Returns
        -------
        list[ProcessingResult]
            One result per input record, preserving order.
        """
        if not isinstance(records, list):
            raise TypeError(f"Expected list, got {type(records).__name__!r}")

        logger.info("Starting batch processing of %d records.", len(records))
        results = [self.process(record) for record in records]
        failed = sum(1 for r in results if not r.success)
        logger.info(
            "Batch complete: %d succeeded, %d failed.",
            len(results) - failed,
            failed,
        )
        return results

    @property
    def processed_count(self) -> int:
        """Total number of successfully processed records."""
        return self._processed_count

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def _validate(self, data: dict[str, Any], result: ProcessingResult) -> None:
        """Populate *result* with any validation errors found in *data*."""
        if not isinstance(data, dict):
            raise ValidationError(f"Expected dict, got {type(data).__name__!r}")

        if not data:
            result.add_error("Payload must not be empty.")
            return

        self._validate_required_fields(data, result)
        self._validate_field_types(data, result)
        self._validate_email(data, result)
        self._validate_age(data, result)
        self._validate_name(data, result)

    def _validate_required_fields(
        self, data: dict[str, Any], result: ProcessingResult
    ) -> None:
        required = {"name", "age"}
        missing = required - data.keys()
        for field_name in sorted(missing):
            result.add_error(f"Missing required field: '{field_name}'.")

    def _validate_field_types(
        self, data: dict[str, Any], result: ProcessingResult
    ) -> None:
        if "age" in data and not isinstance(data["age"], int):
            result.add_error(
                f"Field 'age' must be an integer, got {type(data['age']).__name__!r}."
            )
        if "name" in data and not isinstance(data["name"], str):
            result.add_error(
                f"Field 'name' must be a string, got {type(data['name']).__name__!r}."
            )

    def _validate_email(
        self, data: dict[str, Any], result: ProcessingResult
    ) -> None:
        email: Optional[str] = data.get("email")
        if email is None:
            return
        if not isinstance(email, str) or not self._EMAIL_RE.match(email):
            result.add_error(f"Invalid email address: {email!r}.")

    def _validate_age(
        self, data: dict[str, Any], result: ProcessingResult
    ) -> None:
        age = data.get("age")
        if not isinstance(age, int):
            return  # type error already reported
        if age < 0:
            result.add_error("Field 'age' must be non-negative.")
        elif age > 150:
            message = "Field 'age' exceeds maximum allowed value (150)."
            if self.strict_mode:
                result.add_error(message)
            else:
                logger.warning(message)

    def _validate_name(
        self, data: dict[str, Any], result: ProcessingResult
    ) -> None:
        name = data.get("name")
        if not isinstance(name, str):
            return  # type error already reported
        stripped = name.strip()
        if not stripped:
            result.add_error("Field 'name' must not be blank.")
        elif not self._SAFE_STRING_RE.match(stripped):
            result.add_error(
                f"Field 'name' contains disallowed characters: {name!r}."
            )

    # ------------------------------------------------------------------
    # Transformation helpers
    # ------------------------------------------------------------------