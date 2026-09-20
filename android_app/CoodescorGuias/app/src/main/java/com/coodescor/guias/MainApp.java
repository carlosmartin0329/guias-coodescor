package com.coodescor.guias;

import android.app.Application;
import android.content.Context;
import android.content.SharedPreferences;

/**
 * Aplicación principal de Guías Coodescor para Android.
 * Gestiona la configuración global y preferencias.
 */
public class MainApp extends Application {
    
    private static final String PREFS_NAME = "CoodescorGuiasPrefs";
    private static final String KEY_SERVER_IP = "server_ip";
    private static final String KEY_SERVER_PORT = "server_port";
    private static final String DEFAULT_SERVER_IP = "192.168.1.100";
    private static final String DEFAULT_SERVER_PORT = "8000";
    
    private static Context appContext;
    
    @Override
    public void onCreate() {
        super.onCreate();
        appContext = getApplicationContext();
    }
    
    /**
     * Obtiene el contexto de la aplicación
     */
    public static Context getAppContext() {
        return appContext;
    }
    
    /**
     * Guarda la configuración del servidor
     */
    public static void saveServerConfig(String ip, String port) {
        SharedPreferences prefs = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        SharedPreferences.Editor editor = prefs.edit();
        editor.putString(KEY_SERVER_IP, ip);
        editor.putString(KEY_SERVER_PORT, port);
        editor.apply();
    }
    
    /**
     * Obtiene la IP del servidor guardada
     */
    public static String getServerIp() {
        SharedPreferences prefs = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getString(KEY_SERVER_IP, DEFAULT_SERVER_IP);
    }
    
    /**
     * Obtiene el puerto del servidor guardado
     */
    public static String getServerPort() {
        SharedPreferences prefs = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.getString(KEY_SERVER_PORT, DEFAULT_SERVER_PORT);
    }
    
    /**
     * Obtiene la URL base del servidor
     */
    public static String getServerUrl() {
        return "http://" + getServerIp() + ":" + getServerPort();
    }
    
    /**
     * Limpia la configuración guardada
     */
    public static void clearServerConfig() {
        SharedPreferences prefs = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        SharedPreferences.Editor editor = prefs.edit();
        editor.remove(KEY_SERVER_IP);
        editor.remove(KEY_SERVER_PORT);
        editor.apply();
    }
    
    /**
     * Verifica si hay configuración guardada
     */
    public static boolean hasServerConfig() {
        SharedPreferences prefs = appContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE);
        return prefs.contains(KEY_SERVER_IP);
    }
}
