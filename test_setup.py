#!/usr/bin/env python3
"""
Simple Travel Agent Setup Test
Verifies that all components are working correctly
"""

import os
import sys
from datetime import datetime

def test_imports():
    """Test all required imports"""
    print("🔍 Testing imports...")
    
    try:
        import fastapi
        print("  ✅ FastAPI")
        
        import openai
        print("  ✅ OpenAI")
        
        import amadeus
        print("  ✅ Amadeus")
        
        import sqlalchemy
        print("  ✅ SQLAlchemy")
        
        import jose
        print("  ✅ Python-JOSE")
        
        import passlib
        print("  ✅ Passlib")
        
        # Test local imports
        import simple_utils
        print("  ✅ Simple Utils")
        
        import auth_models
        print("  ✅ Auth Models")
        
        import database
        print("  ✅ Database")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False

def test_environment():
    """Test environment variables"""
    print("\n🔍 Testing environment variables...")
    
    required_vars = [
        "OPENAI_API_KEY",
        "AMADEUS_API_KEY", 
        "AMADEUS_API_SECRET"
    ]
    
    all_good = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {'*' * 10}...{value[-4:]}")
        else:
            print(f"  ❌ {var}: Not set")
            all_good = False
    
    return all_good

def test_database_connection():
    """Test database connection"""
    print("\n🔍 Testing database connection...")
    
    try:
        from database import get_db, engine
        from sqlalchemy import text
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("  ✅ Database connection successful")
            return True
            
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        print("  💡 Make sure PostgreSQL is running and database 'travelagent' exists")
        return False

def test_api_keys():
    """Test API key validity (basic check)"""
    print("\n🔍 Testing API keys...")
    
    # Test OpenAI key format
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key.startswith("sk-"):
        print("  ✅ OpenAI API key format looks correct")
    else:
        print("  ❌ OpenAI API key format incorrect")
        return False
    
    # Test Amadeus keys
    amadeus_key = os.getenv("AMADEUS_API_KEY")
    amadeus_secret = os.getenv("AMADEUS_API_SECRET")
    
    if amadeus_key and len(amadeus_key) > 10:
        print("  ✅ Amadeus API key looks correct")
    else:
        print("  ❌ Amadeus API key missing or too short")
        return False
        
    if amadeus_secret and len(amadeus_secret) > 10:
        print("  ✅ Amadeus API secret looks correct")
    else:
        print("  ❌ Amadeus API secret missing or too short")
        return False
    
    return True

def main():
    """Run all tests"""
    print("🚀 Simple Travel Agent Setup Test")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Environment Variables", test_environment),
        ("Database Connection", test_database_connection),
        ("API Keys", test_api_keys)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  ❌ {test_name} test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary:")
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status} {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All tests passed! Your Simple Travel Agent is ready to run.")
        print("\n🚀 To start the application:")
        print("   python simple_main.py")
        print("\n📚 API Documentation will be available at:")
        print("   http://localhost:8000/docs")
    else:
        print("❌ Some tests failed. Please fix the issues above before running the application.")
        print("\n💡 Common fixes:")
        print("   - Install missing packages: pip install -r requirements.txt")
        print("   - Set up .env file with your API keys")
        print("   - Start PostgreSQL and create 'travelagent' database")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
