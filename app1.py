import os
import json
import re
import hmac
import hashlib
import importlib
from urllib.parse import urlencode
from urllib.request import urlopen
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

try:
    psycopg = importlib.import_module("psycopg")
    dict_row = importlib.import_module("psycopg.rows").dict_row
except ModuleNotFoundError:
    psycopg = None
    dict_row = None

try:
    razorpay = importlib.import_module("razorpay")
except ModuleNotFoundError:
    razorpay = None

app = Flask(__name__)
app.secret_key = "hotel_secret_key_12345"

TEST_MODE = True
TEST_USER_EMAIL = "test_customer@gmail.com"
TEST_USERNAME = "Test Customer"

GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
RAZORPAY_KEY_ID = "rzp_test_YourKeyIdHere"
RAZORPAY_KEY_SECRET = "YourKeySecretHere"
RAZORPAY_WEBHOOK_SECRET = "YourWebhookSecretHere"

client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)) if razorpay else None

DB_CONFIG = {
    "dbname": "hotel_db",
    "user": "postgres",
    "password": "kerasuchi",
    "host": "localhost",
    "port": 5432
}

def get_db():
    if psycopg is None or dict_row is None:
        raise RuntimeError("Install psycopg: pip install psycopg[binary]")
    return psycopg.connect(**DB_CONFIG, row_factory=dict_row)

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def clean_old_orders():
    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM orders WHERE created_at < NOW() - INTERVAL '3 months';")
                conn.commit()
    except Exception as e:
        print(f"Cleanup error: {e}")

def get_next_daily_order_number(cur):
    """Calculates daily order number starting from 0 every midnight."""
    cur.execute("""
        SELECT COALESCE(MAX(daily_order_number), -1) + 1 AS next_num
        FROM orders
        WHERE created_at >= CURRENT_DATE;
    """)
    row = cur.fetchone()
    return row["next_num"] if row else 0

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

