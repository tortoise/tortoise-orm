"""Dameng-specific SQL functions.

This module contains SQL functions that are specific to Dameng database.
"""

from __future__ import annotations

from typing import Any, Optional

from pypika.functions import Function
from pypika.terms import Term

from tortoise.expressions import F


class ToChar(Function):
    """
    TO_CHAR function converts a datetime or numeric value to string.
    
    Example:
        await Model.filter(
            id=ToChar(F("created_at"), "YYYY-MM-DD")
        )
    """
    
    def __init__(self, field: Term, format_string: str) -> None:
        super().__init__("TO_CHAR", field, format_string)


class ToDate(Function):
    """
    TO_DATE function converts a string to date.
    
    Example:
        await Model.filter(
            created_at__gt=ToDate("2023-01-01", "YYYY-MM-DD")
        )
    """
    
    def __init__(self, date_string: str, format_string: str) -> None:
        super().__init__("TO_DATE", date_string, format_string)


class ToNumber(Function):
    """
    TO_NUMBER function converts a string to number.
    
    Example:
        await Model.filter(
            amount__gt=ToNumber("1000.50")
        )
    """
    
    def __init__(self, value: str, format_string: str = None) -> None:
        if format_string:
            super().__init__("TO_NUMBER", value, format_string)
        else:
            super().__init__("TO_NUMBER", value)


class SysDate(Function):
    """
    SYSDATE function returns the current system date.
    
    Example:
        await Model.filter(
            created_at__lt=SysDate()
        )
    """
    
    def __init__(self) -> None:
        super().__init__("SYSDATE")


class AddMonths(Function):
    """
    ADD_MONTHS function adds months to a date.
    
    Example:
        await Model.filter(
            expiry_date__gt=AddMonths(F("created_at"), 12)
        )
    """
    
    def __init__(self, date_field: Term, months: int) -> None:
        super().__init__("ADD_MONTHS", date_field, months)


class LastDay(Function):
    """
    LAST_DAY function returns the last day of the month.
    
    Example:
        await Model.filter(
            due_date=LastDay(F("created_at"))
        )
    """
    
    def __init__(self, date_field: Term) -> None:
        super().__init__("LAST_DAY", date_field)


class MonthsBetween(Function):
    """
    MONTHS_BETWEEN function returns the number of months between two dates.
    
    Example:
        await Model.filter(
            duration__gt=MonthsBetween(F("end_date"), F("start_date"))
        )
    """
    
    def __init__(self, date1: Term, date2: Term) -> None:
        super().__init__("MONTHS_BETWEEN", date1, date2)


class NextDay(Function):
    """
    NEXT_DAY function returns the next occurrence of a weekday.
    
    Example:
        await Model.filter(
            meeting_date=NextDay(F("created_at"), "MONDAY")
        )
    """
    
    def __init__(self, date_field: Term, weekday: str) -> None:
        super().__init__("NEXT_DAY", date_field, weekday)


class Decode(Function):
    """
    DECODE function provides if-then-else logic.
    
    Example:
        await Model.annotate(
            status_text=Decode(
                F("status"),
                1, "Active",
                2, "Inactive",
                "Unknown"
            )
        )
    """
    
    def __init__(self, field: Term, *args) -> None:
        super().__init__("DECODE", field, *args)


class NVL(Function):
    """
    NVL function replaces NULL with a default value.
    
    Example:
        await Model.annotate(
            name_display=NVL(F("name"), "Unnamed")
        )
    """
    
    def __init__(self, field: Term, default_value: Any) -> None:
        super().__init__("NVL", field, default_value)


class NVL2(Function):
    """
    NVL2 function returns one value if not NULL, another if NULL.
    
    Example:
        await Model.annotate(
            has_email=NVL2(F("email"), "Yes", "No")
        )
    """
    
    def __init__(self, field: Term, not_null_value: Any, null_value: Any) -> None:
        super().__init__("NVL2", field, not_null_value, null_value)


class InitCap(Function):
    """
    INITCAP function capitalizes the first letter of each word.
    
    Example:
        await Model.annotate(
            title_case=InitCap(F("name"))
        )
    """
    
    def __init__(self, field: Term) -> None:
        super().__init__("INITCAP", field)


class Instr(Function):
    """
    INSTR function finds the position of a substring.
    
    Example:
        await Model.annotate(
            at_pos=Instr(F("email"), "@")
        )
    """
    
    def __init__(self, string: Term, substring: Term, 
                 start_pos: Optional[int] = None, occurrence: Optional[int] = None) -> None:
        args = [string, substring]
        if start_pos is not None:
            args.append(start_pos)
            if occurrence is not None:
                args.append(occurrence)
        super().__init__("INSTR", *args)


class LPad(Function):
    """
    LPAD function left-pads a string to a specified length.
    
    Example:
        await Model.annotate(
            padded_id=LPad(F("id"), 5, "0")
        )
    """
    
    def __init__(self, field: Term, length: int, pad_string: str) -> None:
        super().__init__("LPAD", field, length, pad_string)


class RPad(Function):
    """
    RPAD function right-pads a string to a specified length.
    
    Example:
        await Model.annotate(
            padded_name=RPad(F("name"), 20, " ")
        )
    """
    
    def __init__(self, field: Term, length: int, pad_string: str) -> None:
        super().__init__("RPAD", field, length, pad_string)


class RowNum(Function):
    """
    ROWNUM returns the row number in the result set.
    
    Example:
        await Model.filter(
            RowNum() <= 10
        )
    """
    
    def __init__(self) -> None:
        super().__init__("ROWNUM")


class ListAgg(Function):
    """
    LISTAGG aggregates values into a delimited string.
    
    Note: Although this is an aggregate function, we inherit from Function
    to have better control over the function name and parameters.
    
    Example:
        await Model.annotate(
            names=ListAgg(F("name"), ",")
        ).group_by("department")
    """
    
    def __init__(self, field: Term, delimiter: str, order_by: Optional[Term] = None) -> None:
        if order_by:
            # LISTAGG(field, delimiter) WITHIN GROUP (ORDER BY order_by)
            super().__init__("LISTAGG", field, delimiter)
            # Note: ORDER BY handling would need to be implemented in the SQL generator
        else:
            super().__init__("LISTAGG", field, delimiter)