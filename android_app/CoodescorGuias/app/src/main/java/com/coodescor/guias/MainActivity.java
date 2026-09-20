package com.coodescor.guias;

import android.Manifest;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.provider.MediaStore;
import android.graphics.Bitmap;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.provider.Settings;
import android.text.InputType;
import android.util.Log;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.view.inputmethod.EditorInfo;
import android.view.inputmethod.InputMethodManager;
import android.webkit.ConsoleMessage;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.google.android.material.floatingactionbutton.FloatingActionButton;

/**
 * Actividad principal que muestra el WebView con la aplicación Guías Coodescor.
 * Soporta:
 * - Navegación completa en la app web
 * - Carga de imágenes desde la cámara/galería
 * - Detección de conexión a Internet
 * - Configuración de la IP del servidor
 */
public class MainActivity extends AppCompatActivity {
    
    private static final String TAG = "CoodescorGuias";
    private static final int REQUEST_CODE_CAMERA = 1001;
    private static final int REQUEST_CODE_STORAGE = 1002;
    private static final int FILE_CHOOSER_RESULT_CODE = 1003;
    
    private WebView webView;
    private ProgressBar progressBar;
    private LinearLayout noConnectionBanner;
    private LinearLayout setupDialog;
    private FloatingActionButton fabRefresh;
    
