"""Shared test configuration (connection parameters from environment)."""
import os

HOST = os.environ.get("DB2_HOST", "localhost")
DATABASE = os.environ.get("DB2_DATABASE", "testdb")
USER = os.environ.get("DB2_USER", "db2inst1")
PASSWORD = os.environ.get("DB2_PASSWORD", "password")
PORT = int(os.environ.get("DB2_PORT", 50000))

SYNC_URL = f"db2+syn://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
ASYNC_URL = f"db2+asyn://{USER}:{PASSWORD}@{HOST}:{PORT}/{DATABASE}"
