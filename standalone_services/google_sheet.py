import os
import json
from time import sleep
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SHEET_SERVICE_ACCOUNT_FILE')
SPREADSHEET_KEY = os.getenv('GOOGLE_SHEET_SPREADSHEET_KEY')  # Replace with your sheet name
WORKSHEET_INDEX = int(os.getenv('GOOGLE_SHEET_WORKSHEET_INDEX'))    # Replace with your worksheet title
POSITION_RECORDS_DIR = "position_records"

# 🌐 Google Sheet Setup
class GoogleSheetService:
    def __init__(self):
        self.credentials = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        self.google_sheet_client = gspread.authorize(self.credentials)
        self.sheet = self.google_sheet_client.open_by_key(SPREADSHEET_KEY)

    def append_position_record(self, worksheet_name: str, position_data: dict):
        """
        Given a worksheet name and a position dict, push to the correct sheet.
        """
        try:
            worksheet = self.sheet.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = self.sheet.add_worksheet(title=worksheet_name, rows="1000", cols="20")
            # add headers
            worksheet.append_row([
                "position_side", "entry_price", "close_price", "pnl", 
                "open_time", "close_time", "open_reason", "close_reason"
            ])
        
        row = [
            position_data.get("position_side", ""),
            position_data.get("entry_price", ""),
            position_data.get("close_price", ""),
            position_data.get("pnl", ""),
            position_data.get("open_time", ""),
            position_data.get("close_time", ""),
            position_data.get("open_reason", ""),
            position_data.get("close_reason", ""),
        ]
        worksheet.append_row(row, value_input_option="RAW")

def sync_all_positions_to_sheet():
    sheet_service = GoogleSheetService()

    files = [f for f in os.listdir(POSITION_RECORDS_DIR) if f.endswith(".json")]
    files.sort()
    sleep(0.5) # wait for file to finish writting

    for file in files:
        file_path = os.path.join(POSITION_RECORDS_DIR, file)
        with open(file_path, "r") as f:
            data = json.load(f)

        file_name = os.path.basename(file_path)
        worksheet_name = file_name.split("_")[0] + "_" + file_name.split("_")[1]

        sheet_service.append_position_record(worksheet_name=worksheet_name, position_data=data)
        print(f"Pushed {file_name} to worksheet [{worksheet_name}] ✅")
        os.remove(file_path)

if __name__ == "__main__":
    while True:
        sync_all_positions_to_sheet()
        sleep(30)

# EOF
