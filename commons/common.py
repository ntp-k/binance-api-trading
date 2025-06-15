from datetime import datetime, timezone, timedelta

def get_datetime_now_string_gmt_plus_7():
    dt = datetime.now(timezone.utc) + timedelta(hours=7)
    dt_str = dt.strftime('%Y-%m-%d %H:%M:%S')
    return dt_str

if __name__ == "__main__":
    pass

# EOF
