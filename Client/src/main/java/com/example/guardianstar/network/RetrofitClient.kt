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

    // 动态获取 API 实例
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
    
    // 为了兼容之前的代码，提供一个基于默认 Context 的访问方式是不太安全的
    // 我们将修改调用处，重新传 Context
}
