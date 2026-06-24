# 智能交通轨迹匹配与交通参数计算 - 一键流水线

本项目提供从路网 CSV 到 HMM 地图匹配与结果可视化的一键化流水线，覆盖：数据构建、坐标系统一、匹配执行与结果导出。

English summary: this repository provides a Python pipeline for road-network conversion, coordinate normalization, HMM map matching, and exportable matching metrics.

## 目录
- pipeline.py：参数化一键脚本
- 实现匹配的代码.py：原匹配脚本（将被 pipeline 替代）
- 得到node和link数据.py / 简单转换数据类型.py / 经纬度转换.py：原子脚本
- requirements.txt：依赖清单

## 快速开始
1. 安装依赖
```bash
pip install -r requirements.txt
```

也可以使用项目配置安装：

```bash
pip install .
```

2. 准备输入
- 路网 CSV：包含字段 from_node,to_node,start_point,end_point,polyline,length
- GPS Parquet：包含 numbers/create_time/lon/latitude 或 agent_id/time/lng/lat

3. 运行流水线
```bash
python pipeline.py --network-csv "./2024-02-10 11-30_network.csv" \
  --gps-parquet ./part-00050-xxxx.parquet \
  --crs-in gcj02 \
  --gps-buffer 500 --top-k 20 --gps-radius 15 \
  --use-heading-inf --omitted-l 6 --del-dwell \
  --out-dir ./data/output
```
- --crs-in：输入路网坐标系（wgs84 或 gcj02）。若为 gcj02，脚本会自动转换为 WGS84。
- HMM 参数：`--gps-buffer/--top-k/--gps-radius/--use-heading-inf/--omitted-l/--del-dwell/--dense-gps`
- 输出：
  - data/output/network/network_node(.csv/.geojson)、network_link(.csv/.geojson)
  - 若 gcj02：生成 network_*_converted.geojson
  - 匹配结果：data/output/match_visualization/QuickStart-Match/general_match_res.csv 与 HTML 可视化
  - 评估指标：match 目录下 `metrics.json`（行数、唯一路段、agent 数、告警/错误 agent 列表）

## 注意事项
- 坐标系务必确认：若路网/轨迹为 GCJ-02，请使用 --crs-in gcj02。
- 若需自定义匹配参数（gps_buffer/top_k/gps_radius 等），可在 pipeline.py 中修改 _map_match 内的 MapMatch 初始化参数。
- 大规模数据建议分片运行（按城市/日期/时间窗），并缓存子图以提升吞吐。

## 质量保障

仓库已配置 GitHub Actions，对 `master` / `main` 分支和 Pull Request 执行基础校验：

- 编译所有 Python 脚本，提前发现语法错误
- 检查依赖清单是否存在关键依赖

下一步建议补充一份脱敏的最小样例数据，并为以下函数添加单元测试：

- `_create_nodes_links_from_network`
- `_gcj02_to_wgs84`
- `_read_network_csv`

## 许可
仅供学习与研究使用。
