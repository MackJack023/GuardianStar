package com.example.guardianstar.manager

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.google.android.gms.location.Geofence
import com.google.android.gms.location.GeofencingEvent

class GeofenceBroadcastReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        val geofencingEvent = GeofencingEvent.fromIntent(intent) ?: return
        
        if (geofencingEvent.hasError()) {
            Log.e("Geofence", "Error: ${geofencingEvent.errorCode}")
            return
        }

        val geofenceTransition = geofencingEvent.geofenceTransition
        if (geofenceTransition == Geofence.GEOFENCE_TRANSITION_ENTER ||
            geofenceTransition == Geofence.GEOFENCE_TRANSITION_EXIT) {
            
            val triggeringGeofences = geofencingEvent.triggeringGeofences
            triggeringGeofences?.forEach {
                Log.i("Geofence", "Transition: $geofenceTransition, ID: ${it.requestId}")
                
                val type = if (geofenceTransition == Geofence.GEOFENCE_TRANSITION_ENTER) "ENTER" else "EXIT"
                val deviceId = android.provider.Settings.Secure.getString(context.contentResolver, android.provider.Settings.Secure.ANDROID_ID) ?: "unknown"
                
                val alert = com.example.guardianstar.network.AlertData(
                    type = type,
                    timestamp = System.currentTimeMillis(),
                    deviceId = deviceId
                )
                
                com.example.guardianstar.network.RetrofitClient.getApi(context).sendAlert(alert).enqueue(object : retrofit2.Callback<Void> {
                    override fun onResponse(call: retrofit2.Call<Void>, response: retrofit2.Response<Void>) {
                        Log.d("Geofence", "Alert sent: $type")
                    }
                    override fun onFailure(call: retrofit2.Call<Void>, t: Throwable) {
                        Log.e("Geofence", "Failed to send alert: ${t.message}")
                    }
                })
            }
        }
    }
}
