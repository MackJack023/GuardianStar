package com.example.guardianstar.monitor.network

import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

data class DeviceSummary(
    val deviceId: String,
    val lastUpdatedAt: Long? = null,
    val lastUpdatedText: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    val safeZoneActive: Boolean = false
)

data class LocationData(
    val latitude: Double,
    val longitude: Double,
    val timestamp: Long,
    val deviceId: String,
    val time_str: String? = null
)

data class AlertData(
    val type: String,
    val timestamp: Long,
    val deviceId: String,
    val time_str: String? = null
)

data class SafeZoneRequest(
    val deviceId: String,
    val latitude: Double,
    val longitude: Double,
    val radius: Float
)

data class SafeZoneState(
    val active: Boolean,
    val deviceId: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    val radius: Float? = null,
    val updatedAt: Long? = null
)

interface MonitorApi {
    @GET("/api/devices")
    fun getDevices(): Call<List<DeviceSummary>>

    @GET("/api/latest")
    fun getLatestLocation(@Query("deviceId") deviceId: String? = null): Call<LocationData>

    @GET("/api/alerts")
    fun getAlerts(@Query("deviceId") deviceId: String? = null): Call<List<AlertData>>

    @GET("/api/history")
    fun getHistory(@Query("deviceId") deviceId: String? = null): Call<List<LocationData>>

    @GET("/api/safe-zone")
    fun getSafeZone(@Query("deviceId") deviceId: String? = null): Call<SafeZoneState>

    @POST("/api/safe-zone")
    fun setSafeZone(@Body request: SafeZoneRequest): Call<SafeZoneState>

    @DELETE("/api/safe-zone")
    fun clearSafeZone(@Query("deviceId") deviceId: String): Call<SafeZoneState>
}
