import os
import json
import numpy as np
from scipy.spatial import KDTree

def run_knn_search(target_lon, target_lat, k=3):
    # 1. 更加强壮的路径处理
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir)) # 往上跳两级找根目录
    
    # 尝试多个可能存放数据的地方
    possible_paths = [
        os.path.join(current_dir, '03_campus_objects.json'),
        os.path.join(current_dir, '03_campus_objects.geojson'),
        os.path.join(root_dir, 'data', '03_campus_objects.json'),
        os.path.join(root_dir, '03_campus_objects.json')
    ]
    
    input_path = None
    for p in possible_paths:
        if os.path.exists(p):
            input_path = p
            break
            
    if not input_path:
        print(f"❌ 错误：在所有预设路径中都找不到 03_campus_objects.json")
        return []

    print(f"--- 启动 KNN 查询 (K={k}) ---")
    print(f"📄 正在读取数据: {input_path}")

    # 2. 加载设施数据
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        features = data['features'] if 'features' in data else data
        
        if not features:
            print("⚠️ 警告：设施列表为空！")
            return []

        coords = []
        facilities_info = []
        
        for feat in features:
            # 兼容标准 GeoJSON 格式
            if isinstance(feat, dict) and 'geometry' in feat:
                lon, lat = feat['geometry']['coordinates']
                props = feat['properties']
            # 兼容普通列表格式
            else:
                lon, lat = feat.get('coordinates', [0, 0])
                props = feat
                
            coords.append([lon, lat])
            facilities_info.append({"props": props, "geometry": {"type":"Point", "coordinates":[lon, lat]}})

        # 3. 构建 KD-Tree 并查询
        tree = KDTree(coords)
        # 执行查询
        distances, indices = tree.query([target_lon, target_lat], k=min(k, len(coords)))

        # 4. 封装结果
        results = []
        # 如果k=1，scipy返回的是标量，需转为列表
        if k == 1 or not isinstance(indices, (list, np.ndarray)):
            distances, indices = [distances], [indices]

        for d, idx in zip(distances, indices):
            info = facilities_info[idx]
            obj_id = info['props'].get('objectId', 'unknown')
            name = info['props'].get('name', '未命名设施')
            dist_m = round(d * 111320, 2) # 经纬度转米

            results.append({
                "objectId": obj_id,
                "value": dist_m,
                "level": 1,
                "label": f"最近设施: {name}",
                "style": {"color": "#007bff", "opacity": 0.9},
                "description": f"距离查询点 {dist_m} 米",
                "geometry": info['geometry']
            })

        # 5. 保存结果（用于调试）
        output_path = os.path.join(current_dir, 'analysis_result_knn.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=4)
        return results

    except Exception as e:
        print(f"❌ 运行时出错: {str(e)}")
        return []

if __name__ == "__main__":
    # 本地测试
    test_lon, test_lat = 103.722, 36.108 
    res = run_knn_search(test_lon, test_lat, k=3)
    print(f"测试完成，找到 {len(res)} 个结果")