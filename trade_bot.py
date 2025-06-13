import macd_simlulate_trade
import macd_bot_trade
import time

def main():
    while True:
        macd_bot_trade.main()
        time.sleep(30)

if __name__ == "__main__":
    print("Running Trading bot")
    main()

# EOF
