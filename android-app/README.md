# Food Ordering Android app (no Firebase / no third-party push service)

This is an Android Studio WebView app for the customer-facing pages of the Flask website. Admin routes are blocked inside the app; the admin dashboard remains available in a normal browser.

## How notifications work

The app asks for Android notification permission and creates **local Android notifications**. While the customer app is open and its website page is active, it checks the signed-in customer's order statuses through `/api/mobile/orders/statuses` every 20 seconds. If an order changes from another status to `delivered`, Android displays a notification.

This does **not** use Firebase Cloud Messaging, VAPID, or any external push provider. Android notification permission only allows an app to display notifications; it does not itself deliver updates from your Render server. Without a push service, this version cannot reliably notify the user while the app is fully closed or Android has stopped its background work. It needs the app open/active for polling.

## Setup

1. Deploy the Flask backend to Render as usual. This app uses the existing `/api/auth/google` and `/api/register` endpoints. No Flask auth route change is required. No Firebase Cloud Messaging, `google-services.json`, or Firebase environment variable is used.
2. In Render Environment, copy the value of `GOOGLE_CLIENT_ID`. It must be the Web application OAuth client ID ending in `.apps.googleusercontent.com`.
3. In Google Cloud Console > APIs & Services > Credentials, keep the existing Web OAuth client used by your working Chrome login. Create an additional **OAuth client ID > Android** with package name `com.localfood.foodapp` and the SHA-1 signing certificate fingerprint for the APK you will install. For a debug APK, use Android Studio's Gradle `signingReport` task to find the debug SHA-1. If you later publish a Play Store-signed build, configure that signing certificate SHA-1 too.
4. Open `app/src/main/java/com/localfood/foodapp/MainActivity.kt`. Replace `https://YOUR-RENDER-SERVICE.onrender.com/` with your real HTTPS Render URL. Replace `YOUR_WEB_CLIENT_ID.apps.googleusercontent.com` in `GOOGLE_WEB_CLIENT_ID` with the exact **Web application client ID** copied from Render, not the Android client ID.
5. The Android app now shows its native Google sign-in button. It obtains a Google ID token through Google Play services and sends that token to the existing Flask `/api/auth/google` route inside the WebView session. Existing browser sign-in remains unchanged.
6. Let Android Studio sync Gradle. Ensure Android SDK Platform 35 is installed if prompted.
7. Use **Build > Build APK(s)**. Android Studio will generate a debug APK under `app/build/outputs/apk/debug/`.
8. Install the newly built APK (uninstall the older one first if needed), open it, sign in, and allow notifications. Place a test order and use the admin dashboard in a browser to change its status to `delivered` while the app remains open.

### Google Sign-In troubleshooting

- Error 10 / DEVELOPER_ERROR commonly means the Android package name or SHA-1 does not match the Android OAuth client.
- Missing ID token or token audience errors usually mean `GOOGLE_WEB_CLIENT_ID` is not exactly the same Web client ID as Render's `GOOGLE_CLIENT_ID`.
- Google native authentication uses Google Play services authentication only; this is separate from push notifications and does not add Firebase Cloud Messaging.

## Deploy backend changes

Commit and push the included `app.py`, `requirements.txt`, and `schema.sql` changes to the GitHub repository connected to Render. Render should redeploy automatically. The added route is authenticated by the customer's existing Flask session and only returns orders belonging to that signed-in account.

## Important limits

- No Firebase, VAPID, `google-services.json`, or Firebase secrets are needed.
- Notifications are detected by polling while the app is active. If the app is closed, force-stopped, or Android suspends the WebView, an update may not be detected until the app is opened again.
- Android 13+ requires the user to grant notification permission.
- Google sign-in may be blocked in an embedded WebView by Google; test the existing login flow on your phone.
