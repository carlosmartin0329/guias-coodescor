# Reglas ProGuard del APK de Guías Coodescor.
# El APK es un contenedor WebView: solo se conservan las clases que Android
# instancia por reflexión desde el manifiesto.
-keep class com.coodescor.guias.MainApp { *; }
-keep class com.coodescor.guias.MainActivity { *; }
-keepclassmembers class * extends android.webkit.WebViewClient { *; }
-keepclassmembers class * extends android.webkit.WebChromeClient { *; }
-dontwarn android.webkit.**
