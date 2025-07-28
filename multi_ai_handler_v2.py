#!/usr/bin/env python3

import json
import logging
import asyncio
from typing import Dict, Any, Optional
import openai
import requests
from dotenv import load_dotenv
import os

load_dotenv()

class MultiAIHandlerV2:
    """Handles follow-up queries using both OpenAI and Gemini for better reliability"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize OpenAI
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if openai_api_key:
            self.openai_client = openai.OpenAI(api_key=openai_api_key)
            self.openai_available = True
            self.logger.info("✅ OpenAI client initialized")
        else:
            self.openai_available = False
            self.logger.warning("⚠️ OpenAI API key not found")
        
        # Initialize Gemini
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            self.gemini_api_key = gemini_api_key
            self.gemini_available = True
            self.logger.info("✅ Gemini API client initialized")
        else:
            self.gemini_available = False
            self.logger.warning("⚠️ Gemini API key not found")
    
    async def extract_filters_openai(self, query: str) -> Dict[str, Any]:
        """Extract filters using OpenAI"""
        if not self.openai_available:
            return {}
        
        try:
            system_prompt = """
            You are a flight filter extraction assistant. Extract ONLY filters from the user query.
            
            Return ONLY valid JSON with these fields:
            {
                "filters": {
                    "direct_only": false,
                    "specific_airlines": [],
                    "max_price": null,
                    "preferred_times": [],
                    "exclude_airlines": [],
                    "max_stops": null,
                    "preferred_airlines": []
                },
                "cabin_class": "ECONOMY"
            }
            
            FILTER DETECTION:
            - "spicejet flights only", "only spicejet", "spice jet flights" = specific_airlines: ["SpiceJet"]
            - "air india flights only", "only air india", "airindia flights" = specific_airlines: ["Air India"]
            - "qatar airways flights", "qatar flights only" = specific_airlines: ["Qatar Airways"]
            - "emirates flights only", "only emirates" = specific_airlines: ["Emirates"]
            - "indigo flights only", "only indigo" = specific_airlines: ["IndiGo"]
            - "vistara flights", "only vistara" = specific_airlines: ["Vistara"]
            - "direct flights only", "direct only", "non-stop only" = direct_only: true
            - "under 5000", "less than 5000" = max_price: 5000
            - "morning flights", "early morning" = preferred_times: ["morning"]
            - "evening flights", "night flights" = preferred_times: ["evening"]
            - "no air india", "exclude air india" = exclude_airlines: ["Air India"]
            - "maximum 1 stop", "max 1 stop" = max_stops: 1
            - "prefer air india", "preferably air india" = preferred_airlines: ["Air India"]
            
            CABIN CLASS DETECTION:
            - "business class", "business" = cabin_class: "BUSINESS"
            - "economy class", "economy" = cabin_class: "ECONOMY"
            - "first class", "first" = cabin_class: "FIRST"
            
            Return ONLY the JSON, no other text.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
                temperature=0.1,
                max_tokens=200
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean up response
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            result = json.loads(content)
            self.logger.info(f"✅ OpenAI extracted filters: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ OpenAI filter extraction error: {e}")
            return {}
    
    async def extract_filters_gemini(self, query: str) -> Dict[str, Any]:
        """Extract filters using Gemini API"""
        if not self.gemini_available:
            return {}
        
        try:
            prompt = f"""
            Extract flight filters from this query: "{query}"
            
            Return ONLY valid JSON with this exact format:
            {{
                "filters": {{
                    "direct_only": false,
                    "specific_airlines": [],
                    "max_price": null,
                    "preferred_times": [],
                    "exclude_airlines": [],
                    "max_stops": null,
                    "preferred_airlines": []
                }},
                "cabin_class": "ECONOMY"
            }}
            
            Examples:
            - "spicejet flights only" → specific_airlines: ["SpiceJet"]
            - "air india flights only" → specific_airlines: ["Air India"]
            - "qatar airways flights" → specific_airlines: ["Qatar Airways"]
            - "emirates flights only" → specific_airlines: ["Emirates"]
            - "direct flights only" → direct_only: true
            - "business class" → cabin_class: "BUSINESS"
            
            Return ONLY the JSON, no other text.
            """
            
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
            
            payload = {
                "contents": [
                    {
                        "parts": [
                            {
                                "text": prompt
                            }
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 200
                }
            }
            
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            
            result = response.json()
            content = result["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            # Clean up response
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            result = json.loads(content)
            self.logger.info(f"✅ Gemini extracted filters: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Gemini filter extraction error: {e}")
            return {}
    
    async def extract_filters_multi_ai(self, query: str) -> Dict[str, Any]:
        """Extract filters using both OpenAI and Gemini, return the best result"""
        
        self.logger.info(f"🔍 Multi-AI filter extraction for: '{query}'")
        
        # Try both AI services
        openai_result = await self.extract_filters_openai(query)
        gemini_result = await self.extract_filters_gemini(query)
        
        # Compare results and return the best one
        if openai_result and gemini_result:
            # Both succeeded, compare quality
            openai_airlines = openai_result.get("filters", {}).get("specific_airlines", [])
            gemini_airlines = gemini_result.get("filters", {}).get("specific_airlines", [])
            
            if len(openai_airlines) > len(gemini_airlines):
                self.logger.info("✅ Using OpenAI result (more airlines detected)")
                return openai_result
            elif len(gemini_airlines) > len(openai_airlines):
                self.logger.info("✅ Using Gemini result (more airlines detected)")
                return gemini_result
            else:
                # Same number of airlines, use OpenAI as default
                self.logger.info("✅ Using OpenAI result (default)")
                return openai_result
                
        elif openai_result:
            self.logger.info("✅ Using OpenAI result (only OpenAI succeeded)")
            return openai_result
            
        elif gemini_result:
            self.logger.info("✅ Using Gemini result (only Gemini succeeded)")
            return gemini_result
            
        else:
            self.logger.warning("❌ Both AI services failed")
            return {}
    
    def get_ai_status(self) -> Dict[str, bool]:
        """Get status of AI services"""
        return {
            "openai_available": self.openai_available,
            "gemini_available": self.gemini_available,
            "any_ai_available": self.openai_available or self.gemini_available
        }

# Test the multi-AI handler
async def test_multi_ai_v2():
    """Test the multi-AI handler"""
    handler = MultiAIHandlerV2()
    
    print("🤖 Multi-AI Handler V2 Test")
    print("=" * 40)
    
    # Check AI availability
    status = handler.get_ai_status()
    print(f"OpenAI Available: {status['openai_available']}")
    print(f"Gemini Available: {status['gemini_available']}")
    print(f"Any AI Available: {status['any_ai_available']}")
    
    if not status['any_ai_available']:
        print("❌ No AI services available. Please set OPENAI_API_KEY or GEMINI_API_KEY")
        return
    
    # Test queries
    test_queries = [
        "show only spicejet flights",
        "air india flights only",
        "qatar airways flights",
        "emirates flights only",
        "direct flights only",
        "business class flights",
        "show only Qatar Airways"
    ]
    
    print("\n🧪 Testing Multi-AI Filter Extraction:")
    print("-" * 45)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        result = await handler.extract_filters_multi_ai(query)
        
        if result:
            filters = result.get("filters", {})
            airlines = filters.get("specific_airlines", [])
            direct_only = filters.get("direct_only", False)
            cabin_class = result.get("cabin_class", "ECONOMY")
            
            print(f"  Airlines: {airlines}")
            print(f"  Direct Only: {direct_only}")
            print(f"  Cabin Class: {cabin_class}")
        else:
            print("  ❌ No filters extracted")

def test_environment_variables():
    """Test if environment variables are properly set"""
    
    print("\n🔧 Environment Variables Check:")
    print("-" * 30)
    
    env_vars = ['OPENAI_API_KEY', 'GEMINI_API_KEY']
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Show first few characters for security
            masked_value = value[:8] + "..." if len(value) > 8 else value
            print(f"✅ {var}: {masked_value}")
        else:
            print(f"⚠️  {var}: Not set")

if __name__ == "__main__":
    test_environment_variables()
    asyncio.run(test_multi_ai_v2()) 