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
    bot_id          INT IDENTITY(1,1)   NOT NULL,                                       -- Auto-increment integer (PostgreSQL syntax)
    enabled         BIT                 NOT NULL    DEFAULT 1,                          -- Use BIT for booleans in SQL Server
    strategy        NVARCHAR(50)        NOT NULL,
    run_mode        NVARCHAR(10)        NOT NULL,                                       -- e.g., 'backtest, simulation, live'
    symbol          NVARCHAR(20)        NOT NULL,                                       -- e.g., 'BTCUSDT'
    leverage        INT                 NOT NULL    DEFAULT 1   CHECK (leverage >= 1),
    quantity        INT                 NOT NULL    DEFAULT 1   CHECK (quantity >= 1),
    timeframe       NVARCHAR(10)        NOT NULL,                                       -- e.g., '15m'
    timeframe_limit INT                 NOT NULL    DEFAULT 1   CHECK (timeframe_limit BETWEEN 1 AND 1500),
    param_1         NVARCHAR(50),
    param_2         NVARCHAR(50),
    param_3         NVARCHAR(50),
    notes           TEXT,
    created_at      DATETIME            NOT NULL    DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME            NOT NULL    DEFAULT CURRENT_TIMESTAMP
    
	CONSTRAINT bot_configs_pk PRIMARY KEY (bot_id)
);

```

## bot_positions
```
CREATE TABLE bnb.bot_positions (
    position_id     nvarchar(100)   NOT NULL,                               -- e.g. 'macd-BTCUSDT|LONG|64200.0|0.005'
    strategy        NVARCHAR(50)    NOT NULL,                               -- e.g. 'macd'
    symbol          NVARCHAR(20)    NOT NULL,                               -- e.g. 'BTCUSDT'
    side            NVARCHAR(8)     NOT NULL,                               -- 'LONG' or 'SHORT'
    entry_price     FLOAT           NOT NULL,
    amount          FLOAT           NOT NULL,
    open_time       DATETIME        NOT NULL   DEFAULT CURRENT_TIMESTAMP,   -- Stored in GMT+7
    close_price     FLOAT           NULL,
    close_time      DATETIME        NULL,
    unrealized_pnl  FLOAT           NULL,                                   -- optional, you can pre-calculate or compute on read
    is_closed       BIT             NOT NULL   DEFAULT 0,                   -- to simplify querying active vs closed positions

    CONSTRAINT bot_positions_pk PRIMARY KEY (position_id)
);

```