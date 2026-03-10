package com.example.guardianstar.utils

import android.content.Context

object ServerConfig {
    private const val PREF_NAME = "server_config"
    private const val KEY_BASE_URL = "base_url"
    private const val DEFAULT_URL = "http://10.0.2.2:8080/"

    fun getBaseUrl(context: Context): String {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        var url = prefs.getString(KEY_BASE_URL, DEFAULT_URL) ?: DEFAULT_URL
        if (!url.endsWith("/")) {
            url += "/"
        }
        return url
    }

    fun setBaseUrl(context: Context, url: String) {
        val prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE)
        prefs.edit().putString(KEY_BASE_URL, url).apply()
    }
}
