# Food Ordering Android app (no Firebase / no third-party push service)

This is an Android Studio WebView app for the customer-facing pages of the Flask website. Admin routes are blocked inside the app; the admin dashboard remains available in a normal browser.

## How notifications work

The app asks for Android notification permission and creates **local Android notifications**. While the customer app is open and its website page is active, it checks the signed-in customer's order statuses through `/api/mobile/orders/statuses` every 20 seconds. If an order changes from another status to `delivered`, Android displays a notification.

This does **not** use Firebase Cloud Messaging, VAPID, or any external push provider. Android notification permission only allows an app to display notifications; it does not itself deliver updates from your Render server. Without a push service, this version cannot reliably notify the user while the app is fully closed or Android has stopped its background work. It needs the app open/active for polling.

## Setup

1. Deploy the Flask backend to Render as usual and make sure the database schema includes the existing `orders` table. No Firebase environment variable or Firebase file is required.
2. Open this `android-app` folder in Android Studio.
3. In `app/src/main/java/com/localfood/foodapp/MainActivity.kt`, replace `https://YOUR-RENDER-SERVICE.onrender.com/` with your actual HTTPS Render website URL. Keep the trailing `/`.
4. Let Android Studio sync Gradle. Ensure Android SDK Platform 35 is installed if prompted.
5. Use **Build > Build APK(s)**. Android Studio will generate a debug APK under `app/build/outputs/apk/debug/`.
6. Install the APK on an Android phone, open it, sign in, and allow notifications. Place a test order and use the admin dashboard in a browser to change its status to `delivered` while the app remains open.

## Deploy backend changes

Commit and push the included `app.py`, `requirements.txt`, and `schema.sql` changes to the GitHub repository connected to Render. Render should redeploy automatically. The added route is authenticated by the customer's existing Flask session and only returns orders belonging to that signed-in account.

## Important limits

- No Firebase, VAPID, `google-services.json`, or Firebase secrets are needed.
- Notifications are detected by polling while the app is active. If the app is closed, force-stopped, or Android suspends the WebView, an update may not be detected until the app is opened again.
- Android 13+ requires the user to grant notification permission.
- Google sign-in may be blocked in an embedded WebView by Google; test the existing login flow on your phone.
