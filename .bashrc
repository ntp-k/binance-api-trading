# append this to $HOME/.bashrc
alias dev='cd "$HOME/binance-api-trading" && source .venv/bin/activate'
alias diskused='du -h --max-depth=1 | sort -hr'
alias diskfree='df -h'
alias sll='cd "$HOME/binance-api-trading/logs/$(find "$HOME/binance-api-trading/logs" -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort | tail -n1)" && ls -lah'
