"""
Database configuration and connection setup for PostgreSQL
"""
from sqlalchemy import create_engine, MetaData, text
from sqlalchemy.orm import declarative_base, sessionmaker
import os
from typing import Generator
from dotenv import load_dotenv

load_dotenv()


# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Set to True for SQL query logging
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class for models
Base = declarative_base()

# Metadata for database operations
metadata = MetaData()

def get_db() -> Generator:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """
    Create all tables in the database
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

def drop_tables():
    """
    Drop all tables in the database (use with caution)
    """
    Base.metadata.drop_all(bind=engine)
    print("🗑️ Database tables dropped")

def reset_database():
    """
    Reset database by dropping and recreating all tables
    """
    drop_tables()
    create_tables()
    print("🔄 Database reset completed")

def test_connection():
    """
    Test database connection
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
