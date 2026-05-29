# Campus-GIS-Path-Optimization
# 智慧校园空间分析算法引擎 (Smart Campus GIS Engine)

## 项目定位
本项目由旨在利用 **Python + 图论算法** 对校园生活服务设施进行全方位的可达性量化评估与空间优化。

## 核心算法实现
本项目独立实现了 5 大核心 GIS 空间分析算法，所有结果均通过 **CesiumJS** 集成标准校核。

1. **多级等时圈分析 (Isochrone Analysis)**
   - 算法：Dijkstra 扩散搜索。
   - 价值：评估 5/10/15 分钟步行服务覆盖范围。
2. **最短路径规划 (Dijkstra Pathfinding)**
   - 算法：基于路网拓扑权重的最优路径检索。
   - 价值：提供高精度校园步行导航建议。
3. **服务覆盖盲区识别 (Blind Spot Identification)**
   - 算法：空间差异运算 (Difference Overlay)。
   - 价值：精准定位校园设施布局空白区。
4. **最近邻检索 (KNN Search)**
   - 算法：基于 **KD-Tree** 空间索引的快速查询。
   - 价值：毫秒级响应离用户最近的设施需求。
5. **食堂服务分区 (Voronoi Partition)**
   - 算法：泰森多边形 + 校园边界约束裁切。
   - 价值：划分校园设施的逻辑服务腹地。

## 技术栈
- **语言：** Python 3.13
- **核心库：** NetworkX (图建模), GeoPandas (矢量处理), SciPy (空间索引), Shapely (几何运算)
- **坐标系：** WGS84 (EPSG:4326) / Web Mercator (EPSG:3857) 动态投影转换
- **可视化：** QGIS 3.x / CesiumJS

## 可视化结果预览
![等时圈与盲区分析结果](visuals/等时圈分析结果截图.png)(visuals/blind_spot_analysis.png)

## 如何运行
1. 安装依赖：`pip install -r requirements.txt`
2. 运行分析：`python scripts/isochrone_analysis.py`
## 规范说明
生成的 `analysis_result_isochrone.json` 包含以下字段：
- `objectId`: 关联设施唯一标识
- `level/value`: 响应的时间梯度
- `style`: 预定义渲染样式
- `geometry`: GeoJSON 标准几何体
