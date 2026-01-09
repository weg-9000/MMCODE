"""
Authentication and Authorization Framework
Implements JWT-based authentication with RLS integration
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text
from pydantic import BaseModel, EmailStr
import bcrypt
import secrets
import logging

from app.core.config import settings
from app.db.session import get_db

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer()


class User(BaseModel):
    """User model for authentication"""
    id: str
    email: EmailStr
    role: str
    is_active: bool = True
    permissions: List[str] = []
    
    class Config:
        from_attributes = True


class UserRole(BaseModel):
    """User role definition"""
    name: str
    permissions: List[str]
    db_role: str  # PostgreSQL role name


class TokenData(BaseModel):
    """JWT token payload"""
    sub: str  # user_id
    email: str
    role: str
    permissions: List[str]
    exp: int
    iat: int


class AuthenticationManager:
    """Manages authentication and authorization"""
    
    def __init__(self):
        self.roles = {
            "admin": UserRole(
                name="admin",
                permissions=[
                    "sessions:read", "sessions:write", "sessions:delete",
                    "agents:read", "agents:write", "agents:delete", 
                    "tasks:read", "tasks:write", "tasks:delete",
                    "artifacts:read", "artifacts:write", "artifacts:delete",
                    "knowledge:read", "knowledge:write", "knowledge:delete",
                    "security:read", "security:write", "security:delete",
                    "audit:read", "audit:write"
                ],
                db_role="app_admin"
            ),
            "user": UserRole(
                name="user",
                permissions=[
                    "sessions:read", "sessions:write",
                    "agents:read", 
                    "tasks:read", "tasks:write",
                    "artifacts:read", "artifacts:write",
                    "knowledge:read", "knowledge:write"
                ],
                db_role="app_user"
            ),
            "security_analyst": UserRole(
                name="security_analyst", 
                permissions=[
                    "sessions:read",
                    "security:read", "security:write",
                    "pentesting:read", "pentesting:write",
                    "findings:read", "findings:write",
                    "audit:read"
                ],
                db_role="security_analyst"
            ),
            "audit_reviewer": UserRole(
                name="audit_reviewer",
                permissions=[
                    "audit:read",
                    "security:read",
                    "findings:read"
                ],
                db_role="audit_reviewer"
            ),
            "readonly": UserRole(
                name="readonly",
                permissions=[
                    "sessions:read",
                    "agents:read",
                    "tasks:read", 
                    "artifacts:read",
                    "knowledge:read"
                ],
                db_role="app_readonly"
            )
        }
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)
    
    def create_access_token(self, user: User) -> str:
        """Create JWT access token"""
        to_encode = {
            "sub": user.id,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions,
            "exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    
    def create_refresh_token(self, user: User) -> str:
        """Create JWT refresh token"""
        to_encode = {
            "sub": user.id,
            "exp": datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_token(self, token: str) -> TokenData:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            
            if payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            return TokenData(**payload)
            
        except JWTError as e:
            logger.error(f"JWT verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"}
            )
    
    def get_user_permissions(self, role: str) -> List[str]:
        """Get permissions for a role"""
        if role not in self.roles:
            return []
        return self.roles[role].permissions
    
    def check_permission(self, user: User, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in user.permissions
    
    def get_db_role(self, user_role: str) -> str:
        """Get PostgreSQL role for user role"""
        if user_role not in self.roles:
            return "app_readonly"
        return self.roles[user_role].db_role


# Global authentication manager
auth_manager = AuthenticationManager()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Get current authenticated user"""
    
    token = credentials.credentials
    token_data = auth_manager.verify_token(token)
    
    # Get user from database (simplified - in real implementation, store users in DB)
    user = User(
        id=token_data.sub,
        email=token_data.email,
        role=token_data.role,
        permissions=token_data.permissions
    )
    
    # Set user context in database session for RLS
    await set_user_context(db, user.id)
    
    return user


async def set_user_context(db: AsyncSession, user_id: str) -> None:
    """Set user context in database session for RLS policies"""
    try:
        await db.execute(
            text("SELECT set_config('app.current_user_id', :user_id, false)"),
            {"user_id": user_id}
        )
        await db.commit()
    except Exception as e:
        logger.error(f"Failed to set user context: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to set security context"
        )


