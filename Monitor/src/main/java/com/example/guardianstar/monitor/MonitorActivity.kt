package com.example.guardianstar.monitor

import android.annotation.SuppressLint
import android.os.Bundle
import android.webkit.WebView
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AccessTime
import androidx.compose.material.icons.rounded.AddLocation
import androidx.compose.material.icons.rounded.CheckCircle
import androidx.compose.material.icons.rounded.LocationOn
import androidx.compose.material.icons.rounded.Radar
import androidx.compose.material.icons.rounded.Refresh
import androidx.compose.material.icons.rounded.Smartphone
import androidx.compose.material.icons.rounded.Timeline
import androidx.compose.material.icons.rounded.Warning
import androidx.compose.material.icons.rounded.WrongLocation
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.example.guardianstar.monitor.network.AlertData
import com.example.guardianstar.monitor.network.DeviceSummary
import com.example.guardianstar.monitor.network.LocationData
import com.example.guardianstar.monitor.network.RetrofitClient
import com.example.guardianstar.monitor.network.SafeZoneRequest
import com.example.guardianstar.monitor.network.SafeZoneState
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import retrofit2.Call
import retrofit2.Callback
import retrofit2.Response
import java.text.SimpleDateFormat
import java.util.Locale
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

class MonitorActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MaterialTheme(
                colorScheme = lightColorScheme(
                    primary = Color(0xFF4A90E2),
                    secondary = Color(0xFF50E3C2),
                    background = Color(0xFFF5F7FA),
                    surface = Color.White,
                    onSurface = Color(0xFF2C3E50)
                )
            ) {
                MonitorScreen()
            }
        }
    }
}

