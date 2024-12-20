import os
import psycopg2
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def get_db_connection():
    """Get a PostgreSQL database connection"""
    return psycopg2.connect(os.getenv('DATABASE_URL'))

def init_db():
    """Initialize the database schema"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            text TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            channel_id TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

def store_message(text, user_id, user_name, channel_id, channel_name):
    """Store a new message in the database"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute('''
        INSERT INTO messages (text, user_id, user_name, channel_id, channel_name, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
    ''', (text, user_id, user_name, channel_id, channel_name, datetime.now()))
    
    conn.commit()
    cur.close()
    conn.close()
