# Native Android + Firebase Cloud Messaging deployment

## Architecture

- Existing Flask + PostgreSQL stays as the backend.
- Customer, Reception and Chef are native Android WebView apps with different package IDs.
- Firebase Cloud Messaging (FCM) supplies Android push notifications.
- The apps register their FCM token with `/api/fcm/register` after the relevant web login session is available.
- Flask sends FCM from the existing order/payment/status events.

## Firebase setup (one Firebase project, three Android apps)

Create one Firebase project. Register these three Android apps exactly:

- `com.localfood.customer`
- `com.localfood.reception`
- `com.localfood.chef`

For each registered Android app, download its own `google-services.json` and put it here:

- `android-apps/CustomerApp/app/google-services.json`
- `android-apps/ReceptionApp/app/google-services.json`
- `android-apps/ChefApp/app/google-services.json`

Do not commit those files to GitHub if your repository policy requires them to stay private; the repository `.gitignore` already ignores `google-services.json`.

Firebase's Android setup requires the Google services plugin and the app-specific `google-services.json`. The package name in Firebase must exactly match the Android `applicationId`. See the official Firebase setup documentation.

## Firebase Admin service account for Render

The Flask server needs a Firebase Admin SDK service account so it can send FCM messages.

1. In Firebase Console open Project settings.
2. Open Service accounts.
3. Generate a new private key.
4. Download the JSON file locally as `firebase-service-account.json`.
5. NEVER commit this JSON file to GitHub.
6. In the project folder run:

```bash
python scripts/encode_firebase_service_account.py firebase-service-account.json
```

Copy the single long output value.

## Render environment variables

Add this variable to the existing Render Web Service:

```text
FIREBASE_SERVICE_ACCOUNT_JSON_B64=<the long base64 value>
```

Keep the existing database variables, Flask secret, Razorpay variables, etc. unchanged.

After saving the environment variable, deploy/redeploy the Render service.

## Android app server URL

In each app edit:

`app/src/main/res/values/strings.xml`

Replace:

```text
https://YOUR-RENDER-DOMAIN.onrender.com
```

with your real HTTPS Render URL.

Example:

```xml
<string name="server_url">https://foodcentre.onrender.com</string>
```

Do this separately for CustomerApp, ReceptionApp and ChefApp.

## Build each APK

Open each project separately in Android Studio:

```text
android-apps/CustomerApp
android-apps/ReceptionApp
android-apps/ChefApp
```

Allow Gradle to sync/download dependencies.

Then:

```text
Build -> Build APK(s)
```

The APK will be under the app/build/outputs/apk directory.

## Install/test

### Customer

1. Install Customer APK.
2. Allow notifications when Android asks.
3. Log in to the customer account.
4. Keep the app installed.
5. Close the app.
6. Create an order/payment event from the customer flow or use the FCM test endpoint while authenticated.

### Reception

1. Install Reception APK.
2. Allow notifications.
3. Enter the reception/admin password.
4. Wait for registration to complete.
5. Close the app.
6. Create a new customer order.
7. Reception should receive an Android notification.

### Chef

1. Install Chef APK.
2. Allow notifications.
3. Enter the chef password.
4. Wait for registration to complete.
5. Close the app.
6. Mark an order as paid.
7. Chef should receive the new cooking-order notification.

## Android requirements

FCM Android clients require Android 6.0+ and Google Play services/Google Play Store on supported devices. Android 13+ requires the `POST_NOTIFICATIONS` runtime permission, which these apps request at launch.

## What is already connected in Flask

FCM is triggered for these backend events:

- new customer order -> Reception
- test/online payment confirmation -> Customer + Chef
- counter payment -> Customer + Chef
- order accepted -> Customer
- order preparing -> Customer
- order prepared -> Customer
- order delivered -> Customer
- order cancelled -> Customer

This means the closed-app notification is driven by the server-side event, not by an HTML popup. If a popup is shown while the webpage is open, the same backend event can also send the Android notification.

## FCM test endpoint

Authenticated Customer/Reception sessions can call:

```text
POST /api/fcm/test
```

For example from the browser developer console while logged into the web app:

```javascript
fetch('/api/fcm/test', {method:'POST'}).then(r => r.json()).then(console.log)
```

For Reception the endpoint sends a reception test; for Customer it sends a customer test. The Chef app can be tested by creating a paid order, or by adding a dedicated chef test control later.

## Render logs

After deployment, look for:

```text
Firebase Admin initialized for FCM
```

If Firebase initialization fails, Render logs will show `Could not initialize Firebase Admin`.

If an FCM send fails, the logs show `FCM failed for device ...`.
