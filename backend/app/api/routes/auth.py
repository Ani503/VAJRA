from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models.user import User
from backend.app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from backend.app.core.security import verify_password, create_access_token
from backend.app.core.auth import get_current_user
from backend.app.services.audit import log_audit

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.service_id == req.service_id).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Service ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if hasattr(user, "is_active") and user.is_active == 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account has been disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.service_id, "role": user.role})
    log_audit(db, user.service_id, user.role, "LOGIN", "USER", str(user.id), "User successfully logged in.")

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            service_id=user.service_id,
            name=user.name,
            role=user.role,
            base_id=user.base_id,
        )
    )

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        service_id=current_user.service_id,
        name=current_user.name,
        role=current_user.role,
        base_id=current_user.base_id,
    )
