"""
Database models for user authentication and chat history
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Boolean, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid
from datetime import datetime

class User(Base):
    """
    User model for authentication and profile management
    """
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String(50), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(200), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    # User preferences and settings
    preferences = Column(JSON, default=dict)
    
    # Relationships
    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}', email='{self.email}')>"

class ChatSession(Base):
    """
    Chat session model to group related messages
    """
    __tablename__ = "chat_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=True)  # Auto-generated or user-defined title
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Session metadata
    total_messages = Column(Integer, default=0)
    session_type = Column(String(50), default="general")  # general, flight_search, hotel_booking, etc.
    
    # Relationships
    user = relationship("User", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<ChatSession(id={self.id}, session_id='{self.session_id}', user_id={self.user_id})>"

class ChatMessage(Base):
    """
    Individual chat message model
    """
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(String(50), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Message content
    message_text = Column(Text, nullable=False)
    message_type = Column(String(20), default="user")  # user, assistant, system
    
    # Response data (for assistant messages)
    response_data = Column(JSON, nullable=True)  # Flight results, hotel data, etc.
    
    # Message metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime(timezone=True), nullable=True)
    
    # Processing information
    processing_time = Column(Integer, nullable=True)  # Time in milliseconds
    api_calls_made = Column(JSON, nullable=True)  # Track which APIs were called
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User")
    
    def __repr__(self):
        return f"<ChatMessage(id={self.id}, message_id='{self.message_id}', type='{self.message_type}')>"

class UserSession(Base):
    """
    User login session tracking for JWT token management
    """
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True)

    # Session metadata
    ip_address = Column(String(45), nullable=True)  # IPv4 or IPv6
    user_agent = Column(String(500), nullable=True)
    device_info = Column(JSON, nullable=True)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<UserSession(id={self.id}, user_id={self.user_id}, active={self.is_active})>"

class ConversationContext(Base):
    """
    Conversation memory for follow-up queries in flight searches
    """
    __tablename__ = "conversation_contexts"

    id = Column(Integer, primary_key=True, index=True)
    context_id = Column(String(50), unique=True, index=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Context data
    context_type = Column(String(50), default="flight_search")  # flight_search, hotel_search, etc.
    original_query = Column(Text, nullable=False)
    search_params = Column(JSON, nullable=False)  # Store flight search parameters

    # Flight-specific context
    origin = Column(String(10), nullable=True)  # Airport code
    destination = Column(String(10), nullable=True)  # Airport code
    departure_date = Column(String(20), nullable=True)  # Date string
    passengers = Column(Integer, default=1)
    cabin_class = Column(String(20), default="ECONOMY")

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)  # 30 minutes from creation
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User")

    def __repr__(self):
        return f"<ConversationContext(id={self.id}, user_id={self.user_id}, type='{self.context_type}')>"
