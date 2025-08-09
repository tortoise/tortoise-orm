from __future__ import annotations

import re
from typing import Any, List

from tortoise.backends.base.executor import BaseExecutor

from .types import quote_identifier


class DmExecutor(BaseExecutor):
    """Dameng database executor - Handles SQL execution and parameter processing"""
    
    EXPLAIN_PREFIX = "EXPLAIN PLAN FOR"
    
    # Parameter placeholder regex - For precise matching and replacement
    PARAM_PATTERN = re.compile(r':(\d+)\b')
    
    def parameter(self, pos: int) -> str:
        """Return parameter placeholder - Dameng uses :number format"""
        return f":{pos}"
    
    def quote(self, name: str) -> str:
        """Quote identifier - Dameng uses double quotes, handles keywords automatically"""
        return quote_identifier(name)
    
    def convert_parameters(self, query: str) -> str:
        """Convert :1, :2 format parameter placeholders to dmPython's ? format"""
        # Save all string contents to avoid replacing parameters inside strings
        strings = []
        string_pattern = re.compile(r"'[^']*'")
        
        # Temporarily replace strings with placeholders
        def save_string(match):
            strings.append(match.group(0))
            return f"__STR_{len(strings)-1}__"
        
        query_with_placeholders = string_pattern.sub(save_string, query)
        
        # Replace parameters
        query_with_placeholders = self.PARAM_PATTERN.sub('?', query_with_placeholders)
        
        # Restore strings
        for i, string in enumerate(strings):
            query_with_placeholders = query_with_placeholders.replace(
                f"__STR_{i}__", string
            )
        
        return query_with_placeholders