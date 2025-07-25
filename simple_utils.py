"""
Simplified utilities for travel agent
Focus: Essential date parsing and OpenAI integration
"""

import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import openai
from sqlalchemy.orm import Session
from sqlalchemy import and_


class ConversationMemory:
    """Manages conversation context and follow-up queries using database storage"""

    def __init__(self, db: Session = None):
        self.db = db
        self.logger = logging.getLogger(__name__)

    def store_flight_search(self, user_id: str, search_params: Dict[str, Any], query: str, db: Session):
        """Store successful flight search for follow-up queries in database"""
        try:
            # Import here to avoid circular imports
            from auth_models import ConversationContext

            # Clean up expired contexts first
            self._cleanup_expired_contexts(user_id, db)

            # Create new context
            expires_at = datetime.utcnow() + timedelta(minutes=30)  # 30-minute expiration

            # Handle guest users vs authenticated users
            if user_id == "guest_user":
                # For guest users, use a special ID (negative number to avoid conflicts)
                db_user_id = -1
            else:
                db_user_id = int(user_id)

            context = ConversationContext(
                user_id=db_user_id,
                context_type="flight_search",
                original_query=query,
                search_params=search_params.copy(),
                origin=search_params.get("origin"),
                destination=search_params.get("destination"),
                departure_date=search_params.get("departure_date"),
                passengers=search_params.get("passengers", 1),
                cabin_class=search_params.get("cabin_class", "ECONOMY"),
                expires_at=expires_at
            )

            db.add(context)
            db.commit()
            db.refresh(context)

            # Keep only last 5 contexts per user
            self._limit_user_contexts(user_id, db)

            self.logger.info(f"💾 Stored context for user {user_id}: {search_params['origin']} → {search_params['destination']}")

        except Exception as e:
            self.logger.error(f"❌ Failed to store conversation context: {e}")
            db.rollback()

    def get_last_flight_search(self, user_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Get the most recent flight search context from database"""
        try:
            # Import here to avoid circular imports
            from auth_models import ConversationContext

            # Clean up expired contexts first
            self._cleanup_expired_contexts(user_id, db)

            # Handle guest users vs authenticated users
            if user_id == "guest_user":
                db_user_id = -1
            else:
                db_user_id = int(user_id)

            # Get most recent active flight search context
            context = db.query(ConversationContext).filter(
                and_(
                    ConversationContext.user_id == db_user_id,
                    ConversationContext.context_type == "flight_search",
                    ConversationContext.is_active == True,
                    ConversationContext.expires_at > datetime.utcnow()
                )
            ).order_by(ConversationContext.created_at.desc()).first()

            if context:
                return {
                    "type": "flight_search",
                    "query": context.original_query,
                    "params": context.search_params,
                    "timestamp": context.created_at,
                    "origin": context.origin,
                    "destination": context.destination,
                    "departure_date": context.departure_date,
                    "passengers": context.passengers,
                    "cabin_class": context.cabin_class
                }

            return None

        except Exception as e:
            self.logger.error(f"❌ Failed to get conversation context: {e}")
            return None

    def _cleanup_expired_contexts(self, user_id: str, db: Session):
        """Remove expired contexts for a user"""
        try:
            from auth_models import ConversationContext

            # Handle guest users vs authenticated users
            if user_id == "guest_user":
                db_user_id = -1
            else:
                db_user_id = int(user_id)

            db.query(ConversationContext).filter(
                and_(
                    ConversationContext.user_id == db_user_id,
                    ConversationContext.expires_at <= datetime.utcnow()
                )
            ).update({"is_active": False})

            db.commit()

        except Exception as e:
            self.logger.error(f"❌ Failed to cleanup expired contexts: {e}")
            db.rollback()

    def _limit_user_contexts(self, user_id: str, db: Session):
        """Keep only the last 5 contexts per user"""
        try:
            from auth_models import ConversationContext

            # Get all active contexts for user, ordered by creation date
            contexts = db.query(ConversationContext).filter(
                and_(
                    ConversationContext.user_id == int(user_id),
                    ConversationContext.is_active == True
                )
            ).order_by(ConversationContext.created_at.desc()).all()

            # If more than 5, deactivate the oldest ones
            if len(contexts) > 5:
                contexts_to_deactivate = contexts[5:]  # Keep first 5, deactivate rest
                for context in contexts_to_deactivate:
                    context.is_active = False

                db.commit()

        except Exception as e:
            self.logger.error(f"❌ Failed to limit user contexts: {e}")
            db.rollback()

    def detect_follow_up_query(self, query: str, user_id: str, db: Session) -> Optional[Dict[str, Any]]:
        """Detect if query is a follow-up to previous search"""
        query_lower = query.lower().strip()

        # Get last flight search context from database
        last_search = self.get_last_flight_search(user_id, db)
        if not last_search:
            return None

        # 🔧 FIX: If query has complete route information (origin + destination), treat as new query
        # This prevents over-aggressive follow-up detection for queries like "book 2 business class tickets from Mumbai to Goa"
        if self._has_complete_route_info(query_lower):
            self.logger.info(f"🔄 Query has complete route info, treating as new query (not follow-up)")
            return None

        # Detect follow-up patterns
        follow_up_patterns = {
            # Class changes
            "business_class": [
                "business class", "business", "show business", "business flights",
                "premium", "upgrade", "first class", "economy plus",
                "change to business", "make it business"
            ],
            "economy_class": [
                "economy", "economy class", "show economy", "cheaper", "budget",
                "change to economy", "make it economy", "economy instead"
            ],
            # Date modifications
            "different_date": [
                "different date", "another date", "other dates", "next day",
                "day before", "earlier", "later", "weekend"
            ],
            # Passenger changes - IMPROVED
            "more_passengers": [
                "2 passengers", "3 passengers", "4 passengers", "family",
                "add passenger", "more people", "add one more passenger",
                "one more person", "add another passenger", "more passenger",
                "add one more", "one more traveler"
            ],
            # Route changes - NEW
            "destination_change": [
                "change destination to", "destination to", "go to", "fly to",
                "change to", "instead of"
            ],
            "origin_change": [
                "change origin to", "origin to", "from", "start from",
                "depart from", "leave from"
            ],
            # General modifications
            "show_more": [
                "show more", "more flights", "other options", "alternatives",
                "different airlines", "more results"
            ]
        }

        detected_type = None
        for pattern_type, patterns in follow_up_patterns.items():
            if any(pattern in query_lower for pattern in patterns):
                detected_type = pattern_type
                break

        if detected_type:
            self.logger.info(f"🔄 Detected follow-up: {detected_type} for user {user_id}")
            return {
                "type": detected_type,
                "last_search": last_search,
                "original_query": query
            }

        # 🔄 ENHANCED: Check if this is a route change query (has cities but no date)
        # This handles cases like "find flights for Delhi to Mumbai" after a previous search
        if self._has_route_info(query_lower) and not self._has_date_info(query_lower):
            self.logger.info(f"🔄 Detected route change without date for user {user_id}")
            return {
                "type": "route_change_same_date",
                "last_search": last_search,
                "original_query": query
            }

        # 🔄 NEW: Check if this is a date-only modification (has date but no route)
        # This handles cases like "for August 16" after a previous search
        if self._has_date_info(query_lower) and not self._has_route_info(query_lower):
            self.logger.info(f"🔄 Detected date-only modification for user {user_id}")
            return {
                "type": "date_change_same_route",
                "last_search": last_search,
                "original_query": query
            }

        return None

    def _has_route_info(self, query_lower: str) -> bool:
        """Check if query contains route information (cities/airports)"""
        cities = [
            'delhi', 'mumbai', 'bangalore', 'chennai', 'kolkata', 'hyderabad',
            'pune', 'ahmedabad', 'kochi', 'goa', 'jaipur', 'lucknow',
            'del', 'bom', 'blr', 'maa', 'ccu', 'hyd', 'pnq', 'amd', 'cok', 'goi',
            # Common misspellings
            'deli', 'dehli', 'mumbay', 'bombay', 'bangalor', 'banglore',
            'chenai', 'channai', 'cochin'
        ]

        # Check for "from X to Y" pattern or individual cities
        has_cities = any(city in query_lower for city in cities)
        has_route_pattern = 'from' in query_lower and 'to' in query_lower

        return has_cities or has_route_pattern

    def _has_date_info(self, query_lower: str) -> bool:
        """Check if query contains date information"""
        date_keywords = [
            'tomorrow', 'today', 'next week', 'next month', 'monday', 'tuesday',
            'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december',
            'jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
            # Tomorrow variants
            'tommorow', 'tomorow', 'tommorrow', 'tomorrrow', 'tomarow'
        ]

        # Check for date patterns like "July 8", "2025-07-08", "18th", etc.
        import re
        date_patterns = [
            r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}',  # 7/8/2025, 07-08-2025
            r'\d{4}-\d{1,2}-\d{1,2}',          # 2025-07-08
            r'\d{1,2}(st|nd|rd|th)',           # 8th, 21st, 22nd, 23rd
            r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}',  # July 8
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}'  # Jul 8
        ]

        has_date_keywords = any(keyword in query_lower for keyword in date_keywords)
        has_date_patterns = any(re.search(pattern, query_lower, re.IGNORECASE) for pattern in date_patterns)

        return has_date_keywords or has_date_patterns

    def _has_complete_route_info(self, query_lower: str) -> bool:
        """Check if query contains complete route information (both origin and destination)"""
        
        # 🔧 FIX: Don't treat follow-up change phrases as complete routes
        change_phrases = [
            'change destination to', 'change to', 'destination to', 'change origin to',
            'origin to', 'go to', 'fly to'
        ]
        
        # If query contains change phrases, it's likely a follow-up, not a complete route
        if any(phrase in query_lower for phrase in change_phrases):
            return False
        
        cities = [
            'delhi', 'mumbai', 'bangalore', 'chennai', 'kolkata', 'hyderabad',
            'pune', 'ahmedabad', 'kochi', 'goa', 'jaipur', 'lucknow',
            'del', 'bom', 'blr', 'maa', 'ccu', 'hyd', 'pnq', 'amd', 'cok', 'goi',
            # Common misspellings
            'deli', 'dehli', 'mumbay', 'bombay', 'bangalor', 'banglore',
            'chenai', 'channai', 'cochin'
        ]

        # Check for explicit "from X to Y" pattern (but not change phrases)
        if 'from' in query_lower and 'to' in query_lower:
            return True

        # Count how many different cities are mentioned
        cities_found = []
        for city in cities:
            if city in query_lower:
                cities_found.append(city)

        # If 2 or more different cities are mentioned, likely a complete route
        if len(set(cities_found)) >= 2:
            return True

        return False

    def _extract_city_from_query(self, query: str) -> Optional[str]:
        """Extract city name from query and return airport code"""
        query_lower = query.lower()
        
        # City to airport code mapping
        city_map = {
            'delhi': 'DEL', 'mumbai': 'BOM', 'bangalore': 'BLR', 'chennai': 'MAA',
            'kolkata': 'CCU', 'hyderabad': 'HYD', 'pune': 'PNQ', 'ahmedabad': 'AMD',
            'kochi': 'COK', 'goa': 'GOI', 'jaipur': 'JAI', 'lucknow': 'LKO',
            # Common misspellings
            'deli': 'DEL', 'dehli': 'DEL', 'mumbay': 'BOM', 'bombay': 'BOM',
            'bangalor': 'BLR', 'banglore': 'BLR', 'chenai': 'MAA', 'channai': 'MAA',
            'cochin': 'COK'
        }
        
        # Look for cities in the query
        for city, code in city_map.items():
            if city in query_lower:
                return code
        
        return None

import logging
import requests

logger = logging.getLogger(__name__)

class SimpleDateParser:
    """Simple date parser for travel queries"""
    
    def __init__(self):
        # Month mappings
        self.months = {
            'january': 1, 'jan': 1, 'february': 2, 'feb': 2, 'march': 3, 'mar': 3,
            'april': 4, 'apr': 4, 'may': 5, 'june': 6, 'jun': 6,
            'july': 7, 'jul': 7, 'august': 8, 'aug': 8, 'september': 9, 'sep': 9,
            'october': 10, 'oct': 10, 'november': 11, 'nov': 11, 'december': 12, 'dec': 12
        }
    
    def parse_date(self, query: str) -> str:
        """Parse date from query and return YYYY-MM-DD format"""
        query_lower = query.lower()
        today = datetime.now()  # Get current date each time

        # Handle relative dates (including common misspellings)
        tomorrow_variants = ['tomorrow', 'tommorow', 'tomorow', 'tommorrow', 'tomorrrow', 'tomorow', 'tomarow']
        if any(variant in query_lower for variant in tomorrow_variants):
            date = today + timedelta(days=1)
            return date.strftime("%Y-%m-%d")
        
        if 'next week' in query_lower:
            date = today + timedelta(days=7)
            return date.strftime("%Y-%m-%d")

        if 'next month' in query_lower:
            # Calculate next month - if we're past the 15th, use 1st of next month
            # If we're before the 15th, use 15th of next month for better user experience
            next_month = today.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)

            # Use 15th of next month for better flight availability
            if today.day <= 15:
                try:
                    next_month = next_month.replace(day=15)
                except ValueError:
                    # Handle months with less than 15 days (shouldn't happen, but safety)
                    next_month = next_month.replace(day=1)

            return next_month.strftime("%Y-%m-%d")
        
        # Handle specific dates like "August 18", "Aug 20", etc.
        for month_name, month_num in self.months.items():
            pattern = rf'{month_name}\s+(\d{{1,2}})'
            match = re.search(pattern, query_lower)
            if match:
                day = int(match.group(1))
                year = today.year
                # If month has passed, use next year
                if month_num < today.month:
                    year += 1
                return f"{year}-{month_num:02d}-{day:02d}"

        # Return None if no date found - let the system handle inheritance
        return None
    
    def parse_month_range(self, query: str) -> Dict[str, Any]:
        """Parse month range queries like 'flights in August' or 'flights next month'"""
        query_lower = query.lower()
        today = datetime.now()  # Get current date each time

        # Check if this is a specific date query (contains numbers indicating a specific day or relative dates)
        import re

        # Check for relative date terms first (tomorrow, today, etc.)
        tomorrow_variants = ['tomorrow', 'tommorow', 'tomorow', 'tommorrow', 'tomorrrow', 'tomorow', 'tomarow']
        if any(variant in query_lower for variant in tomorrow_variants):
            return {"type": "single_date", "date": self.parse_date(query)}

        if 'today' in query_lower or 'yesterday' in query_lower:
            return {"type": "single_date", "date": self.parse_date(query)}

        # Look for patterns like "august 12", "12 august", "august 12th", etc.
        date_patterns = [
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}\b',
            r'\b\d{1,2}\s+(january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(st|nd|rd|th)\b'
        ]

        for pattern in date_patterns:
            if re.search(pattern, query_lower):
                # This is a specific date query, not a month range query
                return {"type": "single_date", "date": self.parse_date(query)}

        # Check for "next month" queries first
        if 'next month' in query_lower:
            # Calculate next month range
            next_month = today.replace(day=1) + timedelta(days=32)
            next_month = next_month.replace(day=1)

            # Get first and last day of next month
            start_date = next_month
            if next_month.month == 12:
                end_date = datetime(next_month.year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = datetime(next_month.year, next_month.month + 1, 1) - timedelta(days=1)

            month_names = ['', 'January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December']

            return {
                "type": "month_range",
                "start_date": start_date.strftime("%Y-%m-%d"),
                "end_date": end_date.strftime("%Y-%m-%d"),
                "month_name": f"{month_names[next_month.month]} {next_month.year}"
            }

        # Check for month-only queries (like "flights in August", "August flights")
        for month_name, month_num in self.months.items():
            if month_name in query_lower:
                # Check if it's really a month-only query by looking for indicators
                month_indicators = ['in ' + month_name, month_name + ' flights', 'during ' + month_name,
                                  'throughout ' + month_name, month_name + ' month']

                is_month_query = any(indicator in query_lower for indicator in month_indicators)

                # Also check if the query is just asking about the month without specific dates
                if is_month_query or (month_name in query_lower and not re.search(r'\d{1,2}', query_lower)):
                    year = today.year
                    if month_num < today.month:
                        year += 1

                    # Get first and last day of month
                    start_date = datetime(year, month_num, 1)
                    if month_num == 12:
                        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
                    else:
                        end_date = datetime(year, month_num + 1, 1) - timedelta(days=1)

                    return {
                        "type": "month_range",
                        "start_date": start_date.strftime("%Y-%m-%d"),
                        "end_date": end_date.strftime("%Y-%m-%d"),
                        "month_name": f"{month_name.title()} {year}"
                    }

        return {"type": "single_date", "date": self.parse_date(query)}

class SimpleOpenAIHandler:
    """Simple OpenAI integration for query processing"""

    def __init__(self, api_key: str):
        self.client = openai.OpenAI(api_key=api_key)
        self.date_parser = SimpleDateParser()
        self.conversation_memory = ConversationMemory()
        self.logger = logging.getLogger(__name__)

    def classify_query_type(self, query: str) -> Dict[str, Any]:
        """Classify if query is flight-related or general"""
        query_lower = query.lower()

        # Flight-related keywords
        flight_keywords = [
            'flight', 'flights', 'fly', 'flying', 'travel', 'trip', 'journey',
            'book', 'booking', 'ticket', 'tickets', 'airport', 'airline',
            'departure', 'arrival', 'takeoff', 'landing'
        ]

        # Location keywords (Indian cities and common travel terms)
        location_keywords = [
            'delhi', 'mumbai', 'bangalore', 'chennai', 'kolkata', 'hyderabad',
            'pune', 'ahmedabad', 'kochi', 'goa', 'jaipur', 'lucknow',
            'from', 'to', 'between', 'via'
        ]

        # Date/time keywords
        date_keywords = [
            'today', 'tomorrow', 'yesterday', 'next week', 'next month',
            'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday',
            'january', 'february', 'march', 'april', 'may', 'june',
            'july', 'august', 'september', 'october', 'november', 'december'
        ]

        # Count matches
        flight_score = sum(1 for keyword in flight_keywords if keyword in query_lower)
        location_score = sum(1 for keyword in location_keywords if keyword in query_lower)
        date_score = sum(1 for keyword in date_keywords if keyword in query_lower)

        total_score = flight_score + location_score + date_score

        # Classification logic
        if total_score >= 2 or flight_score >= 1:
            return {
                "type": "flight_query",
                "confidence": min(total_score * 0.3, 1.0),
                "scores": {
                    "flight": flight_score,
                    "location": location_score,
                    "date": date_score
                }
            }
        else:
            return {
                "type": "general_query",
                "confidence": 0.8,
                "suggestion": "I'm a flight search assistant. Try asking about flights between cities!"
            }

    def get_smart_suggestions(self, query: str) -> List[str]:
        """Generate smart flight suggestions based on user query context"""
        query_lower = query.lower()

        # Location-based suggestions
        if 'delhi' in query_lower:
            return [
                "Search flights from Delhi to Mumbai tomorrow",
                "Find flights from Delhi to Bangalore next week",
                "Show flights from Delhi to Goa this weekend"
            ]
        elif 'mumbai' in query_lower:
            return [
                "Search flights from Mumbai to Delhi tomorrow",
                "Find flights from Mumbai to Chennai next week",
                "Show flights from Mumbai to Kochi in August"
            ]
        elif any(word in query_lower for word in ['vacation', 'holiday', 'trip']):
            return [
                "Plan a trip: flights from Delhi to Goa next month",
                "Weekend getaway: flights from Mumbai to Bangalore",
                "Holiday flights: Delhi to Chennai in August"
            ]
        elif any(word in query_lower for word in ['business', 'work', 'meeting']):
            return [
                "Business travel: flights from Delhi to Mumbai tomorrow",
                "Quick trip: flights from Bangalore to Hyderabad today",
                "Same-day return: flights from Chennai to Kochi"
            ]
        else:
            return [
                "Search flights from Delhi to Mumbai tomorrow",
                "Find flights from Bangalore to Chennai next week",
                "Show flights from Kochi to Goa in August"
            ]

    def store_successful_search(self, user_id: str, search_params: Dict[str, Any], query: str, db: Session):
        """Store successful flight search for future follow-ups"""
        if user_id and db:
            self.conversation_memory.store_flight_search(user_id, search_params, query, db)

    def handle_follow_up_query(self, follow_up_info: Dict[str, Any]) -> Dict[str, Any]:
        """Handle follow-up queries based on previous search context"""
        follow_up_type = follow_up_info["type"]
        last_search = follow_up_info["last_search"]
        original_query = follow_up_info["original_query"]

        # Create modified search parameters based on follow-up type
        new_params = last_search["params"].copy()

        if follow_up_type == "business_class":
            new_params["cabin_class"] = "BUSINESS"
            self.logger.info(f"🔄 Follow-up: Changing to business class")

        elif follow_up_type == "economy_class":
            new_params["cabin_class"] = "ECONOMY"
            self.logger.info(f"🔄 Follow-up: Changing to economy class")

        elif follow_up_type == "more_passengers":
            # Extract number from query
            import re
            numbers = re.findall(r'\d+', original_query)
            if numbers:
                new_params["passengers"] = int(numbers[0])
                self.logger.info(f"🔄 Follow-up: Changing to {numbers[0]} passengers")
            else:
                new_params["passengers"] = 2  # Default to 2 if no number found

        elif follow_up_type == "different_date":
            # For now, keep same date but could be enhanced to detect specific date changes
            self.logger.info(f"🔄 Follow-up: Date modification requested")

        elif follow_up_type == "show_more":
            # Keep same parameters, just indicate it's a "show more" request
            self.logger.info(f"🔄 Follow-up: Show more options")

        elif follow_up_type == "destination_change":
            # Extract new destination from the query
            self.logger.info(f"🔄 Follow-up: Destination change requested")
            new_destination = self.conversation_memory._extract_city_from_query(original_query)
            if new_destination:
                new_params["destination"] = new_destination
                self.logger.info(f"🔄 Follow-up: Changed destination to {new_destination}")
                return new_params
            else:
                self.logger.warning(f"🔄 Follow-up: Could not extract destination from '{original_query}'")
                return None

        elif follow_up_type == "origin_change":
            # Extract new origin from the query
            self.logger.info(f"🔄 Follow-up: Origin change requested")
            new_origin = self.conversation_memory._extract_city_from_query(original_query)
            if new_origin:
                new_params["origin"] = new_origin
                self.logger.info(f"🔄 Follow-up: Changed origin to {new_origin}")
                return new_params
            else:
                self.logger.warning(f"🔄 Follow-up: Could not extract origin from '{original_query}'")
                return None

        elif follow_up_type == "route_change_same_date":
            # Extract new route from the query but keep the same date
            self.logger.info(f"🔄 Follow-up: Route change with same date from previous search")
            # Need to extract new route from original query using OpenAI
            # Return None to indicate we need fresh parameter extraction
            return None

        elif follow_up_type == "date_change_same_route":
            # Extract new date from the query but keep the same route
            self.logger.info(f"🔄 Follow-up: Date change with same route from previous search")
            # Parse the new date from the query
            new_date = self.date_parser.parse_date(original_query)
            if new_date:
                new_params["departure_date"] = new_date
                self.logger.info(f"🔄 Follow-up: Updated date to {new_date}")
                return new_params
            else:
                # If we can't parse the date, return None to trigger fresh extraction
                self.logger.warning(f"🔄 Follow-up: Could not parse date from '{original_query}', using fresh extraction")
                return None

        return new_params

    async def extract_flight_params(self, query: str, user_id: str = None, db: Session = None) -> Dict[str, Any]:
        """Extract flight search parameters using OpenAI"""
        try:
            # Initialize follow-up metadata
            follow_up_metadata = None
            is_follow_up_query = False

            # Check for follow-up queries first - this takes priority over classification
            if user_id and db:
                follow_up_info = self.conversation_memory.detect_follow_up_query(query, user_id, db)
                if follow_up_info:
                    is_follow_up_query = True
                    self.logger.info(f"🔄 Processing follow-up query: {follow_up_info['type']}")
                    modified_params = self.handle_follow_up_query(follow_up_info)

                    # If handle_follow_up_query returns None, we need fresh parameter extraction
                    if modified_params is not None:
                        # Add follow-up metadata
                        modified_params["is_follow_up"] = True
                        modified_params["follow_up_type"] = follow_up_info["type"]
                        modified_params["original_query"] = follow_up_info["original_query"]
                        return modified_params
                    else:
                        # Continue with fresh extraction but remember this is a follow-up
                        self.logger.info(f"🔄 Follow-up requires fresh parameter extraction")
                        follow_up_metadata = {
                            "is_follow_up": True,
                            "follow_up_type": follow_up_info["type"],
                            "original_query": follow_up_info["original_query"]
                        }

            # Only classify query type if it's not a follow-up
            if not is_follow_up_query:
                classification = self.classify_query_type(query)
                
                if classification["type"] == "general_query":
                    # Provide context-aware responses based on query content
                    query_lower = query.lower()

                    if any(word in query_lower for word in ['weather', 'temperature', 'rain', 'sunny']):
                        message = "I can't check weather, but I can help you find flights! Weather is important for travel planning."
                    elif any(word in query_lower for word in ['joke', 'funny', 'laugh']):
                        message = "I'm not a comedian, but I can make your travel planning fun! Let me find you great flight deals."
                    elif any(word in query_lower for word in ['food', 'cook', 'recipe', 'eat']):
                        message = "I can't help with cooking, but I can help you fly to places with amazing food!"
                    elif any(word in query_lower for word in ['capital', 'country', 'geography']):
                        message = "I can't answer geography questions, but I can help you fly to any capital city!"
                    else:
                        message = classification["suggestion"]

                    return {
                        "error": "general_query",
                        "message": message,
                        "suggestions": self.get_smart_suggestions(query)
                    }

            system_prompt = """
            You are a flight search assistant. Extract flight search parameters from user queries.

            IMPORTANT: Handle spelling mistakes intelligently. Common misspellings to recognize:
            - "tommorow", "tommorrow", "tomorow", "tomorrrow", "tomarow" = "tomorrow"
            - "deli", "dehli" = "Delhi"
            - "mumbay", "bombay" = "Mumbai"
            - "bangalor", "banglore" = "Bangalore"
            - "chenai", "channai" = "Chennai"
            - "kochi", "cochin" = "Kochi"

            Return ONLY valid JSON with these fields:
            {
                "origin": "airport_code",
                "destination": "airport_code",
                "departure_date": "YYYY-MM-DD",
                "passengers": 1,
                "cabin_class": "ECONOMY"
            }

            Airport codes:
            Delhi=DEL, Mumbai=BOM, Bangalore=BLR, Chennai=MAA, Kolkata=CCU,
            Hyderabad=HYD, Pune=PNQ, Ahmedabad=AMD, Kochi=COK, Goa=GOI

            For dates (today is 2025-07-04):
            - "tomorrow" or any misspelling = 2025-07-05
            - "today" = 2025-07-04
            - "next week" = 2025-07-11
            - "August 18" = 2025-08-18
            - "next month" = 2025-08-15

            CABIN CLASS DETECTION (CRITICAL):
            - ALWAYS check the entire query for cabin class keywords FIRST
            - If ANY of these words appear: "business class", "business", "business cabin", "premium economy", "premium", "business only", "only business" = set "cabin_class": "BUSINESS"
            - If ANY of these words appear: "first class", "first", "luxury", "first only", "only first" = set "cabin_class": "FIRST"
            - If ANY of these words appear: "economy class", "economy", "coach", "economy only", "only economy" = set "cabin_class": "ECONOMY"
            - If user says "show only business class" or "business class only" = MUST set "cabin_class": "BUSINESS"
            - If user says "show only economy class" or "economy class only" = MUST set "cabin_class": "ECONOMY"
            - Default to "ECONOMY" ONLY if NO cabin class keywords are found
            - IMPORTANT: When user explicitly requests a specific class, prioritize that over default

            SPECIAL HANDLING:
            - If query has cities but NO date mentioned, omit "departure_date" from response
            - If you cannot extract origin/destination, return {"error": "missing_location"}
            - Examples of queries without dates: "find flights for Delhi to Mumbai", "flights from Chennai to Kochi"
            - ALWAYS check for cabin class keywords in the query and set cabin_class accordingly
            
            EXAMPLES:
            - "show only business class Flight Details" → {"cabin_class": "BUSINESS"}
            - "business class flights from Delhi to Mumbai" → {"cabin_class": "BUSINESS"}
            - "show only economy class flights" → {"cabin_class": "ECONOMY"}
            - "first class tickets" → {"cabin_class": "FIRST"}
            - "flights from Delhi to Mumbai" → {"cabin_class": "ECONOMY"} (default, no class mentioned)
            """

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,
                max_tokens=200
            )

            content = response.choices[0].message.content.strip()

            # Clean up response (remove markdown formatting if present)
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]

            params = json.loads(content)

            # If OpenAI couldn't extract locations, return error
            if "error" in params:
                return params

            # Always enhance date parsing with our custom parser for better accuracy
            custom_date = self.date_parser.parse_date(query)
            logger.info(f"🔍 Date validation starting: OpenAI={params.get('departure_date', 'None')}, Custom={custom_date}, Query='{query}'")

            # If OpenAI provided a date, check if it's reasonable
            if "departure_date" in params and params["departure_date"]:
                logger.info(f"🔍 OpenAI provided date: {params['departure_date']}")
                try:
                    openai_date = datetime.strptime(params["departure_date"], "%Y-%m-%d")
                    today = datetime.now()

                    # Only validate against custom date if custom parser found a date
                    if custom_date:
                        custom_date_obj = datetime.strptime(custom_date, "%Y-%m-%d")
                    else:
                        custom_date_obj = None

                    # Check for specific relative date terms and validate accordingly
                    query_lower = query.lower()
                    should_use_custom = False

                    tomorrow_variants = ['tomorrow', 'tommorow', 'tomorow', 'tommorrow', 'tomorrrow', 'tomorow', 'tomarow']
                    if any(variant in query_lower for variant in tomorrow_variants):
                        expected_date = today + timedelta(days=1)
                        # If OpenAI date is not tomorrow, use custom parser
                        if openai_date.date() != expected_date.date():
                            should_use_custom = True
                            logger.info(f"🔄 OpenAI date {params['departure_date']} incorrect for 'tomorrow', using custom parser: {custom_date}")

                    elif 'next week' in query_lower:
                        expected_date = today + timedelta(days=7)
                        # Allow some flexibility for "next week" (5-9 days)
                        if not (5 <= (openai_date - today).days <= 9):
                            should_use_custom = True
                            logger.info(f"🔄 OpenAI date {params['departure_date']} incorrect for 'next week', using custom parser: {custom_date}")

                    elif 'next month' in query_lower and custom_date_obj:
                        # Check if it's actually next month
                        if openai_date.month != custom_date_obj.month or openai_date.year != custom_date_obj.year:
                            should_use_custom = True
                            logger.info(f"🔄 OpenAI date {params['departure_date']} incorrect for 'next month', using custom parser: {custom_date}")

                    else:
                        # For other cases, check if date is in the past or too far in future
                        if openai_date < today or openai_date > today + timedelta(days=730):
                            should_use_custom = True
                            logger.info(f"🔄 OpenAI date {params['departure_date']} seems incorrect (past/too far), using custom parser: {custom_date}")

                    if should_use_custom and custom_date:
                        params["departure_date"] = custom_date

                except Exception as e:
                    logger.warning(f"Date parsing error: {e}, using custom parser")
                    if custom_date:
                        params["departure_date"] = custom_date
            else:
                logger.info(f"🔍 No OpenAI date provided, checking custom parser: {custom_date}")
                if custom_date:
                    params["departure_date"] = custom_date

            # 🔄 ENHANCED: Check if this is an incomplete query that needs context from previous search
            if user_id and db and not params.get("departure_date"):
                logger.info(f"🔍 No date found in query, checking for previous search context...")
                last_search = self.conversation_memory.get_last_flight_search(user_id, db)
                if last_search:
                    # Inherit date from previous search if current query has new route but no date
                    params["departure_date"] = last_search.get("departure_date")
                    params["is_follow_up"] = True
                    params["follow_up_type"] = "route_change_same_date"
                    params["inherited_date"] = True
                    logger.info(f"🔄 Inherited date from previous search: {params['departure_date']}")
                else:
                    # No previous search found, use default date (2 weeks from now)
                    today = datetime.now()
                    default_date = today + timedelta(days=14)
                    params["departure_date"] = default_date.strftime("%Y-%m-%d")
                    logger.info(f"🔄 No previous search found, using default date: {params['departure_date']}")

            logger.info(f"📅 Final departure date: {params['departure_date']}")

            # Add follow-up metadata if this was a follow-up query requiring fresh extraction
            if follow_up_metadata is not None:
                params.update(follow_up_metadata)
                logger.info(f"🔄 Added follow-up metadata: {follow_up_metadata}")

            return params

        except Exception as e:
            logger.error(f"OpenAI extraction error: {e}")
            return {"error": f"openai_error: {str(e)}"}
    
    def extract_cities_fallback(self, query: str) -> Dict[str, str]:
        """Fallback city extraction using regex"""
        city_patterns = {
            'delhi': 'DEL', 'mumbai': 'BOM', 'bangalore': 'BLR', 'chennai': 'MAA',
            'kolkata': 'CCU', 'hyderabad': 'HYD', 'pune': 'PNQ', 'ahmedabad': 'AMD',
            'kochi': 'COK', 'goa': 'GOI', 'jaipur': 'JAI', 'lucknow': 'LKO'
        }
        
        query_lower = query.lower()
        found_cities = []
        
        for city, code in city_patterns.items():
            if city in query_lower:
                found_cities.append(code)
        
        if len(found_cities) >= 2:
            return {"origin": found_cities[0], "destination": found_cities[1]}
        elif len(found_cities) == 1:
            return {"origin": found_cities[0], "destination": ""}
        else:
            return {"origin": "", "destination": ""}

class CurrencyConverter:
    """Simple currency converter for EUR to INR"""

    def __init__(self):
        self.eur_to_inr_rate = 89.5  # Approximate rate, can be updated

    def get_live_rate(self) -> float:
        """Get live EUR to INR exchange rate"""
        try:
            # Using a free API for exchange rates
            response = requests.get(
                "https://api.exchangerate-api.com/v4/latest/EUR",
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("rates", {}).get("INR", self.eur_to_inr_rate)
        except Exception as e:
            logger.warning(f"Could not fetch live exchange rate: {e}")

        return self.eur_to_inr_rate

    def convert_eur_to_inr(self, eur_amount: float, use_live_rate: bool = True) -> Dict[str, Any]:
        """Convert EUR to INR"""
        if use_live_rate:
            rate = self.get_live_rate()
        else:
            rate = self.eur_to_inr_rate

        inr_amount = eur_amount * rate

        return {
            "inr_amount": round(inr_amount, 2),
            "eur_amount": eur_amount,
            "exchange_rate": rate,
            "formatted_inr": f"₹{inr_amount:,.0f}",
            "formatted_eur": f"€{eur_amount:.2f}"
        }

class SimpleFlightFormatter:
    """Simple flight data formatter with currency conversion"""

    def __init__(self):
        self.currency_converter = CurrencyConverter()
    
    def _safe_extract_time(self, time_string: str) -> str:
        """Safely extract time from various formats"""
        try:
            if not time_string:
                return "N/A"
            
            # Handle ISO format: "2025-08-19T08:00:00"
            if "T" in time_string and len(time_string) >= 16:
                return time_string[11:16]  # Extract HH:MM
            
            # Handle other formats - return as is
            return time_string
        except Exception as e:
            logger.warning(f"Error extracting time from '{time_string}': {e}")
            return "N/A"
    
    def _safe_extract_date(self, date_string: str) -> str:
        """Safely extract date from various formats"""
        try:
            if not date_string:
                return "N/A"
            
            # Handle ISO format: "2025-08-19T08:00:00"
            if "T" in date_string and len(date_string) >= 10:
                return date_string[:10]  # Extract YYYY-MM-DD
            
            # Handle other formats - return as is
            return date_string
        except Exception as e:
            logger.warning(f"Error extracting date from '{date_string}': {e}")
            return "N/A"

    def format_amadeus_response(self, amadeus_data: List[Dict], requested_cabin_class: str = None) -> List[Dict[str, Any]]:
        """Format Amadeus API response to simple structure with INR conversion and cabin class filtering"""
        flights = []
        
        logger.info(f"🔍 Formatting flights with requested cabin class: {requested_cabin_class}")

        for offer in amadeus_data:
            try:
                itinerary = offer["itineraries"][0]
                segment = itinerary["segments"][0]

                # Convert price to INR
                eur_price = float(offer['price']['total'])
                currency_info = self.currency_converter.convert_eur_to_inr(eur_price)

                # Extract cabin class from travelerPricings (more reliable than segment data)
                cabin_class = "ECONOMY"  # Default
                try:
                    if "travelerPricings" in offer and len(offer["travelerPricings"]) > 0:
                        traveler_pricing = offer["travelerPricings"][0]
                        if "fareDetailsBySegment" in traveler_pricing and len(traveler_pricing["fareDetailsBySegment"]) > 0:
                            fare_details = traveler_pricing["fareDetailsBySegment"][0]
                            cabin_class = fare_details.get("cabin", "ECONOMY")
                except Exception as e:
                    logger.debug(f"Could not extract cabin class, using default: {e}")
                
                # Filter by requested cabin class if specified
                if requested_cabin_class and cabin_class != requested_cabin_class:
                    logger.debug(f"🔍 Skipping flight with cabin class {cabin_class} (requested: {requested_cabin_class})")
                    continue

                # Extract additional flight details
                aircraft = segment.get("aircraft", {}).get("code", "N/A")
                departure_terminal = segment.get("departure", {}).get("terminal", "N/A")
                arrival_terminal = segment.get("arrival", {}).get("terminal", "N/A")
                operating_carrier = segment.get("operating", {}).get("carrierCode", segment["carrierCode"])

                # Create route string
                route = f"{segment['departure']['iataCode']} → {segment['arrival']['iataCode']}"

                # Safely extract departure and arrival times
                departure_at = segment["departure"]["at"]
                arrival_at = segment["arrival"]["at"]
                
                departure_date = self._safe_extract_date(departure_at)
                departure_time = self._safe_extract_time(departure_at)
                arrival_date = self._safe_extract_date(arrival_at)
                arrival_time = self._safe_extract_time(arrival_at)
                
                flight = {
                    "flight_number": f"{segment['carrierCode']}{segment['number']}",
                    "airline": segment["carrierCode"],
                    "departure_date": departure_date,
                    "departure_time": departure_time,
                    "arrival_date": arrival_date,
                    "arrival_time": arrival_time,
                    "departure_airport": segment["departure"]["iataCode"],
                    "arrival_airport": segment["arrival"]["iataCode"],
                    "departure_terminal": departure_terminal,
                    "arrival_terminal": arrival_terminal,
                    "duration": itinerary["duration"],
                    "price": currency_info["formatted_inr"],  # Primary price in INR
                    "price_eur": currency_info["formatted_eur"],  # Original EUR price
                    "price_numeric": currency_info["inr_amount"],  # Numeric INR for sorting
                    "price_eur_numeric": eur_price,  # Original EUR numeric
                    "currency": "INR",
                    "exchange_rate": currency_info["exchange_rate"],
                    "cabin_class": cabin_class,  # Use properly extracted cabin class
                    "booking_class": cabin_class,  # Alias for frontend compatibility
                    "aircraft": aircraft,
                    "operating_carrier": operating_carrier,
                    "route": route,
                    "stops": len(itinerary["segments"]) - 1,
                    "is_direct": len(itinerary["segments"]) == 1
                }

                # Add connecting flights information if there are multiple segments
                if len(itinerary["segments"]) > 1:
                    connecting_flights = []
                    for i, seg in enumerate(itinerary["segments"]):
                        try:
                            # Safely extract departure and arrival times
                            departure_at = seg.get("departure", {}).get("at", "")
                            arrival_at = seg.get("arrival", {}).get("at", "")
                            
                            departure_time = self._safe_extract_time(departure_at)
                            arrival_time = self._safe_extract_time(arrival_at)
                            
                            connecting_flights.append({
                                "segment": i + 1,
                                "flight_number": f"{seg['carrierCode']}{seg['number']}",
                                "departure": f"{seg['departure']['iataCode']} {departure_time}",
                                "arrival": f"{seg['arrival']['iataCode']} {arrival_time}",
                                "duration": seg.get("duration", "N/A")
                            })
                        except Exception as e:
                            logger.warning(f"Error formatting connecting flight segment {i+1}: {e}")
                            # Add a fallback entry
                            connecting_flights.append({
                                "segment": i + 1,
                                "flight_number": f"{seg.get('carrierCode', 'N/A')}{seg.get('number', 'N/A')}",
                                "departure": f"{seg.get('departure', {}).get('iataCode', 'N/A')} N/A",
                                "arrival": f"{seg.get('arrival', {}).get('iataCode', 'N/A')} N/A",
                                "duration": seg.get("duration", "N/A")
                            })
                    flight["connecting_flights"] = connecting_flights

                flights.append(flight)

            except Exception as e:
                logger.error(f"Flight formatting error: {e}")
                continue

        return flights
