from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.config import settings
from api.routes import router

def create_app() -> FastAPI:
    """Application factory for Chest X-Ray AI Diagnostics."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="Clinical-grade Deep Learning Diagnostic Engine & Explainable AI for Chest Radiograph Pneumonia Detection.",
        docs_url="/docs",
        redoc_url="/redoc"
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

    return app

app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.app:app", host=settings.HOST, port=settings.PORT, reload=True)
