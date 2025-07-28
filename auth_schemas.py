"""
Pydantic schemas for authentication and chat history API
"""
from pydantic import BaseModel, EmailStr, field_validator, ConfigDict, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    email: EmailStr
    username: str
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        return v

    @field_validator('username')
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError('Username must be at least 3 characters long')
        if not v.isalnum():
            raise ValueError('Username must contain only alphanumeric characters')
        return v

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    user_id: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    preferences: Optional[Dict[str, Any]] = None

# Token schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class TokenData(BaseModel):
    user_id: Optional[int] = None

# Chat session schemas
class ChatSessionBase(BaseModel):
    title: Optional[str] = None
    session_type: str = "general"

class ChatSessionCreate(ChatSessionBase):
    pass

class ChatSessionResponse(ChatSessionBase):
    id: int
    session_id: str
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    is_active: bool
    total_messages: int
    message_text: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class ChatSessionUpdate(BaseModel):
    title: Optional[str] = None
    is_active: Optional[bool] = None

# Chat message schemas
class ChatMessageBase(BaseModel):
    message_text: str
    message_type: str = "user"  # user, assistant, system

class ChatMessageCreate(BaseModel):
    content: Optional[str] = None  # Frontend might send 'content'
    message_text: Optional[str] = None  # Frontend might send 'message_text'
    session_id: Optional[str] = None  # If None, creates new session
    message_type: str = "user"  # user, assistant, system
    response_data: Optional[Dict[str, Any]] = None

    @model_validator(mode='after')
    def validate_content(self):
        """Ensure we have either content or message_text"""
        if not self.content and not self.message_text:
            raise ValueError("Either 'content' or 'message_text' must be provided")
        # If both are provided, prefer content
        if self.content and self.message_text:
            self.message_text = self.content
        # If only message_text is provided, copy to content
        elif self.message_text and not self.content:
            self.content = self.message_text
        # If only content is provided, copy to message_text
        elif self.content and not self.message_text:
            self.message_text = self.content
        return self

class ChatMessageResponse(ChatMessageBase):
    id: int
    message_id: str
    session_id: int
    user_id: int
    created_at: datetime
    is_edited: bool
    response_data: Optional[Dict[str, Any]] = None
    processing_time: Optional[int] = None
    message_text: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

# Chat history schemas
class ChatHistoryResponse(BaseModel):
    session: ChatSessionResponse
    messages: List[ChatMessageResponse]
    
    model_config = ConfigDict(from_attributes=True)

class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionResponse]
    total_count: int
    page: int
    page_size: int
    
    model_config = ConfigDict(from_attributes=True)

# API Response schemas
class APIResponse(BaseModel):
    status: str
    message: str
    data: Optional[Any] = None

class ErrorResponse(BaseModel):
    status: str = "error"
    message: str
    detail: Optional[str] = None

# User preferences schema
class UserPreferences(BaseModel):
    theme: Optional[str] = "light"
    language: Optional[str] = "en"
    notifications: Optional[bool] = True
    default_travel_class: Optional[str] = "ECONOMY"
    preferred_airlines: Optional[List[str]] = []
    preferred_airports: Optional[List[str]] = []
    
    model_config = ConfigDict(from_attributes=True)
