
import pyodbc
import os
import pyodbc
import os
from core.adapter_base import AdapterBase
from dotenv import load_dotenv

# Fetch variables
load_dotenv()
server = os.getenv("AZURE_SQL_DB_SERVER")
database = os.getenv("AZURE_SQL_DB_DATABASE")
username = os.getenv("AZURE_SQL_DB_HOME_PC_USER")
password = os.getenv("AZURE_SQL_DB_ADMIN_PASSWORD")

connection_string = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

class AzureSQLAdapter(AdapterBase):
    def __init__(self):
        self.conn = pyodbc.connect(os.getenv("AZURE_SQL_CONN"))

    def fetch_bot_configs(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM BotConfigs WHERE is_active=1")
        rows = cursor.fetchall()
        # return list of dicts with keys like 'mode', 'strategy', etc.
        return [...]



if __name__ == "__main__":

    conn = pyodbc.connect(connection_string)
    SQL_QUERY = """
    SELECT bot_id, symbol, timeframe, timeframe_limit, leverage, quantity, strategy, poll_interval, enabled, notes, created_at, updated_at
    FROM [binance-bot-db].bnb.bot_configs;
    """
    cursor = conn.cursor()
    cursor.execute(SQL_QUERY)
    records = cursor.fetchall()
    for r in records:
        print(r)

# EOF
