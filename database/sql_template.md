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
# bot_configs
```
CREATE TABLE bnb.bot_configs (
    bot_id int IDENTITY(1,1) NOT NULL,   -- Auto-increment integer (PostgreSQL syntax)
    enabled BIT NOT NULL DEFAULT 1,      -- Use BIT for booleans in SQL Server
    strategy VARCHAR(50) NOT NULL,
    run_mode VARCHAR(10) NOT NULL,      -- e.g., 'backtest, simulation, live'
    symbol VARCHAR(20) NOT NULL,         -- e.g., 'BTCUSDT'
    leverage INT NOT NULL DEFAULT 1 CHECK (leverage >= 1),
    quantity INT NOT NULL DEFAULT 1 CHECK (quantity >= 1),
    timeframe VARCHAR(10) NOT NULL,      -- e.g., '15m'
    timeframe_limit INT NOT NULL DEFAULT 1 CHECK (timeframe_limit BETWEEN 1 AND 1500),
    param_1 VARCHAR(50),
    param_2 VARCHAR(50),
    param_3 VARCHAR(50),
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    
	CONSTRAINT bot_configs_pk PRIMARY KEY (bot_id)
);

```