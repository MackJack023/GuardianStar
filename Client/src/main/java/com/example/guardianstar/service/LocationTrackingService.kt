package com.example.guardianstar.service

import android.annotation.SuppressLint
import android.app.Notification
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.location.Location
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.provider.Settings
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import com.example.guardianstar.R
import com.example.guardianstar.manager.GeofenceManager
import com.example.guardianstar.network.LocationData
import com.example.guardianstar.network.RetrofitClient
import com.example.guardianstar.network.SafeZoneState
import com.google.android.gms.location.FusedLocationProviderClient
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response

class LocationTrackingService : Service() {

    companion object {
        private val _locationFlow = MutableStateFlow<Location?>(null)
        val locationFlow: StateFlow<Location?> = _locationFlow.asStateFlow()

        private val _connectionError = MutableStateFlow<String?>(null)
        val connectionError: StateFlow<String?> = _connectionError.asStateFlow()

        private val _serviceRunning = MutableStateFlow(false)
        val serviceRunning: StateFlow<Boolean> = _serviceRunning.asStateFlow()

        private const val NOTIFICATION_ID = 1

        fun updateConnectionError(error: String?) {
            _connectionError.value = error
        }
    }

    private lateinit var fusedLocationClient: FusedLocationProviderClient
    private lateinit var locationCallback: LocationCallback
    private lateinit var geofenceManager: GeofenceManager
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var appliedSafeZoneSignature: String? = null
    private val deviceId: String by lazy {
        Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID) ?: "unknown_device"
    }

    override fun onCreate() {
        super.onCreate()
        _serviceRunning.value = true
        fusedLocationClient = LocationServices.getFusedLocationProviderClient(this)
        geofenceManager = GeofenceManager(this)

        locationCallback = object : LocationCallback() {
            override fun onLocationResult(locationResult: LocationResult) {
                locationResult.lastLocation?.let { location ->
                    Log.d("GuardianStar", "Location: ${location.latitude}, ${location.longitude}")
                    _locationFlow.value = location
                    uploadLocation(location)
                }
            }
        }

        ServiceCompat.startForeground(this, NOTIFICATION_ID, createNotification(), foregroundType())
        startLocationUpdates()
        startSafeZoneSync()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        _serviceRunning.value = true
        ServiceCompat.startForeground(this, NOTIFICATION_ID, createNotification(), foregroundType())
        return START_STICKY
    }

    private fun foregroundType(): Int {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION
        } else {
            0
        }
    }

    @SuppressLint("HardwareIds")
    private fun uploadLocation(location: Location) {
        serviceScope.launch {
            val locationData = LocationData(
                latitude = location.latitude,
                longitude = location.longitude,
                timestamp = System.currentTimeMillis(),
                deviceId = deviceId
            )

            try {
                RetrofitClient.getApi(this@LocationTrackingService)
                    .sendLocation(locationData)
                    .enqueue(object : Callback<Void> {
                        override fun onResponse(call: Call<Void>, response: Response<Void>) {
                            if (response.isSuccessful) {
                                updateConnectionError(null)
                            } else {
                                updateConnectionError("Upload failed: ${response.code()}")
                            }
                        }

                        override fun onFailure(call: Call<Void>, t: Throwable) {
                            updateConnectionError("Upload error: ${t.message}")
                        }
                    })
            } catch (error: Exception) {
                updateConnectionError("Retrofit error: ${error.message}")
            }
        }
    }

    private fun startSafeZoneSync() {
        serviceScope.launch {
            syncSafeZone()
            while (isActive) {
                delay(30_000)
                syncSafeZone()
            }
        }
    }

    private fun syncSafeZone() {
        try {
            RetrofitClient.getApi(this)
                .getSafeZone(deviceId)
                .enqueue(object : Callback<SafeZoneState> {
                    override fun onResponse(
                        call: Call<SafeZoneState>,
                        response: Response<SafeZoneState>
                    ) {
                        if (!response.isSuccessful) {
                            return
                        }

                        val safeZone = response.body() ?: SafeZoneState(active = false)
                        applySafeZone(safeZone)
                    }

                    override fun onFailure(call: Call<SafeZoneState>, t: Throwable) {
                        Log.w("GuardianStar", "Safe zone sync failed: ${t.message}")
                    }
                })
        } catch (error: Exception) {
            Log.w("GuardianStar", "Safe zone sync error", error)
        }
    }

    private fun applySafeZone(safeZone: SafeZoneState) {
        val latitude = safeZone.latitude
        val longitude = safeZone.longitude
        val radius = safeZone.radius

        if (!safeZone.active || latitude == null || longitude == null || radius == null) {
            if (appliedSafeZoneSignature != null) {
                geofenceManager.removeSafeZone()
                appliedSafeZoneSignature = null
            }
            return
        }

        val newSignature = "$latitude,$longitude,$radius"
        if (newSignature == appliedSafeZoneSignature) {
            return
        }

        geofenceManager.updateSafeZone(latitude, longitude, radius)
        appliedSafeZoneSignature = newSignature
    }

    private fun startLocationUpdates() {
        val locationRequest = LocationRequest.Builder(
            Priority.PRIORITY_BALANCED_POWER_ACCURACY,
            600_000
        )
            .setMinUpdateDistanceMeters(50f)
            .setWaitForAccurateLocation(false)
            .build()

        try {
            fusedLocationClient.requestLocationUpdates(
                locationRequest,
                locationCallback,
                Looper.getMainLooper()
            )
        } catch (error: SecurityException) {
            Log.e("GuardianStar", "Permission lost: ${error.message}")
        }
    }

    private fun createNotification(): Notification {
        val channelId = "child_safety_channel"
        val notificationManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        if (notificationManager.getNotificationChannel(channelId) == null) {
            val channel = android.app.NotificationChannel(
                channelId,
                getString(R.string.notification_channel_name),
                NotificationManager.IMPORTANCE_LOW
            )
            channel.description = getString(R.string.notification_channel_desc)
            notificationManager.createNotificationChannel(channel)
        }

        return NotificationCompat.Builder(this, channelId)
            .setContentTitle(getString(R.string.service_running))
            .setContentText(getString(R.string.service_desc))
            .setSmallIcon(android.R.drawable.ic_menu_mylocation)
            .setOngoing(true)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        super.onDestroy()
        _serviceRunning.value = false
        _locationFlow.value = null
        geofenceManager.removeSafeZone()
        appliedSafeZoneSignature = null
        try {
            fusedLocationClient.removeLocationUpdates(locationCallback)
        } catch (error: Exception) {
            Log.e("GuardianStar", "Error removing location updates", error)
        }
        serviceScope.cancel()
    }
}