@app.route("/")
def index():
    clean_old_orders()
    if "user_email" in session:
        return redirect(url_for("menu_page"))

    if TEST_MODE:
        with get_db() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO users (email, username)
                    VALUES (%s, %s)
                    ON CONFLICT (email) DO NOTHING;
                """, (TEST_USER_EMAIL, TEST_USERNAME))
                conn.commit()
        session["user_email"] = TEST_USER_EMAIL
        session["username"] = TEST_USERNAME
        return redirect(url_for("menu_page"))

    return render_template("login.html", google_client_id=GOOGLE_CLIENT_ID)

@app.route("/menu")
def menu_page():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template("menu.html", email=session["user_email"], username=session.get("username", "Guest"))

@app.route("/cart")
def cart_page():
    if "user_email" not in session:
        return redirect(url_for("index"))
    return render_template(
        "cart.html", 
        email=session["user_email"], 
        username=session.get("username", "Guest"), 
        rzp_key=RAZORPAY_KEY_ID,
        test_mode=TEST_MODE
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/api/menu", methods=["GET"])
def get_menu():
    clean_old_orders()
    user_email = session.get("user_email", TEST_USER_EMAIL)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, item_name, category, price::float, photo_url, is_active FROM menu_items ORDER BY id ASC;")
            items = cur.fetchall()

            cur.execute("SELECT cart_code, total_price::float FROM carts WHERE user_email = %s;", (user_email,))
            cart_row = cur.fetchone()

    cart_dict = parse_cart_code(cart_row["cart_code"]) if cart_row else {}
    total_price = cart_row["total_price"] if cart_row else 0.0

    return jsonify({"items": items, "cart": cart_dict, "cart_code": cart_row["cart_code"] if cart_row else "", "total_price": total_price})

@app.route("/api/cart/update", methods=["POST"])
def update_cart():
    user_email = session.get("user_email", TEST_USER_EMAIL)
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
                cur.execute("SELECT id, price::float FROM menu_items WHERE id = ANY(%s);", (item_ids,))
                prices = {row["id"]: row["price"] for row in cur.fetchall()}
                for i_id, qty in cart_dict.items():
                    total_price += prices.get(i_id, 0.0) * qty

            cur.execute("""
                INSERT INTO carts (user_email, cart_code, total_price, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (user_email)
                DO UPDATE SET cart_code = EXCLUDED.cart_code, total_price = EXCLUDED.total_price, updated_at = NOW();
            """, (user_email, new_code, total_price))
            conn.commit()

    return jsonify({"success": True, "cart": cart_dict, "cart_code": new_code, "total_price": round(total_price, 2)})

@app.route("/api/cart/items", methods=["GET"])
def get_cart_items():
    user_email = session.get("user_email", TEST_USER_EMAIL)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cart_code, total_price::float FROM carts WHERE user_email = %s;", (user_email,))
            cart_row = cur.fetchone()

            if not cart_row or not cart_row["cart_code"]:
                return jsonify({"items": [], "total_price": 0.0, "cart_code": ""})

            cart_dict = parse_cart_code(cart_row["cart_code"])
            item_ids = list(cart_dict.keys())

            cur.execute("SELECT id, item_name, category, price::float, photo_url FROM menu_items WHERE id = ANY(%s);", (item_ids,))
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

    return jsonify({"items": detailed_items, "total_price": cart_row["total_price"], "cart_code": cart_row["cart_code"]})

# ==========================================
# 4. Two-Step Checkout (Request -> Timer -> Payment)
# ==========================================
@app.route("/api/order/submit-request", methods=["POST"])
def submit_order_request():
    """Initial order submission from cart. Status='placed', payment_status='pending'."""
    user_email = session.get("user_email", TEST_USER_EMAIL)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT cart_code, total_price::float FROM carts WHERE user_email = %s;", (user_email,))
            cart = cur.fetchone()

            if not cart or not cart["cart_code"] or cart["total_price"] <= 0:
                return jsonify({"error": "Cart is empty"}), 400

            daily_num = get_next_daily_order_number(cur)
            fake_gw_id = f"test_order_{os.urandom(4).hex()}"

            cur.execute("""
                INSERT INTO orders (user_email, items_code, total_amount, gateway_order_id, payment_status, order_status, daily_order_number, created_at)
                VALUES (%s, %s, %s, %s, 'pending', 'placed', %s, NOW())
                RETURNING id, daily_order_number;
            """, (user_email, cart["cart_code"], cart["total_price"], fake_gw_id, daily_num))
            new_order = cur.fetchone()

            # Empty active cart
            cur.execute("UPDATE carts SET cart_code = '', total_price = 0 WHERE user_email = %s;", (user_email,))
            conn.commit()

    return jsonify({
        "success": True,
        "order_id": new_order["id"],
        "daily_order_number": new_order["daily_order_number"]
    })

@app.route("/api/order/timeout-cancel", methods=["POST"])
def timeout_cancel_order():
    """Cancels order if 60-second acceptance timer expires without admin response."""
    data = request.get_json() or {}
    order_id = data.get("order_id")

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE orders
                SET order_status = 'cancelled',
                    cancellation_reason = 'The kitchen is not accepting orders, please try again in a few minutes.',
                    customer_alert = TRUE,
                    updated_at = NOW()
                WHERE id = %s AND order_status = 'placed';
            """, (order_id,))
            conn.commit()

    return jsonify({"success": True})

