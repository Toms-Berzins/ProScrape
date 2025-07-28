#!/usr/bin/env python3
"""Test the final i18n API."""

import uvicorn
from api.main import app

if __name__ == "__main__":
    print("Starting final API server on port 8004...")
    uvicorn.run(app, host="127.0.0.1", port=8004, log_level="info")