@Composable
fun MonitorScreen() {
    val context = LocalContext.current
    val api = RetrofitClient.api
    val scope = rememberCoroutineScope()
    var devices by remember { mutableStateOf<List<DeviceSummary>>(emptyList()) }
    var selectedDeviceId by remember { mutableStateOf<String?>(null) }
    var location by remember { mutableStateOf<LocationData?>(null) }
    var lastUpdateTime by remember { mutableStateOf("Waiting for updates...") }
    var alerts by remember { mutableStateOf<List<AlertData>>(emptyList()) }
    var safeZone by remember { mutableStateOf(SafeZoneState(active = false)) }
    var webView by remember { mutableStateOf<WebView?>(null) }
    var isConnected by remember { mutableStateOf(false) }
    var showHistory by remember { mutableStateOf(true) }
    var isOutOfZone by remember { mutableStateOf(false) }

    fun renderSafeZone(zone: SafeZoneState) {
        val lat = zone.latitude
        val lng = zone.longitude
        val radius = zone.radius
        if (zone.active && lat != null && lng != null && radius != null) {
            webView?.evaluateJavascript("addCircle($lat, $lng, $radius);", null)
        } else {
            webView?.evaluateJavascript("removeCircle();", null)
        }
    }

    fun updateOutOfZone(currentLocation: LocationData?, zone: SafeZoneState) {
        val lat = zone.latitude
        val lng = zone.longitude
        val radius = zone.radius?.toDouble()
        isOutOfZone = if (currentLocation == null || !zone.active || lat == null || lng == null || radius == null) {
            false
        } else {
            calculateDistance(lat, lng, currentLocation.latitude, currentLocation.longitude) > radius
        }
    }

    fun clearData() {
        location = null
        lastUpdateTime = "Waiting for updates..."
        alerts = emptyList()
        safeZone = SafeZoneState(active = false)
        isOutOfZone = false
        isConnected = false
        webView?.evaluateJavascript("clearHistoryPath();", null)
        webView?.evaluateJavascript("removeCircle();", null)
    }

    fun loadDevice(deviceId: String) {
        selectedDeviceId = deviceId

        api.getLatestLocation(deviceId).enqueue(object : Callback<LocationData> {
            override fun onResponse(call: Call<LocationData>, response: Response<LocationData>) {
                if (response.isSuccessful && response.body() != null) {
                    val current = response.body()!!
                    location = current
                    lastUpdateTime = current.time_str
                        ?: SimpleDateFormat("HH:mm:ss", Locale.getDefault()).format(current.timestamp)
                    isConnected = true
                    webView?.evaluateJavascript("updateLocation(${current.latitude}, ${current.longitude});", null)
                    updateOutOfZone(current, safeZone)
                } else {
                    location = null
                    lastUpdateTime = "No location yet"
                    isConnected = false
                }
            }

            override fun onFailure(call: Call<LocationData>, t: Throwable) {
                isConnected = false
            }
        })

        api.getAlerts(deviceId).enqueue(object : Callback<List<AlertData>> {
            override fun onResponse(call: Call<List<AlertData>>, response: Response<List<AlertData>>) {
                alerts = if (response.isSuccessful && response.body() != null) response.body()!! else emptyList()
            }

            override fun onFailure(call: Call<List<AlertData>>, t: Throwable) {
                alerts = emptyList()
            }
        })

        api.getSafeZone(deviceId).enqueue(object : Callback<SafeZoneState> {
            override fun onResponse(call: Call<SafeZoneState>, response: Response<SafeZoneState>) {
                safeZone = if (response.isSuccessful && response.body() != null) response.body()!! else SafeZoneState(active = false)
                renderSafeZone(safeZone)
                updateOutOfZone(location, safeZone)
            }

            override fun onFailure(call: Call<SafeZoneState>, t: Throwable) {
                safeZone = SafeZoneState(active = false)
                renderSafeZone(safeZone)
            }
        })

        if (showHistory) {
            api.getHistory(deviceId).enqueue(object : Callback<List<LocationData>> {
                override fun onResponse(call: Call<List<LocationData>>, response: Response<List<LocationData>>) {
                    if (response.isSuccessful && response.body() != null) {
                        val pathJson = response.body()!!.joinToString(prefix = "[", postfix = "]") {
                            "[${it.longitude}, ${it.latitude}]"
                        }
                        webView?.evaluateJavascript("drawHistoryPath($pathJson);", null)
                    }
                }

                override fun onFailure(call: Call<List<LocationData>>, t: Throwable) {}
            })
        } else {
            webView?.evaluateJavascript("clearHistoryPath();", null)
        }
    }

    fun refreshAll() {
        api.getDevices().enqueue(object : Callback<List<DeviceSummary>> {
            override fun onResponse(call: Call<List<DeviceSummary>>, response: Response<List<DeviceSummary>>) {
                val result = if (response.isSuccessful && response.body() != null) response.body()!! else emptyList()
                devices = result
                if (result.isEmpty()) {
                    selectedDeviceId = null
                    clearData()
                    return
                }
                val target = if (selectedDeviceId != null && result.any { it.deviceId == selectedDeviceId }) {
                    selectedDeviceId!!
                } else {
                    result.first().deviceId
                }
                loadDevice(target)
            }

            override fun onFailure(call: Call<List<DeviceSummary>>, t: Throwable) {
                devices = emptyList()
                selectedDeviceId = null
                clearData()
            }
        })
    }

    fun saveSafeZone() {
        val deviceId = selectedDeviceId ?: location?.deviceId ?: return
        val current = location ?: return
        api.setSafeZone(SafeZoneRequest(deviceId, current.latitude, current.longitude, 100f))
            .enqueue(object : Callback<SafeZoneState> {
                override fun onResponse(call: Call<SafeZoneState>, response: Response<SafeZoneState>) {
                    if (response.isSuccessful && response.body() != null) {
                        safeZone = response.body()!!
                        renderSafeZone(safeZone)
                        updateOutOfZone(location, safeZone)
                        refreshAll()
                        Toast.makeText(context, "Safe zone saved", Toast.LENGTH_SHORT).show()
                    } else {
                        Toast.makeText(context, "Failed to save safe zone", Toast.LENGTH_SHORT).show()
                    }
                }

                override fun onFailure(call: Call<SafeZoneState>, t: Throwable) {
                    Toast.makeText(context, "Failed to save safe zone", Toast.LENGTH_SHORT).show()
                }
            })
    }

    fun removeSafeZone() {
        val deviceId = selectedDeviceId ?: return
        api.clearSafeZone(deviceId).enqueue(object : Callback<SafeZoneState> {
            override fun onResponse(call: Call<SafeZoneState>, response: Response<SafeZoneState>) {
                safeZone = SafeZoneState(active = false)
                renderSafeZone(safeZone)
                updateOutOfZone(location, safeZone)
                refreshAll()
                Toast.makeText(context, "Safe zone removed", Toast.LENGTH_SHORT).show()
            }

            override fun onFailure(call: Call<SafeZoneState>, t: Throwable) {
                Toast.makeText(context, "Failed to remove safe zone", Toast.LENGTH_SHORT).show()
            }
        })
    }

    LaunchedEffect(Unit) {
        while (true) {
            refreshAll()
            delay(10_000)
        }
    }

    LaunchedEffect(showHistory) {
        selectedDeviceId?.let { loadDevice(it) }
    }

    Scaffold(containerColor = Color(0xFFF5F7FA)) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            TopBar(isConnected = isConnected, onRefresh = { scope.launch { refreshAll() } })
            DeviceStrip(
                devices = devices,
                selectedDeviceId = selectedDeviceId,
                onSelect = { loadDevice(it) },
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            )
            if (isOutOfZone || alerts.isNotEmpty()) {
                AlertBanner(alert = if (isOutOfZone) {
                    AlertData("EXIT", System.currentTimeMillis(), selectedDeviceId ?: "UNKNOWN", "Just now")
                } else {
                    alerts.first()
                })
            }
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(300.dp)
                    .padding(horizontal = 16.dp, vertical = 8.dp)
                    .clip(RoundedCornerShape(16.dp))
                    .background(Color.White)
            ) {
                MapModule(
                    onWebViewCreated = { created ->
                        webView = created
                        location?.let {
                            created.evaluateJavascript("updateLocation(${it.latitude}, ${it.longitude});", null)
                        }
                        renderSafeZone(safeZone)
                    }
                )
                if (location == null) {
                    EmptyStateModule()
                }
                FloatingActionButton(
                    onClick = { showHistory = !showHistory },
                    modifier = Modifier
                        .align(Alignment.TopEnd)
                        .padding(12.dp)
                        .size(40.dp),
                    containerColor = if (showHistory) MaterialTheme.colorScheme.primary else Color.White,
                    contentColor = if (showHistory) Color.White else Color.Gray
                ) {
                    Icon(Icons.Rounded.Timeline, contentDescription = "Toggle history", modifier = Modifier.size(20.dp))
                }
            }
            if (selectedDeviceId != null) {
                SafeZoneActions(
                    isSafeZoneSet = safeZone.active,
                    onSet = { saveSafeZone() },
                    onRemove = { removeSafeZone() },
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
                )
            }
            Spacer(modifier = Modifier.weight(1f))
            DeviceStatusCard(location = location, lastUpdate = lastUpdateTime, modifier = Modifier.padding(16.dp))
        }
    }
}

