"""
Authentication API Endpoints
Provides login, token refresh, and user management endpoints
"""

from datetime import datetime
from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
import logging

from app.security.authentication import (
    auth_manager, user_service, get_current_user, 
    log_security_event, User, security
)
from app.db.session import get_db

logger = logging.getLogger(__name__)

router = APIRouter()


class LoginRequest(BaseModel):
    """Login request model"""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Login response model"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: Dict


class RefreshTokenRequest(BaseModel):
    """Refresh token request model"""
    refresh_token: str


class UserResponse(BaseModel):
    """User information response"""
    id: str
    email: str
    role: str
    permissions: list
    is_active: bool


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Authenticate user and return JWT tokens
    
    **Security Features:**
    - Password verification
    - JWT token generation 
    - Audit logging
    - Rate limiting (configured in middleware)
    """
    try:
        # Authenticate user
        user = await user_service.authenticate_user(
            credentials.email, 
            credentials.password
        )
        
        if not user:
            # Log failed login attempt
            await log_security_event(
                db=db,
                user=User(
                    id="anonymous",
                    email=credentials.email,
                    role="anonymous", 
                    permissions=[]
                ),
                event_type="login_failed",
                target=f"email:{credentials.email}",
                result="failure",
                error_message="Invalid credentials"
            )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Generate tokens
        access_token = auth_manager.create_access_token(user)
        refresh_token = auth_manager.create_refresh_token(user)
        
        # Log successful login
        await log_security_event(
            db=db,
            user=user,
            event_type="login_success",
            target=f"email:{user.email}",
            result="success"
        )
        
        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=1800,  # 30 minutes
            user={
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "permissions": user.permissions
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service error"
        )


@router.post("/refresh", response_model=Dict)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        # In production, validate refresh token against database
        # For now, decode and validate
        from jose import jwt, JWTError
        from app.core.config import settings
        
        try:
            payload = jwt.decode(
                refresh_request.refresh_token, 
                settings.SECRET_KEY, 
                algorithms=["HS256"]
            )
            
            if payload.get("type") != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            user_id = payload.get("sub")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token"
                )
            
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
        
        # Get user (simplified - should query from database)
        user_email = None
        user_role = None
        
        for email, user_data in user_service.users.items():
            if user_data["id"] == user_id:
                user_email = email
                user_role = user_data["role"]
                break
        
        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        permissions = auth_manager.get_user_permissions(user_role)
        user = User(
            id=user_id,
            email=user_email,
            role=user_role,
            permissions=permissions
        )
        
        # Generate new access token
        new_access_token = auth_manager.create_access_token(user)
        
        # Log token refresh
        await log_security_event(
            db=db,
            user=user,
            event_type="token_refresh",
            target=f"user:{user_id}",
            result="success"
        )
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer",
            "expires_in": 1800
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh service error"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current user information
    
    **Requires:** Valid JWT token in Authorization header
    """
    # Log user info access
    await log_security_event(
        db=db,
        user=current_user,
        event_type="user_info_access",
        target=f"user:{current_user.id}",
        result="success"
    )
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        role=current_user.role,
        permissions=current_user.permissions,
        is_active=current_user.is_active
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout user (in production, invalidate tokens)
    """
    # Log logout
    await log_security_event(
        db=db,
        user=current_user,
        event_type="logout",
        target=f"user:{current_user.id}",
        result="success"
    )
    
    return {"message": "Successfully logged out"}


@router.get("/demo-tokens")
async def get_demo_tokens():
    """
    Get demo tokens for testing (REMOVE IN PRODUCTION)
    
    **WARNING:** This endpoint should be removed in production
    """
    from app.security.authentication import create_demo_tokens
    
    tokens = await create_demo_tokens()
    
    return {
        "message": "Demo tokens generated - REMOVE IN PRODUCTION",
        "tokens": tokens,
        "usage": {
            "admin": "Full system access",
            "user": "Standard user access", 
            "security_analyst": "Security platform access"
        },
        "example": {
            "curl": "curl -H 'Authorization: Bearer <token>' http://localhost:8000/api/v1/sessions/"
        }
    }


@router.get("/permissions")
async def get_permissions(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user permissions
    """
    return {
        "user_id": current_user.id,
        "role": current_user.role,
        "permissions": current_user.permissions,
        "db_role": auth_manager.get_db_role(current_user.role)
    }


@router.get("/health")
async def auth_health():
    """
    Authentication service health check
    """
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": datetime.utcnow().isoformat(),
        "features": {
            "jwt_auth": True,
            "rls_integration": True,
            "role_based_access": True,
            "audit_logging": True
        }
    }