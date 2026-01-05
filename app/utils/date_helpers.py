"""
app/utils/date_helpers.py
Date parsing and formatting utilities
"""
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def parse_date(date_str: Optional[str], default: datetime = None) -> datetime:
    """
    Parse date string in various formats
    
    Args:
        date_str: Date string in various formats
        default: Default datetime if parsing fails
        
    Returns:
        Parsed datetime object
    """
    if date_str is None:
        return default or datetime.utcnow()
    
    # List of common date formats
    date_formats = [
        "%Y-%m-%d",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m-%d-%Y",
        "%m/%d/%Y",
    ]
    
    for fmt in date_formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    # Try ISO format
    try:
        return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        pass
    
    logger.warning(f"Could not parse date: {date_str}, using default")
    return default or datetime.utcnow()


def parse_excel_date(date_value) -> datetime:
    """
    Parse Excel date formats (including serial numbers)
    
    Args:
        date_value: Excel date value (can be string, datetime, or number)
        
    Returns:
        Parsed datetime object
    """
    if isinstance(date_value, datetime):
        return date_value
    
    if isinstance(date_value, str):
        return parse_date(date_value)
    
    # Handle Excel serial date numbers
    if isinstance(date_value, (int, float)):
        try:
            excel_epoch = datetime(1900, 1, 1)
            return excel_epoch + timedelta(days=date_value - 2)
        except Exception as e:
            logger.warning(f"Could not parse Excel date number: {date_value}, error: {e}")
            return datetime.utcnow()
    
    return datetime.utcnow()


def format_date(dt: datetime, fmt: str = "%Y-%m-%d") -> str:
    """Format datetime to string"""
    return dt.strftime(fmt)


def get_date_range(days: int = 30) -> tuple:
    """
    Get date range for last N days
    
    Returns:
        Tuple of (start_date, end_date)
    """
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    return start_date, end_date