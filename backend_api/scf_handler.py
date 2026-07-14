"""
Tencent Cloud SCF entry point.
Wraps the FastAPI app using Mangum for serverless execution.
"""
import sys, os

# Ensure project root is in path
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mangum import Mangum
from backend_api.main import app

# Mangum handler for Tencent Cloud API Gateway / AWS API Gateway v1 format
handler = Mangum(app, lifespan="off")
