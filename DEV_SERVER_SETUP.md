# Dev Server PostgreSQL Setup Guide

## 🎯 Overview

This guide helps you set up PostgreSQL for airline detection and conversation memory on your dev server. The system automatically creates tables and populates them with sample data.

## 📋 Prerequisites

### 1. PostgreSQL Installation
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql postgresql-server
sudo postgresql-setup initdb
sudo systemctl start postgresql

# macOS (using Homebrew)
brew install postgresql
brew services start postgresql
```

### 2. Python Dependencies
```bash
pip install psycopg2-binary python-dotenv
```

## 🔧 Database Setup

### 1. Create PostgreSQL User
```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Create user and database
CREATE USER travelagent WITH PASSWORD 'your_password';
CREATE DATABASE travelagent OWNER travelagent;
GRANT ALL PRIVILEGES ON DATABASE travelagent TO travelagent;
\q
```

### 2. Environment Configuration
Create or update your `.env` file:

```env
# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=travelagent
DB_USER=travelagent
DB_PASSWORD=your_password

# Other configurations...
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key
AMADEUS_CLIENT_ID=your_amadeus_client_id
AMADEUS_CLIENT_SECRET=your_amadeus_client_secret
```

## 🚀 Automatic Setup

### Option 1: Run Migration Script (Recommended)
```bash
cd travelbot
python database_migration.py
```

This script will:
- ✅ Create database if it doesn't exist
- ✅ Create all required tables
- ✅ Insert sample airline data
- ✅ Verify the setup

### Option 2: Manual Setup
If you prefer manual setup:

```bash
# Connect to your database
psql -h localhost -U travelagent -d travelagent

