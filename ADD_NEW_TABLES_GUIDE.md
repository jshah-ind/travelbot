# Adding New Tables to Dev Database

## 🎯 Overview

This guide helps you add the new tables and data needed for airline detection and conversation memory to your existing dev database without affecting your current setup.

## 📋 What Will Be Added

### New Tables:
1. **`airlines`** - Stores airline codes, names, and aliases for detection
2. **`airline_queries`** - Tracks user queries for airline detection analytics
3. **`conversation_context`** - Stores conversation context for follow-up queries

### Sample Data:
- **60+ Airlines** with codes, names, and aliases
- **Common variations** like "airindia", "air-india", "air_india" for "Air India"

## 🚀 Quick Setup

### Step 1: Update Environment Variables
Make sure your `.env` file has the correct database credentials:

```bash
DB_HOST=your_dev_server_host
DB_PORT=5432
DB_NAME=travelagent
DB_USER=your_username
DB_PASSWORD=your_password
```

### Step 2: Run the Add Tables Script
```bash
cd travelbot
python3 add_new_tables.py
```

### Step 3: Verify Setup
The script will automatically:
- ✅ Check if tables already exist (skips if they do)
- ✅ Create missing tables
- ✅ Insert sample airline data (only if table is empty)
- ✅ Verify all tables exist

## 📊 What the Script Does

### 1. **Smart Table Creation**
- Checks if tables already exist
- Only creates missing tables
- Won't affect existing data

### 2. **Sample Airlines Data**
Includes 60+ airlines with aliases:
```sql
-- Examples of what gets inserted:
('AI', 'Air India', ['airindia', 'air-india', 'air_india'])
('6E', 'IndiGo', ['indigo airlines', 'indigo air'])
('SG', 'SpiceJet', ['spice jet', 'spice-jet', 'spice_jet'])
('EM', 'Emirates', ['emirates airlines', 'emirates air'])
('QR', 'Qatar Airways', ['qatar airways', 'qatar air'])
```

### 3. **Performance Indexes**
Creates indexes for fast queries:
- `idx_airlines_code` on airline_code
- `idx_airlines_name` on airline_name
- `idx_queries_timestamp` on timestamp
- `idx_conversation_user_id` on user_id

## 🔍 Verification

After running the script, you should see:
```
✅ Airlines table created successfully
✅ Airline queries table created successfully
✅ Conversation context table created successfully
✅ Inserted 60 sample airlines
✅ Table 'airlines' exists
✅ Table 'airline_queries' exists
✅ Table 'conversation_context' exists
```

## 🧪 Testing the Setup

### Test 1: Check Tables Exist
```sql
-- Connect to your database and run:
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name IN ('airlines', 'airline_queries', 'conversation_context');
```

### Test 2: Check Sample Data
```sql
-- Check airlines data:
SELECT airline_code, airline_name FROM airlines LIMIT 10;

-- Check aliases:
SELECT airline_code, aliases FROM airlines WHERE airline_code = 'AI';
```

### Test 3: Test Airline Detection
```python
# In your Python environment:
from enhanced_airline_detector_postgres import EnhancedAirlineDetectorPostgres

detector = EnhancedAirlineDetectorPostgres()
result = detector.detect_airlines("air india flights only")
print(result)
```

## 🔧 Troubleshooting

### Issue: Connection Failed
```
❌ Database connection failed: connection to server at "localhost" (127.0.0.1), port 5432 failed
```
**Solution**: Check your `.env` file and ensure PostgreSQL is running

### Issue: Permission Denied
```
❌ Failed to create airlines table: permission denied for database travelagent
```
**Solution**: Ensure your database user has CREATE permissions

### Issue: Table Already Exists
```
✅ Airlines table already exists, skipping...
```
**This is normal!** The script is designed to skip existing tables.

### Issue: JSONB Not Supported
```
❌ Failed to create airlines table: type "jsonb" does not exist
```
**Solution**: Ensure PostgreSQL version 9.4+ is installed

## 📈 Benefits After Setup

### 1. **Enhanced Airline Detection**
- Automatic learning from Amadeus API responses
- Fuzzy matching for airline names
- Support for aliases and variations

### 2. **Follow-up Query Support**
- Stores conversation context
- Enables "show only business class" type queries
- Automatic context expiration

### 3. **Analytics and Tracking**
- Track which airlines users search for
- Monitor query success rates
- Performance optimization data

## 🔄 Next Steps

After successful setup:

1. **Restart your application** to load the new tables
2. **Test airline filtering**: Try "air india flights only"
3. **Test follow-up queries**: Search for flights, then "show only business class"
4. **Monitor logs** to see airline detection in action

## 📝 Manual SQL (Alternative)

If you prefer to run SQL manually:

```sql
-- Create airlines table
CREATE TABLE IF NOT EXISTS airlines (
    id SERIAL PRIMARY KEY,
    airline_code VARCHAR(10) UNIQUE NOT NULL,
    airline_name VARCHAR(255) NOT NULL,
    aliases JSONB,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    usage_count INTEGER DEFAULT 1
);

-- Create indexes
CREATE INDEX idx_airlines_code ON airlines(airline_code);
CREATE INDEX idx_airlines_name ON airlines(airline_name);

-- Insert sample data (run the Python script for full data)
INSERT INTO airlines (airline_code, airline_name, aliases) 
VALUES ('AI', 'Air India', '["airindia", "air-india", "air_india"]');
```

The automated script is recommended as it handles all the complexity and provides detailed logging. 