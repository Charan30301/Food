# Food Ordering Website + Android customer app (no third-party push)

This project contains the Flask/PostgreSQL food-ordering website and an Android Studio app wrapper for customer pages. The admin dashboard remains accessible in a regular browser and is blocked inside the Android app.

## Notifications without Firebase

The Android app uses Android's local notification API and polls the authenticated backend every 20 seconds while the app is active. It notifies when an order status changes to `delivered`. No Firebase Cloud Messaging, VAPID, or third-party push credentials are used.

**Important:** notification permission allows an app to show notifications; it does not cause a Render server to send updates to a closed app. This no-third-party version does not guarantee notifications when the app is closed or suspended. Reliable remote notifications while closed require some delivery mechanism such as a push service or a continuously running connection/service with Android background limitations.

## Deploy website/backend

1. Push the updated `app.py`, `requirements.txt`, and `schema.sql` to the GitHub repository connected to Render.
2. Confirm Render has the required existing environment variables for Flask, PostgreSQL, Google sign-in and payment features.
3. Wait for the Render deployment to finish and test the website in a browser.
4. No Firebase environment variables or `google-services.json` are needed.

## Build Android app

Follow `android-app/README.md`. Set the live HTTPS Render URL in `android-app/app/src/main/java/com/localfood/foodapp/MainActivity.kt`, open the `android-app` folder in Android Studio, sync Gradle, then choose **Build > Build APK(s)**.
