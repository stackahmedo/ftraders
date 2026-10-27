"""F Rahman Traders ERP - FastAPI application."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from .bootstrap import ensure_reference_data
from .config import CORS_ORIGINS
from .db import SessionLocal
from .errors import BusinessError
from .money import MoneyError
from .routers import admin, auth, customers, documents, payments, products, stock

log = logging.getLogger("erp")


@asynccontextmanager
async def lifespan(_: FastAPI):
    db = SessionLocal()
    try:
        ensure_reference_data(db)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        log.error("Database tables are missing. Run:  alembic upgrade head")
    finally:
        db.close()
    yield


app = FastAPI(title="F Rahman Traders ERP", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(BusinessError)
async def business_error(_: Request, exc: BusinessError):
    return JSONResponse(status_code=exc.status_code,
                        content={"detail": exc.message, "code": exc.code, **exc.extra})


@app.exception_handler(MoneyError)
async def money_error(_: Request, exc: MoneyError):
    return JSONResponse(status_code=400, content={"detail": str(exc), "code": "invalid_amount"})


for r in (auth, products, customers, stock, documents, payments, admin):
    app.include_router(r.router)


@app.get("/api/health")
def health():
    return {"ok": True}


# Serve the built React app (frontend/dist) from the same process in production.
DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if DIST.exists():
    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if full_path.startswith("api/"):
            raise HTTPException(404, "Not found")
        target = (DIST / full_path).resolve()
        if full_path and target.is_file() and DIST in target.parents:
            return FileResponse(target)
        return FileResponse(DIST / "index.html")
