from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.core.security import decode_access_token
from backend.app.models.user import User

security_scheme = HTTPBearer(auto_error=False)

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db)
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    service_id = payload["sub"]
    user = db.query(User).filter(User.service_id == service_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if hasattr(user, "is_active") and user.is_active == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def require_role(allowed_roles: list[str]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation not permitted for role '{current_user.role}'. Required one of: {allowed_roles}"
            )
        return current_user
    return role_checker

# Standard role requirements
require_commander = require_role(["Fleet Commander"])
require_maintenance_or_above = require_role(["Fleet Commander", "Maintenance Officer"])
require_any_authenticated = require_role(["Fleet Commander", "Maintenance Officer", "Analyst"])
