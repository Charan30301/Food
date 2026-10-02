package com.localfood.chef;

import android.Manifest;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Bundle;
import android.webkit.CookieManager;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

public class MainActivity extends AppCompatActivity {
 private WebView webView; private static final int REQ=7001;
 @Override protected void onCreate(Bundle state) { super.onCreate(state); createChannel(); requestPermission(); webView=new WebView(this); setContentView(webView); CookieManager.getInstance().setAcceptCookie(true); CookieManager.getInstance().setAcceptThirdPartyCookies(webView,true); webView.getSettings().setJavaScriptEnabled(true); webView.getSettings().setDomStorageEnabled(true); webView.setWebChromeClient(new WebChromeClient()); webView.setWebViewClient(new WebViewClient() { @Override public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) { return false; } @Override public void onPageFinished(WebView v,String u) { injectRegistration(); } }); webView.addJavascriptInterface(new Bridge(),"AndroidFCM"); webView.loadUrl(getString(R.string.server_url)+getString(R.string.start_path)); }
 private void injectRegistration() { String js="javascript:(function(){if(window.__fcmBridgeInstalled)return;window.__fcmBridgeInstalled=true;async function r(){try{const t=window.AndroidFCM.getToken();if(!t)return;await fetch('/api/fcm/register',{method:'POST',headers:{'Content-Type':'application/json'},credentials:'include',body:JSON.stringify({token:t,role:'"+getString(R.string.app_role)+"',package_name:'"+getPackageName()+"'})});}catch(e){}}r();setInterval(r,4000);})();"; webView.evaluateJavascript(js,null); }
 private void requestPermission() { if(Build.VERSION.SDK_INT>=33 && ContextCompat.checkSelfPermission(this,Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED) ActivityCompat.requestPermissions(this,new String[]{Manifest.permission.POST_NOTIFICATIONS},REQ); }
 private void createChannel() { if(Build.VERSION.SDK_INT>=26){ NotificationChannel c=new NotificationChannel("orders","Orders",NotificationManager.IMPORTANCE_HIGH); c.setDescription("Order and status notifications"); c.enableVibration(true); getSystemService(NotificationManager.class).createNotificationChannel(c); } }
 public class Bridge { @JavascriptInterface public String getToken() { return getSharedPreferences("fcm",MODE_PRIVATE).getString("token",""); } }
 @Override public void onBackPressed() { if(webView!=null && webView.canGoBack()) webView.goBack(); else super.onBackPressed(); }
}
