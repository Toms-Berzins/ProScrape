#!/usr/bin/env python3
"""Test the enhanced WebSocket implementation."""

import uvicorn
from api.main import app

if __name__ == "__main__":
    print("Starting API with enhanced WebSocket support on port 8005...")
    uvicorn.run(app, host="127.0.0.1", port=8005, log_level="info")