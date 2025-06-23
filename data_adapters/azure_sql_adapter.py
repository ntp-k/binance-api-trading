import pyodbc
import os
from dotenv import load_dotenv

from commons.custom_logger import CustomLogger
from data_adapters.base_adapter import BaseAdapter
from datetime import datetime
from models.enum.run_mode import RunMode
from models.run import Run
from models.trading_position import TradingPosition

# Fetch variables

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

    def fetch_activate_bots(self) -> list: # type: ignore
        try:
            self.logger.debug(
                "Fetching activate bots from Azure SQL Server...")
            cursor = self.conn.cursor()

            sql = "SELECT * FROM [binance-bot-db].bnb.activate_bots;"
            cursor.execute(sql)

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            activate_bots = [dict(zip(columns, row)) for row in rows]

            self.logger.debug(
                f"Retrieved {len(activate_bots)} activate bot(s).")
            self.logger.debug(activate_bots)

            return activate_bots
        except Exception as e:
            self.logger.error(f"Failed to fetch activate bots configs: {e}")
            return []

    def fetch_bot(self, bot_id): # type: ignore
        try:
            self.logger.debug(
                f"Fetching bot id [{bot_id}] from Azure SQL Server...")
            cursor = self.conn.cursor()

            sql = "SELECT * FROM [binance-bot-db].bnb.bots WHERE bot_id = ?;"
            cursor.execute(sql, (bot_id,))

            columns = [column[0] for column in cursor.description]
            rows = cursor.fetchall()
            bots = [dict(zip(columns, row)) for row in rows]

            self.logger.debug(
                f"Retrieved bot id [{bot_id}]")
            self.logger.debug(bots)

            return bots[0]
        except Exception as e:
            self.logger.error_e(f"Failed to fetch bot id [{bot_id}]", e)
            return []

    def create_run(self, bot_id: int, mode: RunMode, initial_balance: float, start_time: datetime) -> int: # type: ignore
        try:
            self.logger.debug(f"Inserting run for bot_id [{bot_id}], mode [{mode}]...")

            cursor = self.conn.cursor()
            sql = """
                INSERT INTO [binance-bot-db].bnb.runs (bot_id, mode, initial_balance, start_time)
                OUTPUT INSERTED.run_id
                VALUES (?, ?, ?, ?);
            """
            cursor.execute(sql, (bot_id, mode.value, initial_balance, start_time))
            run_id = cursor.fetchone()[0] # type: ignore
            self.conn.commit()

            self.logger.debug(f"Inserted run_id [{run_id}] for bot_id [{bot_id}]")
            return run_id

        except Exception as e:
            self.logger.error_e(f"Failed to insert run for bot_id [{bot_id}]", e)
            raise e

    def update_run(self, run: Run):
        try:
            self.logger.debug(f"Updating run_id [{run.run_id}] in database...")

            cursor = self.conn.cursor()
            sql = """
                UPDATE [binance-bot-db].bnb.runs
                SET
                    end_time = ?,
                    total_positions = ?,
                    winning_positions = ?,
                    final_balance = ?
                WHERE run_id = ?;
            """
            cursor.execute(sql, (
                run.end_time,
                run.total_positions,
                run.winning_positions,
                run.final_balance,
                run.run_id
            ))
            self.conn.commit()

            self.logger.debug(f"Run ID [{run.run_id}] updated successfully.")

        except Exception as e:
            self.logger.error_e(f"Failed to update run_id [{run.run_id}]", e)
            raise e
    
    def insert_trading_position(self, position):
        try:
            self.logger.debug(f"Inserting trading position for run_id [{position.run_id}]...")

            cursor = self.conn.cursor()
            sql = """
                INSERT INTO [binance-bot-db].bnb.positions 
                    (run_id, position_side, entry_price, open_time, close_time, close_price, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?);
            """
            cursor.execute(sql, (
                position.run_id,
                position.position_side.value,  # Assuming enum
                position.entry_price,
                position.open_time,
                position.close_time,
                position.close_price,
                datetime.now()
            ))
            self.conn.commit()

            self.logger.debug(f"Position inserted successfully for run_id [{position.run_id}]")

        except Exception as e:
            self.logger.error_e(f"Failed to insert trading position for run_id [{position.run_id}]", e)
            raise e

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
    # az = AzureSQLAdapter()
    # az.fetch_active_bots()

    print('Bye!')

# EOF