# Run the SQL commands from database_migration.py manually
```

## 📊 Tables Created

### 1. Airlines Table
```sql
CREATE TABLE airlines (
    id SERIAL PRIMARY KEY,
    airline_code VARCHAR(10) UNIQUE NOT NULL,
    airline_name VARCHAR(255) NOT NULL,
    aliases JSONB,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 1
);
```

**Purpose**: Stores airline information for detection and filtering

### 2. Airline Queries Table
```sql
CREATE TABLE airline_queries (
    id SERIAL PRIMARY KEY,
    query_text TEXT NOT NULL,
    detected_airline_code VARCHAR(10),
    detected_airline_name VARCHAR(255),
    success BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Purpose**: Tracks user queries for airline detection analytics

### 3. Conversation Context Table
```sql
CREATE TABLE conversation_context (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    context_type VARCHAR(50) NOT NULL,
    original_query TEXT NOT NULL,
    search_params JSONB,
    origin VARCHAR(10),
    destination VARCHAR(10),
    departure_date DATE,
    passengers INTEGER DEFAULT 1,
    cabin_class VARCHAR(20) DEFAULT 'ECONOMY',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);
```

**Purpose**: Stores conversation context for follow-up queries

## 🎯 Sample Data

The migration script automatically inserts **70+ airlines** including:

### Indian Airlines
- Air India (AI)
- IndiGo (6E)
- SpiceJet (SG)
- Vistara (UK)
- Jet Airways (9W)
- GoAir (G8)
- AirAsia India (I5)
- Akasa Air (QP)

### International Airlines
- Emirates (EM)
- Qatar Airways (QR)
- Etihad Airways (EY)
- British Airways (BA)
- Lufthansa (LH)
- Singapore Airlines (SQ)
- And many more...

## 🔍 Verification

### 1. Check Database Connection
```bash
python -c "
import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=os.getenv('DB_PORT', '5432'),
        database=os.getenv('DB_NAME', 'travelagent'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'password')
    )
    print('✅ Database connection successful!')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
"
```

### 2. Check Tables
```bash
psql -h localhost -U travelagent -d travelagent -c "
SELECT 
    table_name, 
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as columns
FROM information_schema.tables t 
WHERE table_schema = 'public' 
ORDER BY table_name;
"
```

### 3. Check Sample Data
```bash
psql -h localhost -U travelagent -d travelagent -c "
SELECT airline_code, airline_name FROM airlines LIMIT 10;
"
```

## 🧪 Testing

### 1. Test Airline Detection
```python
from enhanced_airline_detector_postgres import EnhancedAirlineDetectorPostgres
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize detector
db_config = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': os.getenv('DB_PORT', '5432'),
    'database': os.getenv('DB_NAME', 'travelagent'),
    'user': os.getenv('DB_USER', 'postgres'),
    'password': os.getenv('DB_PASSWORD', 'password')
}

detector = EnhancedAirlineDetectorPostgres(db_config)

# Test queries
test_queries = [
    "air india flights only",
    "show me indigo flights",
    "spicejet from delhi to mumbai",
    "emirates business class"
]

for query in test_queries:
    result = detector.detect_airlines(query)
    print(f"Query: {query}")
    print(f"Result: {result}")
    print("---")
```

### 2. Test Conversation Context
```python
from simple_utils import ConversationMemory
from database import get_db

# Test conversation memory
db = next(get_db())
memory = ConversationMemory()

# Store a search
search_params = {
    "origin": "DEL",
    "destination": "BOM", 
    "departure_date": "2025-07-29",
    "passengers": 1,
    "cabin_class": "ECONOMY"
}

memory.store_flight_search("123", search_params, "flights from delhi to mumbai", db)

# Retrieve the search
last_search = memory.get_last_flight_search("123", db)
print(f"Last search: {last_search}")
```

## 🔄 Automatic Table Creation

### How It Works
The system automatically creates tables when:

1. **EnhancedAirlineDetectorPostgres** is initialized
2. **ConversationMemory** is used
3. **Migration script** is run

### Automatic Features
- ✅ **CREATE TABLE IF NOT EXISTS**: Tables are created if they don't exist
- ✅ **Indexes**: Performance indexes are created automatically
- ✅ **Sample Data**: 70+ airlines are inserted automatically
- ✅ **Error Handling**: Graceful handling of connection issues

## 🚨 Troubleshooting

### 1. Connection Issues
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check if port is listening
netstat -tlnp | grep 5432

# Test connection
psql -h localhost -U travelagent -d travelagent
```

### 2. Permission Issues
```bash
# Grant permissions
sudo -u postgres psql
GRANT ALL PRIVILEGES ON DATABASE travelagent TO travelagent;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO travelagent;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO travelagent;
\q
```

### 3. Environment Variables
```bash
# Check .env file exists
ls -la .env

# Test environment loading
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print(f'DB_HOST: {os.getenv(\"DB_HOST\")}')
print(f'DB_NAME: {os.getenv(\"DB_NAME\")}')
print(f'DB_USER: {os.getenv(\"DB_USER\")}')
"
```

## 📈 Performance

### Indexes Created
- `idx_airlines_code`: Fast airline code lookups
- `idx_airlines_name`: Fast airline name searches
- `idx_queries_timestamp`: Fast query history retrieval
- `idx_conversation_user_id`: Fast user context retrieval
- `idx_conversation_expires`: Fast cleanup of expired contexts

### Optimization Tips
1. **Regular Cleanup**: Run cleanup scripts for expired contexts
2. **Connection Pooling**: Use connection pooling for high traffic
3. **Monitoring**: Monitor query performance with `EXPLAIN ANALYZE`

## 🔄 Migration Between Environments

### From Local to Dev Server
1. **Export local data** (if needed):
```bash
pg_dump -h localhost -U travelagent travelagent > backup.sql
```

2. **Import to dev server**:
```bash
psql -h dev-server -U travelagent -d travelagent < backup.sql
```

3. **Update environment variables**:
```env
DB_HOST=your-dev-server-ip
DB_PORT=5432
DB_NAME=travelagent
DB_USER=travelagent
DB_PASSWORD=your_password
```

## ✅ Success Checklist

- [ ] PostgreSQL installed and running
- [ ] Database user created with proper permissions
- [ ] `.env` file configured with database credentials
- [ ] Migration script run successfully
- [ ] Tables created and verified
- [ ] Sample data inserted
- [ ] Connection test passed
- [ ] Airline detection test working
- [ ] Conversation memory test working

## 🎉 Next Steps

1. **Restart your application** to use the new database
2. **Test airline filtering** with queries like "air india flights only"
3. **Test conversation memory** with follow-up queries
4. **Monitor performance** and adjust as needed

The PostgreSQL setup is now complete and ready for production use! 