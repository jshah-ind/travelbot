#!/usr/bin/env python3
"""
Add New Tables Script for Travel Agent
Adds only the new tables and data for airline detection without affecting existing database
"""

import os
import sys
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# DATABASE_URL ="postgresql://postgres:abc123!@104.225.217.245:5432/travelagent"


class AddNewTables:
    def __init__(self):
        # Database configuration from environment variables
        self.db_config = {
            'host':os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database':  os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD')
        }
        print(self.db_config)
        
    def get_connection(self):
        """Get PostgreSQL connection"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return None
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if a table already exists"""
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (table_name,))
            
            exists = cursor.fetchone()[0]
            return exists
            
        except Exception as e:
            logger.error(f"❌ Failed to check table {table_name}: {e}")
            return False
        finally:
            cursor.close()
            conn.close()
    
    def add_airlines_table(self):
        """Add airlines table if it doesn't exist"""
        if self.check_table_exists('airlines'):
            logger.info("✅ Airlines table already exists, skipping...")
            return True
        
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        try:
            # Create airlines table
            cursor.execute('''
                CREATE TABLE airlines (
                    id SERIAL PRIMARY KEY,
                    airline_code VARCHAR(10) UNIQUE NOT NULL,
                    airline_name VARCHAR(255) NOT NULL,
                    aliases JSONB,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    usage_count INTEGER DEFAULT 1
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('''
                CREATE INDEX idx_airlines_code ON airlines(airline_code)
            ''')
            cursor.execute('''
                CREATE INDEX idx_airlines_name ON airlines(airline_name)
            ''')
            
            conn.commit()
            logger.info("✅ Airlines table created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create airlines table: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def add_airline_queries_table(self):
        """Add airline_queries table if it doesn't exist"""
        if self.check_table_exists('airline_queries'):
            logger.info("✅ Airline queries table already exists, skipping...")
            return True
        
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        try:
            # Create airline_queries table
            cursor.execute('''
                CREATE TABLE airline_queries (
                    id SERIAL PRIMARY KEY,
                    query_text TEXT NOT NULL,
                    detected_airline_code VARCHAR(10),
                    detected_airline_name VARCHAR(255),
                    success BOOLEAN DEFAULT FALSE,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create index
            cursor.execute('''
                CREATE INDEX idx_queries_timestamp ON airline_queries(timestamp)
            ''')
            
            conn.commit()
            logger.info("✅ Airline queries table created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create airline_queries table: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def add_conversation_context_table(self):
        """Add conversation_context table if it doesn't exist"""
        if self.check_table_exists('conversation_context'):
            logger.info("✅ Conversation context table already exists, skipping...")
            return True
        
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        try:
            # Create conversation_context table
            cursor.execute('''
                CREATE TABLE conversation_context (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    context_type VARCHAR(50) NOT NULL,
                    original_query TEXT NOT NULL,
                    search_params JSONB,
                    origin VARCHAR(10),
                    destination VARCHAR(10),
                    departure_date DATE,
                    passengers INTEGER DEFAULT 1,
                    cabin_class VARCHAR(20) DEFAULT 'ECONOMY',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL
                )
            ''')
            
            # Create indexes
            cursor.execute('''
                CREATE INDEX idx_conversation_user_id ON conversation_context(user_id)
            ''')
            cursor.execute('''
                CREATE INDEX idx_conversation_expires ON conversation_context(expires_at)
            ''')
            cursor.execute('''
                CREATE INDEX idx_conversation_created ON conversation_context(created_at)
            ''')
            
            conn.commit()
            logger.info("✅ Conversation context table created successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to create conversation_context table: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def insert_sample_airlines(self):
        """Insert sample airline data if airlines table is empty"""
        conn = self.get_connection()
        if not conn:
            return False
        
        cursor = conn.cursor()
        
        try:
            # Check if airlines table has data
            cursor.execute("SELECT COUNT(*) FROM airlines")
            count = cursor.fetchone()[0]
            
            if count > 0:
                logger.info(f"✅ Airlines table already has {count} records, skipping sample data insertion")
                return True
            
            # Sample airlines data
            sample_airlines = [
                ('AI', 'Air India', ['airindia', 'air-india', 'air_india']),
                ('6E', 'IndiGo', ['indigo airlines', 'indigo air']),
                ('SG', 'SpiceJet', ['spice jet', 'spice-jet', 'spice_jet']),
                ('UK', 'Vistara', ['vistara airlines', 'vistara air']),
                ('9W', 'Jet Airways', ['jet airways', 'jet air']),
                ('G8', 'GoAir', ['go air', 'goair']),
                ('I5', 'AirAsia India', ['airasia india', 'airasia']),
                ('QP', 'Akasa Air', ['akasa air', 'akasa']),
                ('EM', 'Emirates', ['emirates airlines', 'emirates air']),
                ('QR', 'Qatar Airways', ['qatar airways', 'qatar air']),
                ('EY', 'Etihad Airways', ['etihad airways', 'etihad air']),
                ('BA', 'British Airways', ['british airways', 'british air']),
                ('LH', 'Lufthansa', ['lufthansa airlines', 'lufthansa air']),
                ('SQ', 'Singapore Airlines', ['singapore airlines', 'singapore air']),
                ('TG', 'Thai Airways', ['thai airways', 'thai air']),
                ('MH', 'Malaysia Airlines', ['malaysia airlines', 'malaysia air']),
                ('CX', 'Cathay Pacific', ['cathay pacific', 'cathay air']),
                ('JL', 'Japan Airlines', ['japan airlines', 'japan air']),
                ('NH', 'All Nippon Airways', ['all nippon airways', 'all nippon air']),
                ('UA', 'United Airlines', ['united airlines', 'united air']),
                ('AA', 'American Airlines', ['american airlines', 'american air']),
                ('DL', 'Delta Air Lines', ['delta air lines', 'delta air']),
                ('WN', 'Southwest Airlines', ['southwest airlines', 'southwest air']),
                ('B6', 'JetBlue Airways', ['jetblue airways', 'jetblue air']),
                ('AS', 'Alaska Airlines', ['alaska airlines', 'alaska air']),
                ('NK', 'Spirit Airlines', ['spirit airlines', 'spirit air']),
                ('F9', 'Frontier Airlines', ['frontier airlines', 'frontier air']),
                ('G4', 'Allegiant Air', ['allegiant air', 'allegiant airlines']),
                ('WS', 'WestJet', ['westjet airlines', 'westjet air']),
                ('AC', 'Air Canada', ['air canada', 'aircanada']),
                ('QF', 'Qantas', ['qantas airways', 'qantas air']),
                ('VA', 'Virgin Australia', ['virgin australia airlines', 'virgin australia air']),
                ('VS', 'Virgin Atlantic', ['virgin atlantic airways', 'virgin atlantic air']),
                ('TK', 'Turkish Airlines', ['turkish airlines', 'turkish air']),
                ('MS', 'EgyptAir', ['egypt air', 'egypt-air']),
                ('RJ', 'Royal Jordanian', ['royal jordanian airlines', 'royal jordanian air']),
                ('SV', 'Saudi Arabian Airlines', ['saudi arabian airlines', 'saudi arabian air']),
                ('KU', 'Kuwait Airways', ['kuwait airways', 'kuwait air']),
                ('WY', 'Oman Air', ['oman air', 'omanair']),
                ('GF', 'Gulf Air', ['gulf air', 'gulfair']),
                ('2B', 'Bahrain Air', ['bahrain air', 'bahrainair']),
                ('FZ', 'Flydubai', ['fly dubai', 'fly-dubai']),
                ('G9', 'Air Arabia', ['air arabia', 'airarabia']),
                ('XY', 'flynas', ['fly nas', 'fly-nas']),
                ('J9', 'Jazeera Airways', ['jazeera airways', 'jazeera air']),
                ('PC', 'Pegasus Airlines', ['pegasus airlines', 'pegasus air']),
                ('SU', 'Aeroflot', ['aeroflot airlines', 'aeroflot air']),
                ('S7', 'S7 Airlines', ['s7 airlines', 's7 air']),
                ('U6', 'Ural Airlines', ['ural airlines', 'ural air']),
                ('WZ', 'Red Wings Airlines', ['red wings airlines', 'red wings air']),
                ('UT', 'UTair', ['utair airlines', 'utair air']),
                ('N4', 'Nordwind Airlines', ['nordwind airlines', 'nordwind air']),
                ('ZF', 'Azur Air', ['azur air', 'azur airlines']),
                ('CA', 'Air China', ['air china', 'airchina']),
                ('CZ', 'China Southern Airlines', ['china southern airlines', 'china southern air']),
                ('MU', 'China Eastern Airlines', ['china eastern airlines', 'china eastern air']),
                ('HU', 'Hainan Airlines', ['hainan airlines', 'hainan air']),
                ('MF', 'Xiamen Airlines', ['xiamen airlines', 'xiamen air']),
                ('ZH', 'Shenzhen Airlines', ['shenzhen airlines', 'shenzhen air']),
                ('3U', 'Sichuan Airlines', ['sichuan airlines', 'sichuan air']),
                ('FM', 'Shanghai Airlines', ['shanghai airlines', 'shanghai air']),
                ('KE', 'Korean Air', ['korean air', 'korean airlines']),
                ('OZ', 'Asiana Airlines', ['asiana airlines', 'asiana air']),
                ('LJ', 'Jin Air', ['jin air', 'jinair']),
                ('BX', 'Air Busan', ['air busan', 'airbusan']),
                ('TW', 'T\'way Air', ['t\'way air', 't\'way airlines']),
                ('7C', 'Jeju Air', ['jeju air', 'jeju airlines']),
                ('ZE', 'Eastar Jet', ['eastar jet', 'eastar airlines']),
                ('RS', 'Air Seoul', ['air seoul', 'airseoul']),
                ('YG', 'Fly Gangwon', ['fly gangwon', 'flygangwon']),
                ('YP', 'Air Premia', ['air premia', 'airpremia']),
                ('YJ', 'Air Incheon', ['air incheon', 'airincheon']),
                ('KO', 'Aero K', ['aero k', 'aerok']),
                ('AM', 'Air Max', ['air max', 'airmax']),
                ('JE', 'Air Jeju', ['air jeju', 'airjeju']),
                ('GW', 'Air Gangwon', ['air gangwon', 'airgangwon'])
            ]
            
            for code, name, aliases in sample_airlines:
                cursor.execute('''
                    INSERT INTO airlines (airline_code, airline_name, aliases)
                    VALUES (%s, %s, %s)
                ''', (code, name, json.dumps(aliases)))
            
            conn.commit()
            logger.info(f"✅ Inserted {len(sample_airlines)} sample airlines")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to insert sample airlines: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
    
    def verify_tables(self):
        """Verify that all required tables exist"""
        tables_to_check = ['airlines', 'airline_queries', 'conversation_context']
        
        for table in tables_to_check:
            if self.check_table_exists(table):
                logger.info(f"✅ Table '{table}' exists")
            else:
                logger.error(f"❌ Table '{table}' is missing")
                return False
        
        return True
    
    def run_add_tables(self):
        """Add new tables and data"""
        logger.info("🚀 Starting to add new tables and data...")
        
        # Step 1: Add airlines table
        if not self.add_airlines_table():
            logger.error("❌ Failed to add airlines table")
            return False
        
        # Step 2: Add airline_queries table
        if not self.add_airline_queries_table():
            logger.error("❌ Failed to add airline_queries table")
            return False
        
        # Step 3: Add conversation_context table
        if not self.add_conversation_context_table():
            logger.error("❌ Failed to add conversation_context table")
            return False
        
        # Step 4: Insert sample airlines data
        if not self.insert_sample_airlines():
            logger.error("❌ Failed to insert sample airlines")
            return False
        
        # Step 5: Verify all tables exist
        if not self.verify_tables():
            logger.error("❌ Table verification failed")
            return False
        
        logger.info("🎉 New tables and data added successfully!")
        return True

def main():
    """Main function to add new tables"""
    add_tables = AddNewTables()
    
    if add_tables.run_add_tables():
        print("\n✅ New tables and data added successfully!")
        print("\n📋 What was added:")
        print("1. airlines table - for airline detection")
        print("2. airline_queries table - for tracking queries")
        print("3. conversation_context table - for follow-up queries")
        print("4. Sample airline data - 60+ airlines with aliases")
        print("\n🔄 Next steps:")
        print("1. Restart your application")
        print("2. Test airline detection functionality")
        print("3. Test follow-up query functionality")
    else:
        print("\n❌ Failed to add new tables!")
        print("\n🔧 Troubleshooting:")
        print("1. Check PostgreSQL is running")
        print("2. Verify database credentials in .env")
        print("3. Ensure user has CREATE permissions")

if __name__ == "__main__":
    main() 