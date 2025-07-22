"""
Simplified Travel Agent - Core OpenAI-based Flight Search
Focus: Clean architecture with OpenAI query handling and date/month range support
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import os
import logging
import json
from datetime import datetime, timedelta
import openai
from amadeus import Client
from sqlalchemy.orm import Session
import dotenv
from dotenv import load_dotenv

from simple_utils import SimpleOpenAIHandler, SimpleFlightFormatter, SimpleDateParser
from auth_routes import router as auth_router
from auth_utils import get_current_user, get_current_user_optional
from auth_models import User
from database import get_db, create_tables

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Initialize FastAPI
app = FastAPI(title="Simple Travel Agent", version="1.0.0")

# Include authentication routes
app.include_router(auth_router)

# Mount static files for frontend
if os.path.exists("frontend"):
    app.mount("/static", StaticFiles(directory="frontend"), name="static")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class FlightSearchRequest(BaseModel):
    query: str

class FlightSearchResponse(BaseModel):
    status: str
    message: str
    flights: List[Dict[str, Any]]
    search_info: Dict[str, Any]

# Initialize services
openai_handler = SimpleOpenAIHandler(os.getenv("OPENAI_API_KEY"))
flight_formatter = SimpleFlightFormatter()  # Now includes currency conversion
amadeus_client = Client(
    client_id=os.getenv("AMADEUS_API_KEY"),
    client_secret=os.getenv("AMADEUS_API_SECRET")
)

class SimpleTravelAgent:
    """Core travel agent with OpenAI integration"""

    def __init__(self):
        self.openai_handler = openai_handler
        self.amadeus = amadeus_client
        self.formatter = flight_formatter

    async def search_flights(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search flights using Amadeus API"""
        try:
            # Extract search parameters
            origin = params.get("origin")
            destination = params.get("destination")
            departure_date = params.get("departure_date")
            passengers = params.get("passengers", 1)
            cabin_class = params.get("cabin_class", "ECONOMY")

            logger.info(f"🛫 Searching flights: {params}")

            # Search flights using Amadeus
            response = self.amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=departure_date,
                adults=passengers,
                travelClass=cabin_class,
                max=10
            )

            if not response.data:
                return {
                    "status": "error",
                    "message": f"No flights found from {origin} to {destination} on {departure_date}",
                    "flights": [],
                    "search_info": params
                }

            # Format flights with currency conversion
            formatted_flights = self.formatter.format_amadeus_response(response.data)

            # Sort by price (ascending)
            formatted_flights.sort(key=lambda x: x.get("price_numeric", float('inf')))

            logger.info(f"✅ Found {len(formatted_flights)} flights")

            return {
                "status": "success",
                "message": f"Found {len(formatted_flights)} flights from {origin} to {destination}",
                "flights": formatted_flights,
                "search_info": params
            }

        except Exception as e:
            logger.error(f"❌ Flight search error: {e}")
            return {
                "status": "error",
                "message": f"Flight search failed: {str(e)}",
                "flights": [],
                "search_info": params
            }

