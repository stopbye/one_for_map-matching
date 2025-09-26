#gotrackit 要求geometry
import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString

# 读取新生成的 CSV 文件（link 与 node）
link_csv_path = r'network_link.csv'
node_csv_path = r'network_node.csv'
link_df = pd.read_csv(link_csv_path)
node_df = pd.read_csv(node_csv_path)

# 该函数将 WKT 字符串转换为 Geometry 对象
def wkt_to_geometry(wkt_str):
    if pd.isna(wkt_str):
        return None
    return gpd.GeoSeries.from_wkt([wkt_str])[0]

# 将 geometry 列转换为 Geometry 类型
link_df['geometry'] = link_df['geometry'].apply(wkt_to_geometry)
node_df['geometry'] = node_df['geometry'].apply(wkt_to_geometry)

# 指定 CRS（使用通用经纬度坐标系标注；若为 GCJ-02，请后续再做转换）
crs = 'EPSG:4326'

# 将 DataFrame 转换为 GeoDataFrame
link_gdf = gpd.GeoDataFrame(link_df, geometry='geometry', crs=crs)
node_gdf = gpd.GeoDataFrame(node_df, geometry='geometry', crs=crs)

# 保存为新的 GeoJSON 文件
link_geojson_path = r'network_link.geojson'
node_geojson_path = r'network_node.geojson'
link_gdf.to_file(link_geojson_path, driver='GeoJSON')
node_gdf.to_file(node_geojson_path, driver='GeoJSON')

print(f"已生成: {link_geojson_path} 与 {node_geojson_path}")