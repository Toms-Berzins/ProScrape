#!/usr/bin/env python3
"""Start the enhanced API on the standard port 8000."""

import uvicorn
from api.main import app

if __name__ == "__main__":
    print("Starting ProScrape API with enhanced WebSocket on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")