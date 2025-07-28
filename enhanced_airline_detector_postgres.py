#!/usr/bin/env python3

import re
import json
import psycopg2
from typing import Dict, List, Set, Optional
from datetime import datetime
import os
from psycopg2.extras import RealDictCursor

class EnhancedAirlineDetectorPostgres:
    """Enhanced airline detection that learns from Amadeus API responses and stores in PostgreSQL"""
    
    def __init__(self, db_config: Dict[str, str] = None):
        # Default PostgreSQL configuration
        self.db_config = db_config or {
            'host': 'localhost',
            'port': '5432',
            'database': 'travelagent',
            'user': 'postgres',
            'password': 'password'
        }
        self.init_database()
        
        # Common airline name variations for fuzzy matching
        self.name_variations = {
            "air india": ["airindia", "air-india", "air_india"],
            "spicejet": ["spice jet", "spice-jet", "spice_jet"],
            "indigo": ["indigo airlines", "indigo air"],
            "vistara": ["vistara airlines", "vistara air"],
            "emirates": ["emirates airlines", "emirates air"],
            "qatar": ["qatar airways", "qatar air"],
            "etihad": ["etihad airways", "etihad air"],
            "british": ["british airways", "british air"],
            "lufthansa": ["lufthansa airlines", "lufthansa air"],
            "singapore": ["singapore airlines", "singapore air"],
            "thai": ["thai airways", "thai air"],
            "malaysia": ["malaysia airlines", "malaysia air"],
            "cathay": ["cathay pacific", "cathay air"],
            "japan": ["japan airlines", "japan air"],
            "ana": ["all nippon airways", "all nippon air"],
            "united": ["united airlines", "united air"],
            "american": ["american airlines", "american air"],
            "delta": ["delta air lines", "delta air"],
            "southwest": ["southwest airlines", "southwest air"],
            "jetblue": ["jetblue airways", "jetblue air"],
            "alaska": ["alaska airlines", "alaska air"],
            "spirit": ["spirit airlines", "spirit air"],
            "frontier": ["frontier airlines", "frontier air"],
            "allegiant": ["allegiant air", "allegiant airlines"],
            "westjet": ["westjet airlines", "westjet air"],
            "air canada": ["aircanada", "air-canada"],
            "qantas": ["qantas airways", "qantas air"],
            "virgin australia": ["virgin australia airlines", "virgin australia air"],
            "virgin atlantic": ["virgin atlantic airways", "virgin atlantic air"],
            "turkish": ["turkish airlines", "turkish air"],
            "egyptair": ["egypt air", "egypt-air"],
            "royal jordanian": ["royal jordanian airlines", "royal jordanian air"],
            "saudi arabian": ["saudi arabian airlines", "saudi arabian air"],
            "kuwait": ["kuwait airways", "kuwait air"],
            "oman air": ["omanair", "oman-air"],
            "gulf air": ["gulfair", "gulf-air"],
            "bahrain air": ["bahrainair", "bahrain-air"],
            "flydubai": ["fly dubai", "fly-dubai"],
            "air arabia": ["airarabia", "air-arabia"],
            "flynas": ["fly nas", "fly-nas"],
            "jazeera": ["jazeera airways", "jazeera air"],
            "pegasus": ["pegasus airlines", "pegasus air"],
            "aeroflot": ["aeroflot airlines", "aeroflot air"],
            "s7": ["s7 airlines", "s7 air"],
            "ural": ["ural airlines", "ural air"],
            "red wings": ["red wings airlines", "red wings air"],
            "utair": ["utair airlines", "utair air"],
            "nordwind": ["nordwind airlines", "nordwind air"],
            "azur": ["azur air", "azur airlines"],
            "air china": ["airchina", "air-china"],
            "china southern": ["china southern airlines", "china southern air"],
            "china eastern": ["china eastern airlines", "china eastern air"],
            "hainan": ["hainan airlines", "hainan air"],
            "xiamen": ["xiamen airlines", "xiamen air"],
            "shenzhen": ["shenzhen airlines", "shenzhen air"],
            "sichuan": ["sichuan airlines", "sichuan air"],
            "shanghai": ["shanghai airlines", "shanghai air"],
            "korean": ["korean air", "korean airlines"],
            "asiana": ["asiana airlines", "asiana air"],
            "jin air": ["jinair", "jin-air"],
            "air busan": ["airbusan", "air-busan"],
            "tway": ["t'way air", "t'way airlines"],
            "jeju": ["jeju air", "jeju airlines"],
            "eastar": ["eastar jet", "eastar airlines"],
            "air seoul": ["airseoul", "air-seoul"],
            "fly gangwon": ["flygangwon", "fly-gangwon"],
            "air premia": ["airpremia", "air-premia"],
            "air incheon": ["airincheon", "air-incheon"],
            "aero k": ["aerok", "aero-k"],
            "air max": ["airmax", "air-max"],
            "air jeju": ["airjeju", "air-jeju"],
            "air gangwon": ["airgangwon", "air-gangwon"],
        }
    
    def get_connection(self):
        """Get PostgreSQL connection"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            return None
    
    def init_database(self):
        """Initialize the database with airlines table"""
        conn = self.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        try:
            # Create airlines table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS airlines (
                    id SERIAL PRIMARY KEY,
                    airline_code VARCHAR(10) UNIQUE NOT NULL,
                    airline_name VARCHAR(255) NOT NULL,
                    aliases JSONB,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 1
                )
            ''')
            
            # Create airline_queries table to track what users search for
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS airline_queries (
                    id SERIAL PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    detected_airline_code VARCHAR(10),
                    detected_airline_name VARCHAR(255),
                    success BOOLEAN DEFAULT FALSE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_airlines_code ON airlines(airline_code)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_airlines_name ON airlines(airline_name)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_queries_timestamp ON airline_queries(timestamp)
            ''')
            
            conn.commit()
            print("✅ PostgreSQL database initialized successfully")
            
        except Exception as e:
            print(f"❌ Database initialization error: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def learn_from_amadeus_response(self, amadeus_flights: List[Dict]) -> None:
        """Learn airlines from actual Amadeus API response"""
        conn = self.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        try:
            for flight in amadeus_flights:
                # Extract airline info from Amadeus response
                airline_code = flight.get("validatingAirlineCodes", [None])[0] if flight.get("validatingAirlineCodes") else None
                airline_name = None
                
                # Try to get airline name from segments
                segments = flight.get("itineraries", [{}])[0].get("segments", [])
                for segment in segments:
                    carrier = segment.get("carrierCode", "")
                    if carrier == airline_code:
                        # Try to get airline name from operating carrier
                        operating_carrier = segment.get("operating", {})
                        if operating_carrier:
                            airline_name = operating_carrier.get("carrierCode", "")
                        break
                
                if airline_code and airline_name:
                    # Check if airline already exists
                    cursor.execute(
                        "SELECT airline_name, aliases, usage_count FROM airlines WHERE airline_code = %s", 
                        (airline_code,)
                    )
                    existing = cursor.fetchone()
                    
                    if existing:
                        # Update existing airline
                        existing_name, existing_aliases, usage_count = existing
                        aliases = existing_aliases if existing_aliases else []
                        
                        # Add new name if different
                        if airline_name.lower() not in [alias.lower() for alias in aliases]:
                            aliases.append(airline_name)
                        
                        cursor.execute('''
                            UPDATE airlines 
                            SET airline_name = %s, aliases = %s, last_seen = CURRENT_TIMESTAMP, usage_count = usage_count + 1
                            WHERE airline_code = %s
                        ''', (airline_name, json.dumps(aliases), airline_code))
                    else:
                        # Insert new airline
                        aliases = [airline_name]
                        cursor.execute('''
                            INSERT INTO airlines (airline_code, airline_name, aliases)
                            VALUES (%s, %s, %s)
                        ''', (airline_code, airline_name, json.dumps(aliases)))
            
            conn.commit()
            print(f"✅ Learned {len(amadeus_flights)} flights from Amadeus response")
            
        except Exception as e:
            print(f"❌ Learning error: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def get_known_airlines(self) -> Dict[str, str]:
        """Get all known airlines from database"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT airline_code, airline_name FROM airlines ORDER BY usage_count DESC")
            airlines = dict(cursor.fetchall())
            return airlines
        except Exception as e:
            print(f"❌ Error getting airlines: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()
    
    def get_airline_aliases(self) -> Dict[str, List[str]]:
        """Get all airline aliases from database"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT airline_code, airline_name, aliases FROM airlines")
            aliases = {}
            
            for row in cursor.fetchall():
                airline_code, airline_name, aliases_json = row
                if aliases_json:
                    try:
                        aliases_list = json.loads(aliases_json) if isinstance(aliases_json, str) else aliases_json
                    except (json.JSONDecodeError, TypeError):
                        aliases_list = [airline_name]
                else:
                    aliases_list = [airline_name]
                aliases[airline_name] = aliases_list
            
            return aliases
        except Exception as e:
            print(f"❌ Error getting aliases: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()
    
    def detect_airlines(self, query: str) -> dict:
        """Detect airlines from natural language query using database"""
        query_lower = query.lower()
        detected_airlines = []
        
        # Check if this is a filter query
        filter_keywords = ["only", "show only", "just", "merely", "simply", "exclusively", "flights", "flight"]
        has_filter_keywords = any(keyword in query_lower for keyword in filter_keywords)
        
        if not has_filter_keywords:
            return {}
        
        # Get airlines from database
        known_airlines = self.get_known_airlines()
        airline_aliases = self.get_airline_aliases()
        
        # Check for airline codes (2-3 letter codes like WY, EK, AI)
        airline_codes = re.findall(r'\b[A-Z]{2,3}\b', query.upper())
        for code in airline_codes:
            if code in known_airlines:
                detected_airlines.append(known_airlines[code])
        
        # Check for airline names and aliases
        for airline_name, aliases in airline_aliases.items():
            for alias in aliases:
                if alias.lower() in query_lower:
                    detected_airlines.append(airline_name)
                    break
        
        # Handle airlines not in database (fuzzy matching)
        if not detected_airlines:
            detected_airlines = self._fuzzy_match_airlines(query_lower)
        
        # Log the query for learning
        self._log_query(query, detected_airlines)
        
        # Remove duplicates and return
        if detected_airlines:
            unique_airlines = list(set(detected_airlines))
            return {
                "filters": {
                    "specific_airlines": unique_airlines,
                    "direct_only": False,
                    "max_price": None,
                    "preferred_times": [],
                    "exclude_airlines": [],
                    "max_stops": None,
                    "preferred_airlines": []
                }
            }
        
        return {}
    
    def _fuzzy_match_airlines(self, query_lower: str) -> List[str]:
        """Fuzzy match airlines not in database"""
        detected = []
        
        # Check for common airline name patterns
        for base_name, variations in self.name_variations.items():
            if base_name in query_lower:
                # Try to find a matching airline in database
                known_airlines = self.get_known_airlines()
                for code, name in known_airlines.items():
                    if base_name in name.lower():
                        detected.append(name)
                        break
        
        return detected
    
    def _log_query(self, query: str, detected_airlines: List[str]):
        """Log query for learning purposes"""
        conn = self.get_connection()
        if not conn:
            return
        
        cursor = conn.cursor()
        
        try:
            detected_code = None
            detected_name = None
            success = len(detected_airlines) > 0
            
            if detected_airlines:
                detected_name = detected_airlines[0]
                # Find the airline code for the detected name
                known_airlines = self.get_known_airlines()
                for code, name in known_airlines.items():
                    if name == detected_name:
                        detected_code = code
                        break
            
            cursor.execute('''
                INSERT INTO airline_queries (query_text, detected_airline_code, detected_airline_name, success)
                VALUES (%s, %s, %s, %s)
            ''', (query, detected_code, detected_name, success))
            
            conn.commit()
        except Exception as e:
            print(f"❌ Error logging query: {e}")
            conn.rollback()
        finally:
            cursor.close()
            conn.close()
    
    def get_query_stats(self) -> Dict:
        """Get statistics about airline queries"""
        conn = self.get_connection()
        if not conn:
            return {}
        
        cursor = conn.cursor()
        
        try:
            # Total queries
            cursor.execute("SELECT COUNT(*) FROM airline_queries")
            total_queries = cursor.fetchone()[0]
            
            # Successful queries
            cursor.execute("SELECT COUNT(*) FROM airline_queries WHERE success = TRUE")
            successful_queries = cursor.fetchone()[0]
            
            # Most common queries
            cursor.execute('''
                SELECT query_text, COUNT(*) as count 
                FROM airline_queries 
                GROUP BY query_text 
                ORDER BY count DESC 
                LIMIT 10
            ''')
            common_queries = cursor.fetchall()
            
            # Most used airlines
            cursor.execute('''
                SELECT airline_name, usage_count 
                FROM airlines 
                ORDER BY usage_count DESC 
                LIMIT 10
            ''')
            popular_airlines = cursor.fetchall()
            
            return {
                "total_queries": total_queries,
                "successful_queries": successful_queries,
                "success_rate": (successful_queries / total_queries * 100) if total_queries > 0 else 0,
                "common_queries": common_queries,
                "popular_airlines": popular_airlines
            }
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {}
        finally:
            cursor.close()
            conn.close()
    
    def test_detection(self, sample_flights: List[Dict] = None):
        """Test airline detection with sample data"""
        if sample_flights:
            self.learn_from_amadeus_response(sample_flights)
        
        test_queries = [
            "shows only SpiceJet flights",
            "show only Air India flights",
            "WY flights only",
            "only Emirates",
            "just IndiGo flights",
            "AI flights",
            "EK only",
            "show me Qatar Airways flights",
            "unknown airline flights",  # Test unknown airline
            "xyz flights only"  # Test non-existent airline
        ]
        
        print("=== Testing Enhanced Airline Detection (PostgreSQL) ===")
        print(f"Known airlines: {len(self.get_known_airlines())}")
        
        for query in test_queries:
            result = self.detect_airlines(query)
            if result:
                airlines = result["filters"]["specific_airlines"]
                print(f"✅ '{query}' -> {airlines}")
            else:
                print(f"❌ '{query}' -> No airlines detected")

if __name__ == "__main__":
    # Example usage with PostgreSQL
    db_config = {
        'host': 'localhost',
        'port': '5432',
        'database': 'travelagent',
        'user': 'postgres',
        'password': 'password'
    }
    
    detector = EnhancedAirlineDetectorPostgres(db_config)
    
    # Sample Amadeus-style flight data
    sample_flights = [
        {
            "validatingAirlineCodes": ["AI"],
            "itineraries": [{
                "segments": [{
                    "carrierCode": "AI",
                    "operating": {"carrierCode": "Air India"}
                }]
            }]
        },
        {
            "validatingAirlineCodes": ["SG"],
            "itineraries": [{
                "segments": [{
                    "carrierCode": "SG",
                    "operating": {"carrierCode": "SpiceJet"}
                }]
            }]
        },
        {
            "validatingAirlineCodes": ["WY"],
            "itineraries": [{
                "segments": [{
                    "carrierCode": "WY",
                    "operating": {"carrierCode": "Oman Air"}
                }]
            }]
        }
    ]
    
    detector.test_detection(sample_flights)
    
    # Show statistics
    stats = detector.get_query_stats()
    print(f"\n=== Statistics ===")
    print(f"Total queries: {stats.get('total_queries', 0)}")
    print(f"Success rate: {stats.get('success_rate', 0):.1f}%") 