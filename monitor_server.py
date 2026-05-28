"""Monitor CommonCrawl index server and notify when back online."""

import json
import logging
import time
import urllib.error
import urllib.request
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def check_server():
    """Check if index server is responding."""
    try:
        url = "https://index.commoncrawl.org/collinfo.json"
        req = urllib.request.urlopen(url, timeout=10)
        data = req.read()
        if req.status == 200 and len(data) > 0:
            return True, f"OK ({len(data)} bytes)"
    except urllib.error.URLError as e:
        return False, f"URLError: {type(e).__name__}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
    return False, "Unknown error"

def main():
    """Monitor server every 10 minutes."""
    logger.info("Starting CommonCrawl index server monitor")
    logger.info("Will notify when server is back online")

    last_status = None
    check_count = 0

    while True:
        check_count += 1
        is_up, message = check_server()
        current_status = "UP" if is_up else "DOWN"

        # Only log on status change
        if last_status != current_status:
            logger.info(f"Status changed: {current_status} - {message}")
            if is_up and last_status == "DOWN":
                logger.info("✅ SERVER IS BACK ONLINE!")
                logger.info("   Tested endpoint: https://index.commoncrawl.org/collinfo.json")
                logger.info("   You can now run: uv run build_database.py")
        elif check_count % 6 == 0:  # Log every hour
            logger.info(f"Still {current_status} - {message}")

        last_status = current_status
        time.sleep(600)  # Check every 10 minutes

if __name__ == "__main__":
    main()
