"""Dameng-specific field types.

This module contains field types that are specific to Dameng database.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from tortoise.fields import Field

if TYPE_CHECKING:  # pragma: nocoverage
    from tortoise.models import Model


class XMLField(Field):
    """
    XML Field for storing XML data in Dameng database.
    
    Dameng has native XML support with the XMLTYPE data type.
    """
    
    SQL_TYPE = "XMLTYPE"
    
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
    
    def to_python_value(self, value: Any) -> Any:
        """Convert database value to Python string."""
        if value is None:
            return None
        return str(value)
    
    def to_db_value(self, value: Any, instance: "Model") -> Any:
        """Convert Python value to database value."""
        if value is None:
            return None
        return str(value)


class IntervalField(Field):
    """
    Interval Field for storing time intervals in Dameng database.
    
    Dameng supports various INTERVAL types for storing time durations.
    
    Parameters:
        interval_type: Type of interval (e.g., 'DAY', 'HOUR', 'DAY TO SECOND')
    """
    
    def __init__(self, interval_type: str = "DAY TO SECOND", **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.interval_type = interval_type.upper()
    
    @property
    def SQL_TYPE(self) -> str:  # type: ignore
        """Return the SQL type for this interval field."""
        return f"INTERVAL {self.interval_type}"
    
    def to_python_value(self, value: Any) -> Any:
        """Convert database interval to Python timedelta or string."""
        if value is None:
            return None
        # Dameng intervals are returned as strings, keep them as is
        # Application can parse as needed
        return str(value)
    
    def to_db_value(self, value: Any, instance: "Model") -> Any:
        """Convert Python value to database interval."""
        if value is None:
            return None
        return str(value)


class RowIDField(Field):
    """
    ROWID Field for accessing Dameng's internal row identifier.
    
    This is a read-only field that provides access to Dameng's ROWID pseudocolumn.
    """
    
    SQL_TYPE = "ROWID"
    
    def __init__(self, **kwargs: Any) -> None:
        # ROWID is always read-only
        kwargs['pk'] = False
        kwargs['null'] = True
        kwargs['generated'] = True
        super().__init__(**kwargs)