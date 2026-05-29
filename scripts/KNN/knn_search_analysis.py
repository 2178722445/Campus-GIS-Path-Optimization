import os
import json
import numpy as np
from scipy.spatial import KDTree

def run_knn_search(target_lon, target_lat, k=3):
    # 1. 路径处理
    current_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(current_dir, '03_campus_objects.json')
    output_path = os.path.join(current_dir, 'analysis_result_knn.json')
    preview_path = os.path.join(current_dir, 'knn_preview.geojson')

    print(f"--- 启动 KNN 最近邻查询 (K={k}) ---")

    # 2. 加载设施数据
    if not os.path.exists(input_path):
        # 兼容后缀名
        input_path = os.path.join(current_dir, '03_campus_objects.geojson')

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    features = data['features'] if 'features' in data else data
    
    coords = []
    facilities_info = []
    
    for feat in features:
        if 'geometry' in feat:
            lon, lat = feat['geometry']['coordinates']
            props = feat['properties']
        else:
            lon, lat = feat.get('coordinates', [0, 0])
            props = feat
            
        coords.append([lon, lat])
        facilities_info.append({"props": props, "geometry": {"type":"Point", "coordinates":[lon, lat]}})

    # 3. 构建 KD-Tree 索引并查询
    tree = KDTree(coords)
    distances, indices = tree.query([target_lon, target_lat], k=k)

    # 4. 封装结果 (针对三维集成)
    results = []
    if k == 1:
        distances, indices = [distances], [indices]

    for d, idx in zip(distances, indices):
        info = facilities_info[idx]
        obj_id = info['props'].get('objectId', 'unknown')
        name = info['props'].get('name', '未命名设施')
        
        # 经纬度转米 (粗略估算)
        dist_m = round(d * 111320, 2)

        res_item = {
            "objectId": obj_id,
            "value": dist_m,
            "level": 1,
            "label": f"最近设施: {name}",
            "style": {
                "color": "#007bff", # 蓝色高亮
                "opacity": 0.9
            },
            "description": f"距离查询点 {dist_m} 米",
            "geometry": info['geometry']
        }
        results.append(res_item)

    # 保存结果文件 (集成用)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    # 5. 生成 QGIS 预览文件 (包含搜索中心、连线和目标点)
    preview_geojson = {
        "type": "FeatureCollection",
        "features": []
    }

    # A. 加入搜索中心点
    preview_geojson["features"].append({
        "type": "Feature",
        "properties": {"label": "搜索起点 (用户位置)"},
        "geometry": {"type": "Point", "coordinates": [target_lon, target_lat]}
    })

    for res in results:
        # B. 加入设施目标点
        preview_geojson["features"].append({
            "type": "Feature",
            "properties": res,
            "geometry": res["geometry"]
        })
        # C. 加入连线 (核心视觉效果)
        preview_geojson["features"].append({
            "type": "Feature",
            "properties": {"dist_m": res["value"]},
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [target_lon, target_lat],
                    res["geometry"]["coordinates"]
                ]
            }
        })

    with open(preview_path, 'w', encoding='utf-8') as f:
        json.dump(preview_geojson, f, ensure_ascii=False, indent=4)

    print(f"✅ 算法执行成功！")
    print(f"📄 集成文件: {output_path}")
    print(f"📍 QGIS预览: {preview_path}")

if __name__ == "__main__":
    # 模拟用户点击兰州交大的一个位置 (请根据你画的底图微调坐标)
    # 你可以先在 QGIS 里点一个位置，看下面的 Coordinate 框复制坐标过来
    test_lon, test_lat = 103.722, 36.108 
    run_knn_search(test_lon, test_lat, k=3)