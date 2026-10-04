from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .capture.manager import capture_manager
from .config import CORS_ORIGINS
from .database import init_db
from .routers import api_config, auth, cameras, stats
from .version import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    capture_manager.start_all()
    yield
    capture_manager.stop_all()


app = FastAPI(title="RSTP Converter", version=__version__, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(cameras.router)
app.include_router(api_config.router)
app.include_router(stats.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}
