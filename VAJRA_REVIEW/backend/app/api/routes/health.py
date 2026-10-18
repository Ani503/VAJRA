from fastapi import APIRouter
from backend.app.config import settings

router = APIRouter(tags=["Health"])

@router.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "VAJRA Predictive Maintenance Platform",
        "version": "1.0.0",
        "offline_mode": settings.OFFLINE_MODE,
        "ml_enabled": settings.ML_ENABLED,
    }
