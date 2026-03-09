package com.example.guardianstar.network

import retrofit2.Call
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

data class LocationData(
    val latitude: Double,
    val longitude: Double,
    val timestamp: Long,
    val deviceId: String
)

data class AlertData(
    val type: String,
    val timestamp: Long,
    val deviceId: String
)

data class SafeZoneState(
    val active: Boolean,
    val deviceId: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    val radius: Float? = null,
    val updatedAt: Long? = null
)

interface LocationApi {
    @POST("/api/location")
    fun sendLocation(@Body location: LocationData): Call<Void>

    @POST("/api/alert")
    fun sendAlert(@Body alert: AlertData): Call<Void>

    @GET("/api/safe-zone")
    fun getSafeZone(@Query("deviceId") deviceId: String): Call<SafeZoneState>
}
