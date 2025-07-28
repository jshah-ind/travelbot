#!/usr/bin/env python3

import json
import logging
import asyncio
from typing import Dict, Any, Optional
import requests
from dotenv import load_dotenv
import os

load_dotenv()

class GeminiAIHandler:
    """Handles follow-up queries using Google Gemini API for filter extraction"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize Gemini
        gemini_api_key = os.getenv('GEMINI_API_KEY')
        if gemini_api_key:
            self.gemini_api_key = gemini_api_key
            self.gemini_available = True
            self.logger.info("✅ Gemini API client initialized")
        else:
            self.gemini_available = False
            self.logger.warning("⚠️ Gemini API key not found")
    
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
    
    def get_ai_status(self) -> Dict[str, bool]:
        """Get status of AI services"""
        return {
            "gemini_available": self.gemini_available,
            "any_ai_available": self.gemini_available
        }

# Test the Gemini AI handler
async def test_gemini_ai():
    """Test the Gemini AI handler"""
    handler = GeminiAIHandler()
    
    print("🤖 Gemini AI Handler Test")
    print("=" * 40)
    
    # Check AI availability
    status = handler.get_ai_status()
    print(f"Gemini Available: {status['gemini_available']}")
    print(f"Any AI Available: {status['any_ai_available']}")
    
    if not status['any_ai_available']:
        print("❌ No AI services available. Please set GEMINI_API_KEY")
        return
    
    # Test queries
    test_queries = [
        "show only spicejet flights",
        "air india flights only",
        "qatar airways flights",
        "emirates flights only",
        "direct flights only",
        "business class flights"
    ]
    
    print("\n🧪 Testing Gemini AI Filter Extraction:")
    print("-" * 45)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        result = await handler.extract_filters_gemini(query)
        
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
    
    env_vars = ['GEMINI_API_KEY']
    
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
    asyncio.run(test_gemini_ai()) 