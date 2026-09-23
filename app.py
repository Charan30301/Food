import json
import os
from urllib.parse import urlencode
from urllib.request import urlopen
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "your-secret-key-change-in-production")

# --- Google Client ID (from Google Cloud Console) ---
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com")

# --- PostgreSQL Connection Configuration ---
DB_CONFIG = {
    "dbname": "hotel_db",
    "user": "postgres",
    "password": "kerasuchi",
    "host": "localhost",
    "port": 5000
}

def get_db():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


def verify_google_token(token):
    """Verify a Google ID token without requiring the google-auth package."""
    query = urlencode({"id_token": token})
    with urlopen(
        f"https://oauth2.googleapis.com/tokeninfo?{query}", timeout=10
    ) as response:
        idinfo = json.loads(response.read())

    if idinfo.get("aud") != GOOGLE_CLIENT_ID:
        raise ValueError("Invalid Google token audience")
    return idinfo


@app.route("/")
def index():
    # If the user is already logged in during this session, go straight to menu
    if "user_email" in session:
        return redirect(url_for("menu"))
    return render_template("login.html", google_client_id=GOOGLE_CLIENT_ID)


@app.route("/api/auth/google", methods=["POST"])
def verify_google():
    """Verifies the Google token sent by client, extracts Gmail, and checks PostgreSQL."""
    data = request.get_json() or {}
    token = data.get("credential")

    if not token:
        return jsonify({"error": "Missing Google token"}), 400

    try:
        # Verify identity with Google API
        idinfo = verify_google_token(token)
        gmail = idinfo.get("email")

        if not gmail:
            return jsonify({"error": "Email not provided by Google"}), 400

        # Query PostgreSQL to see if the user exists
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, email, username FROM users WHERE email = %s;", (gmail,))
                user = cur.fetchone()

        if user:
            # User already exists! Store in session and instruct frontend to redirect to menu
            session["user_email"] = user["email"]
            session["username"] = user["username"]
            return jsonify({
                "exists": True,
                "email": user["email"],
                "username": user["username"],
                "redirect_url": "/menu"
            })
        else:
            # New user: send back the verified email so user only needs to enter a username
            return jsonify({
                "exists": False,
                "email": gmail
            })

    except ValueError:
        return jsonify({"error": "Invalid Google token"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/register", methods=["POST"])
def register():
    """Takes the verified email and user-entered username, saves to Postgres."""
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    username = data.get("username", "").strip()

    if not email or not username:
        return jsonify({"error": "Email and username are required"}), 400

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                # Insert customer record
                cur.execute(
                    """
                    INSERT INTO users (email, username)
                    VALUES (%s, %s)
                    ON CONFLICT (email) DO UPDATE SET username = EXCLUDED.username
                    RETURNING id, email, username;
                    """,
                    (email, username)
                )
                user = cur.fetchone()
                conn.commit()

        # Set session
        session["user_email"] = user["email"]
        session["username"] = user["username"]

        return jsonify({
            "success": True,
            "redirect_url": "/menu"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/menu")
def menu():
    # Only authenticated users can access the menu
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("menu.html", username=session.get("username"), email=session.get("user_email"))


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)