import os
import asyncio
import threading
from flask import Flask, redirect, request, session, jsonify
import requests
import db
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "<YOUR_FLASK_SECRET_KEY>")

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1515335648188432424")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "<YOUR_DISCORD_CLIENT_SECRET>")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/callback")

db.init_db()

# -------- DISCORD BOT SETUP --------

DISCORD_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "<YOUR_DISCORD_BOT_TOKEN>")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "1491435881733558374"))

ROLE_MAP = {
    1: 1515290650000000000,  # Visitor
    2: 1515290700000000000,  # Newcomer
    3: 1509940190725279834,  # Member
    4: 1515290501878775909,  # Regular
    5: 1515290564541550733,  # Veteran
    6: 1515290613812166727,  # Elite
}

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)


async def sync_member_roles(member: discord.Member, new_level: int):
    guild = member.guild

    new_role_id = ROLE_MAP.get(new_level)
    if not new_role_id:
        return

    new_role = guild.get_role(new_role_id)
    if not new_role:
        return

    if new_role in member.roles:
        return

    for role_id in ROLE_MAP.values():
        role = guild.get_role(role_id)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason="XP progression sync")
            except discord.Forbidden:
                pass

    try:
        await member.add_roles(new_role, reason="XP progression sync")
    except discord.Forbidden:
        pass


@tasks.loop(minutes=10)
async def sync_roles():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    data = db.get_all_xp()

    for user_id, xp in data:
        try:
            member = guild.get_member(int(user_id))
            if member is None:
                member = await guild.fetch_member(int(user_id))

            level = db.get_tier(xp)
            await sync_member_roles(member, level)
            print(f"{member} -> XP {xp} -> Level {level}")

        except discord.NotFound:
            continue
        except discord.Forbidden:
            print(f"No permission for {user_id}")
        except Exception as e:
            print(f"Error {user_id}: {e}")


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    sync_roles.start()


def run_bot_in_thread():
    """Run the Discord bot in a separate thread with its own event loop"""
    try:
        asyncio.run(bot.start(DISCORD_TOKEN))
    except Exception as e:
        print(f"Bot error: {e}")


# -------- START BOT IN BACKGROUND THREAD --------

bot_thread = threading.Thread(target=run_bot_in_thread, daemon=True)
bot_thread.start()

# -------- DISCORD OAUTH --------

@app.route("/login")
def login():
    url = (
        "https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        "&response_type=code"
        "&scope=identify"
        f"&redirect_uri={REDIRECT_URI}"
    )
    return redirect(url)


@app.route("/callback")
def callback():
    code = request.args.get("code")

    if not code:
        return jsonify({"error": "missing code"}), 400

    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "scope": "identify"
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    r = requests.post(
        "https://discord.com/api/oauth2/token",
        data=data,
        headers=headers
    )

    r.raise_for_status()

    token = r.json()["access_token"]

    user = requests.get(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    session["user_id"] = user["id"]
    session["username"] = user["username"]

    return redirect("/dashboard")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/dashboard")
def dashboard():
    return app.send_static_file("dashboard.html")


@app.route("/activity")
def activity():
    return app.send_static_file("activity.html")


# -------- API --------

def require_login():
    return "user_id" in session


@app.route("/me")
def me():
    if not require_login():
        return jsonify({"error": "not logged in"}), 401

    # FIXED: get_user_profile -> get_user_xp
    profile = db.get_user_xp(session["user_id"])

    tier = next(
        (t for t in db.PROGRESSION_TIERS if profile["xp"] >= t["min"]),
        db.PROGRESSION_TIERS[-1]
    )

    return jsonify({
        "user_id": session["user_id"],
        "username": session["username"],
        "xp": profile["xp"],
        "streak": profile["streak"],
        "last_claim": profile["last_claim"],
        "level": tier["level"],
        "title": tier["title"],
        "next_threshold": tier["next"],
    })


@app.route("/add_xp", methods=["POST"])
def api_add_xp():
    if not require_login():
        return jsonify({"error": "not logged in"}), 401

    data = request.json or {}

    try:
        amount = int(data.get("amount", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "invalid amount"}), 400

    if amount <= 0:
        return jsonify({"error": "invalid amount"}), 400

    db.add_xp(session["user_id"], amount)

    return jsonify({"status": "ok"})


@app.route("/set_xp", methods=["POST"])
def api_set_xp():
    if not require_login():
        return jsonify({"error": "not logged in"}), 401

    data = request.json or {}

    try:
        xp = int(data.get("xp", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "invalid xp"}), 400

    if xp < 0:
        return jsonify({"error": "invalid xp"}), 400

    db.set_xp(session["user_id"], xp)

    return jsonify({"status": "ok"})


@app.route("/claim_daily", methods=["POST"])
def api_claim_daily():
    if not require_login():
        return jsonify({"error": "not logged in"}), 401

    try:
        result = db.claim_daily(session["user_id"])
        return jsonify({
            "status": "ok",
            "profile": result
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/health")
def health():
    return jsonify({
        "status": "ok"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
