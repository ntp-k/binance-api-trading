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

def print_result_table(results: list[dict]):
    # Define header
    header = f"| {'Bot':<40} {'Duration':<20} {'Trades':<8} {'Win Rate':<10} {'Initial':<10} {'Final':<10} {'ROI':<11} {'Daily ROI':<11} {'Auunal ROI':<8} |"
    print("\n" + "-" * len(header))
    print(header)
    print("-" * len(header))


    # Print each row
    for r in results:
        print(
            f"| {r['bot_fullname']:<40} "
            f"{str(r['duration']):<20} "
            f"{r['total_trades']:<8} "
            f"{r['win_rate']:.2f} %{' ' * (11 - len(f'{r['win_rate']:.2f} %'))}"
            f"${r['initial_balance']:<9.2f} "
            f"${r['final_balance']:<9.2f} "
            f"{r['roi']:.2f} %{' ' * (12 - len(f'{r['roi']:.2f} %'))}"
            f"{r['daily_roi']:.2f} %{' ' * (12 - len(f'{r['daily_roi']:.2f} %'))}"
            f"{r['annual_roi']:.2f} %{' ' * (10 - len(f'{r['annual_roi']:.2f} %'))} |"
            # f"{r['roi']:<8.2f}% "
            # f"{r['annualized_roi']:.2f}%"
        )
    print("-" * len(header) + "\n")


def calculate_roi_metrics(initial_balance: float, final_balance: float, duration: timedelta):
    """
    Calculates the Daily ROI and Simpler Annual ROI.

    Args:
        initial_balance (float): The starting balance of your investment.
        final_balance (float): The ending balance of your investment.
        duration (timedelta): The duration of the investment.

    Returns:
        tuple: A tuple containing:
            - daily_roi (float): The average daily ROI as a percentage.
            - simpler_annual_roi (float): The simpler annual ROI as a percentage.
            Returns (None, None) if duration is zero days to avoid division by zero.
    """
    if initial_balance <= 0:
        raise ValueError("Initial balance must be greater than zero.")
    if duration.total_seconds() <= 0:
        print("Warning: Duration is zero or negative. Cannot calculate daily or annual ROI.")
        return None, None

    # 1. Calculate Total ROI over the duration
    total_roi = (final_balance - initial_balance) / initial_balance

    # 2. Calculate the number of days in the duration
    # We use total_seconds() to get the most precise duration in seconds,
    # then convert it to days.
    total_days = duration.total_seconds() / (24 * 60 * 60)

    # 3. Calculate Daily ROI
    # We assume a linear progression for daily ROI over the short period.
    daily_roi = total_roi / total_days

    # 4. Calculate Simpler Annual ROI (non-compounding)
    # This assumes the daily ROI is consistently applied for 365 days,
    # without compounding the profits back into the principal.
    simpler_annual_roi = daily_roi * 365

    return daily_roi * 100, simpler_annual_roi * 100


if __name__ == "__main__":
    pass

# EOF
