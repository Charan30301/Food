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