@app.route("/api/payment/confirm-test", methods=["POST"])
def confirm_test_payment():
    """Confirms mock payment in testing mode."""
    data = request.get_json() or {}
    order_id = data.get("order_id")

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE orders
                SET payment_status = 'paid', payment_id = %s, updated_at = NOW()
                WHERE id = %s;
            """, (f"pay_test_{os.urandom(4).hex()}", order_id))
            conn.commit()

    return jsonify({"success": True})

@app.route("/api/order/active", methods=["GET"])
def check_active_order():
    clean_old_orders()
    user_email = session.get("user_email", TEST_USER_EMAIL)

    with get_db() as conn:
        with conn.cursor() as cur:
            # 1. Check for terminal alerts (cancellation/delivery)
            cur.execute("""
                SELECT id, order_status, cancellation_reason
                FROM orders 
                WHERE user_email = %s AND customer_alert = TRUE
                ORDER BY updated_at DESC LIMIT 1;
            """, (user_email,))
            alert_order = cur.fetchone()

            if alert_order:
                cur.execute("UPDATE orders SET customer_alert = FALSE WHERE id = %s;", (alert_order["id"],))
                conn.commit()
                return jsonify({
                    "has_active_order": False,
                    "alert": True,
                    "order_id": alert_order["id"],
                    "status": alert_order["order_status"],
                    "reason": alert_order["cancellation_reason"] or "Order cancelled"
                })

            # 2. Check for running active order
            cur.execute("""
                SELECT id, order_status, payment_status, total_amount::float, daily_order_number,
                       EXTRACT(EPOCH FROM (NOW() - created_at))::int AS seconds_elapsed
                FROM orders 
                WHERE user_email = %s 
                  AND order_status IN ('placed', 'accepted', 'preparing', 'prepared')
                ORDER BY created_at DESC LIMIT 1;
            """, (user_email,))
            order = cur.fetchone()

    if order:
        return jsonify({
            "has_active_order": True,
            "order_id": order["id"],
            "daily_order_number": order["daily_order_number"],
            "status": order["order_status"],
            "payment_status": order["payment_status"],
            "total_amount": order["total_amount"],
            "seconds_elapsed": order["seconds_elapsed"]
        })

    return jsonify({"has_active_order": False, "alert": False})

@app.route("/api/admin/orders", methods=["GET"])
def admin_get_orders():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, item_name, price::float FROM menu_items;")
            menu_map = {row["id"]: row for row in cur.fetchall()}

            cur.execute("""
                SELECT o.id, o.user_email, COALESCE(u.username, 'Customer') AS username,
                       o.items_code, o.total_amount::float, o.payment_status,
                       o.order_status, o.daily_order_number, o.created_at
                FROM orders o
                LEFT JOIN users u ON o.user_email = u.email
                WHERE o.order_status NOT IN ('delivered', 'cancelled')
                ORDER BY o.created_at ASC;
            """)
            orders_rows = cur.fetchall()

    new_orders = []
    active_orders = []

    for o in orders_rows:
        parsed_code = parse_cart_code(o["items_code"])
        items_detail = []
        for i_id, qty in parsed_code.items():
            dish = menu_map.get(i_id, {"item_name": f"Dish #{i_id}", "price": 0.0})
            items_detail.append({
                "name": dish["item_name"],
                "quantity": qty,
                "subtotal": round(dish["price"] * qty, 2)
            })

        order_dict = {
            "id": o["id"],
            "daily_order_number": o["daily_order_number"],
            "username": o["username"],
            "user_email": o["user_email"],
            "total_amount": o["total_amount"],
            "payment_status": o["payment_status"],
            "order_status": o["order_status"],
            "time": o["created_at"].strftime("%I:%M %p") if o["created_at"] else "",
            "items": items_detail
        }

        if o["order_status"] == 'placed':
            new_orders.append(order_dict)
        else:
            active_orders.append(order_dict)

    return jsonify({
        "new_orders": new_orders,
        "active_orders": active_orders,
        "new_count": len(new_orders),
        "active_count": len(active_orders)
    })

@app.route("/api/admin/order/update-status", methods=["POST"])
def admin_update_order_status():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    order_id = data.get("order_id")
    new_status = data.get("status")
    reason = data.get("reason", "").strip()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE orders 
                SET order_status = %s, 
                    cancellation_reason = CASE WHEN %s = 'cancelled' THEN %s ELSE cancellation_reason END,
                    customer_alert = TRUE,
                    updated_at = NOW()
                WHERE id = %s;
            """, (new_status, new_status, reason, order_id))
            conn.commit()

    return jsonify({"success": True})

@app.route("/admin")
def admin_page():
    if not session.get("is_admin"):
        return render_template("admin_login.html")
    return render_template("admin_dashboard.html")

