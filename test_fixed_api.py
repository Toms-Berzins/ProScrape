#!/usr/bin/env python3
"""Test the fixed translation API."""

import uvicorn
from api.main import app

if __name__ == "__main__":
    print("Starting fixed API server on port 8003...")
    uvicorn.run(app, host="127.0.0.1", port=8003, log_level="info")