import argparse
import os
from typing import Tuple

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString

# Optional: speed up GEOS ops if available


def _ensure_dir(path: str) -> None:
    """确保目录存在（不存在则创建）。

    参数:
        path: 目录路径
    """
    if path and not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def _read_network_csv(network_csv_path: str) -> pd.DataFrame:
    """读取原始路网 CSV。

    期望字段: from_node/to_node/start_point/end_point/polyline/length。
    """
    if not os.path.exists(network_csv_path):
        raise FileNotFoundError(f"Network CSV not found: {network_csv_path}")
    return pd.read_csv(network_csv_path)


def _create_nodes_links_from_network(
    df: pd.DataFrame,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """从路网表构建节点与边表（WKT 几何）。

    - 节点: 由 start_point/end_point 的 POINT 派生；按 node_id 去重。
    - 边: 由 polyline 的 LINESTRING 派生；自动生成 link_id。
    """
    # 节点: start/end 点坐标解析
    def create_point(coord_str: str):
        if pd.isna(coord_str):
            return None
        s = coord_str.replace('POINT (', '').replace(')', '')
        lon, lat = map(float, s.split())
        return Point(lon, lat)

    nodes = []
    for _, row in df.iterrows():
        if pd.notna(row.get('start_point')):
            nodes.append({'node_id': int(row['from_node']), 'geometry': create_point(row['start_point'])})
    for _, row in df.iterrows():
        if pd.notna(row.get('end_point')):
            nodes.append({'node_id': int(row['to_node']), 'geometry': create_point(row['end_point'])})

    nodes_df = pd.DataFrame(nodes)
    if not nodes_df.empty:
        nodes_df.drop_duplicates(subset=['node_id'], keep='first', inplace=True)
        nodes_df['geometry'] = nodes_df['geometry'].apply(lambda p: p.wkt if p else None)

    # 边: polyline 解析为 LineString
    def create_linestring(polyline_str: str):
        if pd.isna(polyline_str):
            return None
        s = polyline_str.replace('LINESTRING (', '').replace(')', '')
        coords = [tuple(map(float, pt.split())) for pt in s.split(', ')]
        return LineString(coords)

    links = []
    for idx, row in df.iterrows():
        if pd.notna(row.get('polyline')):
            links.append({
                'link_id': f"link_{idx + 1}",
                'from_node': int(row['from_node']),
                'to_node': int(row['to_node']),
                'dir': 1,
                'length': row.get('length'),
                'geometry': create_linestring(row['polyline'])
            })

    links_df = pd.DataFrame(links)
    if not links_df.empty:
        links_df['geometry'] = links_df['geometry'].apply(lambda l: l.wkt if l else None)

    return nodes_df, links_df


def _export_csv(nodes_df: pd.DataFrame, links_df: pd.DataFrame, out_dir: str) -> Tuple[str, str]:
    """导出节点/边 CSV。

    返回: (node_csv, link_csv)
    """
    _ensure_dir(out_dir)
    node_csv = os.path.join(out_dir, 'network_node.csv')
    link_csv = os.path.join(out_dir, 'network_link.csv')
    nodes_df.to_csv(node_csv, index=False)
    links_df.to_csv(link_csv, index=False)
    return node_csv, link_csv


def _wkt_to_geometry(wkt_str: str):
    """WKT 字符串转几何对象。"""
    if pd.isna(wkt_str):
        return None
    return gpd.GeoSeries.from_wkt([wkt_str])[0]


def _csv_to_geojson(csv_path: str, geom_col: str, out_geojson: str, crs_epsg: str) -> str:
    """将包含 WKT 的 CSV 转为 GeoJSON（指定 CRS 标签）。"""
    df = pd.read_csv(csv_path)
    if geom_col not in df.columns:
        raise ValueError(f"Missing geometry column in {csv_path}")
    df['geometry'] = df['geometry'].apply(_wkt_to_geometry)
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs=crs_epsg)
    _ensure_dir(os.path.dirname(out_geojson))
    gdf.to_file(out_geojson, driver='GeoJSON')
    return out_geojson


# GCJ-02 -> WGS84 conversion helpers
import math


def _out_of_china(lng: float, lat: float) -> bool:
    """判断坐标是否在中国境内（用于 GCJ 偏移判断）。"""
    return not (73.66 < lng < 135.05 and 3.86 < lat < 53.55)


def _transformlng(lng: float, lat: float) -> float:
    pi = math.pi
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + 0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 * math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * pi) + 40.0 * math.sin(lng / 3.0 * pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * pi) + 300.0 * math.sin(lng / 30.0 * pi)) * 2.0 / 3.0
    return ret


