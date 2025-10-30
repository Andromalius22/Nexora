import logging
import os
import time
import shutil

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, "game.log")

# Optional: backup previous log
if os.path.exists(log_file):
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    shutil.move(log_file, os.path.join(LOG_DIR, f"game_{timestamp}.log"))

# Create a root logger
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, mode="w")  # Overwrite current log
        #logging.StreamHandler()                  # Also log to console
    ]
)

# Convenience function to get module-specific loggers
def get_logger(name):
    return logging.getLogger(name)
