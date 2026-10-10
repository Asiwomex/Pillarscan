"""Lambda entry point. Mangum translates API Gateway events for FastAPI."""

from mangum import Mangum

from api.app import app

handler = Mangum(app, lifespan="off")
