#该代码将原数据分离成node和link
import pandas as pd
from shapely.geometry import Point

# 读取原始网络数据
input_file_path = r'2024-02-10 11-30_network.csv'
df = pd.read_csv(input_file_path)

# 定义一个函数将坐标字符串转换为 Point 对象
def create_point(coord_str):
    if pd.isna(coord_str):
        return None
    # 去掉 POINT ( 和 )，然后分割字符串
    coord_str = coord_str.replace('POINT (', '').replace(')', '')
    lon, lat = map(float, coord_str.split())
    return Point(lon, lat)

# 创建一个新的 DataFrame 来存储节点信息
nodes = []

# 处理 from_node 和 start_point
for index, row in df.iterrows():
    from_node = int(row['from_node'])
    start_point = row['start_point']
    if pd.notna(start_point):
        point = create_point(start_point)
        nodes.append({'node_id': from_node, 'geometry': point})

# 处理 to_node 和 end_point
for index, row in df.iterrows():
    to_node = int(row['to_node'])
    end_point = row['end_point']
    if pd.notna(end_point):
        point = create_point(end_point)
        nodes.append({'node_id': to_node, 'geometry': point})

# 将节点信息转换为 DataFrame
nodes_df = pd.DataFrame(nodes)

# 去除重复的节点
nodes_df.drop_duplicates(subset=['node_id'], keep='first', inplace=True)

# 将 geometry 列转换为 WKT 字符串
nodes_df['geometry'] = nodes_df['geometry'].apply(lambda p: p.wkt if p else None)

# 保存到新的 CSV 文件
output_file_path = r'network_node.csv'
nodes_df.to_csv(output_file_path, index=False)

print(f"新文件已生成并保存到 {output_file_path}")

import pandas as pd
from shapely.geometry import LineString

# 读取原始网络数据
input_file_path = r'2024-02-10 11-30_network.csv'
df = pd.read_csv(input_file_path)

# 定义一个函数将 polyline 字符串转换为 LineString 对象
def create_linestring(polyline_str):
    if pd.isna(polyline_str):
        return None
    # 去掉 LINESTRING ( 和 )，然后分割字符串
    polyline_str = polyline_str.replace('LINESTRING (', '').replace(')', '')
    coords = [tuple(map(float, point.split())) for point in polyline_str.split(', ')]
    return LineString(coords)

# 创建一个新的 DataFrame 来存储链接信息
links = []

# 处理每一行数据
for index, row in df.iterrows():
    link_id = f"link_{index + 1}"  # 自动生成 link_id
    from_node = int(row['from_node'])
    to_node = int(row['to_node'])
    dir = 1
    length = row['length']
    polyline = row['polyline']
    if pd.notna(polyline):
        linestring = create_linestring(polyline)
        links.append({
            'link_id': link_id,
            'from_node': from_node,
            'to_node': to_node,
            'dir': dir,
            'length': length,
            'geometry': linestring
        })

# 将链接信息转换为 DataFrame
links_df = pd.DataFrame(links)

# 将 geometry 列转换为 WKT 字符串
links_df['geometry'] = links_df['geometry'].apply(lambda l: l.wkt if l else None)

# 保存到新的 CSV 文件
output_file_path = r'network_link.csv'
links_df.to_csv(output_file_path, index=False)

print(f"新文件已生成并保存到 {output_file_path}")
