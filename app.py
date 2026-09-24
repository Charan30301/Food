import os
import re
from urllib.parse import quote
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "hotel_secret_key_12345")

# --- Merchant Configuration ---
MERCHANT_UPI_ID = "hotelmerchantexample@okaxis"  # Replace with your real UPI ID
MERCHANT_NAME = "Grand Palace Hotel"

# --- PostgreSQL Config ---
DB_CONFIG = {
    "dbname": "hotel_db",
    "user": "postgres",
    "password": "kerasuchi",  # Replace with your DB password
    "host": "localhost",
    "port": 5432
}

def get_db():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


# ---------------- Cart Code Helpers ----------------
def parse_cart_code(code_str):
    cart = {}
    if not code_str:
        return cart
    matches = re.findall(r'(\d+)\+(\d+)a', code_str)
    for item_id, qty in matches:
        cart[int(item_id)] = int(qty)
    return cart

def build_cart_code(cart_dict):
    parts = []
    for item_id, qty in sorted(cart_dict.items()):
        if qty > 0:
            parts.append(f"{item_id}+{qty}a")
    return "".join(parts)


# ---------------- Routes ----------------
@app.route("/")
def index():
    if "user_email" not in session:
        session["user_email"] = "customer@example.com"
        session["username"] = "Guest Customer"
    return redirect(url_for("menu_page"))

@app.route("/menu")
def menu_page():
    if "user_email" not in session:
        return redirect("/")
    return render_template("menu.html", email=session["user_email"], username=session.get("username", "Guest"))

@app.route("/cart")
def cart_page():
    if "user_email" not in session:
        return redirect(url_for("menu_page"))
    return render_template("cart.html", email=session["user_email"], username=session.get("username", "Guest"))


@app.route("/api/menu", methods=["GET"])
def get_menu():
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, item_name, category, price::float, photo_url, is_active 
                FROM menu_items 
                ORDER BY id ASC;
            """)
            items = cur.fetchall()

            cur.execute("SELECT cart_code, total_price::float FROM carts WHERE user_email = %s;", (user_email,))
            cart_row = cur.fetchone()

    cart_dict = parse_cart_code(cart_row["cart_code"]) if cart_row else {}
    total_price = cart_row["total_price"] if cart_row else 0.0

    return jsonify({
        "items": items,
        "cart": cart_dict,
        "cart_code": cart_row["cart_code"] if cart_row else "",
        "total_price": total_price
    })


@app.route("/api/cart/update", methods=["POST"])
def update_cart():
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    item_id = int(data.get("itemId"))
    delta = int(data.get("delta", 0))

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cart_code FROM carts WHERE user_email = %s;", (user_email,))
            cart_row = cur.fetchone()
            current_code = cart_row["cart_code"] if cart_row else ""
            cart_dict = parse_cart_code(current_code)

            new_qty = cart_dict.get(item_id, 0) + delta
            if new_qty > 0:
                cart_dict[item_id] = new_qty
            else:
                cart_dict.pop(item_id, None)

            new_code = build_cart_code(cart_dict)

            total_price = 0.0
            if cart_dict:
                item_ids = list(cart_dict.keys())
                cur.execute(
                    "SELECT id, price::float FROM menu_items WHERE id = ANY(%s);",
                    (item_ids,)
                )
                prices = {row["id"]: row["price"] for row in cur.fetchall()}
                for i_id, qty in cart_dict.items():
                    total_price += prices.get(i_id, 0.0) * qty

            cur.execute("""
                INSERT INTO carts (user_email, cart_code, total_price, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (user_email)
                DO UPDATE SET 
                    cart_code = EXCLUDED.cart_code,
                    total_price = EXCLUDED.total_price,
                    updated_at = NOW();
            """, (user_email, new_code, total_price))
            conn.commit()

    return jsonify({
        "success": True,
        "cart": cart_dict,
        "cart_code": new_code,
        "total_price": round(total_price, 2)
    })


@app.route("/api/cart/items", methods=["GET"])
def get_cart_items():
    """Returns row details (photo, name, category, quantity, item total) for all items in the cart."""
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cart_code, total_price::float FROM carts WHERE user_email = %s;", (user_email,))
            cart_row = cur.fetchone()

            if not cart_row or not cart_row["cart_code"]:
                return jsonify({"items": [], "total_price": 0.0, "cart_code": ""})

            cart_dict = parse_cart_code(cart_row["cart_code"])
            item_ids = list(cart_dict.keys())

            cur.execute("""
                SELECT id, item_name, category, price::float, photo_url 
                FROM menu_items 
                WHERE id = ANY(%s);
            """, (item_ids,))
            menu_data = cur.fetchall()

    detailed_items = []
    for item in menu_data:
        qty = cart_dict.get(item["id"], 0)
        detailed_items.append({
            "id": item["id"],
            "item_name": item["item_name"],
            "category": item["category"],
            "price": item["price"],
            "photo_url": item["photo_url"],
            "quantity": qty,
            "line_total": round(item["price"] * qty, 2)
        })

    return jsonify({
        "items": detailed_items,
        "total_price": cart_row["total_price"],
        "cart_code": cart_row["cart_code"]
    })


@app.route("/api/order/create", methods=["POST"])
def create_order():
    """Generates an order record, empties the cart, and prepares the UPI deep-link."""
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Fetch current cart
            cur.execute("SELECT cart_code, total_price::float FROM carts WHERE user_email = %s;", (user_email,))
            cart = cur.fetchone()

            if not cart or not cart["cart_code"] or cart["total_price"] <= 0:
                return jsonify({"error": "Cart is empty"}), 400

            # 2. Insert into orders
            cur.execute("""
                INSERT INTO orders (user_email, items_code, total_amount, status)
                VALUES (%s, %s, %s, 'placed')
                RETURNING id;
            """, (user_email, cart["cart_code"], cart["total_price"]))
            order_id = cur.fetchone()["id"]

            # 3. Clear cart
            cur.execute("UPDATE carts SET cart_code = '', total_price = 0 WHERE user_email = %s;", (user_email,))
            conn.commit()

    # Generate UPI intent URI
    total = cart["total_price"]
    note = f"Order #{order_id} Preorder"
    upi_url = f"upi://pay?pa={MERCHANT_UPI_ID}&pn={quote(MERCHANT_NAME)}&am={total:.2f}&cu=INR&tn={quote(note)}"

    return jsonify({
        "success": True,
        "order_id": order_id,
        "upi_url": upi_url,
        "amount": total
    })


@app.route("/api/order/active", methods=["GET"])
def check_active_order():
    """Checks if the user has an active (placed or preparing) order."""
    user_email = session.get("user_email")
    if not user_email:
        return jsonify({"has_active_order": False})

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, status, total_amount::float 
                FROM orders 
                WHERE user_email = %s AND status IN ('placed', 'preparing')
                ORDER BY created_at DESC 
                LIMIT 1;
            """, (user_email,))
            order = cur.fetchone()

    if order:
        return jsonify({
            "has_active_order": True,
            "order_id": order["id"],
            "status": order["status"]
        })
    return jsonify({"has_active_order": False})


if __name__ == "__main__":
    app.run(debug=True, port=5000)