package com.example.guardianstar.monitor.push

import android.Manifest
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.example.guardianstar.monitor.network.AlertData

object AlertNotificationHelper {
    private const val CHANNEL_ID = "guardian_monitor_alerts"

    fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return
        }
        val manager = context.getSystemService(NotificationManager::class.java)
        if (manager.getNotificationChannel(CHANNEL_ID) != null) {
            return
        }
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Guardian alerts",
            NotificationManager.IMPORTANCE_HIGH
        ).apply {
            description = "Real-time safe-zone alerts from GuardianStar backend"
        }
        manager.createNotificationChannel(channel)
    }

    fun showAlertNotification(context: Context, alert: AlertData) {
        if (
            Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) {
            return
        }

        val isExit = alert.type.equals("EXIT", ignoreCase = true)
        val title = if (isExit) "Safe-zone alert" else "Safe-zone update"
        val message = if (isExit) {
            "Device ${alert.deviceId.takeLast(6).uppercase()} left the safe zone"
        } else {
            "Device ${alert.deviceId.takeLast(6).uppercase()} entered the safe zone"
        }

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_dialog_alert)
            .setContentTitle(title)
            .setContentText(message)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .build()

        NotificationManagerCompat.from(context)
            .notify(alert.timestamp.toInt(), notification)
    }
}
