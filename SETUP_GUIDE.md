# Simple Travel Agent - Complete Setup Guide

## 📁 What's Included

This `simple_travel_agent` folder contains **only the essential files** needed to run the simplified travel agent with conversation memory functionality:

### Core Files:
- `simple_main.py` - Main FastAPI application
- `simple_utils.py` - OpenAI handler with conversation memory
- `auth_*.py` - Authentication system (routes, models, utils, schemas)
- `database.py` - Database configuration
- `requirements.txt` - Minimal dependencies
- `.env` - Environment variables (with working API keys)

### Helper Files:
- `README.md` - Detailed documentation
- `start.sh` - Quick startup script
- `test_setup.py` - Setup verification script
- `SETUP_GUIDE.md` - This guide

## 🚀 Quick Start (3 Steps)

### Step 1: Setup Environment
```bash
cd simple_travel_agent

# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Database Setup
```bash
# Make sure PostgreSQL is running
# Create the database (if not exists)
createdb travelagent

# The app will create tables automatically on startup
```

### Step 3: Run the Application
```bash
# Option 1: Use the startup script
./start.sh

# Option 2: Run directly
python simple_main.py

# Option 3: Test setup first
python test_setup.py
```

## ✅ Verification

The application should start and show:
```
INFO:     Started server process [XXXXX]
INFO:     Waiting for application startup.
✅ Database tables created successfully
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

## 🧪 Test the Conversation Memory

### 1. Create a user account:
```bash
curl -X POST "http://localhost:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser", 
    "password": "password123",
    "full_name": "Test User"
  }'
```

### 2. Sign in to get JWT token:
```bash
curl -X POST "http://localhost:8000/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "password123"
  }'
```

### 3. Test conversation memory:

**Initial search:**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "find flights from Delhi to Kochi for tomorrow"}'
```

**Follow-up search (inherits date):**
```bash
curl -X POST "http://localhost:8000/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "find flights for Delhi to Mumbai"}'
```

The second search should automatically use tomorrow's date from the first search!

## 🔧 Configuration

### Environment Variables (.env):
- ✅ **OPENAI_API_KEY** - Already configured
- ✅ **AMADEUS_API_KEY** - Already configured  
- ✅ **AMADEUS_API_SECRET** - Already configured
- 🔧 **DATABASE_URL** - Update if your PostgreSQL settings differ
- 🔧 **SECRET_KEY** - Update for production use

### Database Settings:
- Default: `postgresql://postgres:password@localhost:5432/travelagent`
- Update in `.env` if your PostgreSQL credentials are different

## 🎯 Key Features Working

✅ **Conversation Memory**: Remembers previous searches  
✅ **Date Inheritance**: Auto-inherits dates in follow-up queries  
✅ **OpenAI Integration**: Natural language processing  
✅ **Flight Search**: Real-time Amadeus API integration  
✅ **Authentication**: JWT-based user system  
✅ **Currency Conversion**: Prices in Indian Rupees (INR)  

## 📊 What's Different from Original

This simplified version:
- ❌ Removed complex testing frameworks
- ❌ Removed spell checking utilities  
- ❌ Removed debug modules
- ❌ Removed chat history routes
- ❌ Removed performance optimizations
- ✅ **Kept core conversation memory functionality**
- ✅ **Kept OpenAI integration**
- ✅ **Kept authentication system**
- ✅ **Kept flight search**

## 🆘 Troubleshooting

### Import Errors:
```bash
pip install -r requirements.txt
```

### Database Connection Issues:
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Create database if missing
createdb travelagent
```

### API Key Issues:
- Check `.env` file exists and has correct keys
- Verify OpenAI key starts with `sk-`
- Verify Amadeus keys are not empty

### Test Everything:
```bash
python test_setup.py
```

## 🎉 Success!

If everything works, you now have a **minimal, clean travel agent** with:
- Conversation memory that inherits dates
- OpenAI-powered natural language processing  
- Real-time flight search
- User authentication

**API Documentation**: http://localhost:8000/docs  
**Health Check**: http://localhost:8000/health
