from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional
import pandas as pd

class SignalType(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"

class Signal:
    def __init__(
        self,
        signal_type: SignalType,
        symbol: str,
        price: float,
        stop_loss: float,
        take_profit: float,
        reason: str = ""
    ):
        self.signal_type = signal_type
        self.symbol = symbol
        self.price = price
        self.stop_loss = stop_loss
        self.take_profit = take_profit
        self.reason = reason

    def __repr__(self):
        return f"<Signal {self.signal_type.value} {self.symbol} @ {self.price} | SL: {self.stop_loss} TP: {self.take_profit} | {self.reason}>"

class StrategyBase(ABC):
    """
    Abstract base class for all plug-and-play day trading strategies.
    """

    def __init__(self, name: str, params: Optional[Dict[str, Any]] = None):
        self.name = name
        self.params = params or {}

    @abstractmethod
    def evaluate(self, symbol: str, df_15m: pd.DataFrame) -> Signal:
        """
        Evaluates the strategy on the provided 15-minute candle DataFrame (with technical indicators).
        Returns a Signal instance (BUY, SELL, or HOLD).
        """
        pass

    def get_parameters(self) -> Dict[str, Any]:
        return self.params
