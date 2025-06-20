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

## bots
```
CREATE TABLE bnb.bots (
    bot_id                  INT IDENTITY(1,1)   NOT NULL,
    bot_name                VARCHAR(100)        UNIQUE NOT NULL,
    strategy                VARCHAR(100)        NOT NULL,
    symbol                  NVARCHAR(20)        NOT NULL,                                                               -- e.g., 'BTCUSDT'
    leverage                INT                 NOT NULL    DEFAULT 1   CHECK (leverage >= 1),
    quantity                FLOAT               NOT NULL    DEFAULT 1   CHECK (quantity >= 0),
    timeframe               NVARCHAR(10)        NOT NULL,                                                               -- e.g., '15m'
    timeframe_limit         INT                 NOT NULL    DEFAULT 1   CHECK (timeframe_limit BETWEEN 1 AND 1500),     -- bumver of candles that will be fetch from data source
    candle_for_indicator    INT                                                                                         -- number of candles use to calculate indicators before it become stable.
    config                  JSON,
    created_at              DATETIME2                       DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT bots_pk PRIMARY KEY (bot_id)
);

JSON Example {"a": "val_a", "b": "val_b"}

```

## active_bots
```
CREATE TABLE bnb.activate_bots (
    activate_id           INT IDENTITY(1,1)   NOT NULL,
    bot_id              INT                 NOT NULL,
    mode                NVARCHAR(10)        NOT NULL,
    initial_balance     DECIMAL(18, 2)      NOT NULL,
    created_at          DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP

    CONSTRAINT activate_bots_pk PRIMARY KEY (activate_id)
    CONSTRAINT activate_bots_bots_FK FOREIGN KEY (bot_id) REFERENCES [binance-bot-db].bnb.bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

```

## runs
```
CREATE TABLE bnb.runs (
    run_id             INT IDENTITY(1,1)    NOT NULL,
    bot_id              INT                 NOT NULL,
    mode                NVARCHAR(10)        NOT NULL,                                   -- e.g., 'BACKTEST, FORWARDTEST, LIVE'
    start_time          DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP,
    end_time            DATETIME2,
    total_trades        INT,
    total_positions     INT,
    winning_positions   INT,
    initial_balance     DECIMAL(18, 2)      NOT NULL,
    final_balance       DECIMAL(18, 2),
    note               TEXT,
    created_at          DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP

    CONSTRAINT runs_pk PRIMARY KEY (run_id)
    CONSTRAINT runs_bots_FK FOREIGN KEY (bot_id) REFERENCES [binance-bot-db].bnb.bots(bot_id) ON DELETE CASCADE ON UPDATE CASCADE
);

```

## trades
```
CREATE TABLE bnb.trades (
    trade_id        INT IDENTITY(1,1)   NOT NULL,
    run_id          INT                 NOT NULL,
    trade_side      VARCHAR(10)         NOT NULL,   -- 'BUY' or 'SELL'
    trade_type      VARCHAR(15),                     -- example 'MARKET', 'LIMIT'
    price           DECIMAL(20,8)       NOT NULL,
    reduce_only     BIT,
    trade_time      DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP
    
    CONSTRAINT trades_pk PRIMARY KEY (trade_id) 
    CONSTRAINT trades_runs_FK FOREIGN KEY (run_id) REFERENCES [binance-bot-db].bnb.runs
);

```

## positions
```
CREATE TABLE bnb.positions (
    position_id     INT IDENTITY(1,1)   NOT NULL,
    run_id          INT                 NOT NULL,
    position_side   NVARCHAR(8)         NOT NULL,   -- 'LONG' or 'SHORT'
    entry_price     FLOAT               NOT NULL    DEFAULT 0,
    open_time       DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP,
    close_time      DATETIME2,
    close_price     FLOAT,
    created_at      DATETIME2           NOT NULL    DEFAULT CURRENT_TIMESTAMP

    CONSTRAINT positions_pk PRIMARY KEY (position_id)
    CONSTRAINT positions_runs_FK FOREIGN KEY (run_id) REFERENCES [binance-bot-db].bnb.runs
);

```





