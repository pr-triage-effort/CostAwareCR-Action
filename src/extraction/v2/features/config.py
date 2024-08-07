import os
from datetime import datetime, timezone

# The number of days used to compile historical data for feature extraction
HISTORY_LIMIT = True
HISTORY_RANGE_DAYS = 60

# Check the last update time before recomputing
MAX_DATA_AGE = 1

# Number of days in a year
DAYS_PER_YEAR = 365.25

# Default merge ratio
DEFAULT_MERGE_RATIO = 0.5

# Same current time reference for feature calculations
DATETIME_NOW = datetime.now(timezone.utc)