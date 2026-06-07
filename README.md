智慧校园空间分析微服务系统 (Smart Campus GIS API)

## 项目简介
本项目通过 **Python + Flask** 构建了一套标准化的校园空间分析服务引擎。该系统旨在为 WebGIS 前端提供实时、精准的空间决策支持。

## 核心算法与接口 (API Endpoints)
本项目实现了 5 大核心 GIS 算法，并通过 RESTful API 对外发布：

1. **等时圈分析 (Isochrone):** `/api/analysis/isochrone` - 评估设施服务覆盖范围。
2. **最短路径 (Dijkstra):** `/api/analysis/path` - 提供最优步行导航。
3. **最近邻检索 (KNN):** `/api/analysis/knn` - 快速定位最近服务点。
4. **服务盲区识别 (Blind Spot):** `/api/analysis/blind_spot` - 识别资源配置空白。
5. **服务分区 (Voronoi):** `/api/analysis/voronoi` - 划分设施逻辑腹地。

## 🛠️ 技术栈
- **后端框架:** Flask (Python)
- **空间计算:** NetworkX, GeoPandas, SciPy, Shapely
- **数据标准:** GeoJSON, 标准化集成 JSON
- **坐标系统:** WGS84 (EPSG:4326) / Web Mercator (EPSG:3857)

## 可视化结果预览
![等时圈与盲区分析结果](visuals/等时圈分析结果截图.png)

## 📥 快速启动
1. 安装依赖: `pip install -r requirements.txt`
2. 启动服务: `python app.py`
3. 访问地址: `http://127.0.0.1:5000/api/analysis/isochrone`
