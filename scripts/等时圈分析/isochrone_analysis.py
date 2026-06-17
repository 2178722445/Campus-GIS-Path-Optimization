import os
import json
import geopandas as gpd
import networkx as nx
from shapely.geometry import Point, MultiPoint, mapping

def run_isochrone_analysis(target_id=None):
    """
    等时圈分析核心模块 - 修正版
    """
    # 1. 路径自动定位（确保能找到同文件夹下的数据）
    current_dir = os.path.dirname(os.path.abspath(__file__))
    roads_path = os.path.join(current_dir, '04_paths_or_roads.geojson')
    objects_path = os.path.join(current_dir, '03_campus_objects.json')

    if not os.path.exists(roads_path) or not os.path.exists(objects_path):
        print(f"❌ 错误：在 {current_dir} 找不到必要的数据文件。")
        return []

    # 2. 构建路网拓扑 (米制坐标系计算)
    print("正在加载并转换路网坐标...")
    roads = gpd.read_file(roads_path)
    if roads.crs is None:
        roads.set_crs(epsg=4326, inplace=True)
    roads = roads.to_crs(epsg=3857) # 转为米制以计算距离

    G = nx.Graph()
    for _, row in roads.iterrows():
        coords = list(row.geometry.coords)
        for i in range(len(coords) - 1):
            p1, p2 = coords[i], coords[i+1]
            dist = Point(p1).distance(Point(p2))
            # 步行速度 1.2m/s
            G.add_edge(p1, p2, weight=dist/1.2)

    # 3. 读取设施点
    with open(objects_path, 'r', encoding='utf-8') as f:
        facilities_data = json.load(f)
    
    features_list = facilities_data['features'] if 'features' in facilities_data else facilities_data

    # 4. 参数配置
    time_limits = [300, 600, 900] 
    styles = {
        300: {"color": "#28a745", "opacity": 0.6}, # 5min - 绿
        600: {"color": "#ffc107", "opacity": 0.5}, # 10min - 黄
        900: {"color": "#dc3545", "opacity": 0.4}  # 15min - 红
    }

    results = []
    nodes_list = list(G.nodes)

    # 5. 执行循环分析
    print("正在执行 Dijkstra 扩散搜索...")
    for feat in features_list:
        # 获取 ID 和名称
        props = feat.get('properties', feat)
        obj_id = props.get('objectId') or props.get('id') or 'unknown'
        obj_name = props.get('name') or obj_id

        # 过滤指定 ID
        if target_id and obj_id != target_id:
            continue

        # 获取经纬度
        geom = feat.get('geometry', {})
        coords = geom.get('coordinates', [0,0])
        lon, lat = coords[0], coords[1]
        
        # 设施点转米制坐标以匹配路网
        p_m = gpd.GeoSeries([Point(lon, lat)], crs="EPSG:4326").to_crs(epsg=3857)[0]
        
        # 寻找路网最近点
        source_node = min(nodes_list, key=lambda n: Point(n).distance(p_m))

        for idx, t in enumerate(time_limits):
            # Dijkstra 算法搜索可达节点
            subgraph_nodes = nx.single_source_dijkstra_path_length(G, source_node, cutoff=t, weight='weight')
            
            if len(subgraph_nodes) < 3: continue
            
            # 1. 生成几何体 (凸包)
            hull = MultiPoint(list(subgraph_nodes.keys())).convex_hull
            
            # 2. 【关键修复】将计算出的 3857 结果精准转回 4326 经纬度
            hull_gdf = gpd.GeoSeries([hull], crs="EPSG:3857").to_crs(epsg=4326)
            
            # 3. 字段封装
            res_item = {
                "objectId": obj_id,   
                "value": t,                  
                "level": idx + 1,            
                "label": f"{obj_name} {t//60}分钟服务圈",
                "style": styles[t],          
                "description": f"从 {obj_name} 出发步行 {t//60} 分钟可达范围", 
                "geometry": mapping(hull_gdf.iloc[0]) # 这里现在是正确的 [103.x, 36.x] 格式
            }
            results.append(res_item)
            
    print(f"✅ 全部设施分析完成，共生成 {len(results)} 个分析要素")

    # 6. 保存最终结果 (集成用)
    output_filename = os.path.join(current_dir, 'analysis_result_isochrone.json')
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    # 7. 生成 QGIS 预览文件
    preview_geojson = {"type": "FeatureCollection", "features": []}
    for item in results:
        preview_geojson["features"].append({
            "type": "Feature",
            "properties": {
                "objectId": item["objectId"],
                "level": item["level"],
                "label": item["label"]
            },
            "geometry": item["geometry"]
        })

    preview_filename = os.path.join(current_dir, 'qgis_preview.geojson')
    with open(preview_filename, 'w', encoding='utf-8') as f:
        json.dump(preview_geojson, f, ensure_ascii=False, indent=4)
    
    return results 

if __name__ == "__main__":
    data = run_isochrone_analysis()