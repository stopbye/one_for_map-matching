#改代码实现匹配
import pandas as pd
import geopandas as gpd
from gotrackit.map.Net import Net
from gotrackit.MapMatch import MapMatch
from gotrackit.gps.Trajectory import TrajectoryPoints
import os


if __name__ == '__main__':
    # 读取GPS样例数据
    parquet_file_path = r"part-00050-b48df2a5-821b-4dd8-97b1-06dab11d2966.c000"
    gps_df = pd.read_parquet(parquet_file_path)

    # 检查并重命名列
    column_mapping = {
        'numbers': 'agent_id',
        'create_time': 'time',
        'lon': 'lng',
        'latitude': 'lat'
    }
    gps_df.rename(columns=column_mapping, inplace=True)

    # 过滤出特定车辆的数据

    # 确保所有必需的列都存在
    required_columns = ['agent_id', 'time', 'lng', 'lat']
    missing_columns = [col for col in required_columns if col not in gps_df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    # 设置数据类型
    column_types = {
        'agent_id': 'string',
        'time': 'string',
        'lng': 'float64',
        'lat': 'float64'
    }
    gps_df = gps_df.astype(column_types)

    # 利用gps数据构建TrajectoryPoints, 并且对数据进行清洗
    # 使用经纬度坐标系（WGS84），避免与经纬度列不匹配
    tp = TrajectoryPoints(gps_points_df=gps_df, plain_crs='EPSG:4326')
    #tp.lower_frequency(lower_n=2).kf_smooth(o_deviation=0.3)  # 由于样例数据定位频率高且有一定的误差，因此先做间隔采样然后执行滤波平滑
    gps_df = tp.trajectory_data(_type='df')

    # tp.dense(dense_interval=120)  # 由于样例数据是稀疏定位数据，我们在匹配前进行增密处理
    # gps_df = tp.trajectory_data(_type='df')
    # tp.export_html(out_fldr=r'./data/output/match_visualization/QuickStart-Match-1')  # 输出增密前后的轨迹对比

    # 读取路网数据（优先使用已转换为WGS84的数据；若不存在，请使用原始 geojson）
    link_file_path = r'network_link_converted.geojson'
    node_file_path = r'network_node_converted.geojson'
    link = gpd.read_file(link_file_path)
    node = gpd.read_file(node_file_path)

    # 构建Net类、初始化
    my_net = Net(link_gdf=link, node_gdf=node, not_conn_cost=1200)
    my_net.init_net()  # net初始化

    # 构建匹配类
    output_folder = r'./data/output/match_visualization/QuickStart-Match-1'
    os.makedirs(output_folder, exist_ok=True)

    mpm = MapMatch(
        net=my_net,
        gps_buffer=500,
        top_k=20,
        flag_name='general_sample',
        time_format='%Y-%m-%d %H:%M:%S',
        use_heading_inf=True,
        omitted_l=6.0,
        export_html=True,
        del_dwell=False,
        out_fldr=output_folder,
        dense_gps=False,
        gps_radius=15.0
    )

    # 执行匹配（一次）并输出结果
    match_res, warn_info, error_info = mpm.execute(gps_df=gps_df)
    out_dir = r'./data/output/match_visualization/QuickStart-Match-1'
    os.makedirs(out_dir, exist_ok=True)
    match_res.to_csv(fr'{out_dir}/general_match_res.csv', encoding='utf_8_sig', index=False)