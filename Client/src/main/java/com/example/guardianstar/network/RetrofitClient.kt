package com.example.guardianstar.network

import android.content.Context
import com.example.guardianstar.utils.ServerConfig
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

object RetrofitClient {
    private var retrofit: Retrofit? = null
    private var currentBaseUrl: String? = null

    private val okHttpClient = OkHttpClient.Builder()
        .addInterceptor(HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        })
        .build()

    // Build Retrofit dynamically so server URL changes in app settings are applied immediately.
    fun getApi(context: Context): LocationApi {
        val url = ServerConfig.getBaseUrl(context)

        synchronized(this) {
            if (retrofit == null || currentBaseUrl != url) {
                currentBaseUrl = url
                retrofit = Retrofit.Builder()
                    .baseUrl(url)
                    .client(okHttpClient)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build()
            }
        }
        return retrofit!!.create(LocationApi::class.java)
    }
}
