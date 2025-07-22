#!/usr/bin/env python3
"""
Test script to verify frontend integration is working
"""

import requests
import json
import time

def test_frontend_integration():
    """Test that frontend and backend are properly integrated"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Simple Travel Agent Frontend Integration")
    print("=" * 60)
    
    # Test 1: Frontend serving
    print("1. Testing frontend serving...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200 and "Simple Travel Agent" in response.text:
            print("   ✅ Frontend is being served correctly")
        else:
            print("   ❌ Frontend serving failed")
            return False
    except Exception as e:
        print(f"   ❌ Frontend test failed: {e}")
        return False
    
    # Test 2: API health check
    print("2. Testing API health...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            health_data = response.json()
            print(f"   ✅ API is healthy: {health_data['status']}")
        else:
            print("   ❌ API health check failed")
            return False
    except Exception as e:
        print(f"   ❌ API health test failed: {e}")
        return False
    
    # Test 3: Flight search (guest mode)
    print("3. Testing flight search (guest mode)...")
    try:
        search_data = {
            "query": "flights from Delhi to Mumbai tomorrow"
        }
        response = requests.post(
            f"{base_url}/search",
            json=search_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            result = response.json()
            if result["status"] == "success" and len(result["flights"]) > 0:
                print(f"   ✅ Flight search successful: {len(result['flights'])} flights found")
                print(f"   💰 Sample price: {result['flights'][0]['price']}")
            else:
                print(f"   ❌ Flight search failed: {result.get('message', 'Unknown error')}")
                return False
        else:
            print(f"   ❌ Flight search request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Flight search test failed: {e}")
        return False
    
    # Test 4: Authentication endpoints
    print("4. Testing authentication endpoints...")
    try:
        # Test signup endpoint (should work even if user exists)
        signup_data = {
            "email": "test@example.com",
            "username": "testuser",
            "password": "testpassword123",
            "full_name": "Test User"
        }
        response = requests.post(
            f"{base_url}/auth/signup",
            json=signup_data,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 400]:  # 400 is OK if user already exists
            print("   ✅ Signup endpoint is working")
        else:
            print(f"   ❌ Signup endpoint failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"   ❌ Authentication test failed: {e}")
        return False
    
    # Test 5: Static files
    print("5. Testing static file serving...")
    try:
        response = requests.get(f"{base_url}/static/app.js")
        if response.status_code == 200 and "searchFlights" in response.text:
            print("   ✅ Static JavaScript file is being served")
        else:
            print("   ❌ Static file serving failed")
            return False
    except Exception as e:
        print(f"   ❌ Static file test failed: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 All frontend integration tests passed!")
    print("\n📱 Frontend is ready at: http://localhost:8000")
    print("🔧 API docs available at: http://localhost:8000/docs")
    print("\n🧪 Test Features:")
    print("   • Sign up/Sign in for full conversation memory")
    print("   • Search: 'Find flights from Delhi to Mumbai tomorrow'")
    print("   • Follow-up: 'Show me business class only'")
    print("   • Route change: 'Find flights for Delhi to Kochi'")
    
    return True

if __name__ == "__main__":
    success = test_frontend_integration()
    exit(0 if success else 1)
