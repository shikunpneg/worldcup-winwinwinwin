"""
Vercel serverless entry point.
Wraps FastAPI app using Mangum for Vercel Python Functions.
"""
import sys, os

# Ensure project root is in path
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mangum import Mangum
from backend_api.main import app

handler = Mangum(app)
