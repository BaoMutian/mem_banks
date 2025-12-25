# Memory Bank Visualizer

记忆库与测试结果可视化工具，用于展示各数据集的任务执行结果和提取的记忆。

## 目录结构

```
mem_banks/
├── alfworld/
│   ├── alfworld_memories.jsonl      # 记忆库文件
│   └── *_results.json               # 测试结果文件
├── scienceworld/
│   ├── scienceworld_memories.jsonl
│   └── *_results.json
├── visualize.py                     # 可视化脚本
└── visualization.html               # 生成的网页
```

## 使用方法

```bash
# 生成可视化页面
python visualize.py

# 启动本地服务器查看
python -m http.server 8765

# 浏览器访问
# http://localhost:8765/visualization.html
```

## 功能特性

- **多数据集支持**：标签页切换不同数据集
- **全局统计**：总任务数、成功率、平均步数等
- **按任务类型分组统计**
- **任务详情展开**：查看执行轨迹（动作/观察/思考）
- **记忆展示**：显示每个任务提取的记忆项和使用的检索记忆

## 数据格式

**memories.jsonl**：每行一条记忆，包含 `task_id`、`trajectory`、`memory_items` 等字段

**results.json**：包含 `summary`（统计）和 `results`（各任务详情）

