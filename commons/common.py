from datetime import datetime, timezone, timedelta

def get_datetime_now_string_gmt_plus_7():
    dt = datetime.now(timezone.utc) + timedelta(hours=7)
    dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    return dt_str

def format_duration(ms: int) -> str:
    """Convert milliseconds to a human-readable duration string"""
    seconds = ms // 1000
    minutes, sec = divmod(seconds, 60)
    hours, min_ = divmod(minutes, 60)
    days, hr = divmod(hours, 24)

    parts = []
    if days > 0:
        parts.append(f"{days}d")
    if hr > 0:
        parts.append(f"{hr}h")
    if min_ > 0:
        parts.append(f"{min_}m")
    if sec > 0 or not parts:
        parts.append(f"{sec}s")

    return " ".join(parts)


if __name__ == "__main__":
    pass

# EOF