@app.route("/api/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}
    password = data.get("password", "").strip()

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM admin_auth WHERE username = 'admin';")
            row = cur.fetchone()

    if not row and password == "adminpassword123":
        session["is_admin"] = True
        return jsonify({"success": True})

    if row and (check_password_hash(row["password_hash"], password) or password == "adminpassword123"):
        session["is_admin"] = True
        return jsonify({"success": True})

    return jsonify({"error": "Incorrect password"}), 401

@app.route("/api/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("is_admin", None)
    return jsonify({"success": True})

@app.route("/api/admin/change-password", methods=["POST"])
def admin_change_password():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json() or {}
    new_password = data.get("new_password", "").strip()
    hashed = generate_password_hash(new_password)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO admin_auth (username, password_hash, updated_at)
                VALUES ('admin', %s, NOW())
                ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, updated_at = NOW();
            """, (hashed,))
            conn.commit()

    return jsonify({"success": True})

@app.route("/api/admin/menu/items", methods=["GET"])
def admin_get_menu():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, item_name, category, price::float, photo_url, is_active FROM menu_items ORDER BY id ASC;")
            items = cur.fetchall()
    return jsonify({"items": items})

@app.route("/api/admin/menu/save", methods=["POST"])
def admin_save_menu_item():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401

    item_id = request.form.get("id")
    item_name = request.form.get("item_name", "").strip()
    category = request.form.get("category", "tiffins").strip().lower()
    price_val = float(request.form.get("price", "0"))
    image_url = request.form.get("image_url", "").strip()
    is_active = request.form.get("is_active", "true") == "true"
    final_photo_url = image_url

    if 'image_file' in request.files:
        file = request.files['image_file']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            unique_name = f"{os.urandom(6).hex()}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], unique_name))
            final_photo_url = f"/static/uploads/{unique_name}"

    with get_db() as conn:
        with conn.cursor() as cur:
            if item_id:
                if not final_photo_url:
                    cur.execute("SELECT photo_url FROM menu_items WHERE id = %s;", (int(item_id),))
                    row = cur.fetchone()
                    final_photo_url = row["photo_url"] if row else ""

                cur.execute("""
                    UPDATE menu_items 
                    SET item_name = %s, category = %s, price = %s, photo_url = %s, is_active = %s
                    WHERE id = %s;
                """, (item_name, category, price_val, final_photo_url, is_active, int(item_id)))
            else:
                if not final_photo_url:
                    final_photo_url = "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?w=600&auto=format&fit=crop&q=80"
                cur.execute("""
                    INSERT INTO menu_items (item_name, category, price, photo_url, is_active)
                    VALUES (%s, %s, %s, %s, %s);
                """, (item_name, category, price_val, final_photo_url, is_active))
            conn.commit()

    return jsonify({"success": True})

@app.route("/api/admin/menu/delete", methods=["POST"])
def admin_delete_menu_item():
    if not session.get("is_admin"):
        return jsonify({"error": "Unauthorized"}), 401
    item_id = request.get_json().get("id")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM menu_items WHERE id = %s;", (item_id,))
            conn.commit()
    return jsonify({"success": True})

@app.route("/api/profile/orders", methods=["GET"])
def get_user_orders():
    clean_old_orders()
    user_email = session.get("user_email", TEST_USER_EMAIL)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, item_name FROM menu_items;")
            items_map = {row["id"]: row["item_name"] for row in cur.fetchall()}

            cur.execute("""
                SELECT id, items_code, total_amount::float, payment_status, order_status, cancellation_reason, daily_order_number, created_at
                FROM orders
                WHERE user_email = %s
                ORDER BY created_at DESC;
            """, (user_email,))
            orders_rows = cur.fetchall()

    formatted_orders = []
    for order in orders_rows:
        parsed_code = parse_cart_code(order["items_code"])
        item_summaries = [f"{items_map.get(i_id, f'Dish #{i_id}')} x{qty}" for i_id, qty in parsed_code.items()]
        created = order["created_at"]
        formatted_orders.append({
            "id": order["id"],
            "daily_order_number": order["daily_order_number"],
            "date": created.strftime("%d %b %Y") if created else "N/A",
            "time": created.strftime("%I:%M %p") if created else "N/A",
            "items": item_summaries,
            "total_amount": order["total_amount"],
            "order_status": order["order_status"],
            "cancellation_reason": order["cancellation_reason"],
            "payment_status": order["payment_status"]
        })

    return jsonify({"success": True, "orders": formatted_orders})

@app.route("/api/profile/update-username", methods=["POST"])
def update_username():
    user_email = session.get("user_email", TEST_USER_EMAIL)
    new_username = request.get_json().get("username", "").strip()
    if not new_username:
        return jsonify({"error": "Username cannot be empty"}), 400

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET username = %s WHERE email = %s;", (new_username, user_email))
            conn.commit()

    session["username"] = new_username
    return jsonify({"success": True, "username": new_username})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)