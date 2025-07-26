from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.docker_settings import docker_settings
import logging

logger = logging.getLogger(__name__)


def setup_cors_middleware(app: FastAPI) -> None:
    """
    Configure CORS middleware for Docker and frontend integration.
    
    This middleware handles:
    - Vue.js frontend development servers
    - Chrome extension communications
    - Docker service-to-service communication
    - Production frontend domains
    """
    
    logger.info(f"Configuring CORS for origins: {docker_settings.cors_origins}")
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=docker_settings.cors_origins,
        allow_credentials=docker_settings.cors_allow_credentials,
        allow_methods=docker_settings.cors_allow_methods,
        allow_headers=docker_settings.cors_allow_headers,
        expose_headers=[
            "Content-Range",
            "X-Content-Range",
            "X-Total-Count"
        ],
        max_age=3600,  # Cache preflight requests for 1 hour
    )


def add_custom_cors_headers():
    """
    Additional CORS headers for specific use cases.
    Can be used as a custom middleware if needed.
    """
    async def cors_middleware(request, call_next):
        response = await call_next(request)
        
        # Add custom headers for WebSocket support
        if request.url.path.startswith("/ws"):
            response.headers["Access-Control-Allow-Origin"] = "*"
            response.headers["Access-Control-Allow-WebSocket-Protocol"] = "*"
        
        # Add Chrome extension specific headers
        origin = request.headers.get("origin", "")
        if "extension://" in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        return response
    
    return cors_middleware


# CORS configuration for different environments
CORS_CONFIGS = {
    "development": {
        "allow_origins": [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ],
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
    },
    "docker": {
        "allow_origins": docker_settings.cors_origins,
        "allow_credentials": docker_settings.cors_allow_credentials,
        "allow_methods": docker_settings.cors_allow_methods,
        "allow_headers": docker_settings.cors_allow_headers,
    },
    "production": {
        "allow_origins": [
            "https://proscrape.com",
            "https://www.proscrape.com",
            "https://api.proscrape.com",
        ],
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "PUT", "DELETE"],
        "allow_headers": ["Content-Type", "Authorization"],
    }
}


def get_cors_config(environment: str = "docker") -> dict:
    """Get CORS configuration for specified environment."""
    return CORS_CONFIGS.get(environment, CORS_CONFIGS["docker"])