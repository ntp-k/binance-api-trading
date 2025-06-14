import os
import datetime
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
load_dotenv()

# 🌐 Google Sheet Setup
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = os.getenv('SERVICE_ACCOUNT_FILE')
SPREADSHEET_KEY = os.getenv('SPREADSHEET_KEY')  # Replace with your sheet name
WORKSHEET_INDEX = int(os.getenv('WORKSHEET_INDEX'))    # Replace with your worksheet title

def init_google_sheet():
    credentials = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
    )
    gc = gspread.authorize(credentials)
    sh = gc.open_by_key(SPREADSHEET_KEY)
    wh = sh.get_worksheet(WORKSHEET_INDEX)
    return wh

# Replace your log_trade(...) to also send data to the sheet
def log_trade_to_sheet(sheet, symbol, leverage, interval, quantity, open_time, close_time, direction, entry_price, close_price, pnl):
    row = [
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        symbol,
        leverage,
        interval,
        quantity,
        open_time,
        close_time,
        direction,
        f"{entry_price:.2f}",
        f"{close_price:.2f}",
        f"{pnl:.2f}"
    ]
    sheet.append_row(row, value_input_option='RAW')

if __name__ == "__main__":
    wh = init_google_sheet()
    log_trade_to_sheet(wh, 'tt', 10, '1m', 1, 'opent', 'closet', 'long', 160, 170, 10)

# EOF
