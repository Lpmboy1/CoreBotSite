import os
import psycopg2
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

PROGRESSION_TIERS = [
    {"min": 2000, "level": 6, "title": "Elite",    "next": None},
    {"min": 1000, "level": 5, "title": "Veteran",  "next": 2000},
    {"min": 500,  "level": 4, "title": "Regular",  "next": 1000},
    {"min": 250,  "level": 3, "title": "Member",   "next": 500},
    {"min": 100,  "level": 2, "title": "Newcomer", "next": 250},
    {"min": 0,    "level": 1, "title": "Visitor",  "next": 100},
]


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_connection()
    cur = conn.cursor()
    try:
        # Create core table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS user_xp (
                user_id TEXT PRIMARY KEY,
                username TEXT,
                xp INTEGER NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0,
                last_claim INTEGER,
                updated_at INTEGER NOT NULL DEFAULT 0
            )
            """
        )

        # Apply schema migrations safely if columns are missing
        cur.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_name = 'user_xp'
        """)
        columns = [row[0] for row in cur.fetchall()]
        
        if "username" not in columns:
            cur.execute("ALTER TABLE user_xp ADD COLUMN username TEXT")
        if "streak" not in columns:
            cur.execute("ALTER TABLE user_xp ADD COLUMN streak INTEGER NOT NULL DEFAULT 0")
        if "last_claim" not in columns:
            cur.execute("ALTER TABLE user_xp ADD COLUMN last_claim INTEGER")
        if "updated_at" not in columns:
            cur.execute("ALTER TABLE user_xp ADD COLUMN updated_at INTEGER NOT NULL DEFAULT 0")

        conn.commit()
    finally:
        cur.close()
        conn.close()


def init_user(user_id, username):
    """Initialize a new user in the database if they don't exist"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO user_xp (user_id, username, xp, streak, updated_at)
            VALUES (%s, %s, 0, 0, %s)
            ON CONFLICT(user_id)
            DO UPDATE SET username = EXCLUDED.username
            """,
            (user_id, username, int(time.time())),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def get_all_xp():
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT user_id, xp FROM user_xp")
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()


def get_user_xp(user_id):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT user_id, xp, streak, last_claim FROM user_xp WHERE user_id = %s",
            (user_id,),
        )
        row = cur.fetchone()
        if row is None:
            return {"user_id": user_id, "xp": 0, "streak": 0, "last_claim": None}
        
        return {
            "user_id": row[0], 
            "xp": row[1], 
            "streak": row[2] or 0, 
            "last_claim": row[3]
        }
    finally:
        cur.close()
        conn.close()


def set_xp(user_id, xp):
    ts = int(time.time())
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO user_xp (user_id, xp, updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT(user_id)
            DO UPDATE SET xp = EXCLUDED.xp, updated_at = EXCLUDED.updated_at
            """,
            (user_id, xp, ts),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def add_xp(user_id, amount):
    ts = int(time.time())
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO user_xp (user_id, xp, updated_at)
            VALUES (%s, %s, %s)
            ON CONFLICT(user_id)
            DO UPDATE SET xp = user_xp.xp + EXCLUDED.xp, updated_at = EXCLUDED.updated_at
            """,
            (user_id, amount, ts),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()


def claim_daily(user_id, amount=25):
    profile = get_user_xp(user_id)
    now = int(time.time())
    last_claim = profile["last_claim"]
    
    current_date = datetime.fromtimestamp(now).date()
    
    if last_claim:
        last_claim_date = datetime.fromtimestamp(last_claim).date()
        if current_date == last_claim_date:
            raise ValueError("Daily reward already claimed today")
        elif current_date == last_claim_date + timedelta(days=1):
            streak = profile["streak"] + 1
        else:
            streak = 1
    else:
        streak = 1

    new_xp = profile["xp"] + amount

    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            INSERT INTO user_xp (user_id, xp, streak, last_claim, updated_at)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT(user_id)
            DO UPDATE SET xp = EXCLUDED.xp, streak = EXCLUDED.streak, last_claim = EXCLUDED.last_claim, updated_at = EXCLUDED.updated_at
            """,
            (user_id, new_xp, streak, now, now),
        )
        conn.commit()
    finally:
        cur.close()
        conn.close()

    return {
        "user_id": user_id,
        "xp": new_xp,
        "streak": streak,
        "last_claim": now,
    }


def get_tier(xp):
    for tier in PROGRESSION_TIERS:
        if xp >= tier["min"]:
            return tier["level"]
    return 1
