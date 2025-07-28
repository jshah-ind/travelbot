"""
Chat history routes for managing chat sessions and messages
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import uuid

from database import get_db
from auth_models import User, ChatSession, ChatMessage
from auth_schemas import (
    ChatSessionCreate, ChatSessionResponse, ChatSessionUpdate,
    ChatMessageCreate, ChatMessageResponse, ChatHistoryResponse,
    ChatSessionListResponse, APIResponse
)
from auth_utils import get_current_user

# Create router
router = APIRouter(prefix="/chat", tags=["chat"])

def generate_session_id() -> str:
    """Generate a unique session ID"""
    return str(uuid.uuid4())

def generate_message_id() -> str:
    """Generate a unique message ID"""
    return str(uuid.uuid4())

@router.post("/sessions", response_model=APIResponse)
async def create_session(
    session_data: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new chat session
    """
    try:
        # Create new chat session
        session = ChatSession(
            session_id=generate_session_id(),
            user_id=current_user.id,
            title=session_data.title,
            session_type=session_data.session_type or "travel",
            is_active=True
        )
        
        db.add(session)
        db.commit()
        db.refresh(session)
        
        # Create session response with correct message count (0 for new session)
        session_dict = {
            "id": session.id,
            "session_id": session.session_id,
            "user_id": session.user_id,
            "title": session.title,
            "session_type": session.session_type,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "is_active": session.is_active,
            "total_messages": 0  # New session has 0 messages
        }
        session_response = ChatSessionResponse.model_validate(session_dict)
        
        return APIResponse(
            status="success",
            message="Chat session created successfully",
            data={"session": session_response}
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create chat session: {str(e)}"
        )

@router.get("/sessions", response_model=APIResponse)
async def get_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's chat sessions with pagination
    """
    try:
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get sessions for current user
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == current_user.id
        ).order_by(
            ChatSession.updated_at.desc()
        ).offset(offset).limit(page_size).all()
        
        # Get total count
        total_count = db.query(ChatSession).filter(
            ChatSession.user_id == current_user.id
        ).count()
        
        # Convert to response models and calculate total messages
        session_responses = []
        for session in sessions:
            # Calculate total messages for this session
            message_count = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).count()
            
            # Create session response with correct message count
            session_dict = {
                "id": session.id,
                "session_id": session.session_id,
                "user_id": session.user_id,
                "title": session.title,
                "session_type": session.session_type,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "is_active": session.is_active,
                "total_messages": message_count
            }
            session_responses.append(ChatSessionResponse.model_validate(session_dict))
        
        return APIResponse(
            status="success",
            message="Chat sessions retrieved successfully",
            data={
                "sessions": session_responses,
                "total_count": total_count,
                "page": page,
                "page_size": page_size
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat sessions: {str(e)}"
        )

@router.get("/sessions/{session_id}", response_model=APIResponse)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get a specific chat session
    """
    try:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Calculate total messages for this session
        message_count = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).count()
        
        # Create session response with correct message count
        session_dict = {
            "id": session.id,
            "session_id": session.session_id,
            "user_id": session.user_id,
            "title": session.title,
            "session_type": session.session_type,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "is_active": session.is_active,
            "total_messages": message_count
        }
        session_response = ChatSessionResponse.model_validate(session_dict)
        
        return APIResponse(
            status="success",
            message="Chat session retrieved successfully",
            data={"session": session_response}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve chat session: {str(e)}"
        )

@router.put("/sessions/{session_id}", response_model=APIResponse)
async def update_session(
    session_id: str,
    session_data: ChatSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a chat session
    """
    try:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Update session fields
        if session_data.title is not None:
            session.title = session_data.title
        if session_data.session_type is not None:
            session.session_type = session_data.session_type
        if session_data.is_active is not None:
            session.is_active = session_data.is_active
        
        session.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(session)
        
        # Calculate total messages for this session
        message_count = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).count()
        
        # Create session response with correct message count
        session_dict = {
            "id": session.id,
            "session_id": session.session_id,
            "user_id": session.user_id,
            "title": session.title,
            "session_type": session.session_type,
            "created_at": session.created_at.isoformat(),
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
            "is_active": session.is_active,
            "total_messages": message_count
        }
        session_response = ChatSessionResponse.model_validate(session_dict)
        
        return APIResponse(
            status="success",
            message="Chat session updated successfully",
            data={"session": session_response}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update chat session: {str(e)}"
        )

@router.delete("/sessions/{session_id}", response_model=APIResponse)
async def delete_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a chat session and all its messages
    """
    try:
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Delete session (messages will be deleted due to cascade)
        db.delete(session)
        db.commit()
        
        return APIResponse(
            status="success",
            message="Chat session deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete chat session: {str(e)}"
        )

@router.post("/messages", response_model=APIResponse)
async def add_message(
    message_data: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Add a new message to a chat session
    """
    try:
        # Verify session exists and belongs to user
        session = db.query(ChatSession).filter(
            ChatSession.session_id == message_data.session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Create new message
        message = ChatMessage(
            message_id=generate_message_id(),
            session_id=session.id,
            user_id=current_user.id,
            message_text=message_data.content,
            message_type=message_data.message_type or "user",
            response_data=message_data.response_data
        )
        
        db.add(message)
        
        # Update session's updated_at timestamp
        session.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(message)
        
        message_response = ChatMessageResponse.model_validate(message)
        
        return APIResponse(
            status="success",
            message="Message added successfully",
            data={"message": message_response}
        )
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add message: {str(e)}"
        )

@router.get("/sessions/{session_id}/messages", response_model=APIResponse)
async def get_messages(
    session_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get messages for a specific chat session
    """
    try:
        # Verify session exists and belongs to user
        session = db.query(ChatSession).filter(
            ChatSession.session_id == session_id,
            ChatSession.user_id == current_user.id
        ).first()
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chat session not found"
            )
        
        # Calculate offset
        offset = (page - 1) * page_size
        
        # Get messages for the session
        messages = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).order_by(
            ChatMessage.created_at.asc()
        ).offset(offset).limit(page_size).all()
        
        # Get total count
        total_count = db.query(ChatMessage).filter(
            ChatMessage.session_id == session.id
        ).count()
        
        # Convert to response models
        message_responses = [ChatMessageResponse.model_validate(message) for message in messages]
        
        return APIResponse(
            status="success",
            message="Messages retrieved successfully",
            data={
                "messages": message_responses,
                "session_id": session_id,
                "count": total_count
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve messages: {str(e)}"
        )

@router.get("/sessions/recent", response_model=APIResponse)
async def get_recent_sessions(
    limit: int = Query(5, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get recent chat sessions for the current user
    """
    try:
        sessions = db.query(ChatSession).filter(
            ChatSession.user_id == current_user.id
        ).order_by(
            ChatSession.updated_at.desc()
        ).limit(limit).all()
        
        # Convert to response models and calculate total messages
        session_responses = []
        for session in sessions:
            # Calculate total messages for this session
            message_count = db.query(ChatMessage).filter(
                ChatMessage.session_id == session.id
            ).count()
            
            # Create session response with correct message count
            session_dict = {
                "id": session.id,
                "session_id": session.session_id,
                "user_id": session.user_id,
                "title": session.title,
                "session_type": session.session_type,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat() if session.updated_at else None,
                "is_active": session.is_active,
                "total_messages": message_count
            }
            session_responses.append(ChatSessionResponse.model_validate(session_dict))
        
        return APIResponse(
            status="success",
            message="Recent sessions retrieved successfully",
            data={"sessions": session_responses}
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recent sessions: {str(e)}"
        ) 