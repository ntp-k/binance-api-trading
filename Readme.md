

# Prerequisites
## Azure SQL Server
[install Microsoft ODBC 18](https://learn.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-ver17&tabs=ubuntu18-install%2Calpine17-install%2Cdebian8-install%2Credhat7-13-install%2Crhel7-offline)
```
if ! [[ "20.04 22.04 24.04 24.10" == *"$(grep VERSION_ID /etc/os-release | cut -d '"' -f 2)"* ]];
then
    echo "Ubuntu $(grep VERSION_ID /etc/os-release | cut -d '"' -f 2) is not currently supported.";
    exit;
fi

# Download the package to configure the Microsoft repo
curl -sSL -O https://packages.microsoft.com/config/ubuntu/$(grep VERSION_ID /etc/os-release | cut -d '"' -f 2)/packages-microsoft-prod.deb
# Install the package
sudo dpkg -i packages-microsoft-prod.deb
# Delete the file
rm packages-microsoft-prod.deb

# Install the driver
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18
# optional: for bcp and sqlcmd
sudo ACCEPT_EULA=Y apt-get install -y mssql-tools18
echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc
source ~/.bashrc
# optional: for unixODBC development headers
sudo apt-get install -y unixodbc-dev
```

# Bot Run Mode
1. backtest
2. forwardtest
3. live

| Feature            | Backtest        | Forwardtest (Simulation) | Live Trading     |
| ------------------ | --------------- | ------------------------- | ---------------- |
| Data source        | Historical      | Live (real-time)          | Live (real-time) |
| Trades executed    | Fake            | Fake                      | Real             |
| Speed              | Fast            | Real-time                 | Real-time        |
| Risk               | None            | None                      | Real money       |
| Purpose            | Strategy design | Pre-deployment test       | Actual trading   |
| Real-world effects | Ignored         | Partially modeled         | Fully felt       |
