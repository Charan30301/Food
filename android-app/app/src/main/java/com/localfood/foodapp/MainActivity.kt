package com.localfood.foodapp

import android.Manifest
import android.app.Activity
import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.WebChromeClient
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import android.util.Log
import org.json.JSONObject
import com.google.android.gms.auth.api.signin.GoogleSignIn
import com.google.android.gms.auth.api.signin.GoogleSignInOptions
import com.google.android.gms.common.api.ApiException
import androidx.activity.result.ActivityResultLauncher
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.ComponentActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : ComponentActivity() {
    companion object {
        // Replace this with your live Render URL before building the app.
        const val SITE_URL = "https://food-preorder.onrender.com/"
        const val CHANNEL_ID = "food_order_updates"
        // Must be the WEB application OAuth client ID used by Flask GOOGLE_CLIENT_ID.
        const val GOOGLE_WEB_CLIENT_ID = "116617699324-nq62vkdhd87uns0sukirvkadpje6lpu2.apps.googleusercontent.com"
        var activeActivity: MainActivity? = null
    }

    private lateinit var webView: WebView
    private lateinit var googleSignInLauncher: ActivityResultLauncher<Intent>
    private lateinit var googleSignInClient: com.google.android.gms.auth.api.signin.GoogleSignInClient
    private val siteHost: String by lazy { Uri.parse(SITE_URL).host ?: "" }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        activeActivity = this
        createNotificationChannel()
        askNotificationPermission()

        val googleOptions = GoogleSignInOptions.Builder(GoogleSignInOptions.DEFAULT_SIGN_IN)
            .requestEmail()
            .requestIdToken(GOOGLE_WEB_CLIENT_ID)
            .build()
        googleSignInClient = GoogleSignIn.getClient(this, googleOptions)
        googleSignInLauncher = registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->
            if (result.resultCode == Activity.RESULT_OK) {
                try {
                    val account = GoogleSignIn.getSignedInAccountFromIntent(result.data)
                        .getResult(ApiException::class.java)
                    val idToken = account.idToken
                    if (idToken.isNullOrBlank()) {
                        sendNativeGoogleError("Google did not return an ID token. Check the Web OAuth client ID and SHA-1 configuration.")
                    } else {
                        sendNativeGoogleTokenToPage(idToken)
                    }
                } catch (e: ApiException) {
                    Log.e("FoodGoogleSignIn", "Google sign-in failed: ${e.statusCode}", e)
                    sendNativeGoogleError("Google sign-in failed (code ${e.statusCode}). Check your OAuth client ID and SHA-1 setup.")
                }
            } else if (result.resultCode != Activity.RESULT_CANCELED) {
                sendNativeGoogleError("Google sign-in was not completed. Please try again.")
            }
        }

        webView = WebView(this)
        setContentView(webView)
        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.loadsImagesAutomatically = true
        webView.settings.javaScriptCanOpenWindowsAutomatically = true
        webView.settings.setSupportMultipleWindows(false)
        webView.webViewClient = WebViewClient()
        webView.webChromeClient = WebChromeClient()
        webView.addJavascriptInterface(NativeBridge(), "FoodNative")
        webView.webViewClient = object : WebViewClient() {
            override fun shouldOverrideUrlLoading(view: WebView, request: WebResourceRequest): Boolean {
                val uri = request.url
                if (uri.scheme == "http" || uri.scheme == "https") {
                    if (uri.host == siteHost) {
                        if (isAdminPath(uri.path.orEmpty())) {
                            view.loadUrl(SITE_URL)
                            return true
                        }
                        return false
                    }
                    // Never embed Google's account page in WebView. Payment provider
                    // pages remain in WebView so existing checkout redirects can work.
                    if (uri.host == "accounts.google.com" || uri.host == "oauth2.googleapis.com") {
                        startActivity(Intent(Intent.ACTION_VIEW, uri))
                        return true
                    }
                    return false
                }
                return true
            }

            override fun onPageFinished(view: WebView, url: String) {
                super.onPageFinished(view, url)
                if (!url.startsWith(SITE_URL.substringBeforeLast("/") + "/")) return
                if (isAdminPath(Uri.parse(url).path.orEmpty())) {
                    view.loadUrl(SITE_URL)
                    return
                }
                startOrderStatusPolling()
            }
        }
        webView.loadUrl(SITE_URL)
    }

    private fun startNativeGoogleSignIn() {
        if (GOOGLE_WEB_CLIENT_ID.startsWith("YOUR_")) {
            sendNativeGoogleError("Set GOOGLE_WEB_CLIENT_ID in MainActivity.kt to the same Web OAuth client ID as Render GOOGLE_CLIENT_ID.")
            return
        }
        googleSignInLauncher.launch(googleSignInClient.signInIntent)
    }

    private fun sendNativeGoogleTokenToPage(idToken: String) {
        val safeToken = JSONObject.quote(idToken)
        runOnUiThread {
            if (::webView.isInitialized) {
                webView.evaluateJavascript("window.handleNativeGoogleCredential && window.handleNativeGoogleCredential($safeToken);", null)
            }
        }
    }

    private fun sendNativeGoogleError(message: String) {
        val safeMessage = JSONObject.quote(message)
        runOnUiThread {
            if (::webView.isInitialized) {
                webView.evaluateJavascript("window.handleNativeGoogleError && window.handleNativeGoogleError($safeMessage);", null)
            }
        }
    }

    private fun isAdminPath(path: String): Boolean =
        path == "/admin" || path.startsWith("/admin/") || path.startsWith("/api/admin")

    private fun startOrderStatusPolling() {
        // Local notifications are generated by Android itself. The app checks the
        // authenticated website session every 20 seconds while the WebView is active.
        val script = """
            (function() {
              if (window.__foodPollTimer) clearInterval(window.__foodPollTimer);
              async function checkFoodOrderStatuses() {
                try {
                  const response = await fetch('/api/mobile/orders/statuses', {
                    method: 'GET', credentials: 'same-origin', cache: 'no-store'
                  });
                  if (!response.ok) return;
                  const data = await response.json();
                  if (!data.success || !Array.isArray(data.orders)) return;
                  const key = 'food_order_statuses_v1';
                  const previous = JSON.parse(localStorage.getItem(key) || '{}');
                  const firstCheck = !localStorage.getItem(key);
                  for (const order of data.orders) {
                    const id = String(order.id);
                    const oldStatus = previous[id];
                    if (!firstCheck && oldStatus && oldStatus !== 'delivered' && order.status === 'delivered') {
                      FoodNative.showOrderNotification(
                        'Your food is ready!',
                        'Order #' + id + ' has been marked completed.',
                        id
                      );
                    }
                    previous[id] = order.status;
                  }
                  localStorage.setItem(key, JSON.stringify(previous));
                } catch (e) { /* Retry on the next polling cycle. */ }
              }
              checkFoodOrderStatuses();
              window.__foodPollTimer = setInterval(checkFoodOrderStatuses, 20000);
            })();
        """.trimIndent()
        webView.evaluateJavascript(script, null)
    }

    inner class NativeBridge {
        @JavascriptInterface fun appVersion(): String = "1.2.0"

        @JavascriptInterface
        fun startGoogleSignIn() {
            runOnUiThread { startNativeGoogleSignIn() }
        }

        @JavascriptInterface
        fun showOrderNotification(title: String, body: String, orderId: String) {
            runOnUiThread {
                if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(
                        this@MainActivity, Manifest.permission.POST_NOTIFICATIONS
                    ) != PackageManager.PERMISSION_GRANTED) return@runOnUiThread
                val launchIntent = Intent(this@MainActivity, MainActivity::class.java)
                val pendingIntent = PendingIntent.getActivity(
                    this@MainActivity, orderId.hashCode(), launchIntent,
                    PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
                )
                val notification = androidx.core.app.NotificationCompat.Builder(this@MainActivity, CHANNEL_ID)
                    .setSmallIcon(android.R.drawable.ic_dialog_info)
                    .setContentTitle(title)
                    .setContentText(body)
                    .setStyle(androidx.core.app.NotificationCompat.BigTextStyle().bigText(body))
                    .setContentIntent(pendingIntent)
                    .setAutoCancel(true)
                    .setPriority(androidx.core.app.NotificationCompat.PRIORITY_HIGH)
                    .build()
                getSystemService(NotificationManager::class.java).notify(orderId.hashCode(), notification)
            }
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(CHANNEL_ID, "Order updates", NotificationManager.IMPORTANCE_HIGH)
            channel.description = "Notifications when your food order is completed"
            getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
        }
    }

    private fun askNotificationPermission() {
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, arrayOf(Manifest.permission.POST_NOTIFICATIONS), 900)
        }
    }

    override fun onBackPressed() {
        if (::webView.isInitialized && webView.canGoBack()) {
            val previous = webView.copyBackForwardList().getItemAtIndex(webView.copyBackForwardList().currentIndex - 1)
            if (previous != null && isAdminPath(Uri.parse(previous.url).path.orEmpty())) {
                webView.loadUrl(SITE_URL)
            } else webView.goBack()
        } else super.onBackPressed()
    }

    override fun onDestroy() {
        if (activeActivity === this) activeActivity = null
        super.onDestroy()
    }
}
