import os
import geopandas as gpd
import json
from shapely.geometry import shape, mapping

def identify_blind_spots():
    # 1. 自动获取当前脚本所在的文件夹路径，解决找不到文件的问题
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 拼接文件的完整路径
    boundary_path = os.path.join(current_dir, '05_facilities_or_regions.geojson')
    isochrone_path = os.path.join(current_dir, 'analysis_result_isochrone.json')
    output_path = os.path.join(current_dir, 'analysis_result_blind_spots.json')

    print(f"--- 启动盲区识别算法 ---")
    print(f"正在读取边界数据: {boundary_path}")

    # 2. 读取校园边界
    try:
        boundary_gdf = gpd.read_file(boundary_path).to_crs(epsg=3857)
    except Exception as e:
        print(f"❌ 错误：无法读取边界文件，请确保文件存在且格式正确。{e}")
        return

    # 3. 读取等时圈分析结果
    try:
        with open(isochrone_path, 'r', encoding='utf-8') as f:
            isochrone_data = json.load(f)
    except Exception as e:
        print(f"❌ 错误：无法读取等时圈结果文件。{e}")
        return
    
    # 提取 15 分钟 (level=3) 的覆盖面
    iso_features = [shape(item['geometry']) for item in isochrone_data if item['level'] == 3]
    if not iso_features:
        print("⚠️ 警告：在结果文件中没找到 15 分钟覆盖面数据。")
        return
        
    iso_gdf = gpd.GeoDataFrame(geometry=iso_features, crs="EPSG:4326").to_crs(epsg=3857)

    # 4. 空间运算：融合覆盖范围
    print("正在融合设施覆盖范围...")
    unioned_coverage = iso_gdf.unary_union

    # 5. 空间运算：识别盲区 (边界 - 覆盖面)
    print("正在识别服务盲区...")
    # 确保 boundary 只有一个几何体
    boundary_geom = boundary_gdf.unary_union
    blind_spots_geom = boundary_geom.difference(unioned_coverage)

    # 6. 结果封装
    results = []
    if blind_spots_geom.geom_type == 'MultiPolygon':
        polygons = list(blind_spots_geom.geoms)
    else:
        polygons = [blind_spots_geom]

    for idx, poly in enumerate(polygons):
        # 剔除面积过小的碎屑（小于100平方米）
        if poly.area < 100: continue 

        # 转回经纬度坐标系
        poly_gdf = gpd.GeoSeries([poly], crs="EPSG:3857").to_crs(epsg=4326)
        
        res_item = {
            "objectId": f"blind_spot_{idx+1}",
            "value": round(poly.area, 2),
            "level": 4, 
            "label": "服务覆盖盲区",
            "style": {
                "color": "#6f42c1", # 紫色
                "opacity": 0.7
            },
            "description": f"该区域为步行15分钟服务盲区，面积约 {round(poly.area, 2)} 平方米",
            "geometry": mapping(poly_gdf.iloc[0])
        }
        results.append(res_item)

    # 7. 保存结果
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
# --- 新增：生成 QGIS 专用预览文件 ---
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

    preview_path = os.path.join(current_dir, 'blind_spot_preview.geojson')
    with open(preview_path, 'w', encoding='utf-8') as f:
        json.dump(preview_geojson, f, ensure_ascii=False, indent=4)
    
    print(f"✅ 已生成 QGIS 预览文件: {preview_path}")
    print(f"✅ 算法执行成功！发现 {len(results)} 处盲区。")
    print(f"分析结果已保存至: {output_path}")

if __name__ == "__main__":
    identify_blind_spots()