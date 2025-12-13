import structlog
from fastapi import FastAPI

logger = structlog.get_logger(__name__)

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.post("/test")
async def test():
    logger.info("Canary check: ok")
    return {"success": "ok"}


@app.get("/healthz")
async def health():
    logger.info("Healh check: ok")
    return {"status": "healthy"}
