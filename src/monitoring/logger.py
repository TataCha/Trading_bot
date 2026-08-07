import os
import logging
from logging.handlers import RotatingFileHandler
from config.settings import get_settings

def setup_logger(name: str = "TradingBot", log_file: str = "logs/trading_bot.log", level: str = "INFO") -> logging.Logger:
    """
    Sets up a structured logger with both console and rotating file handlers.
    """
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    logger = logging.getLogger(name)
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logger.setLevel(numeric_level)

    if not logger.handlers:
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Stream Handler (Console)
        ch = logging.StreamHandler()
        ch.setLevel(numeric_level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # File Handler with Rotation (10MB max per file, keep 5 backups)
        fh = RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
        fh.setLevel(numeric_level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    return logger
