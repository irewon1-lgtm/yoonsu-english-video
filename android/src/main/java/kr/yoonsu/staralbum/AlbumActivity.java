package kr.yoonsu.staralbum;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.content.res.Configuration;
import android.graphics.Color;
import android.graphics.Insets;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.AtomicFile;
import android.view.View;
import android.view.WindowInsets;
import android.view.WindowInsetsController;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import org.json.JSONObject;

public final class AlbumActivity extends Activity {
    private static final String HOST = "appassets.androidplatform.net";
    private static final String BASE = "https://" + HOST + "/";
    private static final String HOME = BASE + "index.html";
    private static final int MIC_PERMISSION = 912;

    private WebView view;
    private FrameLayout canvas;
    private NativeMic mic;
    private byte[] key;
    private AtomicFile cached;
    private final ExecutorService updater = Executors.newSingleThreadExecutor();
    private volatile AlbumCatalog active;
    private AlbumCatalog available;
    private boolean checking, visible, askingMic, leaving;
    private long lastCheck;

    static boolean local(Uri uri) {
        return uri != null && "https".equals(uri.getScheme()) && HOST.equals(uri.getHost())
                && uri.getPort() == -1 && uri.getUserInfo() == null;
    }

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        setTitle("윤수 별빛 사진첩");
        try {
            try (InputStream stream = getAssets().open("content.key")) {
                key = GitHubRelease.readBounded(stream, 32);
            }
            if (key.length != 32) throw new IllegalStateException("Missing album key");
            try (InputStream stream = getAssets().open("initial.bundle")) {
                active = AlbumCatalog.load(GitHubRelease.readBounded(stream, AlbumCatalog.MAX_BUNDLE), key);
            }
            cached = new AtomicFile(new File(getFilesDir(), "album.bundle"));
            try (InputStream stream = cached.openRead()) {
                AlbumCatalog old = AlbumCatalog.load(GitHubRelease.readBounded(stream, AlbumCatalog.MAX_BUNDLE), key);
                if (old.version > active.version) active = old;
            } catch (Exception ignored) { /* The bundled copy is still usable. */ }
        } catch (Exception error) {
            Toast.makeText(this, "사진첩을 읽지 못했어요.", Toast.LENGTH_LONG).show();
            finish();
            return;
        }

