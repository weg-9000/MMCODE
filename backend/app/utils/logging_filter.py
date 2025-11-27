"""
Secure logging filter to prevent sensitive information exposure
"""

import re
import logging
from typing import List


class SensitiveDataFilter(logging.Filter):
    """
    Logging filter that removes or masks sensitive information from log records
    
    Prevents API keys, secrets, passwords and other sensitive data from being logged
    """
    
    SENSITIVE_PATTERNS: List[str] = [
        r'(api[_-]?key)["\']?\s*[:=]\s*["\']?[\w-]{10,}',
        r'(secret[_-]?key)["\']?\s*[:=]\s*["\']?[\w-]{10,}',
        r'(password)["\']?\s*[:=]\s*["\']?[\w-]{8,}',
        r'(token)["\']?\s*[:=]\s*["\']?[\w-]{10,}',
        r'(bearer\s+)[\w-]{10,}',
        r'(supabase[_-]?key)["\']?\s*[:=]\s*["\']?[\w-]{10,}',
        r'(github[_-]?secret)["\']?\s*[:=]\s*["\']?[\w-]{10,}',
        r'(sk-[\w-]{48,})',  # OpenAI API key format
        r'(pk-[\w-]{48,})',  # Anthropic API key format
        r'(pplx-[\w-]{48,})',  # Perplexity API key format
        r'(AIza[\w-]{35})',  # Google API key format
    ]
    
    def __init__(self):
        super().__init__()
        self.compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) 
            for pattern in self.SENSITIVE_PATTERNS
        ]
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter log record to remove sensitive information
        
        Args:
            record: The log record to filter
            
        Returns:
            True to allow the record, False to block it
        """
        # Filter the main message
        if record.msg:
            record.msg = self._sanitize_string(str(record.msg))
        
        # Filter the arguments
        if record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self._sanitize_string(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        # Filter exception info if present
        if record.exc_text:
            record.exc_text = self._sanitize_string(record.exc_text)
        
        return True
    
    def _sanitize_string(self, text: str) -> str:
        """
        Sanitize a string by replacing sensitive patterns
        
        Args:
            text: The text to sanitize
            
        Returns:
            Sanitized text with sensitive data masked
        """
        sanitized = text
        
        for pattern in self.compiled_patterns:
            sanitized = pattern.sub(r'\1=***REDACTED***', sanitized)
        
        return sanitized


def setup_secure_logging() -> None:
    """
    Configure secure logging with sensitive data filtering
    
    This function should be called during application startup to ensure
    all loggers have the sensitive data filter applied
    """
    sensitive_filter = SensitiveDataFilter()
    
    # Apply to root logger
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        handler.addFilter(sensitive_filter)
    
    # Apply to specific loggers that might handle sensitive data
    sensitive_loggers = [
        'app.core.config',
        'app.main',
        'app.core.llm_providers',
        'uvicorn',
        'uvicorn.access',
        'uvicorn.error'
    ]
    
    for logger_name in sensitive_loggers:
        logger = logging.getLogger(logger_name)
        logger.addFilter(sensitive_filter)
    
    logging.getLogger(__name__).info("Secure logging filter configured")


def get_sensitive_filter() -> SensitiveDataFilter:
    """
    Get a new instance of the sensitive data filter
    
    Returns:
        A new SensitiveDataFilter instance
    """
    return SensitiveDataFilter()