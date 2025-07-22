#!/usr/bin/env python3
"""
Quick test to verify the application is working correctly
"""

import requests
import json

def quick_test():
    """Quick test of the application"""
    
    print("🧪 Quick Test - Simple Travel Agent")
    print("=" * 40)
    
    # Test search
    try:
        response = requests.post(
            "http://localhost:8000/search",
            json={"query": "flights from Bangalore to Goa next week"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Search Status: {data['status']}")
            print(f"✅ Message: {data['message']}")
            print(f"✅ Flights Found: {len(data['flights'])}")
            if data['flights']:
                print(f"✅ Sample Price: {data['flights'][0]['price']}")
        else:
            print(f"❌ Search failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
    
    print("\n🌐 Frontend URL: http://localhost:8000")
    print("🔧 API Docs: http://localhost:8000/docs")

if __name__ == "__main__":
    quick_test()
