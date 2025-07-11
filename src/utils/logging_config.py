import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

Path("logs").mkdir(parents=True, exist_ok=True)



def setup_logging(console_level=logging.INFO):
    # Clear any existing loggers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')

    # General logs: DEBUG, INFO, WARNING
    general_handler = RotatingFileHandler('logs/logs.txt', maxBytes=2_000_000, backupCount=5)
    general_handler.setLevel(logging.DEBUG)
    general_handler.setFormatter(formatter)

    # Error logs: ERROR, CRITICAL
    error_handler = RotatingFileHandler('logs/error.txt', maxBytes=1_000_000, backupCount=3)
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)

    # Console logger with custom level
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(formatter)

    # Root logger
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[general_handler, error_handler, console_handler]
    )