# Quick Start Guide - Guardian Monitor App

## 🎯 What Was Fixed

### Critical Errors (All Fixed ✅)
1. **Gradle Configuration** - Added missing settings.gradle.kts and plugin versions
2. **Corrupted Kotlin Code** - Fixed HTML tags mixed into Kotlin code (lines 483-484)
3. **Missing getMapHtml() Function** - Completed the AMap integration function
4. **Missing Resources** - Added colors.xml, strings.xml, and proguard-rules.pro

## 🚀 How to Build & Run

### Step 1: Sync Gradle
1. Open `Monitor` folder in Android Studio
2. Click the **Sync Project with Gradle Files** button (elephant icon)
3. Wait for sync to complete (may take a few minutes on first run)

### Step 2: Build the Project
```
Build → Make Project (Ctrl+F9)
```

### Step 3: Run the App
1. Start an Android emulator or connect a physical device
2. Click **Run** (Shift+F10)
3. Select your device/emulator

## 📱 App Features

### 1. Real-Time Location Tracking
- Updates every 3 seconds
- Shows location on 高德地图 (AMap)
- Displays coordinates and timestamp

### 2. Geofencing (Safe Zone)
- Tap the **"设为安全区"** button to set current location as safe zone
- 100-meter radius
- Automatic alerts when device leaves the zone

### 3. Connection Status
- **Green "在线"** = Connected to server
- **Red "离线"** = Disconnected

### 4. Alert System
- **Red Alert** = Device left safe zone
- **Green Alert** = Device entered safe zone

## ⚙️ Configuration

### Backend Server
**Location:** `RetrofitClient.kt` line 10
```kotlin
private const val BASE_URL = "http://10.0.2.2:8080/"
```

**For Emulator:** Use `10.0.2.2` (already configured)  
**For Physical Device:** Change to your computer's IP address, e.g., `http://192.168.1.100:8080/`

### AMap API Keys
**Location:** `MonitorActivity.kt` lines 41-44
```kotlin
const val AMAP_WEB_API_KEY = "1a7374d7b0262c1b5cab61d733a9b537"
const val AMAP_SECURITY_KEY = "cf704d892b4df206946943574d2fbf7e"
```

## 🔧 Troubleshooting

### Issue: "Plugin was not found"
**Solution:** Make sure you synced Gradle after the fixes. Click the sync button again.

### Issue: "Cannot connect to server"
**Solution:** 
1. Ensure backend server is running
2. Check the BASE_URL in RetrofitClient.kt
3. For physical devices, use your computer's IP instead of 10.0.2.2

### Issue: Map not loading
**Solution:**
1. Check internet connection
2. Verify AMap API keys are valid
3. Check browser console in WebView for JavaScript errors

### Issue: Location not updating
**Solution:**
1. Verify backend server is sending location data
2. Check network connection
3. Look at Logcat for network errors (filter by "OkHttp")

## 📂 Project Structure

```
Monitor/
├── build.gradle.kts          # Build configuration
├── settings.gradle.kts       # Gradle settings
├── proguard-rules.pro        # ProGuard rules
└── src/main/
    ├── AndroidManifest.xml   # App manifest
    ├── java/.../monitor/
    │   ├── MonitorActivity.kt      # Main UI
    │   └── network/
    │       ├── MonitorApi.kt       # API interface
    │       └── RetrofitClient.kt   # Network client
    └── res/
        └── values/
            ├── colors.xml    # Color resources
            ├── strings.xml   # String resources
            └── themes.xml    # App theme
```

## 🎨 UI Components

### Top Bar
- App title "Guardian Monitor"
- Connection status indicator

### Map View
- Full-screen AMap (高德地图)
- Blue marker for device location
- Blue circle for safe zone (when set)

### Bottom Panel
- Device ID (last 6 characters)
- Latitude and Longitude
- Last update time

### Floating Action Button
- **"设为安全区"** - Sets current location as safe zone center

### Alert Card (when triggered)
- Shows when device enters/exits safe zone
- Displays alert type and timestamp

## 📊 API Endpoints

The app expects these endpoints from the backend:

### GET /api/latest
Returns the latest location data:
```json
{
  "latitude": 39.90923,
  "longitude": 116.397428,
  "timestamp": 1732687200000,
  "deviceId": "device-123"
}
```

### GET /api/alerts
Returns list of alerts:
```json
[
  {
    "type": "EXIT",
    "timestamp": 1732687200000,
    "deviceId": "device-123",
    "time_str": "13:30:00"
  }
]
```

## 🔐 Permissions

Already configured in AndroidManifest.xml:
- `INTERNET` - For network requests
- `ACCESS_NETWORK_STATE` - To check connection status

## 📝 Next Steps

1. **Test the app** with your backend server
2. **Customize** the safe zone radius if needed (currently 100 meters)
3. **Add notifications** for alerts (optional enhancement)
4. **Implement** location history tracking (optional enhancement)

## 💡 Tips

- The app uses **Jetpack Compose** for UI - all UI is declarative
- **Material Design 3** provides the modern look and feel
- **Retrofit** handles all network communication
- **WebView** embeds the AMap for map display
- **Coroutines** manage async operations and polling

---

**Need Help?** Check `PROJECT_ANALYSIS.md` for detailed technical information.
