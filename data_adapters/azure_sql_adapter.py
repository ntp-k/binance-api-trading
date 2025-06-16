import pyodbc
import os
from dotenv import load_dotenv

from commons.custom_logger import CustomLogger
from data_adapters.base_adapter import BaseAdapter

# Fetch variables
load_dotenv()

server = os.getenv("AZURE_SQL_DB_SERVER")
database = os.getenv("AZURE_SQL_DB_DATABASE")
username = os.getenv("AZURE_SQL_DB_HOME_PC_USER")
password = os.getenv("AZURE_SQL_DB_ADMIN_PASSWORD")

connection_string = f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'


class AzureSQLAdapter(BaseAdapter):
    def __init__(self):
        self.logger = CustomLogger(name=self.__class__.__name__)

        try:
            self.logger.debug("Attempting to connect to Azure SQL database.")
            self.connection_string = os.getenv(
                "AZURE_SQL_CONN") or self.build_conn_string()
            self.conn = pyodbc.connect(self.connection_string)
            self.logger.debug("Successfully connected to Azure SQL database.")
        except Exception as e:
            self.logger.error(f"Failed to connect to Azure SQL: {e}")
            raise

    def build_conn_string(self):
        server = os.getenv("AZURE_SQL_DB_SERVER", 'Not Set')
        database = os.getenv("AZURE_SQL_DB_DATABASE", 'Not Set')
        username = os.getenv("AZURE_SQL_DB_HOME_PC_USER", 'Not Set')
        password = os.getenv("AZURE_SQL_DB_ADMIN_PASSWORD", 'Not Set')

        if any(val == 'Not Set' for val in [server, database, username, password]):
            raise OSError(
                "Missing one or more Azure SQL DB environment variables.")

        return f'DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'

    def fetch_bot_configs(self) -> list:
        try:
            self.logger.debug(
                "Fetching active bot configs from Azure SQL Server...")
            cursor = self.conn.cursor()

            sql = "SELECT * FROM [binance-bot-db].bnb.bot_configs WHERE enabled = ?;"
            cursor.execute(sql, (1))

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            configs = [dict(zip(columns, row)) for row in rows]

            self.logger.debug(
                f"Retrieved {len(configs)} active bot config(s).")
            self.logger.debug(configs)

            return configs
        except Exception as e:
            self.logger.error(f"Failed to fetch bot configs: {e}")
            return []

    def fetch_bot_position(self, bot_name: str) -> list:
        try:
            self.logger.debug("Fetching bot position from Azure SQL Server...")
            cursor = self.conn.cursor()

            sql = "SELECT * FROM [binance-bot-db].bnb.bot_positions WHERE position_id = ?;"
            cursor.execute(sql, (bot_name.upper()))
            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            positions = [dict(zip(columns, row)) for row in rows]

            self.logger.debug(
                f"Retrieved {len(positions)} bot position.")
            if len(positions) > 1:
                self.logger.warning(
                    'Bot position should not exceed 1 position at any moment')

            self.logger.debug(positions)

            return positions
        except Exception as e:
            self.logger.error(f"Failed to fetch bot position: {e}")
            return []


if __name__ == "__main__":

    # conn = pyodbc.connect(connection_string)
    # SQL_QUERY = """
    # SELECT * FROM [binance-bot-db].bnb.bot_configs WHERE enabled=1;
    # """
    # cursor = conn.cursor()
    # cursor.execute(SQL_QUERY)
    # records = cursor.fetchall()
    # for r in records:
    #     print(r)
    az = AzureSQLAdapter()
    az.fetch_bot_configs()

    print('Bye!')

# EOF
