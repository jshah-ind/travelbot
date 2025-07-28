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
from chat_routes import router as chat_router
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

# Include chat history routes
app.include_router(chat_router)

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
        """Search flights using Amadeus API with advanced filtering"""
        try:
            # Extract search parameters
            origin = params.get("origin")
            destination = params.get("destination")
            departure_date = params.get("departure_date")
            date_range_end = params.get("date_range_end")  # New parameter for date ranges
            passengers = params.get("passengers", 1)
            cabin_class = params.get("cabin_class", "ECONOMY")
            filters = params.get("filters", {})

            logger.info(f"🛫 Searching flights: {params}")

            # Check if this is a date range search
            if date_range_end:
                logger.info(f"🔍 Date range search: {departure_date} to {date_range_end}")
                return await self._search_flights_date_range(
                    origin, destination, departure_date, date_range_end, 
                    passengers, cabin_class, filters
                )
            else:
                # Single date search
                logger.info(f"🔍 Single date search: {departure_date}")
                return await self._search_flights_single_date(
                    origin, destination, departure_date, passengers, cabin_class, filters
                )

            if not response.data:
                return {
                    "status": "error",
                    "message": f"No flights found from {origin} to {destination} on {departure_date}",
                    "flights": [],
                    "search_info": params
                }

            # Format flights with currency conversion and cabin class filtering
            formatted_flights = self.formatter.format_amadeus_response(response.data, cabin_class)

            # Apply advanced filters
            filtered_flights = self._apply_advanced_filters(formatted_flights, filters)
            
            # Debug: Check what cabin classes were returned
            cabin_classes_returned = set()
            for flight in formatted_flights:
                cabin_classes_returned.add(flight.get("cabin_class", "UNKNOWN"))
            logger.info(f"🔍 Cabin classes returned by Amadeus: {cabin_classes_returned}")
            logger.info(f"🔍 Applied filters: {filters}")
            logger.info(f"🔍 Flights after filtering: {len(filtered_flights)} out of {len(formatted_flights)}")

            # Sort by price (ascending)
            filtered_flights.sort(key=lambda x: x.get("price_numeric", float('inf')))

            logger.info(f"✅ Found {len(filtered_flights)} flights after filtering")

            return {
                "status": "success",
                "message": f"Found {len(filtered_flights)} flights from {origin} to {destination}",
                "flights": filtered_flights,
                "search_info": params,
                "filters_applied": filters
            }

        except Exception as e:
            logger.error(f"❌ Flight search error: {e}")
            return {
                "status": "error",
                "message": f"Flight search failed: {str(e)}",
                "flights": [],
                "search_info": params
            }

    async def _search_flights_single_date(self, origin: str, destination: str, departure_date: str, 
                                         passengers: int, cabin_class: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Search flights for a single date"""
        try:
            logger.info(f"🔍 Amadeus API call for single date: {departure_date}")
            response = self.amadeus.shopping.flight_offers_search.get(
                originLocationCode=origin,
                destinationLocationCode=destination,
                departureDate=departure_date,
                adults=passengers,
                travelClass=cabin_class,
                max=50
            )

            if not response.data:
                return {
                    "status": "error",
                    "message": f"No flights found from {origin} to {destination} on {departure_date}",
                    "flights": [],
                    "search_info": {"origin": origin, "destination": destination, "departure_date": departure_date}
                }

            # Format and filter flights
            formatted_flights = self.formatter.format_amadeus_response(response.data, cabin_class)
            filtered_flights = self._apply_advanced_filters(formatted_flights, filters)
            filtered_flights.sort(key=lambda x: x.get("price_numeric", float('inf')))

            logger.info(f"✅ Found {len(filtered_flights)} flights for {departure_date}")

            return {
                "status": "success",
                "message": f"Found {len(filtered_flights)} flights from {origin} to {destination} on {departure_date}",
                "flights": filtered_flights,
                "search_info": {"origin": origin, "destination": destination, "departure_date": departure_date},
                "filters_applied": filters
            }

        except Exception as e:
            logger.error(f"❌ Single date search error: {e}")
            return {
                "status": "error",
                "message": f"Flight search failed: {str(e)}",
                "flights": [],
                "search_info": {"origin": origin, "destination": destination, "departure_date": departure_date}
            }

    async def _search_flights_date_range(self, origin: str, destination: str, start_date: str, end_date: str,
                                       passengers: int, cabin_class: str, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Search flights across a date range"""
        try:
            from datetime import datetime, timedelta
            
            # Convert dates to datetime objects
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Generate list of dates in range
            date_list = []
            current_dt = start_dt
            while current_dt <= end_dt:
                date_list.append(current_dt.strftime("%Y-%m-%d"))
                current_dt += timedelta(days=1)
            
            logger.info(f"🔍 Searching {len(date_list)} dates: {start_date} to {end_date}")
            
            all_flights = []
            successful_dates = []
            
            # Search for each date in the range
            for date in date_list:
                try:
                    logger.info(f"🔍 Searching flights for {date}")
                    response = self.amadeus.shopping.flight_offers_search.get(
                        originLocationCode=origin,
                        destinationLocationCode=destination,
                        departureDate=date,
                        adults=passengers,
                        travelClass=cabin_class,
                        max=20  # Reduced per date to avoid overwhelming results
                    )
                    
                    if response.data:
                        # Format flights and add date information
                        formatted_flights = self.formatter.format_amadeus_response(response.data, cabin_class)
                        
                        # Add search date to each flight
                        for flight in formatted_flights:
                            flight["search_date"] = date
                        
                        all_flights.extend(formatted_flights)
                        successful_dates.append(date)
                        logger.info(f"✅ Found {len(formatted_flights)} flights for {date}")
                    else:
                        logger.info(f"⚠️ No flights found for {date}")
                        
                except Exception as e:
                    logger.warning(f"⚠️ Error searching for {date}: {e}")
                    continue
            
            if not all_flights:
                return {
                    "status": "error",
                    "message": f"No flights found from {origin} to {destination} between {start_date} and {end_date}",
                    "flights": [],
                    "search_info": {"origin": origin, "destination": destination, "date_range": f"{start_date} to {end_date}"}
                }
            
            # Apply advanced filters to all flights
            filtered_flights = self._apply_advanced_filters(all_flights, filters)
            
            # Sort by date first, then by price
            filtered_flights.sort(key=lambda x: (x.get("search_date", ""), x.get("price_numeric", float('inf'))))
            
            logger.info(f"✅ Found {len(filtered_flights)} flights across {len(successful_dates)} dates")

            return {
                "status": "success",
                "message": f"Found {len(filtered_flights)} flights from {origin} to {destination} between {start_date} and {end_date}",
                "flights": filtered_flights,
                "search_info": {"origin": origin, "destination": destination, "date_range": f"{start_date} to {end_date}"},
                "filters_applied": filters,
                "dates_searched": successful_dates
            }

        except Exception as e:
            logger.error(f"❌ Date range search error: {e}")
            return {
                "status": "error",
                "message": f"Date range search failed: {str(e)}",
                "flights": [],
                "search_info": {"origin": origin, "destination": destination, "date_range": f"{start_date} to {end_date}"}
            }

    def _apply_advanced_filters(self, flights: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Apply advanced filters to flight results"""
        filtered_flights = flights.copy()
        
        # Direct flights only filter
        if filters.get("direct_only", False):
            filtered_flights = [f for f in filtered_flights if self._is_direct_flight(f)]
            logger.info(f"🔍 Applied direct flights filter: {len(filtered_flights)} flights remaining")
        
        # Specific airlines filter
        specific_airlines = filters.get("specific_airlines", [])
        if specific_airlines:
            filtered_flights = [f for f in filtered_flights if self._matches_airline(f, specific_airlines)]
            logger.info(f"🔍 Applied specific airlines filter ({specific_airlines}): {len(filtered_flights)} flights remaining")
        
        # Exclude airlines filter
        exclude_airlines = filters.get("exclude_airlines", [])
        if exclude_airlines:
            filtered_flights = [f for f in filtered_flights if not self._matches_airline(f, exclude_airlines)]
            logger.info(f"🔍 Applied exclude airlines filter ({exclude_airlines}): {len(filtered_flights)} flights remaining")
        
        # Max price filter
        max_price = filters.get("max_price")
        if max_price:
            filtered_flights = [f for f in filtered_flights if f.get("price_numeric", float('inf')) <= max_price]
            logger.info(f"🔍 Applied max price filter (₹{max_price}): {len(filtered_flights)} flights remaining")
        
        # Preferred times filter
        preferred_times = filters.get("preferred_times", [])
        if preferred_times:
            filtered_flights = [f for f in filtered_flights if self._matches_time_preference(f, preferred_times)]
            logger.info(f"🔍 Applied time preference filter ({preferred_times}): {len(filtered_flights)} flights remaining")
        
        # Max stops filter
        max_stops = filters.get("max_stops")
        if max_stops is not None:
            filtered_flights = [f for f in filtered_flights if self._get_stop_count(f) <= max_stops]
            logger.info(f"🔍 Applied max stops filter ({max_stops}): {len(filtered_flights)} flights remaining")
        
        # Preferred airlines (sort by preference, don't filter out)
        preferred_airlines = filters.get("preferred_airlines", [])
        if preferred_airlines:
            filtered_flights.sort(key=lambda f: (0 if self._matches_airline(f, preferred_airlines) else 1, f.get("price_numeric", float('inf'))))
            logger.info(f"🔍 Applied preferred airlines sorting ({preferred_airlines})")
        
        return filtered_flights

    def _is_direct_flight(self, flight: Dict[str, Any]) -> bool:
        """Check if flight is direct (no stops)"""
        # Use the is_direct field if available
        if "is_direct" in flight:
            return flight.get("is_direct", False)
        
        # Fallback to segment-based calculation
        segments = flight.get("segments", [])
        if not segments:
            return True
        
        # If there's only one segment, it's direct
        if len(segments) == 1:
            return True
        
        # If there are multiple segments, it's not direct (connecting flight)
        if len(segments) > 1:
            return False
        
        # Check if the single segment has stops
        if segments[0].get("stops", 0) > 0:
            return False
        
        return True

    def _matches_airline(self, flight: Dict[str, Any], airlines: List[str]) -> bool:
        """Check if flight matches any of the specified airlines (primary carrier only)"""
        segments = flight.get("segments", [])
        if not segments:
            return False
        
        # Only check the primary carrier (first segment) for specific airline filters
        primary_carrier = segments[0].get("carrier", {}).get("name", "")
        if not primary_carrier:
            return False
        
        # Check if the primary carrier matches any of the specified airlines
        for airline in airlines:
            if airline.lower() == primary_carrier.lower():
                return True
        
        return False

    def _get_stop_count(self, flight: Dict[str, Any]) -> int:
        """Get the total number of stops for a flight"""
        segments = flight.get("segments", [])
        total_stops = 0
        
        for segment in segments:
            total_stops += segment.get("stops", 0)
        
        return total_stops

    def _matches_time_preference(self, flight: Dict[str, Any], time_preferences: List[str]) -> bool:
        """Check if flight departure time matches time preferences"""
        segments = flight.get("segments", [])
        if not segments:
            return False
        
        # Get departure time from first segment
        departure_time = segments[0].get("departure", {}).get("time", "")
        if not departure_time:
            return False
        
        try:
            # Parse time (assuming format like "10:30")
            hour = int(departure_time.split(":")[0])
            
            for preference in time_preferences:
                if preference == "morning" and 6 <= hour < 12:
                    return True
                elif preference == "afternoon" and 12 <= hour < 18:
                    return True
                elif preference == "evening" and (18 <= hour < 24 or 0 <= hour < 6):
                    return True
            
            return False
        except:
            return False

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


    # Extract class - Enhanced detection
    cabin_class = 'ECONOMY'
    
    # Business class detection - check for multiple patterns
    business_keywords = [
        'business class', 'business', 'business cabin', 'premium economy', 'premium',
        'business only', 'only business', 'show only business', 'business class only'
    ]
    
    # First class detection
    first_keywords = [
        'first class', 'first', 'luxury', 'first only', 'only first', 'show only first'
    ]
    
    # Economy class detection
    economy_keywords = [
        'economy class', 'economy', 'coach', 'economy only', 'only economy', 'show only economy'
    ]
    
    # Check for business class first (highest priority)
    if any(keyword in query_lower for keyword in business_keywords):
        cabin_class = 'BUSINESS'
        print(f"🔍 Simple extraction: Detected BUSINESS class from query: {query}")
    elif any(keyword in query_lower for keyword in first_keywords):
        cabin_class = 'FIRST'
        print(f"🔍 Simple extraction: Detected FIRST class from query: {query}")
    elif any(keyword in query_lower for keyword in economy_keywords):
        cabin_class = 'ECONOMY'
        print(f"🔍 Simple extraction: Detected ECONOMY class from query: {query}")
    else:
        print(f"🔍 Simple extraction: No class specified, defaulting to ECONOMY for query: {query}")

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

        # 🔄 NEW: Check if this is a reset query to clear conversation context
        if openai_handler.conversation_memory.is_reset_query(request.query):
            logger.info(f"🔄 Reset query detected for user {user_id}")
            
            # Clear conversation context
            success = openai_handler.conversation_memory.clear_conversation_context(user_id, db)
            
            if success:
                return {
                    "status": "success",
                    "message": "✅ Conversation context cleared! You can now start a new search.",
                    "flights": [],
                    "search_info": {"reset": True, "message": "Conversation context cleared"}
                }
            else:
                logger.warning(f"⚠️ Failed to clear conversation context for user {user_id}")

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
        logger.info(f"🔍 Cabin class being used: {params.get('cabin_class', 'NOT SET')}")
        logger.info(f"🔍 Query was: '{request.query}'")

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

@app.post("/reset-conversation")
async def reset_conversation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Explicitly clear conversation context for the current user
    This stops follow-up questions and starts a fresh conversation
    """
    try:
        user_id = str(current_user.id)
        logger.info(f"🔄 Explicit conversation reset requested for user: {current_user.email}")
        
        # Clear conversation context
        success = openai_handler.conversation_memory.clear_conversation_context(user_id, db)
        
        if success:
            return {
                "status": "success",
                "message": "✅ Conversation context cleared successfully! You can now start a new search.",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to clear conversation context"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Reset conversation error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/conversation-status")
async def get_conversation_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Check if user has active conversation context
    """
    try:
        user_id = str(current_user.id)
        
        # Get last conversation context
        last_context = openai_handler.conversation_memory.get_last_flight_search(user_id, db)
        
        if last_context:
            return {
                "has_context": True,
                "last_search": {
                    "origin": last_context.get("origin"),
                    "destination": last_context.get("destination"),
                    "departure_date": last_context.get("departure_date"),
                    "cabin_class": last_context.get("cabin_class"),
                    "passengers": last_context.get("passengers")
                },
                "message": "You have an active conversation context. Use 'reset' or 'new search' to clear it."
            }
        else:
            return {
                "has_context": False,
                "message": "No active conversation context. You can start a new search."
            }
            
    except Exception as e:
        logger.error(f"❌ Conversation status error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/new-session")
async def start_new_session(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Start a new session by clearing conversation context
    This is equivalent to reset-conversation but with different semantics
    """
    try:
        user_id = str(current_user.id)
        logger.info(f"🆕 New session requested for user: {current_user.email}")
        
        # Clear conversation context
        success = openai_handler.conversation_memory.clear_conversation_context(user_id, db)
        
        if success:
            return {
                "status": "success",
                "message": "🆕 New session started! Previous conversation context cleared.",
                "user_id": user_id,
                "session_started": True,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to start new session"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ New session error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
