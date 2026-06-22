import os
import json
import numpy as np
from scipy.spatial import KDTree

from data_config import get_objects_path, get_data_dir


def run_knn_search(target_lon, target_lat, k=1, data_dir=None):
    data_dir = get_data_dir(data_dir)
    input_path = get_objects_path(data_dir)

    if not os.path.exists(input_path):
        print(f"错误：找不到设施文件 {input_path}")
        return []

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    features = data['features'] if 'features' in data else data
    if not features:
        return []

    coords = []
    facilities_info = []

    for feat in features:
        if isinstance(feat, dict) and 'geometry' in feat:
            lon, lat = feat['geometry']['coordinates']
            props = feat['properties']
        else:
            lon, lat = feat.get('coordinates', [0, 0])
            props = feat

        coords.append([lon, lat])
        facilities_info.append({
            "props": props,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })

    tree = KDTree(coords)
    k = min(k, len(coords))
    distances, indices = tree.query([target_lon, target_lat], k=k)

    if k == 1:
        distances, indices = [distances], [indices]

    results = []
    for d, idx in zip(distances, indices):
        info = facilities_info[idx]
        obj_id = info['props'].get('objectId', 'unknown')
        name = info['props'].get('name') or obj_id
        dist_m = round(float(d) * 111320, 2)

        results.append({
            "objectId": obj_id,
            "value": dist_m,
            "level": 1,
            "label": f"最近设施: {name}",
            "style": {"color": "#3b82f6", "opacity": 1.0},
            "description": f"距离查询点约 {dist_m} 米",
            "geometry": info['geometry'],
        })

    output_path = os.path.join(data_dir, 'analysis_result_knn.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    return results


if __name__ == "__main__":
    run_knn_search(103.722, 36.108, k=1)
