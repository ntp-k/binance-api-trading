
import pyodbc
import os
import pyodbc
import os
from dotenv import load_dotenv

from base_adapter import BaseAdapter

# Fetch variables
load_dotenv()
server = os.getenv("AZURE_SQL_DB_SERVER")
database = os.getenv("AZURE_SQL_DB_DATABASE")
username = os.getenv("AZURE_SQL_DB_HOME_PC_USER")
password = os.getenv("AZURE_SQL_DB_ADMIN_PASSWORD")

connection_string = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

class AzureSQLAdapter(BaseAdapter):
    def __init__(self):
        self.conn = pyodbc.connect(os.getenv("AZURE_SQL_CONN"))

    def fetch_bot_configs(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM BotConfigs WHERE is_active=1")
        rows = cursor.fetchall()
        # return list of dicts with keys like 'mode', 'strategy', etc.
        return None



if __name__ == "__main__":

    conn = pyodbc.connect(connection_string)
    SQL_QUERY = """
    SELECT * FROM [binance-bot-db].bnb.bot_configs WHERE enabled=1;
    """
    cursor = conn.cursor()
    cursor.execute(SQL_QUERY)
    records = cursor.fetchall()
    for r in records:
        print(r)

    print('Bye!')

# EOF
