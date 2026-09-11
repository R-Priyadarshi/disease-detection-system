from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from contextlib import asynccontextmanager
from core.config import settings
from api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application lifecycle including the background DICOM Storage SCP node."""
    from core.dicom_listener import get_dicom_scp
    scp = get_dicom_scp()
    scp.start()
    yield
    scp.stop()

def create_app() -> FastAPI:
    """Application factory for Chest X-Ray AI Diagnostics."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="Clinical-grade Deep Learning Diagnostic Engine & Explainable AI for Chest Radiograph Pneumonia Detection.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )

    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include REST API endpoints
    app.include_router(router)

    # Mount static files (Web UI)
    web_dir = settings.WEB_DIR
    if web_dir.exists():
        app.mount("/static", StaticFiles(directory=str(web_dir)), name="static")

        @app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
        async def serve_index():
            index_file = web_dir / "index.html"
            if index_file.exists():
                return FileResponse(str(index_file))
            return {"message": f"{settings.PROJECT_NAME} is active. Visit /docs for API documentation."}

        @app.api_route("/manifest.json", methods=["GET", "HEAD"], include_in_schema=False)
        async def serve_manifest():
            manifest_file = web_dir / "manifest.json"
            if manifest_file.exists():
                return FileResponse(str(manifest_file), media_type="application/manifest+json")
            return {"error": "manifest.json not found"}

        @app.api_route("/service-worker.js", methods=["GET", "HEAD"], include_in_schema=False)
        async def serve_service_worker():
            sw_file = web_dir / "service-worker.js"
            if sw_file.exists():
                return FileResponse(str(sw_file), media_type="application/javascript")
            return {"error": "service-worker.js not found"}

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host=settings.HOST, port=settings.PORT, reload=True)