def _transformlat(lng: float, lat: float) -> float:
    pi = math.pi
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + 0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 * math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * pi) + 40.0 * math.sin(lat / 3.0 * pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * pi) + 320 * math.sin(lat * pi / 30.0)) * 2.0 / 3.0
    return ret


def _gcj02_to_wgs84(lng: float, lat: float) -> Tuple[float, float]:
    """GCJ-02 转 WGS84（经纬度）。"""
    a = 6378245.0
    ee = 0.00669342162296594323
    pi = math.pi
    if _out_of_china(lng, lat):
        return lng, lat
    dlat = _transformlat(lng - 105.0, lat - 35.0)
    dlng = _transformlng(lng - 105.0, lat - 35.0)
    radlat = lat / 180.0 * pi
    magic = math.sin(radlat)
    magic = 1 - ee * magic * magic
    sqrtmagic = math.sqrt(magic)
    dlat = (dlat * 180.0) / ((a * (1 - ee)) / (magic * sqrtmagic) * pi)
    dlng = (dlng * 180.0) / (a / sqrtmagic * math.cos(radlat) * pi)
    mglat = lat + dlat
    mglng = lng + dlng
    return lng * 2 - mglng, lat * 2 - mglat


def _convert_geojson_gcj02_to_wgs84(input_geojson: str, output_geojson: str) -> str:
    """将 GeoJSON 中的 Point/LineString 坐标从 GCJ-02 转为 WGS84。"""
    with open(input_geojson, 'r', encoding='utf-8') as f:
        import json
        data = json.load(f)
    features = []
    for feat in data['features']:
        geom = feat['geometry']
        if geom['type'] == 'Point':
            lon, lat = geom['coordinates']
            nlng, nlat = _gcj02_to_wgs84(lon, lat)
            new_coords = [nlng, nlat]
        elif geom['type'] == 'LineString':
            new_coords = [[_gcj02_to_wgs84(lon, lat)[0], _gcj02_to_wgs84(lon, lat)[1]] for lon, lat in geom['coordinates']]
        else:
            raise ValueError(f"Unsupported geometry type: {geom['type']}")
        features.append({'type': 'Feature', 'properties': feat.get('properties', {}), 'geometry': {'type': geom['type'], 'coordinates': new_coords}})
    out = {'type': 'FeatureCollection', 'features': features}
    with open(output_geojson, 'w', encoding='utf-8') as f:
        import json
        json.dump(out, f, ensure_ascii=False)
    return output_geojson


def _map_match(
    gps_parquet: str,
    node_geojson: str,
    link_geojson: str,
    output_dir: str,
    time_format: str = '%Y-%m-%d %H:%M:%S',
    gps_buffer: float = 500.0,
    top_k: int = 20,
    use_heading_inf: bool = True,
    omitted_l: float = 6.0,
    del_dwell: bool = False,
    dense_gps: bool = False,
    gps_radius: float = 15.0
) -> str:
    """执行地图匹配（HMM/Viterbi），并导出结果与基础指标。

    参数对应 gotrackit 的 MapMatch 关键超参，可通过 CLI 传入。
    """
    from gotrackit.map.Net import Net
    from gotrackit.MapMatch import MapMatch
    from gotrackit.gps.Trajectory import TrajectoryPoints

    if not os.path.exists(gps_parquet):
        raise FileNotFoundError(f"GPS parquet not found: {gps_parquet}")
    gps_df = pd.read_parquet(gps_parquet)

    column_mapping = {"numbers": "agent_id", "create_time": "time", "lon": "lng", "latitude": "lat"}
    gps_df.rename(columns=column_mapping, inplace=True)
    required_columns = ['agent_id', 'time', 'lng', 'lat']
    missing = [c for c in required_columns if c not in gps_df.columns]
    if missing:
        raise ValueError(f"Missing columns in GPS data: {missing}")
    gps_df = gps_df.astype({'agent_id': 'string', 'time': 'string', 'lng': 'float64', 'lat': 'float64'})

    # GPS 为经纬度，使用 WGS84
    tp = TrajectoryPoints(gps_points_df=gps_df, plain_crs='EPSG:4326')
    gps_df = tp.trajectory_data(_type='df')

    link = gpd.read_file(link_geojson)
    node = gpd.read_file(node_geojson)

    net = Net(link_gdf=link, node_gdf=node, not_conn_cost=1200)
    net.init_net()

    _ensure_dir(output_dir)
    mpm = MapMatch(
        net=net,
        gps_buffer=gps_buffer,
        top_k=top_k,
        flag_name='general_sample',
        time_format=time_format,
        use_heading_inf=use_heading_inf,
        omitted_l=omitted_l,
        export_html=True,
        del_dwell=del_dwell,
        out_fldr=output_dir,
        dense_gps=dense_gps,
        gps_radius=gps_radius
    )

    match_res, warn_info, error_info = mpm.execute(gps_df=gps_df)
    out_csv = os.path.join(output_dir, 'general_match_res.csv')
    match_res.to_csv(out_csv, encoding='utf_8_sig', index=False)

    # 基础评估指标输出（不影响主流程）
    try:
        metrics = {
            'rows': int(len(match_res)),
            'unique_agents': int(match_res['agent_id'].nunique()) if 'agent_id' in match_res.columns else None,
            'unique_links': int(match_res['link_id'].nunique()) if 'link_id' in match_res.columns else None,
            'warn_agents': list(warn_info.keys()) if isinstance(warn_info, dict) else None,
            'error_agents': error_info if isinstance(error_info, (list, tuple)) else None
        }
        import json
        with open(os.path.join(output_dir, 'metrics.json'), 'w', encoding='utf-8') as f:
            json.dump(metrics, f, ensure_ascii=False, indent=2)
    except Exception as e:
        # 指标写入失败不阻断主流程
        print(f"Warn: failed to write metrics.json due to: {e}")

    return out_csv


