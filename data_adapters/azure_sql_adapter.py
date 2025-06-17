import pyodbc
import os
from dotenv import load_dotenv

from commons.custom_logger import CustomLogger
from data_adapters.base_adapter import BaseAdapter
from models.bot_run import BotRun
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

    def insert_bot_run(self, bot_run: BotRun):
        query = """
            INSERT INTO bnb.bot_runs (
                config_id,
                run_mode,
                start_time,
                end_time,
                duration_minutes,
                total_positions,
                winning_positions,
                losing_positions,
                win_rate,
                initial_balance,
                final_balance,
                roi_percent,
                daily_roi,
                annual_roi,
                notes,
                created_at,
                is_closed
            ) OUTPUT INSERTED.run_id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self.logger.debug(f"Run result: {bot_run}")

        values = (
            int(bot_run.config_id),
            bot_run.run_mode.value,
            bot_run.start_time,
            bot_run.end_time,
            bot_run.duration_minutes,
            bot_run.total_positions,
            bot_run.winning_positions,
            bot_run.losing_positions,
            bot_run.win_rate,
            bot_run.initial_balance,
            bot_run.final_balance,
            bot_run.roi_percent,
            bot_run.daily_roi,
            bot_run.annual_roi,
            bot_run.notes,
            bot_run.created_at,
            1 if bot_run.is_closed else 0
        )

        try:
            self.logger.debug("Logging bot run to Azure SQL Server...")
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            run_id = cursor.fetchone()[0] # type: ignore
            self.conn.commit()
            return run_id
        except Exception as e:
            self.logger.warning_e(f"Failed to insert backtest_run", e)
            self.conn.rollback()
            return None

    def update_bot_run(self, bot_run: BotRun) -> bool:
        query = """
            UPDATE bnb.bot_runs
            SET
                start_time = ?,
                end_time = ?,
                duration_minutes = ?,
                total_positions = ?,
                winning_positions = ?,
                losing_positions = ?,
                win_rate = ?,
                final_balance = ?,
                roi_percent = ?,
                daily_roi = ?,
                annual_roi = ?,
                notes = ?,
                is_closed = ?
            WHERE run_id = ?
        """

        values = (
            bot_run.start_time,
            bot_run.end_time,
            bot_run.duration_minutes,
            bot_run.total_positions,
            bot_run.winning_positions,
            bot_run.losing_positions,
            bot_run.win_rate,
            bot_run.final_balance,
            bot_run.roi_percent,
            bot_run.daily_roi,
            bot_run.annual_roi,
            bot_run.notes,
            1 if bot_run.is_closed else 0,
            bot_run.run_id
        )

        try:
            self.logger.debug(f"Updating bot run run_id: {bot_run.run_id}...")
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.warning_e(f"Failed to update bot run run_id: {bot_run.run_id}", e)
            self.conn.rollback()
            return False

    def insert_trading_position(self, position: TradingPosition) -> bool:
        query = """
            INSERT INTO bnb.bot_positions (
                run_id,
                is_closed,
                side,
                open_time,
                close_time,
                entry_price,
                mark_price,
                close_price,
                unrealized_pnl,
                pnl
            ) OUTPUT INSERTED.position_id
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        values = (
            position.run_id,
            1 if position.is_closed else 0,
            position.side.value,
            position.open_time,
            position.close_time,
            position.entry_price,
            position.mark_price,
            position.close_price,
            position.unrealized_profit,
            position.pnl
        )

        try:
            cursor = self.conn.cursor()
            cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            self.logger.error_e(f"Failed to insert trading position", e)
            self.conn.rollback()
            return False

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
