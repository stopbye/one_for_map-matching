#改代码用于不同坐标系经纬度的转换
import json
from geojson import Feature, Point, LineString, FeatureCollection, dump
import math

# 常量定义
x_pi = 3.14159265358979324 * 3000.0 / 180.0
pi = 3.1415926535897932384626  # π
a = 6378245.0  # 长半轴
ee = 0.00669342162296594323  # 偏心率平方

def gcj02_to_wgs84(lng, lat):
    """
    GCJ02(火星坐标系)转WGS84
    :param lng: 火星坐标系的经度
    :param lat: 火星坐标系纬度
    :return: 转换后的WGS84坐标
    """
    if out_of_china(lng, lat):
        return [lng, lat]
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
    return [lng * 2 - mglng, lat * 2 - mglat]

def out_of_china(lng, lat):
    """
    判断是否在国内，不在国内不做偏移
    :param lng:
    :param lat:
    :return:
    """
    return not (lng > 73.66 and lng < 135.05 and lat > 3.86 and lat < 53.55)

def _transformlng(lng, lat):
    ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + \
          0.1 * lng * lat + 0.1 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 *
            math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lng * pi) + 40.0 *
            math.sin(lng / 3.0 * pi)) * 2.0 / 3.0
    ret += (150.0 * math.sin(lng / 12.0 * pi) + 300.0 *
            math.sin(lng / 30.0 * pi)) * 2.0 / 3.0
    return ret

def _transformlat(lng, lat):
    ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + \
          0.1 * lng * lat + 0.2 * math.sqrt(math.fabs(lng))
    ret += (20.0 * math.sin(6.0 * lng * pi) + 20.0 *
            math.sin(2.0 * lng * pi)) * 2.0 / 3.0
    ret += (20.0 * math.sin(lat * pi) + 40.0 *
            math.sin(lat / 3.0 * pi)) * 2.0 / 3.0
    ret += (160.0 * math.sin(lat / 12.0 * pi) + 320 *
            math.sin(lat * pi / 30.0)) * 2.0 / 3.0
    return ret

def transform_coordinates(coordinates):
    if isinstance(coordinates[0], list):
        # 处理LineString
        wgs_coords = [gcj02_to_wgs84(lon, lat) for lon, lat in coordinates]
        return wgs_coords
    else:
        # 处理Point
        wgs_coords = gcj02_to_wgs84(coordinates[0], coordinates[1])
        return wgs_coords

def convert_geojson(input_file, output_file):
    with open(input_file, 'r') as f:
        data = json.load(f)

    features = []
    for feature in data['features']:
        geometry = feature['geometry']
        coordinates = geometry['coordinates']

        if geometry['type'] == 'Point':
            new_coordinates = transform_coordinates(coordinates)
            new_geometry = Point(new_coordinates)
        elif geometry['type'] == 'LineString':
            new_coordinates = transform_coordinates(coordinates)
            new_geometry = LineString(new_coordinates)
        else:
            raise ValueError(f"Unsupported geometry type: {geometry['type']}")

        new_feature = Feature(geometry=new_geometry, properties=feature['properties'])
        features.append(new_feature)

    feature_collection = FeatureCollection(features)
    with open(output_file, 'w') as f:
        dump(feature_collection, f)

# 转换network_node.geojson
convert_geojson('network_node.geojson', 'network_node_converted.geojson')

# 转换network_link.geojson
convert_geojson('network_link.geojson', 'network_link_converted.geojson')