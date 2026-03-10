package com.example.guardianstar.monitor.push

import android.os.Handler
import android.os.Looper
import android.util.Log
import com.example.guardianstar.monitor.network.AlertData
import com.google.gson.Gson
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import java.util.concurrent.TimeUnit

class AlertPushClient(
    private val baseUrl: String,
    private val onAlert: (AlertData) -> Unit,
    private val onConnectionChanged: (Boolean) -> Unit,
) {
    private val gson = Gson()
    private val handler = Handler(Looper.getMainLooper())
    private val client = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private var stopped = false
    private var reconnectAttempts = 0
    private var subscribedDeviceId: String? = null

    fun start(deviceId: String? = null) {
        subscribedDeviceId = deviceId
        stopped = false
        connect()
    }

    fun updateDevice(deviceId: String?) {
        if (subscribedDeviceId == deviceId) {
            return
        }
        subscribedDeviceId = deviceId
        reconnectNow()
    }

    fun stop() {
        stopped = true
        handler.removeCallbacksAndMessages(null)
        webSocket?.close(1000, "client-stop")
        webSocket = null
        handler.post { onConnectionChanged(false) }
    }

    private fun reconnectNow() {
        webSocket?.cancel()
        webSocket = null
        reconnectAttempts = 0
        connect()
    }

    private fun connect() {
        if (stopped) {
            return
        }
        val request = Request.Builder()
            .url(buildWebSocketUrl())
            .build()
        webSocket = client.newWebSocket(request, socketListener)
    }

    private fun scheduleReconnect() {
        if (stopped) {
            return
        }
        reconnectAttempts += 1
        val delayMs = (1_000L * reconnectAttempts.coerceAtMost(10))
        handler.postDelayed({ connect() }, delayMs)
    }

    private fun buildWebSocketUrl(): String {
        val normalized = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        val wsBase = when {
            normalized.startsWith("https://") -> "wss://${normalized.removePrefix("https://")}"
            normalized.startsWith("http://") -> "ws://${normalized.removePrefix("http://")}"
            normalized.startsWith("wss://") || normalized.startsWith("ws://") -> normalized
            else -> "ws://$normalized"
        }
        val query = subscribedDeviceId?.let { "?deviceId=$it" } ?: ""
        return "${wsBase}api/ws/alerts$query"
    }

    private val socketListener = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            reconnectAttempts = 0
            handler.post { onConnectionChanged(true) }
            Log.i("AlertPushClient", "Connected to alert stream")
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            try {
                val alert = gson.fromJson(text, AlertData::class.java)
                handler.post { onAlert(alert) }
            } catch (error: Exception) {
                Log.w("AlertPushClient", "Failed to parse alert payload", error)
            }
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            handler.post { onConnectionChanged(false) }
            scheduleReconnect()
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            handler.post { onConnectionChanged(false) }
            Log.w("AlertPushClient", "Alert stream disconnected: ${t.message}")
            scheduleReconnect()
        }
    }
}
