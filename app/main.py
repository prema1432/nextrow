import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import db
from app.routes.scans import router as scans_router
from app.routes.reports import router as reports_router
from app.routes.ui import router as ui_router


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scanner.log')
    ]
)


app = FastAPI(
    title="Adobe Analytics Website Scanner",
    description="A tool to scan websites for Adobe Analytics implementation and track network calls",
    version="1.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup_connect_mongo() -> None:
    db.connect_to_mongo()


@app.on_event("shutdown")
def _shutdown_close_mongo() -> None:
    db.close_mongo_connection()


app.include_router(scans_router)
app.include_router(reports_router)
app.include_router(ui_router)
