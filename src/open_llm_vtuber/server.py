import os
import shutil
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from loguru import logger

from .routes import init_client_ws_route, init_webtool_routes
from .service_context import ServiceContext
from .config_manager.utils import Config


class CustomStaticFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        if path.endswith(".js"):
            response.headers["Content-Type"] = "application/javascript"
        return response


class AvatarStaticFiles(StaticFiles):
    async def get_response(self, path: str, scope):
        allowed_extensions = (".jpg", ".jpeg", ".png", ".gif", ".svg")
        if not any(path.lower().endswith(ext) for ext in allowed_extensions):
            return Response("Forbidden file type", status_code=403)
        return await super().get_response(path, scope)


class WebSocketServer:
    def __init__(self, config: Config):
        # Initialize service context first
        self.default_context_cache = ServiceContext()
        
        # Create lifespan context manager for async initialization
        @asynccontextmanager
        async def lifespan(app: FastAPI):
            # Startup
            logger.info("Starting up server...")
            # Load config synchronously
            self.default_context_cache.load_from_config(config)
            
            # Initialize async components (like MCP)
            await self.default_context_cache.initialize_async_components()
            logger.info("Server startup complete")
            
            yield
            
            # Shutdown
            logger.info("Shutting down server...")
            await self.default_context_cache.shutdown_async_components()
        
        # Create FastAPI app with lifespan
        self.app = FastAPI(lifespan=lifespan)

        # Add CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Include routes with the context
        self.app.include_router(
            init_client_ws_route(default_context_cache=self.default_context_cache),
        )
        self.app.include_router(
            init_webtool_routes(default_context_cache=self.default_context_cache),
        )

        # Mount cache directory first (to ensure audio file access)
        if not os.path.exists("cache"):
            os.makedirs("cache")
        self.app.mount(
            "/cache",
            StaticFiles(directory="cache"),
            name="cache",
        )

        # Mount static files
        self.app.mount(
            "/live2d-models",
            StaticFiles(directory="live2d-models"),
            name="live2d-models",
        )
        self.app.mount(
            "/bg",
            StaticFiles(directory="backgrounds"),
            name="backgrounds",
        )
        self.app.mount(
            "/avatars",
            AvatarStaticFiles(directory="avatars"),
            name="avatars",
        )

        # Mount web tool directory separately from frontend
        self.app.mount(
            "/web-tool",
            CustomStaticFiles(directory="web_tool", html=True),
            name="web_tool",
        )

        # Mount main frontend last (as catch-all)
        self.app.mount(
            "/",
            CustomStaticFiles(directory="frontend", html=True),
            name="frontend",
        )

    def run(self):
        pass

    @staticmethod
    def clean_cache():
        """Clean the cache directory by removing and recreating it."""
        cache_dir = "cache"
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
            os.makedirs(cache_dir)
