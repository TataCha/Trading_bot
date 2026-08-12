import logging
from typing import Dict, Any, List, Optional
import requests
from config.settings import Settings, get_settings

logger = logging.getLogger("TradingBot.OrderController")

class OrderController:
    """
    Interface for submitting automated Bracket Orders, querying account balances,
    and managing positions via the Alpaca REST API.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.base_url = self.settings.ALPACA_BASE_URL
        self.headers = {
            "APCA-API-KEY-ID": self.settings.ALPACA_API_KEY,
            "APCA-API-SECRET-KEY": self.settings.ALPACA_SECRET_KEY,
            "Content-Type": "application/json"
        }

    def get_account(self) -> Dict[str, Any]:
        """Fetches account summary from Alpaca API."""
        url = f"{self.base_url}/v2/account"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                return res.json()
            logger.error(f"Failed to get account info: {res.status_code} - {res.text}")
        except Exception as e:
            logger.error(f"Account fetch exception: {e}")
        return {}

    def get_equity(self) -> float:
        """Returns total account equity."""
        account = self.get_account()
        return float(account.get("equity", 0.0))

    def get_positions(self) -> List[Dict[str, Any]]:
        """Returns list of open positions."""
        url = f"{self.base_url}/v2/positions"
        try:
            res = requests.get(url, headers=self.headers, timeout=10)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
        return []

    def submit_bracket_order(
        self,
        symbol: str,
        qty: int,
        side: str = "buy",
        stop_loss_price: float = 0.0,
        take_profit_price: float = 0.0
    ) -> Dict[str, Any]:
        """
        Submits an entry order with simultaneous Bracket Orders (Stop Loss & Take Profit).
        """
        url = f"{self.base_url}/v2/orders"

        # Round prices to 2 decimal places
        sl_price = round(stop_loss_price, 2)
        tp_price = round(take_profit_price, 2)

        order_data = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "market",
            "time_in_force": "gtc",
            "order_class": "bracket",
            "take_profit": {
                "limit_price": str(tp_price)
            },
            "stop_loss": {
                "stop_price": str(sl_price)
            }
        }

        try:
            logger.info(f"Submitting {side.upper()} Bracket Order: {symbol} x {qty} | SL: ${sl_price} | TP: ${tp_price}")
            res = requests.post(url, headers=self.headers, json=order_data, timeout=10)
            if res.status_code in [200, 201]:
                order = res.json()
                logger.info(f"Bracket Order successfully placed! ID: {order.get('id')}")
                return order
            else:
                logger.error(f"Order submission failed ({res.status_code}): {res.text}")
                return {"error": res.text}
        except Exception as e:
            logger.error(f"Exception submitting order for {symbol}: {e}")
            return {"error": str(e)}

    def close_all_positions(self) -> List[Dict[str, Any]]:
        """
        Liquidates all open positions and cancels open orders (used during EOD flush or emergency halt).
        """
        url = f"{self.base_url}/v2/positions?cancel_orders=true"
        try:
            logger.warning("Initiating liquidation of ALL open positions...")
            res = requests.delete(url, headers=self.headers, timeout=15)
            if res.status_code == 207:
                logger.info("Liquidation requests submitted for open positions.")
                return res.json()
            elif res.status_code == 200:
                logger.info("No open positions to liquidate.")
                return []
            else:
                logger.error(f"Failed to close all positions ({res.status_code}): {res.text}")
        except Exception as e:
            logger.error(f"Exception closing all positions: {e}")
        return []