fun calculateDistance(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
    val earthRadiusMeters = 6_371_000.0
    val phi1 = lat1 * Math.PI / 180
    val phi2 = lat2 * Math.PI / 180
    val deltaPhi = (lat2 - lat1) * Math.PI / 180
    val deltaLambda = (lon2 - lon1) * Math.PI / 180
    val a = sin(deltaPhi / 2) * sin(deltaPhi / 2) + cos(phi1) * cos(phi2) * sin(deltaLambda / 2) * sin(deltaLambda / 2)
    val c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earthRadiusMeters * c
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
fun MapModule(onWebViewCreated: (WebView) -> Unit) {
    AndroidView(
        factory = { context ->
            WebView(context).apply {
                onWebViewCreated(this)
                settings.javaScriptEnabled = true
                settings.domStorageEnabled = true
                loadDataWithBaseURL("https://webapi.amap.com", MapHtmlGenerator.getMapHtml(), "text/html", "UTF-8", null)
            }
        },
        modifier = Modifier.fillMaxSize()
    )
}

@Composable
fun TopBar(isConnected: Boolean, onRefresh: () -> Unit) {
    Card(
        modifier = Modifier.padding(16.dp).fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.Radar, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Spacer(modifier = Modifier.width(12.dp))
                Text("Guardian Monitor", fontWeight = FontWeight.Bold)
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onRefresh) {
                    Icon(Icons.Rounded.Refresh, contentDescription = "Refresh")
                }
                StatusChip(isConnected)
            }
        }
    }
}

