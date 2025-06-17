# Create new user for database

## Step 1: on Master database - Check if the user exists in the current database
`SELECT name FROM sys.database_principals`

## Step 2: on Target database - Create server login
`CREATE LOGIN user_xx WITH PASSWORD = 'xx';`

## Step 3: on Target database -  Create user for target database
`CREATE USER user_xx FOR LOGIN user_xx;`

## Step 3: on Target database -  Grant access or schema ownership
`ALTER AUTHORIZATION ON SCHEMA::schemaxx TO user_xx;`
`GRANT CONTROL ON SCHEMA::schemaxx TO user_xx;`


# Create Table
## bot_configs
```
CREATE TABLE bnb.bot_configs (
    config_id       INT IDENTITY(1,1)   NOT NULL,                                       -- Auto-increment integer (PostgreSQL syntax)
    enabled         BIT                 NOT NULL    DEFAULT 1,                          -- Use BIT for booleans in SQL Server
    strategy        NVARCHAR(50)        NOT NULL,
    symbol          NVARCHAR(20)        NOT NULL,                                       -- e.g., 'BTCUSDT'
    leverage        INT                 NOT NULL    DEFAULT 1   CHECK (leverage >= 1),
    quantity        FLOAT               NOT NULL    DEFAULT 1   CHECK (quantity >= 0),
    timeframe       NVARCHAR(10)        NOT NULL,                                       -- e.g., '15m'
    timeframe_limit INT                 NOT NULL    DEFAULT 1   CHECK (timeframe_limit BETWEEN 1 AND 1500),
    param_1         NVARCHAR(50)                    DEFAULT '120',
    param_2         NVARCHAR(50)                    DEFAULT '100',
    param_3         NVARCHAR(50),
    param_4         NVARCHAR(50),
    param_5         NVARCHAR(50),
    notes           TEXT,
    created_at      DATETIME2            NOT NULL    DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME2            NOT NULL    DEFAULT CURRENT_TIMESTAMP
    
	CONSTRAINT bot_configs_pk PRIMARY KEY (config_id)
);

```
## bot_run
```
CREATE TABLE bnb.bot_runs (
    run_id              INT IDENTITY(1,1)   NOT NULL,
    config_id           INT                 NOT NULL,
    run_mode            NVARCHAR(10)        NOT NULL,                                   -- e.g., 'BACKTEST, FORWARDTEST, LIVE'
    is_closed           BIT                 NOT NULL    DEFAULT 0,
    start_time          DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP,
    end_time            DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP,
    duration_minutes    INT                 NOT NULL    DEFAULT 0,
    total_positions     INT                 NOT NULL    DEFAULT 0,
    winning_positions   INT                 NOT NULL    DEFAULT 0,
    losing_positions    INT                 NOT NULL    DEFAULT 0,
    win_rate            DECIMAL(5, 2)       NOT NULL    DEFAULT 0,
    initial_balance     DECIMAL(18, 2)      NOT NULL    DEFAULT 0,
    final_balance       DECIMAL(18, 2)      NOT NULL    DEFAULT 0,
    roi_percent         DECIMAL(9, 2)       NOT NULL    DEFAULT 0,
    daily_roi           DECIMAL(9, 2)       NOT NULL    DEFAULT 0,
    annual_roi          DECIMAL(9, 2)       NOT NULL    DEFAULT 0,
    notes               TEXT,
    created_at          DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP

    CONSTRAINT bot_runs_pk PRIMARY KEY (run_id)
    CONSTRAINT bot_runs_bot_configs_FK FOREIGN KEY (config_id) REFERENCES [binance-bot-db].bnb.bot_configs(config_id) ON DELETE CASCADE ON UPDATE CASCADE
);
```

## bot_positions
```
CREATE TABLE bnb.bot_positions (
    position_id     INT IDENTITY(1,1)   NOT NULL,
    run_id          INT                 NOT NULL,
    is_closed       BIT                 NOT NULL    DEFAULT 0,
    side            NVARCHAR(8)         NOT NULL,   -- 'LONG' or 'SHORT'
    open_time       DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP,
    close_time      DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP,
    entry_price     FLOAT               NOT NULL    DEFAULT 0,
    mark_price      FLOAT               NOT NULL    DEFAULT 0,
    close_price     FLOAT               NOT NULL    DEFAULT 0,
    unrealized_pnl  FLOAT               NOT NULL    DEFAULT 0,
    pnl             FLOAT               NOT NULL    DEFAULT 0,
    created_at      DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP

    CONSTRAINT bot_positions_pk PRIMARY KEY (position_id)
    CONSTRAINT bot_positions_bot_runs_FK FOREIGN KEY (run_id) REFERENCES [binance-bot-db].bnb.bot_runs
);
```

