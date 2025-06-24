from models.enum.macd_stage import MACDStage


def detect_macd_state(value):
    if value > 0:
        return MACDStage.POSITIVE
    elif value < 0:
        return MACDStage.NEGATIVE
    return MACDStage.ZERO


def check_for_increasing(lst, n):
    l = len(lst)
    count = 0
    for i in range(l-n+1, l):
        if lst[i] > lst[i-1]:
            count+=1
    return count == n-1


def check_for_decreasing(lst, n):
    l = len(lst)
    count = 0
    for i in range(l-n+1, l):
        if lst[i] < lst[i-1]:
            count+=1
    return count == n-1

# EOF