async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def get_security_analyst(current_user: User = Depends(get_current_user)) -> User:
    """Require security analyst role or higher"""
    if current_user.role not in ["security_analyst", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Security analyst access required"
        )
    return current_user


def require_permission(permission: str):
    """Decorator to require specific permission"""
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not auth_manager.check_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission required: {permission}"
            )
        return current_user
    
    return permission_checker


class SecurityEnforcedRepository:
    """Base repository with security enforcement"""
    
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user
        self.db_role = auth_manager.get_db_role(user.role)
    
    async def set_role(self) -> None:
        """Set appropriate database role for user"""
        try:
            await self.db.execute(text(f"SET ROLE {self.db_role}"))
        except Exception as e:
            logger.error(f"Failed to set database role {self.db_role}: {e}")
            # Fallback to most restrictive role
            await self.db.execute(text("SET ROLE app_readonly"))


class MockUserService:
    """Mock user service for demonstration - replace with real implementation"""

    def __init__(self):
        # Lazy initialization to avoid bcrypt issues at module import time
        self._users = None

    @property
    def users(self):
        """Lazy load users to avoid bcrypt initialization issues"""
        if self._users is None:
            self._users = {
                "admin@mmcode.ai": {
                    "id": "admin-001",
                    "email": "admin@mmcode.ai",
                    "hashed_password": auth_manager.get_password_hash("admin123"),
                    "role": "admin",
                    "is_active": True
                },
                "user@mmcode.ai": {
                    "id": "user-001",
                    "email": "user@mmcode.ai",
                    "hashed_password": auth_manager.get_password_hash("user123"),
                    "role": "user",
                    "is_active": True
                },
                "analyst@mmcode.ai": {
                    "id": "analyst-001",
                    "email": "analyst@mmcode.ai",
                    "hashed_password": auth_manager.get_password_hash("analyst123"),
                    "role": "security_analyst",
                    "is_active": True
                }
            }
        return self._users
    
    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email/password"""
        user_data = self.users.get(email)
        if not user_data:
            return None
            
        if not auth_manager.verify_password(password, user_data["hashed_password"]):
            return None
        
        if not user_data["is_active"]:
            return None
        
        permissions = auth_manager.get_user_permissions(user_data["role"])
        
        return User(
            id=user_data["id"],
            email=user_data["email"],
            role=user_data["role"],
            permissions=permissions
        )


# Global user service instance
user_service = MockUserService()


async def create_demo_tokens() -> Dict[str, str]:
    """Create demo tokens for testing"""
    tokens = {}
    
    for email in user_service.users:
        user_data = user_service.users[email]
        permissions = auth_manager.get_user_permissions(user_data["role"])
        
        user = User(
            id=user_data["id"],
            email=user_data["email"],
            role=user_data["role"],
            permissions=permissions
        )
        
        access_token = auth_manager.create_access_token(user)
        tokens[user_data["role"]] = access_token
    
    return tokens


# Security context utilities
async def get_user_db_session(user: User) -> AsyncSession:
    """Get database session with user context and appropriate role"""
    from app.db.session import get_db
    
    db = await anext(get_db())
    
    try:
        # Set user context for RLS
        await set_user_context(db, user.id)
        
        # Set appropriate database role
        db_role = auth_manager.get_db_role(user.role)
        await db.execute(text(f"SET ROLE {db_role}"))
        
        yield db
        
    finally:
        await db.close()


# Audit logging integration
async def log_security_event(
    db: AsyncSession,
    user: User,
    event_type: str,
    target: str,
    result: str = "success",
    error_message: Optional[str] = None
) -> None:
    """Log security events for audit trail"""
    from app.models.models import SecurityAuditLog
    
    audit_log = SecurityAuditLog(
        event_type=event_type,
        event_category="security",
        severity="info" if result == "success" else "warning",
        actor_type="human",
        actor_id=user.id,
        target=target,
        context={
            "user_role": user.role,
            "user_email": user.email,
            "timestamp": datetime.utcnow().isoformat()
        },
        result={"status": result},
        error_message=error_message,
        user_id=user.id
    )
    
    db.add(audit_log)
    await db.commit()