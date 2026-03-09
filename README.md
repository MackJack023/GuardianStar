# GuardianStar

GuardianStar 是一个可直接构建、可直接演示、并且已经具备多设备后端能力的儿童守护原型项目。

它包含三部分：

- `Client`：被守护端 Android App
- `Monitor`：监护端 Android App
- `Client/server`：Python 后端

## 现在已经具备的闭环

当前版本已经支持真正的按设备闭环流程：

1. `Client` 上传自己的 `deviceId`、位置和告警
2. 后端按设备分别保存位置、历史轨迹、告警和安全区
3. `Monitor` 拉取设备列表并切换查看不同设备
4. `Monitor` 可以针对某个设备设置或移除安全区
5. `Client` 会按自己的 `deviceId` 同步安全区并注册 Geofence
6. 进入或离开安全区时，`Client` 自动上报告警

## 项目结构

### Client

- `src/main/java/com/example/guardianstar/ui/MainActivity.kt`
  被守护端主界面，包含 Home / History / Profile。
- `src/main/java/com/example/guardianstar/service/LocationTrackingService.kt`
  前台定位服务，负责位置上传、服务状态、按设备同步安全区、注册 Geofence。
- `src/main/java/com/example/guardianstar/network/LocationApi.kt`
  上传位置、告警和获取当前设备安全区的接口。
- `src/main/java/com/example/guardianstar/utils/ServerConfig.kt`
  保存和读取服务端地址，默认值是 `http://10.0.2.2:8080/`。
- `src/main/java/com/example/guardianstar/manager/`
  Geofence 注册与广播接收逻辑。

### Monitor

- `src/main/java/com/example/guardianstar/monitor/MonitorActivity.kt`
  监护端主界面，支持设备切换、地图展示、历史轨迹、告警、安全区设置。
- `src/main/java/com/example/guardianstar/monitor/network/MonitorApi.kt`
  多设备查询接口定义。
- `src/main/java/com/example/guardianstar/monitor/MapHtmlGenerator.kt`
  生成高德地图 WebView HTML。
- `local.properties.example`
  本地开发配置示例。

### Backend

- `Client/server/server.py`
  多设备后端，支持健康检查、设备列表、轨迹、告警和安全区接口。
- `Client/server/Dockerfile`
  后端镜像构建文件。
- `compose.yaml`
  一键启动后端服务。

## 后端接口

### 通用

- `GET /api/health`
- `GET /api/devices`
- `GET /api/latest?deviceId=...`
- `GET /api/history?deviceId=...`
- `GET /api/alerts?deviceId=...`
- `GET /api/safe-zone?deviceId=...`

### 写入

- `POST /api/location`
- `POST /api/alert`
- `POST /api/safe-zone`
- `DELETE /api/safe-zone?deviceId=...`

## 数据持久化

后端会把状态写入 `server_state.json`。

默认路径：

- 本地运行：`Client/server/server_state.json`
- Docker 运行：挂载到容器内 `/data/server_state.json`

## 已验证的构建

当前 Windows 环境下，以下命令已经实际验证通过：

```powershell
cd Client
.\gradlew.bat clean assembleDebug :monitor:assembleDebug
```

APK 输出：

- `Client/build/outputs/apk/debug/GuardianStar-debug.apk`
- `Monitor/build/outputs/apk/debug/monitor-debug.apk`

## 自动化测试

后端多设备接口已经补了基础自动化测试，运行命令：

```powershell
python -m unittest discover -s .\Client\server -p "test_*.py"
```

## 本地启动

### 方式 1：直接运行 Python 后端

```powershell
cd Client\server
python server.py
```

### 方式 2：使用 Docker Compose

```powershell
docker compose up --build
```

后端默认对外提供：

- `http://localhost:8080/`
- `http://localhost:8080/api/health`
- `http://localhost:8080/api/devices`

## Android 使用步骤

### 1. 构建两个 App

```powershell
cd Client
.\gradlew.bat clean assembleDebug :monitor:assembleDebug
```

### 2. 安装 APK

```powershell
adb install -r Client\build\outputs\apk\debug\GuardianStar-debug.apk
adb install -r Monitor\build\outputs\apk\debug\monitor-debug.apk
```

### 3. 启动顺序

1. 先启动后端
2. 在一个或多个设备上启动 `Client`
3. 授予定位权限，并点击 `Start protection service`
4. 启动 `Monitor`
5. 在 `Tracked Devices` 中选择某个设备
6. 点击 `Set Safe Zone`
7. 带着该设备移出安全区，观察监护端是否收到告警

## 配置

### Client

默认地址：

```text
http://10.0.2.2:8080/
```

如果是真机，请在 `Profile -> Server Settings` 中改成电脑局域网 IP，例如：

```text
http://192.168.1.10:8080/
```

### Monitor

复制 `Monitor/local.properties.example` 为 `Monitor/local.properties`：

```properties
monitor.baseUrl=http://10.0.2.2:8080/
amap.webApiKey=your-amap-web-api-key
```

说明：

- 模拟器访问宿主机通常使用 `10.0.2.2`
- 真机需要改为电脑的局域网 IP

## 仓库清理

项目根目录已补充 `.gitignore`，用于忽略：

- Gradle 构建目录
- IDE 配置目录
- `local.properties`
- `server_state.json`
- `.hprof`

如果本地 Git 状态里仍然能看到一些旧构建产物，那是历史文件，不影响当前代码运行。

## 目前仍然是原型的部分

虽然现在已经可以多设备演示，但它仍然是原型系统，还没有：

- 登录/鉴权
- 正式数据库
- 推送通知
- 真正的地图 key 管理
- 生产级 API 框架

如果继续往下做，下一步最值得补的是“账号体系 + SQLite/PostgreSQL + 推送通知”。  