@Composable
fun StatusChip(isConnected: Boolean) {
    Surface(color = if (isConnected) Color(0xFFE8F5E9) else Color(0xFFFFEBEE), shape = CircleShape) {
        Text(
            text = if (isConnected) "Online" else "Offline",
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp),
            color = if (isConnected) Color(0xFF2E7D32) else Color(0xFFC62828),
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
fun DeviceStrip(
    devices: List<DeviceSummary>,
    selectedDeviceId: String?,
    onSelect: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    if (devices.isEmpty()) {
        return
    }
    Card(modifier = modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Tracked Devices", fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(12.dp))
            Row(
                modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                devices.forEach { device ->
                    val selected = device.deviceId == selectedDeviceId
                    OutlinedButton(
                        onClick = { onSelect(device.deviceId) },
                        border = BorderStroke(1.dp, if (selected) MaterialTheme.colorScheme.primary else Color(0xFFDDE4EE)),
                        colors = ButtonDefaults.outlinedButtonColors(
                            containerColor = if (selected) MaterialTheme.colorScheme.primary.copy(alpha = 0.08f) else Color.White
                        )
                    ) {
                        Column(horizontalAlignment = Alignment.Start) {
                            Text("Device ${device.deviceId.takeLast(6).uppercase()}", fontWeight = FontWeight.SemiBold)
                            Text(device.lastUpdatedText ?: "No location yet", style = MaterialTheme.typography.labelSmall)
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun AlertBanner(alert: AlertData) {
    val isExit = alert.type == "EXIT"
    val color = if (isExit) Color(0xFFE53935) else Color(0xFF43A047)
    Card(
        modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp).fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = Color.White)
    ) {
        Row(modifier = Modifier.padding(16.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = if (isExit) Icons.Rounded.Warning else Icons.Rounded.CheckCircle,
                contentDescription = null,
                tint = color
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column {
                Text(
                    text = if (isExit) "Alert: device left the safe zone" else "Notice: device re-entered the safe zone",
                    fontWeight = FontWeight.Bold,
                    color = color
                )
                Text("Device ${alert.deviceId.takeLast(6).uppercase()} at ${alert.time_str ?: "Just now"}", color = Color.Gray)
            }
        }
    }
}

@Composable
fun SafeZoneActions(
    isSafeZoneSet: Boolean,
    onSet: () -> Unit,
    onRemove: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(modifier = modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            horizontalArrangement = Arrangement.SpaceAround
        ) {
            FilledTonalButton(onClick = onSet) {
                Icon(Icons.Rounded.AddLocation, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text("Set Safe Zone")
            }
            if (isSafeZoneSet) {
                OutlinedButton(onClick = onRemove, border = BorderStroke(1.dp, Color(0xFFE53935))) {
                    Icon(Icons.Rounded.WrongLocation, contentDescription = null)
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("Remove Safe Zone", color = Color(0xFFE53935))
                }
            }
        }
    }
}

@Composable
fun DeviceStatusCard(location: LocationData?, lastUpdate: String, modifier: Modifier = Modifier) {
    if (location == null) return
    Card(modifier = modifier.fillMaxWidth(), colors = CardDefaults.cardColors(containerColor = Color.White)) {
        Column(modifier = Modifier.padding(24.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(shape = CircleShape, color = MaterialTheme.colorScheme.primary.copy(alpha = 0.1f), modifier = Modifier.size(40.dp)) {
                    Icon(Icons.Rounded.Smartphone, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(8.dp))
                }
                Spacer(modifier = Modifier.width(16.dp))
                Column {
                    Text("Protected Device", color = Color.Gray)
                    Text(location.deviceId.takeLast(6).uppercase(), fontWeight = FontWeight.Bold, letterSpacing = 1.sp)
                }
            }
            Divider(modifier = Modifier.padding(vertical = 20.dp), color = Color(0xFFF0F0F0))
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                InfoItem(Icons.Rounded.LocationOn, "Latitude", String.format("%.4f", location.latitude))
                InfoItem(Icons.Rounded.LocationOn, "Longitude", String.format("%.4f", location.longitude))
                InfoItem(Icons.Rounded.AccessTime, "Updated", lastUpdate)
            }
        }
    }
}

@Composable
fun InfoItem(icon: ImageVector, label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Icon(icon, contentDescription = null, tint = Color.Gray, modifier = Modifier.size(20.dp))
        Spacer(modifier = Modifier.height(8.dp))
        Text(value, fontWeight = FontWeight.SemiBold)
        Text(label, style = MaterialTheme.typography.labelSmall, color = Color.LightGray)
    }
}

@Composable
fun EmptyStateModule() {
    Box(modifier = Modifier.fillMaxSize().background(Color(0xFFF5F7FA).copy(alpha = 0.75f)), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Surface(shape = CircleShape, color = Color.White, shadowElevation = 4.dp, modifier = Modifier.size(120.dp)) {
                Box(contentAlignment = Alignment.Center, modifier = Modifier.fillMaxSize()) {
                    Icon(Icons.Rounded.Radar, contentDescription = null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(52.dp))
                }
            }
            Spacer(modifier = Modifier.height(24.dp))
            Text("Waiting for device data", fontWeight = FontWeight.Bold)
            Spacer(modifier = Modifier.height(8.dp))
            Text("Open the Client app on at least one device and allow location access.", color = Color.Gray)
        }
    }
}
