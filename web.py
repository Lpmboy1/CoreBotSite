import os
from flask import Flask, redirect, request, session, jsonify
import requests
import db

app = Flask(__name__, static_folder='.', static_url_path='')
app.secret_key = os.getenv("FLASK_SECRET_KEY", "<YOUR_FLASK_SECRET_KEY>")

CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1515335648188432424")
CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "<YOUR_DISCORD_CLIENT_SECRET>")
REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "http://localhost:5000/callback")


db.init_db()


# ---------------- DISCORD OAUTH ----------------

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

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
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


# ---------------- API ----------------

def require_login():
    return "user_id" in session


@app.route("/me")
def me():
    if not require_login():
        return jsonify({"error": "not logged in"}), 401

    profile = db.get_user_profile(session["user_id"])
    tier = next((t for t in db.PROGRESSION_TIERS if profile["xp"] >= t["min"]), db.PROGRESSION_TIERS[-1])

    return {
        "user_id": session["user_id"],
        "username": session["username"],
        "xp": profile["xp"],
        "streak": profile["streak"],
        "last_claim": profile["last_claim"],
        "level": tier["level"],
        "title": tier["title"],
        "next_threshold": tier["next"],
    }


@app.route("/add_xp", methods=["POST"])
def api_add_xp():
    if not require_login():
        return jsonify({"error": "not logged in"}), 401

    data = request.json or {}
    amount = int(data.get("amount", 0))
    if amount <= 0:
        return jsonify({"error": "invalid amount"}), 400

    db.add_xp(session["user_id"], amount)
    return {"status": "ok"}


@app.route("/set_xp", methods=["POST"])
def api_set_xp():
    if not require_login():
        return jsonify({"error": "not logged in"}), 401

    data = request.json or {}
    xp = int(data.get("xp", 0))
    if xp < 0:
        return jsonify({"error": "invalid xp"}), 400

    db.set_xp(session["user_id"], xp)
    return {"status": "ok"}


@app.route("/claim_daily", methods=["POST"])
def api_claim_daily():
    if not require_login():
        return jsonify({"error": "not logged in"}), 401

    try:
        result = db.claim_daily(session["user_id"])
        return {"status": "ok", "profile": result}
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400


if __name__ == "__main__":
    app.run(debug=True)
