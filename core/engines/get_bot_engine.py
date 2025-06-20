from models.enum.run_mode import RunMode
from strategies.base_strategy_engine import BaseStrategyEngine

def get_bot_engine(bot_runner) -> BaseStrategyEngine:
    if bot_runner.run.mode == RunMode.LIVE:
        from core.engines.live_engine import LiveEngine
        return LiveEngine()
    elif bot_runner.run.mode == RunMode.FORWARDTEST:
        from core.engines.forwardtest_engine import ForwardtestEngine
        return ForwardtestEngine()
    else:
        from core.engines.backtest_engine import BacktestEngine
        return BacktestEngine(bot_runner)

# EOF
