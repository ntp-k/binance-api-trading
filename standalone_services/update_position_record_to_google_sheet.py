import os
import json
import traceback
from datetime import datetime, timezone, timedelta
from time import sleep
import gspread
from google.oauth2.service_account import Credentials
from dotenv import load_dotenv
load_dotenv()

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SERVICE_ACCOUNT_FILE = os.getenv('GOOGLE_SHEET_SERVICE_ACCOUNT_FILE', '')
SPREADSHEET_KEY = os.getenv('GOOGLE_SHEET_SPREADSHEET_KEY', '')  # Replace with your sheet name
POSITION_RECORDS_DIR = "position_records"

# 🌐 Google Sheet Setup
class GoogleSheetService:
    def __init__(self):
        if not SERVICE_ACCOUNT_FILE:
            raise ValueError("GOOGLE_SHEET_SERVICE_ACCOUNT_FILE environment variable is not set")
        if not SPREADSHEET_KEY:
            raise ValueError("GOOGLE_SHEET_SPREADSHEET_KEY environment variable is not set")
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise FileNotFoundError(f"Service account file not found: {SERVICE_ACCOUNT_FILE}")
        
        self.credentials = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive'
            ]
        )
        self.google_sheet_client = gspread.authorize(self.credentials)
        self.sheet = self.google_sheet_client.open_by_key(SPREADSHEET_KEY)
    
    def append_position_record_v2(self, worksheet_name: str, position_data: dict):
        """
        Given a worksheet name and a position dict, push to the correct sheet.
        """

        worksheet = self.sheet.worksheet(worksheet_name)

        pnl = float(position_data.get("pnl", "0"))
        open_fee = float(position_data.get("open_fee", "0"))
        close_fee = float(position_data.get("close_fee", "0"))
        position_fee = open_fee + close_fee
        realized_pnl = pnl - position_fee
        _date = datetime.strptime(position_data.get("close_time", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(offset=timedelta(hours=7))).astimezone(timezone.utc).strftime(format="%Y-%m-%d")
        row = [
            None,
            None,
            _date, # date utc,
            realized_pnl,
            pnl,
            position_data.get("max_pnl", ""),
            position_data.get("min_pnl", ""),
            position_fee,
            open_fee,
            close_fee,
            position_data.get("close_reason", ""),
            position_data.get("position_side", ""),
            position_data.get("entry_price", ""),
            position_data.get("close_price", ""),
            position_data.get("open_time", ""),
            position_data.get("close_time", ""),
            position_data.get("open_reason", "")
        ]
        worksheet.append_row(row)

    def append_position_record(self, worksheet_name: str, position_data: dict):
        """
        Given a worksheet name and a position dict, push to the correct sheet.
        """

        worksheet = self.sheet.worksheet(worksheet_name)

        pnl = float(position_data.get("pnl", "0"))
        open_fee = float(position_data.get("open_fee", "0"))
        close_fee = float(position_data.get("close_fee", "0"))
        position_fee = open_fee + close_fee
        realized_pnl = pnl - position_fee
        _date = datetime.strptime(position_data.get("close_time", ""), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone(offset=timedelta(hours=7))).astimezone(timezone.utc).strftime(format="%Y-%m-%d")
        row = [
            position_data.get("position_side", ""),
            position_data.get("open_reason", ""),
            position_data.get("close_reason", ""),
            position_data.get("open_time", ""),
            position_data.get("close_time", ""),
            position_data.get("entry_price", ""),
            position_data.get("close_price", ""),
            position_data.get("max_pnl", ""),
            position_data.get("min_pnl", ""),
            pnl,
            realized_pnl,
            position_fee,
            open_fee,
            close_fee,
            _date # date utc
        ]
        worksheet.append_row(row)

def sync_all_positions_to_sheet():
    sheet_service = GoogleSheetService()

    if not os.path.exists(POSITION_RECORDS_DIR):
        print(f"Position records directory not found: {POSITION_RECORDS_DIR}")
        return

    files = [f for f in os.listdir(POSITION_RECORDS_DIR) if f.endswith(".json")]
    files.sort()
    
    if not files:
        print("No position record files to sync")
        return
    
    sleep(0.5) # wait for file to finish writting

    for file in files:
        if not file.endswith('.json'):
            continue

        file_path = os.path.join(POSITION_RECORDS_DIR, file)
        file_name = os.path.basename(file_path)
        
        try:
            with open(file_path, "r") as f:
                data = json.load(f)

            # Extract worksheet name (e.g., "runid_1" from "runid_1_record_20260630_230703.json")
            parts = file_name.split("_")
            worksheet_name = parts[0] + "_" + parts[1]
            
            # Extract run_id number (e.g., 1 from "runid_1")
            run_id = int(parts[1])

            if run_id < 28:
                sheet_service.append_position_record(worksheet_name=worksheet_name, position_data=data)
            else:
                sheet_service.append_position_record_v2(worksheet_name=worksheet_name, position_data=data)
            print(f"Pushed {file_name} to worksheet [{worksheet_name}] ✅")
            os.remove(file_path)
        except Exception as e:
            print(f"Error processing file {file_name}: {e}")
            traceback.print_exc()
            # Don't remove the file if there was an error
            continue

if __name__ == "__main__":
    print("Starting Google Sheet sync service...")
    print(f"Service Account File: {SERVICE_ACCOUNT_FILE}")
    print(f"Spreadsheet Key: {SPREADSHEET_KEY}")
    print(f"Position Records Directory: {POSITION_RECORDS_DIR}")
    print("-" * 50)
    
    while True:
        try:
            sync_all_positions_to_sheet()
        except KeyboardInterrupt:
            print("\nShutting down Google Sheet sync service...")
            break
        except Exception as e:
            print(f"Error syncing positions to Google Sheet:")
            print(f"Exception: {e}")
            traceback.print_exc()
        sleep(30)

# EOF
