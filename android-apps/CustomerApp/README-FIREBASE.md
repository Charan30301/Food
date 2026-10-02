# Customer App

Package name: `com.localfood.customer`
Start page: `/menu`

1. Register an Android app in your Firebase project using exactly this package name.
2. Download `google-services.json` and place it at `app/google-services.json`. Do not rename it.
3. Replace `server_url` in `app/src/main/res/values/strings.xml` with your HTTPS Render URL.
4. Open this folder in Android Studio, sync Gradle, and Build > Build APK(s).
5. Install the APK on an Android phone with Google Play services.
6. Allow notifications.
7. Log in to the app. The app then registers its FCM token with the Flask backend.
