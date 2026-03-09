package com.example.guardianstar.manager

import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.util.Log
import com.google.android.gms.location.Geofence
import com.google.android.gms.location.GeofencingRequest
import com.google.android.gms.location.LocationServices

class GeofenceManager(private val context: Context) {
    companion object {
        const val SAFE_ZONE_ID = "server_safe_zone"
    }

    private val geofencingClient = LocationServices.getGeofencingClient(context)

    private val geofencePendingIntent: PendingIntent by lazy {
        PendingIntent.getBroadcast(
            context,
            0,
            Intent(context, GeofenceBroadcastReceiver::class.java),
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }

    fun updateSafeZone(latitude: Double, longitude: Double, radius: Float) {
        removeSafeZone()
        addSafeZone(latitude, longitude, radius)
    }

    fun removeSafeZone() {
        geofencingClient.removeGeofences(geofencePendingIntent)
            .addOnFailureListener { error ->
                Log.w("Geofence", "Failed to remove safe zone: ${error.message}")
            }
    }

    private fun addSafeZone(latitude: Double, longitude: Double, radius: Float) {
        val geofence = Geofence.Builder()
            .setRequestId(SAFE_ZONE_ID)
            .setCircularRegion(latitude, longitude, radius)
            .setExpirationDuration(Geofence.NEVER_EXPIRE)
            .setTransitionTypes(
                Geofence.GEOFENCE_TRANSITION_ENTER or Geofence.GEOFENCE_TRANSITION_EXIT
            )
            .build()

        val request = GeofencingRequest.Builder()
            .setInitialTrigger(GeofencingRequest.INITIAL_TRIGGER_ENTER)
            .addGeofence(geofence)
            .build()

        try {
            geofencingClient.addGeofences(request, geofencePendingIntent)
                .addOnFailureListener { error ->
                    Log.e("Geofence", "Failed to add safe zone: ${error.message}")
                }
        } catch (error: SecurityException) {
            Log.e("Geofence", "Location permission missing for geofence", error)
        }
    }
}
