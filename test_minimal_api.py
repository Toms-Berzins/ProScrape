#!/usr/bin/env python3
"""Minimal API to test if basic FastAPI works."""

from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Hello World", "status": "working"}

@app.get("/health")
def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    print("Starting minimal API on port 8001...")
    uvicorn.run(app, host="0.0.0.0", port=8001)