def main():
    """命令行入口：构建路网、坐标转换、执行地图匹配并导出结果。"""
    parser = argparse.ArgumentParser(description='End-to-end pipeline: network build, CRS, map matching')
    parser.add_argument('--network-csv', required=True, help='Path to raw network CSV (from_node/to_node/start_point/end_point/polyline)')
    parser.add_argument('--gps-parquet', required=True, help='Path to GPS parquet file')
    parser.add_argument('--crs-in', default='wgs84', choices=['wgs84', 'gcj02'], help='CRS of input network coordinates')
    parser.add_argument('--out-dir', default='./data/output', help='Output directory')
    # Map matching params
    parser.add_argument('--gps-buffer', type=float, default=500.0)
    parser.add_argument('--top-k', type=int, default=20)
    parser.add_argument('--use-heading-inf', action='store_true', default=True)
    parser.add_argument('--no-use-heading-inf', dest='use_heading_inf', action='store_false')
    parser.add_argument('--omitted-l', type=float, default=6.0)
    parser.add_argument('--del-dwell', action='store_true', default=False)
    parser.add_argument('--dense-gps', action='store_true', default=False)
    parser.add_argument('--gps-radius', type=float, default=15.0)
    args = parser.parse_args()

    out_dir = os.path.abspath(args.out_dir)
    network_out_dir = os.path.join(out_dir, 'network')
    match_out_dir = os.path.join(out_dir, 'match_visualization', 'QuickStart-Match')

    _ensure_dir(out_dir)
    _ensure_dir(network_out_dir)
    _ensure_dir(match_out_dir)

    # 1) Build nodes/links CSV
    df = _read_network_csv(args.network_csv)
    nodes_df, links_df = _create_nodes_links_from_network(df)
    node_csv, link_csv = _export_csv(nodes_df, links_df, network_out_dir)

    # 2) CSV -> GeoJSON (assume input CRS per args.crs_in)
    base_node_geojson = os.path.join(network_out_dir, 'network_node.geojson')
    base_link_geojson = os.path.join(network_out_dir, 'network_link.geojson')
    crs = 'EPSG:4326'  # store as lon/lat schema regardless of GCJ/WGS label
    _csv_to_geojson(node_csv, 'geometry', base_node_geojson, crs)
    _csv_to_geojson(link_csv, 'geometry', base_link_geojson, crs)

    # 3) CRS normalization: if GCJ-02, convert to WGS84
    if args.crs_in.lower() == 'gcj02':
        node_geojson = os.path.join(network_out_dir, 'network_node_converted.geojson')
        link_geojson = os.path.join(network_out_dir, 'network_link_converted.geojson')
        _convert_geojson_gcj02_to_wgs84(base_node_geojson, node_geojson)
        _convert_geojson_gcj02_to_wgs84(base_link_geojson, link_geojson)
    else:
        node_geojson = base_node_geojson
        link_geojson = base_link_geojson

    # 4) Map matching
    out_csv = _map_match(
        gps_parquet=os.path.abspath(args.gps_parquet),
        node_geojson=node_geojson,
        link_geojson=link_geojson,
        output_dir=match_out_dir,
        gps_buffer=args.gps_buffer,
        top_k=args.top_k,
        use_heading_inf=args.use_heading_inf,
        omitted_l=args.omitted_l,
        del_dwell=args.del_dwell,
        dense_gps=args.dense_gps,
        gps_radius=args.gps_radius,
    )
    print(f"Match result saved to: {out_csv}")


if __name__ == '__main__':
    main()


