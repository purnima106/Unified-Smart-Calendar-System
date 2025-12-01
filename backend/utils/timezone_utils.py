#!/usr/bin/env python3
"""
Timezone utility functions for handling calendar events
"""

from datetime import datetime, timezone, timedelta
import pytz
from flask import current_app

def get_user_timezone():
    """Get the user's timezone from configuration"""
    return current_app.config.get('DEFAULT_TIMEZONE', 'UTC')

def parse_datetime_with_timezone(date_time_str, timezone_name=None):
    """
    Parse datetime string with proper timezone handling
    
    Args:
        date_time_str (str): The datetime string to parse
        timezone_name (str): The timezone name (e.g., 'Asia/Kolkata', 'UTC')
    
    Returns:
        datetime: Parsed datetime object in UTC
    """
    if not timezone_name:
        timezone_name = get_user_timezone()
    
    try:
        # Handle different datetime formats
        if date_time_str.endswith('Z'):
            # UTC time
            utc_time = datetime.fromisoformat(date_time_str.replace('Z', '+00:00'))
            return utc_time
        elif '+' in date_time_str or '-' in date_time_str[-6:]:
            # Has timezone offset
            return datetime.fromisoformat(date_time_str)
        else:
            # No timezone info, assume it's in the specified timezone
            local_tz = pytz.timezone(timezone_name)
            naive_time = datetime.fromisoformat(date_time_str)
            local_time = local_tz.localize(naive_time)
            return local_time.astimezone(pytz.UTC)
    except Exception as e:
        print(f"Error parsing datetime '{date_time_str}': {e}")
        # Fallback to naive datetime
        return datetime.fromisoformat(date_time_str)

def convert_to_user_timezone(utc_datetime, timezone_name=None):
    """
    Convert UTC datetime to user's timezone
    
    Args:
        utc_datetime (datetime): UTC datetime object
        timezone_name (str): Target timezone name
    
    Returns:
        datetime: Datetime in user's timezone
    """
    if not timezone_name:
        timezone_name = get_user_timezone()
    
    if utc_datetime.tzinfo is None:
        # Assume UTC if no timezone info
        utc_datetime = utc_datetime.replace(tzinfo=timezone.utc)
    
    user_tz = pytz.timezone(timezone_name)
    return utc_datetime.astimezone(user_tz)

def format_datetime_for_display(datetime_obj, timezone_name=None, format_str="%Y-%m-%d %H:%M"):
    """
    Format datetime for display in user's timezone
    
    Args:
        datetime_obj (datetime): Datetime object
        timezone_name (str): User's timezone
        format_str (str): Format string
    
    Returns:
        str: Formatted datetime string
    """
    if not timezone_name:
        timezone_name = get_user_timezone()
    
    user_time = convert_to_user_timezone(datetime_obj, timezone_name)
    return user_time.strftime(format_str)

def get_timezone_offset(timezone_name=None):
    """
    Get timezone offset as string (e.g., '+05:30')
    
    Args:
        timezone_name (str): Timezone name
    
    Returns:
        str: Timezone offset string
    """
    if not timezone_name:
        timezone_name = get_user_timezone()
    
    tz = pytz.timezone(timezone_name)
    now = datetime.now(tz)
    offset = now.strftime('%z')
    return f"{offset[:3]}:{offset[3:]}"
