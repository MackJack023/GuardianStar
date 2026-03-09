package com.example.guardianstar.monitor

object MapHtmlGenerator {
    // TODO: 请在此处填入你的高德地图 Web API Key
    fun getMapHtml(): String {
        return """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <meta name="viewport" content="initial-scale=1.0, user-scalable=no">
                <title>Guardian Map</title>
                <!-- 引入 MoveAnimation 插件用于平滑移动，CitySearch 用于IP定位 -->
                <script src="https://webapi.amap.com/maps?v=2.0&key=${BuildConfig.AMAP_WEB_API_KEY}&plugin=AMap.Scale,AMap.ToolBar,AMap.MoveAnimation,AMap.CitySearch" onerror="onMapScriptError()"></script>
                <style>
                    * { margin: 0; padding: 0; box-sizing: border-box; }
                    html, body, #container { width: 100%; height: 100%; overflow: hidden; }
                    
                    /* 错误提示样式 */
                    #error-toast {
                        display: none;
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        background: rgba(0, 0, 0, 0.7);
                        color: white;
                        padding: 15px 20px;
                        border-radius: 8px;
                        font-size: 14px;
                        z-index: 9999;
                        text-align: center;
                        max-width: 80%;
                    }

                    /* 自定义定位点样式 */
                    .custom-marker {
                        position: relative;
                        width: 24px;
                        height: 24px;
                    }
                    .marker-core {
                        width: 16px;
                        height: 16px;
                        background-color: #4A90E2;
                        border: 2px solid #fff;
                        border-radius: 50%;
                        box-shadow: 0 2px 6px rgba(0,0,0,0.3);
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        z-index: 2;
                    }
                    /* 波纹动画 */
                    .marker-pulse {
                        position: absolute;
                        top: 50%;
                        left: 50%;
                        transform: translate(-50%, -50%);
                        width: 40px;
                        height: 40px;
                        background-color: rgba(74, 144, 226, 0.4);
                        border-radius: 50%;
                        animation: pulse 2s infinite;
                        z-index: 1;
                    }
                    @keyframes pulse {
                        0% { transform: translate(-50%, -50%) scale(0.5); opacity: 1; }
                        100% { transform: translate(-50%, -50%) scale(1.5); opacity: 0; }
                    }
                    
                    /* 自定义 InfoWindow 样式 */
                    .info-window {
                        background: white;
                        padding: 10px 15px;
                        border-radius: 8px;
                        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                        font-size: 14px;
                        color: #333;
                        min-width: 150px;
                        text-align: center;
                    }
                    .amap-logo, .amap-copyright {
                        display: none !important; /* 隐藏 LOGO，根据需求开启 */
                    }
                </style>
            </head>
            <body>
                <div id="container"></div>
                <div id="error-toast"></div>
                <script>
                    function showToast(msg) {
                        var toast = document.getElementById('error-toast');
                        toast.innerText = msg;
                        toast.style.display = 'block';
                        // 5秒后自动隐藏
                        setTimeout(function() {
                            toast.style.display = 'none';
                        }, 5000);
                    }

                    function onMapScriptError() {
                        showToast('地图组件加载失败，请检查网络或API Key');
                    }

                    var map, marker, circle, polyline;
                    var isFirstLoad = true;

                    // 检查 AMap 是否已定义
                    if (typeof AMap === 'undefined') {
                        onMapScriptError();
                    } else {
                        try {
                            // 初始化地图
                            map = new AMap.Map('container', {
                                resizeEnable: true,
                                zoom: 10,
                                viewMode: '3D',
                                pitch: 45, // 3D 视角
                                showBuildingBlock: true // 显示 3D 楼块
                            });
                            
                            // 添加标准控件
                            map.addControl(new AMap.Scale());
                            map.addControl(new AMap.ToolBar({
                                position: 'RB', // 右下角
                                offset: new AMap.Pixel(10, 20),
                                liteStyle: true
                            }));
                            
                            // 使用IP定位补充初始定位
                            var citySearch = new AMap.CitySearch();
                            citySearch.getLocalCity(function (status, result) {
                                if (status === 'complete' && result.info === 'OK') {
                                    if (result && result.bounds) {
                                        // 只有在还没接收到设备精准位置时才调整视野
                                        if (isFirstLoad) {
                                            var citybounds = result.bounds;
                                            map.setBounds(citybounds);
                                            showToast('等待设备位置，当前显示: ' + result.city);
                                        }
                                    }
                                }
                            });
                            
                            // 创建自定义 Marker 内容
                            var markerContent = document.createElement('div');
                            markerContent.className = 'custom-marker';
                            markerContent.innerHTML = '<div class="marker-pulse"></div><div class="marker-core"></div>';
        
                            marker = new AMap.Marker({
                                position: map.getCenter(),
                                content: markerContent, // 使用自定义 DOM
                                offset: new AMap.Pixel(-12, -12), // 中心点偏移
                                zIndex: 100,
                                visible: false // 初始隐藏，直到收到具体位置
                            });
                            marker.setMap(map);
                            
                            // 创建 InfoWindow
                            var infoWindow = new AMap.InfoWindow({
                                isCustom: true,  // 使用自定义窗体
                                content: '<div class="info-window">设备当前位置</div>',
                                offset: new AMap.Pixel(0, -20)
                            });
                            
                            // 点击 Marker 显示 InfoWindow
                            marker.on('click', function() {
                                infoWindow.open(map, marker.getPosition());
                            });

                        } catch (e) {
                            console.error(e);
                            showToast('地图初始化错误: ' + e.message);
                        }
                    }
                    
                    function updateLocation(lat, lng) {
                        if (!map || !marker) return;
                        var position = [lng, lat];
                        
                        // 确保 Marker 可见
                        if (!marker.getVisible()) {
                            marker.show();
                        }
                        
                        // 平滑移动到新位置
                        if (isFirstLoad) {
                            marker.setPosition(position);
                            map.setCenter(position);
                            map.setZoom(16); // 收到位置后放大
                            isFirstLoad = false;
                        } else {
                            // 使用 moveTo 进行平滑动画
                            if (marker.moveTo) {
                                marker.moveTo(position, {
                                    duration: 1000, // 1秒过渡
                                    autoRotation: false
                                });
                            } else {
                                marker.setPosition(position);
                            }
                            
                            // 视角跟随
                            map.panTo(position);
                        }
                    }

                    function addCircle(lat, lng, radius) {
                        if (!map) return;
                        if (circle) {
                            map.remove(circle);
                        }
                        circle = new AMap.Circle({
                            center: [lng, lat],
                            radius: radius,
                            fillColor: '#4A90E2',
                            fillOpacity: 0.15,
                            strokeColor: '#4A90E2',
                            strokeWeight: 2,
                            strokeOpacity: 0.8,
                            strokeStyle: 'dashed' // 虚线边框更具科技感
                        });
                        map.add(circle);
                        
                        // 自动调整视野以包含围栏和标记
                        if (marker && marker.getVisible()) {
                            map.setFitView([circle, marker], false, [20, 20, 20, 20]);
                        } else {
                            map.setFitView([circle], false, [20, 20, 20, 20]);
                        }
                    }
                    
                    function removeCircle() {
                        if (circle && map) {
                            map.remove(circle);
                            circle = null;
                        }
                    }

                    // 绘制历史轨迹 path: [[lng, lat], [lng, lat], ...]
                    function drawHistoryPath(path) {
                        if (!map) return;
                        if (polyline) {
                            map.remove(polyline);
                        }
                        
                        if (!path || path.length < 2) return;

                        polyline = new AMap.Polyline({
                            path: path,
                            isOutline: true,
                            outlineColor: '#ffeeff',
                            borderWeight: 2,
                            strokeColor: "#3366FF", 
                            strokeOpacity: 1,
                            strokeWeight: 6,
                            strokeStyle: "solid",
                            lineJoin: 'round',
                            lineCap: 'round',
                            zIndex: 50,
                        });

                        polyline.setMap(map);
                        // 调整视野以包含轨迹
                        map.setFitView([polyline]);
                    }
                    
                    function clearHistoryPath() {
                        if (polyline && map) {
                            map.remove(polyline);
                            polyline = null;
                        }
                    }
                </script>
            </body>
            </html>
        """.trimIndent()
    }
}
