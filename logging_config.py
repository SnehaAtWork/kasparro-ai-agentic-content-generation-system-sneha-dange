# logging_config.py
import logging
import sys

def setup_logging(level=logging.INFO):
    fmt = "%(asctime)s — %(name)s — %(levelname)s — %(message)s"
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt))
    root = logging.getLogger()
    root.setLevel(level)
    if not root.handlers:
        root.addHandler(handler)
