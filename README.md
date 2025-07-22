# Simple Travel Agent

A simplified travel agent application with OpenAI-powered conversation memory and flight search capabilities.

## Features

- 🤖 **OpenAI Integration**: Natural language query processing
- 💬 **Conversation Memory**: Remembers previous searches and inherits context
- ✈️ **Flight Search**: Real-time flight data via Amadeus API
- 🔐 **Authentication**: JWT-based user authentication
- 📅 **Smart Date Handling**: Supports relative dates and month ranges
- 💰 **Currency Conversion**: Displays prices in Indian Rupees (INR)

## Quick Start

### 1. Prerequisites

- Python 3.8+
- PostgreSQL database
- OpenAI API key
- Amadeus API credentials

### 2. Installation

```bash
# Clone or copy the simple_travel_agent folder
cd simple_travel_agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Setup

```bash
# Copy the environment template
cp .env.template .env

# Edit .env with your actual API keys and database credentials
nano .env
```

Required environment variables:
- `OPENAI_API_KEY`: Your OpenAI API key
- `AMADEUS_API_KEY`: Your Amadeus API key  
- `AMADEUS_API_SECRET`: Your Amadeus API secret
- `DATABASE_URL`: PostgreSQL connection string
- `SECRET_KEY`: JWT secret key (minimum 32 characters)

### 4. Database Setup

```bash
# Make sure PostgreSQL is running
# Create database named 'travelagent'
createdb travelagent

# The application will automatically create tables on startup
```

### 5. Run the Application

```bash
python simple_main.py
```

The API will be available at: `http://localhost:8000`
The frontend will be available at: `http://localhost:8000` (automatically served)

## Usage

### Web Interface

Simply open your browser and go to `http://localhost:8000` to use the web interface!

The web interface includes:
- 🔐 **User Authentication**: Sign up/sign in functionality
- 💬 **Conversation Memory**: Visual indicators for follow-up queries
- ✈️ **Flight Search**: Natural language flight search
- 📱 **Responsive Design**: Works on desktop and mobile

### API Usage (Advanced)

### Authentication

1. **Sign Up**:
```bash
curl -X POST "http://localhost:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "password123",
    "full_name": "Test User"
  }'
```

2. **Sign In**:
```bash
curl -X POST "http://localhost:8000/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

### Flight Search

Use the JWT token from sign-in for authenticated requests:

```bash
curl -X POST "http://localhost:8000/search" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "find flights from Delhi to Mumbai for tomorrow"}'
```

### Conversation Memory Examples

1. **Initial Search**:
```json
{"query": "find flights from Delhi to Kochi for tomorrow"}
```

2. **Follow-up with New Route** (inherits date):
```json
{"query": "find flights for Delhi to Mumbai"}
```

The system will automatically use the date from the previous search!

## API Endpoints

- `GET /` - Health check
- `GET /health` - Detailed health status
- `POST /auth/signup` - User registration
- `POST /auth/signin` - User login
- `POST /search` - Flight search (requires authentication)

## File Structure

```
simple_travel_agent/
├── simple_main.py          # Main FastAPI application
├── simple_utils.py         # OpenAI handler and utilities
├── auth_routes.py          # Authentication endpoints
├── auth_utils.py           # Authentication utilities
├── auth_models.py          # Database models
├── auth_schemas.py         # Pydantic schemas
├── database.py             # Database configuration
├── requirements.txt        # Python dependencies
├── .env.template          # Environment variables template
├── frontend/              # Web frontend
│   ├── index.html         # Main HTML page
│   ├── app.js            # JavaScript functionality
│   └── package.json      # Frontend metadata
└── README.md              # This file
```

## Key Features

### Conversation Memory
- Remembers previous flight searches
- Automatically inherits dates when not specified in follow-up queries
- Supports route changes while maintaining date context

### Smart Query Processing
- Natural language understanding via OpenAI
- Handles spelling mistakes and variations
- Supports relative dates (tomorrow, next week, etc.)
- Month range queries (flights in August)

### Flight Search
- Real-time flight data from Amadeus
- Price comparison and sorting
- Multiple cabin classes support
- Currency conversion to INR

## Troubleshooting

1. **Database Connection Issues**:
   - Ensure PostgreSQL is running
   - Check DATABASE_URL in .env file
   - Verify database exists

2. **API Key Issues**:
   - Verify OpenAI API key is valid
   - Check Amadeus API credentials
   - Ensure .env file is properly loaded

3. **Import Errors**:
   - Activate virtual environment
   - Install all requirements: `pip install -r requirements.txt`

## Support

For issues or questions, check the logs for detailed error messages. The application uses comprehensive logging to help diagnose problems.
