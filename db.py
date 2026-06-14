import os
import psycopg2
from psycopg2 import sql
import time
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
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_xp (
            user_id TEXT PRIMARY KEY,
            xp INTEGER NOT NULL DEFAULT 0,
            streak INTEGER NOT NULL DEFAULT 0,
            last_claim INTEGER,
            updated_at INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    cur.execute("""
        SELECT column_name FROM information_schema.columns 
        WHERE table_name = 'user_xp'
    """)
    columns = [row[0] for row in cur.fetchall()]
    
    if "streak" not in columns:
        cur.execute("ALTER TABLE user_xp ADD COLUMN streak INTEGER NOT NULL DEFAULT 0")
    if "last_claim" not in columns:
        cur.execute("ALTER TABLE user_xp ADD COLUMN last_claim INTEGER")
    if "updated_at" not in columns:
        cur.execute("ALTER TABLE user_xp ADD COLUMN updated_at INTEGER NOT NULL DEFAULT 0")

    conn.commit()
    cur.close()
    conn.close()


def get_all_xp():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, xp FROM user_xp")
    rows = cur.fetchall()
    conn.close()
    return rows
%s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.clostion()
    cur = conn.cursor()
    cur.execute(
        "SELECT user_id, xp, streak, last_claim FROM user_xp WHERE user_id = ?",
        (user_id,),
    )
    row = cur.fetchone()
    conn.close()
    if row is None:
        return {"user_id": user_id, "xp": 0, "streak": 0, "last_claim": None}
    return {"user_id": row[0], "xp": row[1], "streak": row[2] or 0, "last_claim": row[3]}


def set_xp(user_id, xp):
    ts = int(time.time())
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT I%s, %s, %s)
        ON CONFLICT(user_id)
        DO UPDATE SET xp=excluded.xp, updated_at=excluded.updated_at
        """,
        (user_id, xp, ts),
    )
    conn.commit()
    cur.close
    conn.commit()
    conn.close()


def add_xp(user_id, amount):
    ts = int(time.time())
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT I%s, %s, %s)
        ON CONFLICT(user_id)
        DO UPDATE SET xp = xp + %s, updated_at = %s
        """,
        (user_id, amount, ts, amount, ts),
    )
    conn.commit()
    cur.close
    conn.commit()
    conn.close()


def claim_daily(user_id, amount=25):
    profile = get_user_profile(user_id)
    now = int(time.time())
    last_claim = profile["last_claim"]
    if last_claim and now - last_claim < 86400:
        raise ValueError("Daily reward already claimed")

    last_claim_time = time.gmtime(last_claim) if last_claim else None
    yesterday = time.gmtime(now - 86400)
    if (
        last_claim_time
        and last_claim_time.tm_year == yesterday.tm_year
        and last_claim_time.tm_yday == yesterday.tm_yday
    ):
        streak = profile["streak"] + 1
    else:
        streak = 1

    nonn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO user_xp (user_id, xp, streak, last_claim, updated_at)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT(user_id)
        DO UPDATE SET xp = %s, streak = %s, last_claim = %s, updated_at = %s
        """,
        (user_id, new_xp, streak, now, now, new_xp, streak, now, now),
    )
    conn.commit()
    cur.closeconnection
    conn.commit()
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
