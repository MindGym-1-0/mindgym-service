"""Authentication endpoints for Google OAuth and session management"""
from fastapi import APIRouter, HTTPException, status, Depends, Header
from typing import Optional
from src.types.models import GoogleAuthTokenRequest, AuthResponse
from src.lib.oauth import (
    exchange_auth_code_for_token,
    verify_google_token,
    create_jwt_token,
    verify_jwt_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/google/callback", response_model=AuthResponse)
async def google_auth_callback(request: GoogleAuthTokenRequest):
    """
    Google OAuth callback endpoint
    
    Exchange authorization code for tokens and create user session
    
    Args:
        request: Contains the authorization code from Google
        
    Returns:
        AuthResponse with JWT token and user info
    """
    try:
        # Exchange code for Google tokens
        token_response = await exchange_auth_code_for_token(request.code)
        
        # Verify the ID token
        id_token = token_response.get("id_token")
        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ID token received from Google"
            )
        
        google_user = verify_google_token(id_token)
        
        # Extract user info
        user_id = google_user.get("sub")  # Google's unique identifier
        email = google_user.get("email")
        
        if not user_id or not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing user information from Google"
            )
        
        # TODO: Create or update user in Supabase
        # For now, we'll just create a token
        
        # Create JWT token for your app
        access_token = create_jwt_token(user_id, email)
        
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            user_id=user_id,
            email=email
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed"
        )


@router.post("/verify", response_model=dict)
async def verify_token(authorization: Optional[str] = Header(None)):
    """
    Verify JWT token
    
    Args:
        authorization: Bearer token from Authorization header
        
    Returns:
        Token payload if valid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    try:
        # Extract token from "Bearer <token>"
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authentication scheme")
        
        payload = verify_jwt_token(token)
        return payload
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )


@router.get("/logout")
async def logout():
    """
    Logout endpoint (frontend should discard the token)
    
    Returns:
        Success message
    """
    return {"message": "Logged out successfully"}