# Initialize travel agent
travel_agent = SimpleTravelAgent()

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    try:
        create_tables()
        logger.info("✅ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise

@app.get("/")
async def root():
    """Serve the frontend HTML file"""
    if os.path.exists("frontend/index.html"):
        return FileResponse("frontend/index.html")
    return {"message": "Simple Travel Agent API", "status": "running"}

def simple_extract_flight_params(query: str) -> dict:
    """Simple parameter extraction without OpenAI as fallback"""
    from datetime import datetime, timedelta

    query_lower = query.lower()

    # City mappings (including common misspellings)
    city_map = {
        'delhi': 'DEL', 'deli': 'DEL', 'dehli': 'DEL',  # Delhi misspellings
        'mumbai': 'BOM', 'mumbay': 'BOM', 'bombay': 'BOM',  # Mumbai misspellings
        'bangalore': 'BLR', 'bangalor': 'BLR', 'banglore': 'BLR',  # Bangalore misspellings
        'chennai': 'MAA', 'chenai': 'MAA', 'channai': 'MAA',  # Chennai misspellings
        'kochi': 'COK', 'cochin': 'COK',  # Kochi misspellings
        'kolkata': 'CCU', 'hyderabad': 'HYD', 'pune': 'PNQ', 'ahmedabad': 'AMD', 'goa': 'GOI'
    }

    # Extract cities
    origin = destination = None
    words = query_lower.split()

    # Look for "from X to Y" pattern
    if 'from' in words and 'to' in words:
        from_idx = words.index('from')
        to_idx = words.index('to')
        if from_idx < to_idx:
            # Check words after 'from' and before 'to'
            for i in range(from_idx + 1, to_idx):
                if words[i] in city_map:
                    origin = city_map[words[i]]
                    break
            # Check words after 'to'
            for i in range(to_idx + 1, len(words)):
                if words[i] in city_map:
                    destination = city_map[words[i]]
                    break
    else:
        # Fallback: find any two cities mentioned
        found_cities = []
        for word in words:
            if word in city_map:
                found_cities.append(city_map[word])
        if len(found_cities) >= 2:
            origin, destination = found_cities[0], found_cities[1]
        elif len(found_cities) == 1:
            origin = found_cities[0]
            destination = 'BOM'  # Default to Mumbai

    # Extract date (with spelling mistake handling)
    departure_date = None
    
    # Handle "tomorrow" and common misspellings
    tomorrow_variants = ['tomorrow', 'tommorow', 'tomorow', 'tommorrow', 'tomorrrow', 'tomarow']
    if any(variant in query_lower for variant in tomorrow_variants):
        departure_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    elif 'today' in query_lower:
        departure_date = datetime.now().strftime('%Y-%m-%d')
    else:
        # Try to parse specific dates like "August 19", "19 August", etc.
        import re



        # Month name to number mapping
        months = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
            'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'october': 10, 'oct': 10,
            'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }

        # Try patterns like "August 19", "19 August", "Aug 19", etc.
        for month_name, month_num in months.items():
            # Pattern: "August 19" or "Aug 19"
            pattern1 = rf'{month_name}\s+(\d{{1,2}})'
            match1 = re.search(pattern1, query_lower)
            if match1:
                day = int(match1.group(1))
                current_year = datetime.now().year
                departure_date = f"{current_year}-{month_num:02d}-{day:02d}"

                break

            # Pattern: "19 August" or "19 Aug"
            pattern2 = rf'(\d{{1,2}})\s+{month_name}'
            match2 = re.search(pattern2, query_lower)
            if match2:
                day = int(match2.group(1))
                current_year = datetime.now().year
                departure_date = f"{current_year}-{month_num:02d}-{day:02d}"

                break

        # If no specific date found, use default
        if not departure_date:
            departure_date = '2025-08-15'  # Default date


    # Extract class
    cabin_class = 'ECONOMY'
    if 'business' in query_lower:
        cabin_class = 'BUSINESS'
    elif 'first' in query_lower:
        cabin_class = 'FIRST'

    return {
        'origin': origin or 'DEL',
        'destination': destination or 'BOM',
        'departure_date': departure_date,
        'passengers': 1,
        'cabin_class': cabin_class
    }

@app.get("/api")
async def api_root():
    """API health check endpoint"""
    return {
        "message": "Simple Travel Agent API", 
        "status": "running",
        "authentication_required": True,
        "note": "All flight search queries require user authentication. Please sign up or login first."
    }

@app.post("/search", response_model=FlightSearchResponse)
async def search_flights(
    request: FlightSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Single endpoint for both initial and follow-up flight searches
    Uses OpenAI to understand natural language queries and conversation memory
    REQUIRES USER AUTHENTICATION - Users must sign up/login before querying
    """
    try:
        logger.info(f"🔍 Processing query: {request.query} for user: {current_user.email}")

        # Use authenticated user ID (authentication is now required)
        user_id = str(current_user.id)

        # Extract flight parameters using OpenAI with spelling mistake handling
        try:
            logger.info("🤖 Using OpenAI for intelligent parameter extraction with spelling correction")
            params = await openai_handler.extract_flight_params(
                request.query,
                user_id=user_id,
                db=db
            )
            logger.info(f"📋 OpenAI extracted params: {params}")
        except Exception as openai_error:
            logger.warning(f"⚠️ OpenAI failed, using simple extraction fallback: {openai_error}")
            params = simple_extract_flight_params(request.query)
            logger.info(f"📋 Fallback extracted params: {params}")

        # Handle errors from parameter extraction
        if "error" in params:
            if params["error"] == "general_query":
                raise HTTPException(
                    status_code=400,
                    detail={
                        "type": "general_query",
                        "message": params["message"],
                        "suggestions": params.get("suggestions", [])
                    }
                )
            elif params["error"].startswith("openai_error"):
                # OpenAI failed, use simple extraction as fallback
                logger.warning(f"⚠️ OpenAI failed, using simple extraction fallback")
                params = simple_extract_flight_params(request.query)
                logger.info(f"📋 Fallback extracted params: {params}")
            else:
                error_message = params.get("message", params.get("error", "Parameter extraction failed"))
                raise HTTPException(status_code=400, detail=error_message)

        logger.info(f"✅ Extracted params: {params}")

        # Search flights
        result = await travel_agent.search_flights(params)

        # Store conversation context if parameter extraction was successful (regardless of Amadeus API result)
        if not params.get("error"):
            openai_handler.conversation_memory.store_flight_search(
                user_id=user_id,
                search_params=params,
                query=request.query,
                db=db
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Search endpoint error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

class DirectSearchRequest(BaseModel):
    origin: str
    destination: str
    departure_date: str
    passengers: int = 1
    cabin_class: str = "ECONOMY"

@app.post("/search-direct")
async def search_flights_direct(request: DirectSearchRequest):
    """Direct flight search bypassing OpenAI for testing"""
    try:
        params = {
            "origin": request.origin,
            "destination": request.destination,
            "departure_date": request.departure_date,
            "passengers": request.passengers,
            "cabin_class": request.cabin_class
        }

        logger.info(f"🛫 Direct search: {params}")
        result = await travel_agent.search_flights(params)
        return result

    except Exception as e:
        logger.error(f"❌ Direct search error: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        "amadeus_configured": bool(os.getenv("AMADEUS_API_KEY"))
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
