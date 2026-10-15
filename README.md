# Grand Palace Hotel - Food Preordering & Kitchen Management System

A web-based restaurant food preordering and kitchen operations management system built with Flask and PostgreSQL, styled with an embedded luxury champagne gold and ivory theme.

---

## Key Features

- **Customer Ordering & Tracking**:
  - Live food menu filtered by categories (`Tiffins`, `Fast Food`, `Meals`).
  - Mobile bottom-sheet food details on card click.
  - Cart item synchronization using encoded database cart strings.
  - 60-second real-time kitchen acceptance window with automatic timeout cancellation.
  - Persistent acceptance timer across page reloads and navigation.
  - Interactive 4-stage live stepper tracker with emerald-green status dots (`Accepted` → `Preparing` → `Prepared` → `Delivered`).
  - Themed modal notifications for kitchen updates and cancellation notices with custom kitchen reasons.
  - Fixed-footer slide-out profile sidebar with pinned logout and order history.

- **Kitchen Operations (Admin Dashboard)**:
  - Dual-view orders manager separated into sub-tabs: **New Requests** and **In-Progress Orders**.
  - Dynamic 60-second countdown badge on each new incoming request card.
  - Full-card solid red highlighting for orders pending payment.
  - Single-step themed confirmation modal before updating order lifecycle states.
  - Responsive menu management: desktop table and touch-optimized mobile cards.
  - Mobile-responsive bottom-sheet modal for adding and updating food items.
  - Master kitchen operational toggle (`Kitchen: OPEN` / `Kitchen: CLOSED`).
  - Orphaned media management tool for browsing and deleting files in `static/uploads/`.
  - Automatic client-side menu synchronization using database version bumps.

---

## Tech Stack

- **Backend**: Python 3.10+, Flask
- **Database**: PostgreSQL (psycopg v3 with `dict_row`)
- **Authentication**: Google One-Tap Identity Services OAuth 2.0 (Customer), scrypt hashed credentials (Admin)
- **Payment Processing**: Razorpay Gateway (Live mode) & Instant Bypass Controller (Test mode)
- **Frontend**: Vanilla HTML5, CSS3 (inlined luxury ivory/gold responsive styles), JavaScript (ES6+ Fetch API)

---

## Database Setup

1. Log into your PostgreSQL instance:
   ```bash
   psql -U postgres

## Recent additions

- `/admin/statistics`: today's summary, daily totals for the latest 30 calendar days, and month-by-month totals for the latest 6 calendar months.
- `/admin/cooking`: dedicated accepted/preparing/prepared order board.
- Customer menu/cart loading indicators and lazy-loaded food photos.
- Order tax persistence via `orders.tax_amount` and `orders.tax_rate`.

### Database update
Run the updated `schema.sql` against the existing PostgreSQL database (or deploy the app and open Statistics once; the statistics/payment routes also add the tax columns if missing). Existing orders created before tax persistence was added cannot have exact historical tax reconstructed from the old database fields, so their tax values default to ₹0.00.

### Statistics definitions
Order counts exclude cancelled orders. Cash/counter and online received totals include only orders marked `paid`. Online payments are currently recorded under the generic `online` method; the current code does not identify PhonePe separately. Tax is summed from the tax amount saved against each paid order.


## Notification flow

- New customer order → Reception push.
- Customer order accepted/preparing/prepared/delivered/cancelled → Customer push.
- Customer payment confirmed/counter payment received → Customer push.
- Paid order entering the cooking queue → Chef push.
- Foreground custom popups can also create a browser notification when permission has been granted.

The existing in-page sounds and popup UI are preserved.

## PWA requirements

For install and background push notifications, production must be served over **HTTPS**. `localhost` is also treated as a secure context by browsers for local development.

If a browser does not offer an install prompt, use its browser menu and choose its **Install app / Add to Home screen** option.

## Database

`schema.sql` now includes a `push_subscriptions` table. The subscription endpoint also creates that table automatically if an older deployed database has not yet been migrated.

# Food Ordering & Kitchen Management System

A full-stack food ordering, kitchen display, and reception management ecosystem. The platform comprises a centralized Flask web service with role-based interfaces (Customer, Chef, Reception/Admin) alongside dedicated native Android companion apps for real-time order tracking and push notifications powered by Firebase Cloud Messaging (FCM).

---

## 🌟 System Overview & Role Workflows

1. **Customer Web App & Android App (`/menu`, `/cart`)**
   * Browse categorized menu items, customize quantities, and add items to the cart.
   * Place orders and track cooking status live (`cooking_waiting.html`).
   * Receive real-time FCM notifications as the kitchen updates the preparation progress.

2. **Chef Portal & Kitchen Display System (`/cooking_orders`)**
   * Real-time kitchen view displaying active, queued, and in-progress orders.
   * Action buttons to update statuses: `Cooking`, `Ready to Serve`, and `Completed`.
   * Companion Android app (`ChefApp`) alerts the kitchen staff when new orders arrive.

3. **Reception & Admin Portal (`/admin_dashboard`, `/admin_statistics`, `/admin_menu_edit`)**
   * Overview of dine-in/takeaway orders and cash/counter settlements.
   * Menu editor to create, update, price, and toggle availability of dishes.
   * Business statistics reporting order trends, popular items, and revenue.
   * Dedicated Android application (`ReceptionApp`) for floor and front-desk staff.

---

## 🏗️ Repository Layout

```text
├── app.py                                # Main Flask server and route controllers
├── schema.sql                            # Database initialization schema
├── requirements.txt                      # Python dependencies
├── FCM-DEPLOYMENT.md                     # Firebase deployment instructions
├── scripts/
│   ├── encode_firebase_service_account.py # Service account encoder for cloud deployments
│   └── generate_vapid.py                 # VAPID key generator for push notifications
├── templates/                            # Server-rendered Jinja2 UI templates
│   ├── menu.html                         # Customer menu view
│   ├── cart.html                         # Cart & order confirmation
│   ├── cooking_waiting.html              # Customer order status tracker
│   ├── cooking_orders.html               # Chef Kitchen Display System (KDS)
│   ├── admin_dashboard.html              # Reception & order management
│   ├── admin_menu_edit.html              # Menu CRUD management
│   ├── admin_statistics.html             # Sales, volume, and order analytics
│   ├── login.html                        # General login
│   ├── chef_login.html                   # Dedicated chef access
│   └── admin_login.html                  # Admin portal authentication
└── android-apps/                         # Native companion Android applications
    ├── BUILD-ALL.md                      # Compilation and packaging guidelines
    ├── CustomerApp/                      # Native customer app with order notifications
    ├── ChefApp/                          # Native kitchen display companion app
    └── ReceptionApp/                     # Front-desk and checkout companion app