package com.localfood.customer;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Dialog;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.net.http.SslError;
import android.os.Build;
import android.os.Bundle;
import android.os.Message;
import android.view.ViewGroup;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.SslErrorHandler;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends AppCompatActivity {
    private WebView webView;
    private static final int REQ = 7001;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        createChannel();
        requestPermission();

        webView = new WebView(this);
        setContentView(webView);

        // Cookie configuration
        CookieManager cookieManager = CookieManager.getInstance();
        cookieManager.setAcceptCookie(true);
        cookieManager.setAcceptThirdPartyCookies(webView, true);

        // WebSettings configuration
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setSupportMultipleWindows(true);
        settings.setJavaScriptCanOpenWindowsAutomatically(true);

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }

        // Remove the "; wv" marker so Google OAuth does not block the WebView user agent
        String customUserAgent = settings.getUserAgentString()
                .replace("; wv", "")
                .replaceAll("Version/[0-9.]+\\s", "");
        settings.setUserAgentString(customUserAgent);

        // Support window.open popups used by OAuth logins
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onCreateWindow(WebView view, boolean isDialog, boolean isUserGesture, Message resultMsg) {
                WebView popupWebView = new WebView(MainActivity.this);
                WebSettings popupSettings = popupWebView.getSettings();
                popupSettings.setJavaScriptEnabled(true);
                popupSettings.setDomStorageEnabled(true);
                popupSettings.setUserAgentString(settings.getUserAgentString());

                CookieManager.getInstance().setAcceptThirdPartyCookies(popupWebView, true);

                Dialog dialog = new Dialog(MainActivity.this, android.R.style.Theme_Black_NoTitleBar_Fullscreen);
                dialog.setContentView(popupWebView);
                dialog.show();

                popupWebView.setWebChromeClient(new WebChromeClient() {
                    @Override
                    public void onCloseWindow(WebView window) {
                        dialog.dismiss();
                        window.destroy();
                    }
                });

                popupWebView.setWebViewClient(new WebViewClient() {
                    @Override
                    public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                        String url = request.getUrl().toString();
                        String baseServerUrl = getString(R.string.server_url);

                        // If redirected back to the app server, load in the main WebView and dismiss popup
                        if (url.startsWith(baseServerUrl)) {
                            dialog.dismiss();
                            webView.loadUrl(url);
                            return true;
                        }
                        return false;
                    }
                });

                WebView.WebViewTransport transport = (WebView.WebViewTransport) resultMsg.obj;
                transport.setWebView(popupWebView);
                resultMsg.sendToTarget();
                return true;
            }
        });

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                return false;
            }

            @Override
            public void onPageFinished(WebView v, String u) {
                injectRegistration();
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                super.onReceivedError(view, request, error);
            }

            @SuppressLint("WebViewClientOnReceivedSslError")
            @Override
            public void onReceivedSslError(WebView view, SslErrorHandler handler, SslError error) {
                handler.proceed(); // Allows local/self-signed SSL development certificates
            }
        });

        webView.addJavascriptInterface(new Bridge(), "AndroidFCM");
        webView.loadUrl(getString(R.string.server_url) + getString(R.string.start_path));
    }

    private void injectRegistration() {
        String js = "javascript:(function(){" +
                "if(window.__fcmBridgeInstalled)return;" +
                "window.__fcmBridgeInstalled=true;" +
                "async function r(){" +
                "try{" +
                "const t=window.AndroidFCM.getToken();" +
                "if(!t)return;" +
                "await fetch('/api/fcm/register',{" +
                "method:'POST'," +
                "headers:{'Content-Type':'application/json'}," +
                "credentials:'include'," +
                "body:JSON.stringify({token:t,role:'" + getString(R.string.app_role) + "',package_name:'" + getPackageName() + "'})" +
                "});" +
                "}catch(e){}" +
                "}r();setInterval(r,4000);" +
                "})();";
        webView.evaluateJavascript(js, null);
    }

    private void requestPermission() {
        if (Build.VERSION.SDK_INT >= 33 && ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(this, new String[]{Manifest.permission.POST_NOTIFICATIONS}, REQ);
        }
    }

    private void createChannel() {
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationChannel c = new NotificationChannel("orders", "Orders", NotificationManager.IMPORTANCE_HIGH);
            c.setDescription("Order and status notifications");
            c.enableVibration(true);
            getSystemService(NotificationManager.class).createNotificationChannel(c);
        }
    }

    public class Bridge {
        @JavascriptInterface
        public String getToken() {
            return getSharedPreferences("fcm", MODE_PRIVATE).getString("token", "");
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            super.onBackPressed();
        }
    }
}