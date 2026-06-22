import os
import geopandas as gpd
import json
from shapely.geometry import shape, mapping

from data_config import get_polygons_path, get_data_dir


def identify_blind_spots(data_dir=None):
    data_dir = get_data_dir(data_dir)
    boundary_path = get_polygons_path(data_dir)
    isochrone_path = os.path.join(data_dir, 'analysis_result_isochrone.json')
    output_path = os.path.join(data_dir, 'analysis_result_blind_spots.json')

    print(f"--- 启动盲区识别算法 ---")
    print(f"正在读取边界数据: {boundary_path}")

    if not os.path.exists(boundary_path):
        print(f"错误：找不到边界文件 {boundary_path}")
        return []

    if not os.path.exists(isochrone_path):
        print(f"错误：找不到等时圈结果文件 {isochrone_path}，请先运行等时圈分析")
        return []

    try:
        boundary_gdf = gpd.read_file(boundary_path).to_crs(epsg=3857)
    except Exception as e:
        print(f"错误：无法读取边界文件，请确保文件存在且格式正确。{e}")
        return []

    try:
        with open(isochrone_path, 'r', encoding='utf-8') as f:
            isochrone_data = json.load(f)
    except Exception as e:
        print(f"错误：无法读取等时圈结果文件。{e}")
        return []

    iso_features = [shape(item['geometry']) for item in isochrone_data if item['level'] == 3]
    if not iso_features:
        print("警告：在结果文件中没找到 15 分钟覆盖面数据。")
        return []

    iso_gdf = gpd.GeoDataFrame(geometry=iso_features, crs="EPSG:4326").to_crs(epsg=3857)

    print("正在融合设施覆盖范围...")
    unioned_coverage = iso_gdf.unary_union

    print("正在识别服务盲区...")
    boundary_geom = boundary_gdf.unary_union
    blind_spots_geom = boundary_geom.difference(unioned_coverage)

    results = []
    if blind_spots_geom.geom_type == 'MultiPolygon':
        polygons = list(blind_spots_geom.geoms)
    elif blind_spots_geom.geom_type == 'Polygon':
        polygons = [blind_spots_geom]
    else:
        polygons = []

    for idx, poly in enumerate(polygons):
        if poly.area < 100:
            continue

        poly_gdf = gpd.GeoSeries([poly], crs="EPSG:3857").to_crs(epsg=4326)

        res_item = {
            "objectId": f"blind_spot_{idx + 1}",
            "value": round(poly.area, 2),
            "level": 4,
            "label": "服务覆盖盲区",
            "style": {
                "color": "#6f42c1",
                "opacity": 0.7
            },
            "description": f"该区域为步行15分钟服务盲区，面积约 {round(poly.area, 2)} 平方米",
            "geometry": mapping(poly_gdf.iloc[0])
        }
        results.append(res_item)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    preview_geojson = {
        "type": "FeatureCollection",
        "features": []
    }
    for item in results:
        feature = {
            "type": "Feature",
            "properties": {
                "objectId": item["objectId"],
                "area": item["value"],
                "label": item["label"]
            },
            "geometry": item["geometry"]
        }
        preview_geojson["features"].append(feature)

    preview_path = os.path.join(data_dir, 'blind_spot_preview.geojson')
    with open(preview_path, 'w', encoding='utf-8') as f:
        json.dump(preview_geojson, f, ensure_ascii=False, indent=4)

    print(f"算法执行成功！发现 {len(results)} 处盲区。")
    print(f"分析结果已保存至: {output_path}")
    return results


if __name__ == "__main__":
    identify_blind_spots()