"""
SCF handler - wraps FastAPI + Mangum for Tencent Cloud SCF.
"""
import sys, os, json, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

try:
    from mangum import Mangum
    from backend_api.main import app
    
    # Create Mangum handler for API Gateway events
    mangum_handler = Mangum(app, lifespan="off")
    
    def handler(event, context):
        """Handle SCF events.
        
        Supports:
        - API Gateway events (via Mangum)
        - Direct invocation events (test/health)
        """
        try:
            # Check if this is an API Gateway event or direct invocation
            if isinstance(event, dict) and ("httpMethod" in event or "requestContext" in event or "path" in event):
                # API Gateway event format -> use Mangum
                return mangum_handler(event, context)
            else:
                # Direct invocation or test event
                return {
                    "isBase64Encoded": False,
                    "statusCode": 200,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*",
                    },
                    "body": json.dumps({
                        "status": "ok",
                        "message": "World Cup 2026 Prediction API",
                        "endpoints": [
                            "GET /api/health",
                            "GET /api/today?date=",
                            "GET /api/panorama",
                            "POST /api/simulate",
                            "GET /api/teams",
                        ],
                    }),
                }
        except Exception as e:
            return {
                "isBase64Encoded": False,
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e), "traceback": traceback.format_exc()}),
            }
except ImportError as e:
    # Fallback if mangum or api.main is not available
    _init_error = traceback.format_exc()
    def handler(event, context):
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "status": "ok",
                "note": "ImportError occurred during initialization",
                "init_error": _init_error,
            }),
        }
