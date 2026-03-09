# GuardianStar

GuardianStar 是一个可直接构建和演示的儿童守护原型项目，包含：

- `Client`：被守护端 Android App
- `Monitor`：监护端 Android App
- `Client/server`：轻量级 Python 后端

这套工程现在已经打通了完整的安全区闭环：

1. `Monitor` 设置安全区
2. 后端保存安全区配置
3. `Client` 定时同步安全区并注册 Android Geofence
4. 进入或离开安全区时，`Client` 自动上报告警
5. `Monitor` 拉取并展示告警与轨迹

## 项目结构

### Client

- `src/main/java/com/example/guardianstar/ui/MainActivity.kt`
  被守护端主界面，包含 Home / History / Profile 三页。
- `src/main/java/com/example/guardianstar/service/LocationTrackingService.kt`
  前台定位服务，负责定位上传、服务状态同步、安全区同步与围栏注册。
- `src/main/java/com/example/guardianstar/network/LocationApi.kt`
  上传位置、上传告警、读取安全区的 Retrofit 接口。
- `src/main/java/com/example/guardianstar/utils/ServerConfig.kt`
  保存和读取后端地址，默认值为 `http://10.0.2.2:8080/`。
- `src/main/java/com/example/guardianstar/manager/`
  Geofence 管理与广播接收逻辑。

### Monitor

- `src/main/java/com/example/guardianstar/monitor/MonitorActivity.kt`
  监护端主界面，负责轮询位置、展示地图、显示告警、设置或移除安全区。
- `src/main/java/com/example/guardianstar/monitor/MapHtmlGenerator.kt`
  生成高德地图 WebView HTML。
- `src/main/java/com/example/guardianstar/monitor/network/MonitorApi.kt`
  获取最新位置、历史轨迹、告警、安全区的 Retrofit 接口。
- `local.properties.example`
  本地开发配置示例。

### Backend

- `Client/server/server.py`
  提供位置、历史轨迹、告警、安全区和健康检查接口。
- `Client/server/server_state.json`
  运行时自动生成，用于持久化最近位置、轨迹、告警和安全区配置。

## 已完成的关键能力

- `Client` 支持前台定位服务、权限引导、后端地址配置、Geofence 同步与告警上报
- `Monitor` 支持地图展示、10 秒轮询、轨迹绘制、安全区设置/移除、在线状态显示
- 后端支持：
  - `GET /api/health`
  - `GET /api/latest`
  - `GET /api/history`
  - `GET /api/alerts`
  - `GET /api/safe-zone`
  - `POST /api/location`
  - `POST /api/alert`
  - `POST /api/safe-zone`
  - `DELETE /api/safe-zone`
- 服务端状态支持磁盘持久化，不再只保存在内存里

## 构建验证

当前 Windows 环境下，以下命令已经验证通过：

```powershell
cd Client
.\gradlew.bat clean assembleDebug :monitor:assembleDebug
```

生成的 APK：

- `Client/build/outputs/apk/debug/GuardianStar-debug.apk`
- `Monitor/build/outputs/apk/debug/monitor-debug.apk`

## 快速启动

### 1. 启动后端

```powershell
cd Client\server
python server.py
```

启动后可访问：

- `http://localhost:8080/`
- `http://localhost:8080/api/health`
- `http://localhost:8080/api/latest`

### 2. 构建两个 Android App

```powershell
cd Client
.\gradlew.bat clean assembleDebug :monitor:assembleDebug
```

### 3. 安装 APK

```powershell
adb install -r Client\build\outputs\apk\debug\GuardianStar-debug.apk
adb install -r Monitor\build\outputs\apk\debug\monitor-debug.apk
```

## 本地配置

### Client

`Client` 默认使用：

```text
http://10.0.2.2:8080/
```

如果使用真机，请在 `Profile -> Server Settings` 中改成电脑的局域网 IP，例如：

```text
http://192.168.1.10:8080/
```

### Monitor

复制 `Monitor/local.properties.example` 为 `Monitor/local.properties`，然后按需修改：

```properties
monitor.baseUrl=http://10.0.2.2:8080/
amap.webApiKey=your-amap-web-api-key
```

说明：

- 模拟器访问宿主机后端时，通常使用 `10.0.2.2`
- 真机调试时，请改为电脑的局域网 IP

## 使用顺序建议

1. 先启动后端
2. 启动 `Client`，授予定位权限并开启保护服务
3. 启动 `Monitor`，确认已看到设备位置
4. 在 `Monitor` 中点击 `Set Safe Zone`
5. 携带 `Client` 设备移出安全区，观察 `Monitor` 中是否收到告警

## 仓库清理

项目根目录已补充 `.gitignore`，用于忽略：

- Gradle 构建目录
- IDE 配置目录
- `local.properties`
- `server_state.json`
- `.hprof`

如果之前工作区里已经产生过这些文件，它们可能仍然出现在本地 Git 状态中；这是旧产物，不影响当前代码构建和运行。
