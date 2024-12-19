import os
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv(override=True)

# The number of days used to compile historical data for feature extraction
MAX_TRAINING_PR_AGE = int(os.getenv('MAX_TRAINING_PR_AGE') or '0')
HISTORY_WINDOW_DAYS = int(os.getenv('HISTORY_WINDOW') or '60')

# Number of days in a year
DAYS_PER_YEAR = 365.25

# Default merge ratio
DEFAULT_MERGE_RATIO = 0.5

# Same current time reference for feature calculations
DATETIME_NOW = datetime.now(timezone.utc)

# DB Preload Config
LOAD_PRS = 100
LOAD_PROCESSES = int(os.getenv('PREFILL_PROCESSES') or '2')