    private ValueCallback<Uri[]> uploadMessage;
    private Handler handler = new Handler();
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);
        
        // Configurar vistas
        initViews();
        
        // Verificar permisos
        checkPermissions();
        
        // Configurar WebView
        initWebView();
        
        // Configurar botones
        setupButtons();
        
        // Registrar receptor de cambios de red
        registerNetworkCallback();
    }
    
    @SuppressLint("SetJavaScriptEnabled")
    private void initViews() {
        webView = findViewById(R.id.webView);
        progressBar = findViewById(R.id.progressBar);
        noConnectionBanner = findViewById(R.id.noConnectionBanner);
        setupDialog = findViewById(R.id.setupDialog);
        fabRefresh = findViewById(R.id.fabRefresh);
        
        // Configurar WebView
        WebSettings webSettings = webView.getSettings();
        webSettings.setJavaScriptEnabled(true);
        webSettings.setDomStorageEnabled(true);
        webSettings.setDatabaseEnabled(true);
        webSettings.setAllowFileAccess(true);
        webSettings.setAllowContentAccess(true);
        webSettings.setLoadWithOverviewMode(true);
        webSettings.setUseWideViewPort(true);
        webSettings.setBuiltInZoomControls(true);
        webSettings.setDisplayZoomControls(false);
        webSettings.setSupportZoom(true);
        webSettings.setDefaultTextEncodingName("utf-8");
        
        // Para Android 5.0+
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
            webSettings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);
        }
        
        // Habiltar cache
        webSettings.setCacheMode(WebSettings.LOAD_CACHE_ELSE_NETWORK);
        webSettings.setAppCacheEnabled(true);
        
        // Configurar user agent para identificar dispositivos móviles
        String userAgent = webSettings.getUserAgentString();
        userAgent = userAgent + " CoodescorGuias/Android";
        webSettings.setUserAgentString(userAgent);
    }
    
    private void initWebView() {
        // Verificar si hay configuración de servidor
        if (!MainApp.hasServerConfig()) {
            showSetupDialog();
            return;
        }
        
        // Cargar URL
        loadWebUrl();
        
        // Configurar WebViewClient
        webView.setWebViewClient(new CoodescorWebViewClient());
        
        // Configurar WebChromeClient para manejo de archivos
        webView.setWebChromeClient(new CoodescorWebChromeClient());
    }
    
    private void loadWebUrl() {
        String url = MainApp.getServerUrl();
        Log.d(TAG, "Cargando URL: " + url);
        webView.loadUrl(url);
    }
    
    private void setupButtons() {
        // Botón Reintentar en banner de conexión
        Button btnRetry = findViewById(R.id.btnRetry);
        btnRetry.setOnClickListener(v -> {
            if (isNetworkAvailable()) {
                noConnectionBanner.setVisibility(View.GONE);
                loadWebUrl();
            } else {
                Toast.makeText(this, "Aún no hay conexión", Toast.LENGTH_SHORT).show();
            }
        });
        
        // Botón Guardar en diálogo de configuración
        Button btnSave = findViewById(R.id.btnSave);
        btnSave.setOnClickListener(v -> {
            EditText etServerIp = findViewById(R.id.etServerIp);
            String ip = etServerIp.getText().toString().trim();
            
            if (ip.isEmpty()) {
                Toast.makeText(this, "Por favor ingrese la IP", Toast.LENGTH_SHORT).show();
                return;
            }
            
            // Validar formato IP (simple)
            if (!isValidIp(ip)) {
                Toast.makeText(this, "Formato de IP inválido", Toast.LENGTH_SHORT).show();
                return;
            }
            
            // Guardar configuración
            MainApp.saveServerConfig(ip, "8000");
            setupDialog.setVisibility(View.GONE);
            loadWebUrl();
        });
        
        // Botón Cancelar en diálogo de configuración
        Button btnCancel = findViewById(R.id.btnCancel);
        btnCancel.setOnClickListener(v -> {
            setupDialog.setVisibility(View.GONE);
            finishAffinity();
        });
        
        // FAB Refrescar
        fabRefresh.setOnClickListener(v -> {
            if (isNetworkAvailable()) {
                webView.reload();
            } else {
                Toast.makeText(this, "Sin conexión", Toast.LENGTH_SHORT).show();
            }
        });
    }
    
    private void showSetupDialog() {
        setupDialog.setVisibility(View.VISIBLE);
        EditText etServerIp = findViewById(R.id.etServerIp);
        etServerIp.requestFocus();
        
        // Mostrar teclado
        InputMethodManager imm = (InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE);
        if (imm != null) {
            imm.showSoftInput(etServerIp, InputMethodManager.SHOW_IMPLICIT);
        }
        
        // Configurar accion al presionar Done en el teclado
        etServerIp.setOnEditorActionListener((v, actionId, event) -> {
            if (actionId == EditorInfo.IME_ACTION_DONE || 
                (event != null && event.getKeyCode() == KeyEvent.KEYCODE_ENTER)) {
                Button btnSave = findViewById(R.id.btnSave);
                btnSave.performClick();
                return true;
            }
            return false;
        });
    }
    
    private boolean isValidIp(String ip) {
        // Validación simple de IP
        String[] parts = ip.split("\\.");
        if (parts.length != 4) return false;
        
        for (String part : parts) {
            try {
                int num = Integer.parseInt(part);
                if (num < 0 || num > 255) return false;
            } catch (NumberFormatException e) {
                return false;
            }
        }
        return true;
    }
    
    private void checkPermissions() {
        String[] requiredPermissions = {
                Manifest.permission.INTERNET,
                Manifest.permission.CAMERA,
                Manifest.permission.READ_EXTERNAL_STORAGE,
                Manifest.permission.WRITE_EXTERNAL_STORAGE
        };
        
        boolean allGranted = true;
        for (String permission : requiredPermissions) {
            if (ContextCompat.checkSelfPermission(this, permission) 
                    != PackageManager.PERMISSION_GRANTED) {
                allGranted = false;
                break;
            }
        }
        
        if (!allGranted) {
            ActivityCompat.requestPermissions(
                    this,
                    requiredPermissions,
                    REQUEST_CODE_STORAGE
            );
        }
    }
    
    private boolean isNetworkAvailable() {
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        if (cm == null) return false;
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            NetworkCapabilities capabilities = cm.getNetworkCapabilities(cm.getActiveNetwork());
            return capabilities != null && 
                   (capabilities.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
                    capabilities.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) ||
                    capabilities.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET));
        } else {
            Network activeNetwork = cm.getActiveNetworkInfo();
            return activeNetwork != null && activeNetwork.isConnected();
        }
    }
    
    private void registerNetworkCallback() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) return;
            
            NetworkRequest request = new NetworkRequest.Builder()
                    .addTransportType(NetworkCapabilities.TRANSPORT_WIFI)
                    .addTransportType(NetworkCapabilities.TRANSPORT_CELLULAR)
                    .addTransportType(NetworkCapabilities.TRANSPORT_ETHERNET)
                    .build();
            
            cm.registerNetworkCallback(request, new ConnectivityManager.NetworkCallback() {
                @Override
                public void onAvailable(@NonNull Network network) {
                    runOnUiThread(() -> {
                        noConnectionBanner.setVisibility(View.GONE);
                        fabRefresh.setVisibility(View.GONE);
                    });
                }
                
                @Override
                public void onLost(@NonNull Network network) {
                    runOnUiThread(() -> {
                        noConnectionBanner.setVisibility(View.VISIBLE);
                        fabRefresh.setVisibility(View.VISIBLE);
                    });
                }
            });
        }
    }
    
    private class CoodescorWebViewClient extends WebViewClient {
        @Override
        public boolean shouldOverrideUrlLoading(WebView view, String url) {
            // Abrir links externos en el navegador
            if (url != null && (url.startsWith("http://") || url.startsWith("https://"))) {
                // Si es del mismo dominio, cargar en WebView
                if (url.contains(MainApp.getServerIp())) {
                    return false;
                }
                // De lo contrario, abrir en navegador
                Intent intent = new Intent(Intent.ACTION_VIEW, Uri.parse(url));
                startActivity(intent);
                return true;
            }
            return false;
        }
        
        @Override
        public void onPageStarted(WebView view, String url, Bitmap favicon) {
            super.onPageStarted(view, url, favicon);
            progressBar.setVisibility(View.VISIBLE);
            progressBar.setProgress(0);
        }
        
        @Override
        public void onPageFinished(WebView view, String url) {
            super.onPageFinished(view, url);
            progressBar.setVisibility(View.GONE);
            
            // Verificar si hay error de conexión
            if (!isNetworkAvailable()) {
                noConnectionBanner.setVisibility(View.VISIBLE);
            }
        }
        
        @Override
        public void onReceivedError(WebView view, int errorCode, String description, String failingUrl) {
            super.onReceivedError(view, errorCode, description, failingUrl);
            if (errorCode == ERROR_HOST_LOOKUP || errorCode == ERROR_TIMEOUT || 
                errorCode == ERROR_CONNECT) {
                noConnectionBanner.setVisibility(View.VISIBLE);
                fabRefresh.setVisibility(View.VISIBLE);
            }
        }
        
        @Override
        public void onReceivedHttpError(WebView view, int errorCode, String description, String failingUrl) {
            super.onReceivedHttpError(view, errorCode, description, failingUrl);
            if (errorCode == 404 || errorCode == 500) {
                // Mostrar mensaje de error
                Toast.makeText(MainActivity.this, "Error: " + errorCode, Toast.LENGTH_SHORT).show();
            }
        }
    }
    
    private class CoodescorWebChromeClient extends WebChromeClient {
        @Override
        public boolean onShowFileChooser(WebView webView, ValueCallback<Uri[]> filePathCallback, 
                                         FileChooserParams fileChooserParams) {
            uploadMessage = filePathCallback;
            
            Intent takePictureIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
            if (takePictureIntent.resolveActivity(getPackageManager()) != null) {
                // Intent para tomar foto
                Intent chooserIntent = new Intent(Intent.ACTION_CHOOSER);
                chooserIntent.putExtra(Intent.EXTRA_INTENT, takePictureIntent);
                chooserIntent.putExtra(Intent.EXTRA_TITLE, "Seleccionar imagen");
                
                Intent pickIntent = new Intent(Intent.ACTION_GET_CONTENT);
                pickIntent.setType("image/*");
                
                Intent[] intentArray;
                if (takePictureIntent != null) {
                    intentArray = new Intent[]{takePictureIntent};
                } else {
                    intentArray = new Intent[0];
                }
                
                chooserIntent.putExtra(Intent.EXTRA_INITIAL_INTENTS, intentArray);
                startActivityForResult(chooserIntent, FILE_CHOOSER_RESULT_CODE);
            } else {
                // Solo selector de archivos
                Intent pickIntent = new Intent(Intent.ACTION_GET_CONTENT);
                pickIntent.setType("image/*");
                startActivityForResult(pickIntent, FILE_CHOOSER_RESULT_CODE);
            }
            
            return true;
        }
        
        @Override
        public void onPermissionRequest(PermissionRequest request) {
            // Solicitar permisos para la cámara desde WebView
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
                request.grant(request.getResources());
            }
        }
        
        @Override
        public boolean onConsoleMessage(ConsoleMessage consoleMessage) {
            // Log de mensajes de consola del WebView
            Log.d(TAG, "JS Console: " + consoleMessage.message());
            return super.onConsoleMessage(consoleMessage);
        }
        
        @Override
        public void onProgressChanged(WebView view, int newProgress) {
            super.onProgressChanged(view, newProgress);
            progressBar.setProgress(newProgress);
            if (newProgress >= 100) {
                progressBar.setVisibility(View.GONE);
            }
        }
    }
    
    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        
        if (requestCode == FILE_CHOOSER_RESULT_CODE) {
            if (uploadMessage == null) return;
            
            if (resultCode == RESULT_OK) {
                if (data == null || data.getData() == null) {
                    uploadMessage.onReceiveValue(null);
                } else {
                    Uri[] results = new Uri[]{data.getData()};
                    uploadMessage.onReceiveValue(results);
                }
            } else {
                uploadMessage.onReceiveValue(null);
            }
            uploadMessage = null;
        }
    }
    
    @Override
    public void onRequestPermissionsResult(int requestCode, @NonNull String[] permissions, 
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_CODE_CAMERA || requestCode == REQUEST_CODE_STORAGE) {
            boolean allGranted = true;
            for (int result : grantResults) {
                if (result != PackageManager.PERMISSION_GRANTED) {
                    allGranted = false;
                    break;
                }
            }
            if (allGranted) {
                Toast.makeText(this, "Permisos concedidos", Toast.LENGTH_SHORT).show();
                loadWebUrl();
            } else {
                Toast.makeText(this, "Se necesitan permisos para usar la cámara", Toast.LENGTH_SHORT).show();
            }
        }
    }
    
    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        // Manejar botón Back
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }
    
    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (webView != null) {
            webView.destroy();
        }
    }
    
    @Override
    protected void onPause() {
        super.onPause();
        if (webView != null) {
            webView.onPause();
        }
    }
    
    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) {
            webView.onResume();
        }
        
        // Verificar conexión al reanudar
        if (!isNetworkAvailable()) {
            noConnectionBanner.setVisibility(View.VISIBLE);
        }
    }
}