        canvas = new FrameLayout(this);
        canvas.setBackgroundColor(Color.rgb(17, 29, 53));
        if (Build.VERSION.SDK_INT >= 35) {
            canvas.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {
                @Override public WindowInsets onApplyWindowInsets(View parent, WindowInsets insets) {
                    Insets edge = insets.getInsets(WindowInsets.Type.systemBars() | WindowInsets.Type.displayCutout());
                    parent.setPadding(edge.left, edge.top, edge.right, edge.bottom);
                    return insets;
                }
            });
        }
        mic = new NativeMic(this);
        view = new WebView(this);
        view.setBackgroundColor(Color.rgb(17, 29, 53));
        view.getSettings().setJavaScriptEnabled(true);
        view.getSettings().setDomStorageEnabled(true);
        view.getSettings().setAllowFileAccess(false);
        view.getSettings().setAllowContentAccess(false);
        view.getSettings().setMediaPlaybackRequiresUserGesture(true);
        view.addJavascriptInterface(mic, "NativeMic");
        view.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView web, WebResourceRequest request) {
                return !local(request.getUrl());
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView web, WebResourceRequest request) {
                return AlbumResponse.serve(active, request);
            }
            @Override public void onPageStarted(WebView web, String url, android.graphics.Bitmap icon) {
                mic.stop();
                askingMic = false;
                bars(isPlayer(url));
            }
            @Override public void onPageFinished(WebView web, String url) {
                if (HOME.equals(url)) {
                    applyAvailable();
                    checkUpdate();
                }
            }
        });
        canvas.addView(view, new FrameLayout.LayoutParams(-1, -1));
        setContentView(canvas);
        view.loadUrl(HOME);
    }

    private void checkUpdate() {
        if (view == null || !HOME.equals(view.getUrl()) || checking || !visible || leaving) return;
        long now = android.os.SystemClock.elapsedRealtime();
        if (lastCheck != 0 && now - lastCheck < 12000) return;
        lastCheck = now;
        checking = true;
        updater.execute(new Runnable() {
            @Override public void run() {
                try {
                    byte[] fresh = GitHubRelease.catalog(GitHubRelease.LATEST + "?v=" + System.currentTimeMillis() / 60000, AlbumCatalog.MAX_BUNDLE);
                    final AlbumCatalog next = AlbumCatalog.load(fresh, key);
                    if (next.version > active.version) {
                        FileOutputStream out = cached.startWrite();
                        try {
                            out.write(fresh);
                            cached.finishWrite(out);
                        } catch (Exception error) {
                            cached.failWrite(out);
                            throw error;
                        }
                    }
                    runOnUiThread(new Runnable() {
                        @Override public void run() {
                            checking = false;
                            if (leaving) return;
                            if (next.version > active.version) available = next;
                            if (view != null && HOME.equals(view.getUrl())) applyAvailable();
                        }
                    });
                } catch (Exception error) {
                    runOnUiThread(new Runnable() {
                        @Override public void run() {
                            checking = false;
                            if (view != null && HOME.equals(view.getUrl())) {
                                String status = JSONObject.quote("연결되면 사진첩을 업데이트해요.");
                                js("window.dispatchEvent(new CustomEvent('album-update',{detail:{message:" + status + "}}))");
                            }
                        }
                    });
                }
            }
        });
    }

    private void applyAvailable() {
        if (available != null && available.version > active.version) {
            active = available;
            available = null;
            if (view != null) view.loadUrl(HOME);
        }
    }

    private static boolean isPlayer(String url) {
        return url != null && url.startsWith(BASE + "episodes/") && url.endsWith("/index.html");
    }

    private boolean onPlayer() { return view != null && isPlayer(view.getUrl()); }

    private void bars(boolean player) {
        if (canvas == null) return;
        boolean immersive = player && getResources().getConfiguration().orientation
                == Configuration.ORIENTATION_LANDSCAPE;
        if (Build.VERSION.SDK_INT >= 30) {
            WindowInsetsController controller = getWindow().getInsetsController();
            if (controller != null) {
                if (immersive) {
                    controller.setSystemBarsBehavior(WindowInsetsController.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE);
                    controller.hide(WindowInsets.Type.systemBars());
                } else {
                    controller.show(WindowInsets.Type.systemBars());
                }
            }
        } else {
            getWindow().getDecorView().setSystemUiVisibility(immersive
                    ? View.SYSTEM_UI_FLAG_FULLSCREEN | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                        | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY : 0);
        }
        canvas.requestApplyInsets();
    }

    @Override public void onConfigurationChanged(Configuration configuration) {
        super.onConfigurationChanged(configuration);
        bars(onPlayer());
    }

    boolean canCapture() {
        return visible && !leaving && onPlayer() && granted();
    }

    private boolean granted() {
        return checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED;
    }

    void authorizeMicrophone() {
        if (!visible || !onPlayer()) { micEvent("permission-denied", 0); return; }
        if (granted()) { micEvent("permission-granted", 0); return; }
        if (!askingMic) {
            askingMic = true;
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, MIC_PERMISSION);
        }
    }

    @Override public void onRequestPermissionsResult(int code, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(code, permissions, results);
        if (code == MIC_PERMISSION && askingMic) {
            askingMic = false;
            if (onPlayer()) micEvent(granted() ? "permission-granted" : "permission-denied", 0);
        }
    }

    void micEvent(String type, int token) {
        if (onPlayer()) js("document.dispatchEvent(new CustomEvent('native-mic',{detail:{type:"
                + JSONObject.quote(type) + ",token:" + token + "}}))");
    }

    private void js(String code) { if (view != null) view.evaluateJavascript(code, null); }

    @Override protected void onResume() {
        super.onResume();
        visible = true;
        if (view != null) view.onResume();
        bars(onPlayer());
        js("window.dispatchEvent(new Event('app-resumed'))");
        checkUpdate();
    }

    @Override protected void onPause() {
        visible = false;
        if (mic != null) mic.stop();
        js("window.dispatchEvent(new Event('app-paused'))");
        if (view != null) view.onPause();
        super.onPause();
    }

    @Override @Deprecated public void onBackPressed() {
        if (onPlayer()) view.loadUrl(HOME);
        else super.onBackPressed();
    }

    @Override protected void onDestroy() {
        leaving = true;
        updater.shutdownNow();
        if (mic != null) mic.close();
        if (view != null) {
            view.stopLoading();
            canvas.removeView(view);
            view.destroy();
            view = null;
        }
        super.onDestroy();
    }
}
