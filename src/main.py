"""PythonDepot - Curated Python package discovery platform."""
from fastapi import FastAPI
from datetime import datetime

app = FastAPI(title="PythonDepot", version="0.1.0")

@app.get("/")
async def root():
    return {"message": "PythonDepot API", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}
