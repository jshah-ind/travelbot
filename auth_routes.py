"""
Authentication routes for signup, signin, and user management
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import Optional

from database import get_db
from auth_models import User, UserSession
from auth_schemas import (
    UserCreate, UserLogin, UserResponse, UserUpdate,
    Token, APIResponse, ErrorResponse
)
from auth_utils import AuthUtils, get_current_user, get_current_user_optional

# Create router
router = APIRouter(prefix="/auth", tags=["authentication"])

@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify frontend-backend connectivity"""
    print("🧪 TEST: Frontend successfully reached backend!")
    return {"status": "success", "message": "Backend is reachable", "timestamp": datetime.now().isoformat()}

@router.post("/debug-signup")
async def debug_signup(request: Request):
    """Debug endpoint to see raw request data"""
    try:
        body = await request.body()
        print(f"🔍 DEBUG RAW BODY: {body}")
        print(f"🔍 DEBUG CONTENT TYPE: {request.headers.get('content-type')}")

        import json
        if body:
            try:
                json_data = json.loads(body)
                print(f"🔍 DEBUG PARSED JSON: {json_data}")
                return {"status": "success", "received": json_data}
            except Exception as e:
                print(f"🔍 DEBUG JSON PARSE ERROR: {e}")
                return {"status": "error", "raw_body": body.decode(), "error": str(e)}
        else:
            print("🔍 DEBUG: Empty body")
            return {"status": "error", "message": "Empty body"}
    except Exception as e:
        print(f"🔍 DEBUG ERROR: {e}")
        return {"status": "error", "error": str(e)}

@router.get("/me", response_model=APIResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    Get current user information

    Returns the authenticated user's profile information.
    Requires valid JWT token in Authorization header.
    """
    try:
        user_response = UserResponse.model_validate(current_user)
        return APIResponse(
            status="success",
            message="User information retrieved",
            data={"user": user_response}
        )
    except Exception as e:
        print(f"❌ Error creating user response: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve user information: {str(e)}"
        )

@router.post("/signup", response_model=APIResponse)
async def signup(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    User registration endpoint

    Creates a new user account with the provided information.

    **Request Body:**
    - email: Valid email address
    - username: Alphanumeric username (min 3 characters)
    - password: Password (min 8 characters)
    - full_name: Optional full name

    **Example:**
    ```json
    {
        "email": "user@example.com",
        "username": "testuser",
        "password": "securepassword123",
        "full_name": "Test User"
    }
    ```
    """
    try:
        print(f"🚀 SIGNUP REQUEST: {user_data.email} at {datetime.now()}")
        print(f"🔍 SIGNUP DATA: email={user_data.email}, username={user_data.username}, full_name={user_data.full_name}")
    except Exception as e:
        print(f"🔴 SIGNUP ERROR: Failed to process request: {e}")
        raise HTTPException(
            status_code=400,
            detail=f"Invalid request format: {str(e)}"
        )

    try:
        print(user_data.email, user_data.username, user_data.full_name, user_data.password)
        # Check if user already exists
        existing_user = AuthUtils.get_user_by_email(db, user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        existing_username = AuthUtils.get_user_by_username(db, user_data.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        
        # Create new user
        new_user = AuthUtils.create_user(
            db=db,
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name
        )
        
        # Create tokens
        access_token = AuthUtils.create_access_token(
            data={"sub": str(new_user.id), "email": new_user.email}
        )
        refresh_token = AuthUtils.create_refresh_token(
            data={"sub": str(new_user.id), "email": new_user.email}
        )
        
        # Create user session
        AuthUtils.create_user_session(
            db=db,
            user_id=new_user.id,
            token=access_token,
            ip_address="127.0.0.1",  # Default for API usage
            user_agent="API Client"  # Default for API usage
        )
        
        print(f"🔍 DEBUG: About to create UserResponse from new_user: {new_user}")
        user_response = UserResponse.model_validate(new_user)
        print(f"🔍 DEBUG: UserResponse created successfully")

        return APIResponse(
            status="success",
            message="User registered successfully",
            data={
                "user": user_response,
                "tokens": Token(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=30 * 60  # 30 minutes
                )
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )

@router.post("/signin", response_model=APIResponse)
async def signin(
    user_credentials: UserLogin,
    db: Session = Depends(get_db)
):
    """
    User login endpoint

    Authenticates a user and returns JWT tokens.

    **Request Body:**
    - email: Valid email address
    - password: User's password

    **Example:**
    ```json
    {
        "email": "user@example.com",
        "password": "securepassword123"
    }
    ```
    """
    try:
        print(f"🔍 SIGNIN REQUEST: {user_credentials.email} at {datetime.now()}")
    except Exception as e:
        print(f"❌ SIGNIN: Failed to process request: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid request format: {str(e)}"
        )

    try:
        # Authenticate user
        user = AuthUtils.authenticate_user(
            db, user_credentials.email, user_credentials.password
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Account is deactivated"
            )
        
        # Create tokens
        access_token = AuthUtils.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        refresh_token = AuthUtils.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        # Create user session
        AuthUtils.create_user_session(
            db=db,
            user_id=user.id,
            token=access_token,
            ip_address="127.0.0.1",  # Default for API usage
            user_agent="API Client"  # Default for API usage
        )
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.commit()
        
        return APIResponse(
            status="success",
            message="Login successful",
            data={
                "user": UserResponse.model_validate(user),
                "tokens": Token(
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_in=30 * 60  # 30 minutes
                )
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {str(e)}"
        )

@router.post("/logout", response_model=APIResponse)
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    User logout endpoint
    """
    try:
        # Deactivate all user sessions
        db.query(UserSession).filter(
            UserSession.user_id == current_user.id,
            UserSession.is_active == True
        ).update({"is_active": False})
        
        db.commit()
        
        return APIResponse(
            status="success",
            message="Logged out successfully"
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {str(e)}"
        )

@router.put("/me", response_model=APIResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update user profile
    """
    try:
        update_data = user_update.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(current_user, field, value)
        
        current_user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(current_user)
        
        return APIResponse(
            status="success",
            message="Profile updated successfully",
            data={"user": UserResponse.model_validate(current_user)}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Profile update failed: {str(e)}"
        )

@router.post("/refresh", response_model=APIResponse)
async def refresh_token(
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    try:
        # Get the refresh token from request body
        body = await request.json()
        refresh_token = body.get("refresh_token")
        
        if not refresh_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Refresh token is required"
            )
        
        # Verify refresh token
        payload = AuthUtils.verify_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )
        
        user_id = payload.get("sub")
        user = AuthUtils.get_user_by_id(db, user_id)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        # Create new access token
        new_access_token = AuthUtils.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        # Optionally create new refresh token for enhanced security
        new_refresh_token = AuthUtils.create_refresh_token(
            data={"sub": str(user.id), "email": user.email}
        )
        
        return APIResponse(
            status="success",
            message="Token refreshed successfully",
            data={
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer",
                "expires_in": 30 * 60
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token refresh failed: {str(e)}"
        )
