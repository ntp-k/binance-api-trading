"""
Common utility functions for datetime operations and formatting.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any
from commons.constants import DATETIME_FORMAT_GMT7


def get_datetime_now_gmt_plus_7() -> datetime:
    """
    Get current datetime in GMT+7 timezone.
    
    Returns:
        datetime: Current datetime adjusted to GMT+7
    """
    return datetime.now(timezone.utc) + timedelta(hours=7)


def get_datetime_now_string_gmt_plus_7(format: Optional[str] = None) -> str:
    """
    Get current datetime as string in GMT+7 timezone.
    
    Args:
        format: Optional datetime format string. Defaults to DATETIME_FORMAT_GMT7
    
    Returns:
        str: Formatted datetime string
    """
    dt = datetime.now(timezone.utc) + timedelta(hours=7)
    format_str = format if format is not None else DATETIME_FORMAT_GMT7
    return dt.strftime(format_str)

def format_duration_minutes(minutes: int) -> str:
    """
    Format duration in minutes to human-readable string.
    
    Args:
        minutes: Duration in minutes
    
    Returns:
        str: Formatted duration string (e.g., "10h", "41d 16h 30m")
    
    Examples:
        format_duration_minutes(minutes=600) -> 10h
        format_duration_minutes(minutes=60030) -> 41d 16h 30m
    """
    MINUTES_PER_DAY = 24 * 60
    MINUTES_PER_HOUR = 60
    
    days = minutes // MINUTES_PER_DAY
    hours = (minutes % MINUTES_PER_DAY) // MINUTES_PER_HOUR
    mins = minutes % MINUTES_PER_HOUR

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hours > 0:
        parts.append(f"{hours}h")
    if mins > 0 or not parts:
        parts.append(f"{mins}m")

    return " ".join(parts)

def print_result_table(bots_run: List[Dict[str, Any]]) -> None:
    """
    Print formatted results table for bot performance.
    
    Args:
        bots_run: List of dictionaries containing bot run statistics
    """
    # Define header
    header = f"| {'Bot':<40} {'Duration':<20} {'Position':<8} {'Win Rate':<10} {'Initial':<10} {'Final':<10} {'ROI':<11} {'Daily ROI':<11} {'Annual ROI':<8} |"
    separator = "-" * len(header)
    
    print(f"\n{separator}")
    print(header)
    print(separator)

    # Print each row
    for r in bots_run:
        duration_str = format_duration_minutes(r['duration_minutes'])
        win_rate_str = f"{r['win_rate']:.2f} %"
        roi_str = f"{r['roi_percent']:.2f} %"
        daily_roi_str = f"{r['daily_roi']:.2f} %"
        annual_roi_str = f"{r['annual_roi']:.2f} %"
        
        print(
            f"| {r['bot_fullname']:<40} "
            f"{duration_str:<20} "
            f"{r['total_positions']:<8} "
            f"{win_rate_str:<11} "
            f"${r['initial_balance']:<9.2f} "
            f"${r['final_balance']:<9.2f} "
            f"{roi_str:<12} "
            f"{daily_roi_str:<12} "
            f"{annual_roi_str:<10} |"
        )
    print(f"{separator}\n")


def calculate_roi_metrics(
    initial_balance: float,
    final_balance: float,
    duration: timedelta
) -> tuple[Optional[float], Optional[float]]:
    """
    Calculate Daily ROI and Annual ROI (non-compounding).

    Args:
        initial_balance: Starting balance of investment
        final_balance: Ending balance of investment
        duration: Duration of the investment period

    Returns:
        tuple: (daily_roi, annual_roi) as percentages, or (None, None) if invalid

    Raises:
        ValueError: If initial_balance is not positive

    Note:
        - Daily ROI assumes linear progression
        - Annual ROI is extrapolated from daily ROI (non-compounding)
        - Returns (None, None) for zero or negative duration
    """
    SECONDS_PER_DAY = 24 * 60 * 60
    DAYS_PER_YEAR = 365
    
    if initial_balance <= 0:
        raise ValueError("Initial balance must be greater than zero.")
    
    if duration.total_seconds() <= 0:
        print("Warning: Duration is zero or negative. Cannot calculate daily or annual ROI.")
        return None, None

    # Calculate total ROI over the duration
    total_roi = (final_balance - initial_balance) / initial_balance

    # Calculate the number of days in the duration
    total_days = duration.total_seconds() / SECONDS_PER_DAY

    # Calculate Daily ROI (assumes linear progression)
    daily_roi = total_roi / total_days

    # Calculate Annual ROI (non-compounding)
    annual_roi = daily_roi * DAYS_PER_YEAR

    return daily_roi * 100, annual_roi * 100


if __name__ == "__main__":
    pass

# EOF
