#!/usr/bin/env python3
"""
可视化记忆库和测试结果的脚本
生成一个交互式HTML页面展示各数据集的结果

目录结构:
  mem_banks/
    ├── dataset1/
    │   ├── model1/
    │   │   ├── *_memories.jsonl
    │   │   └── *_results.json
    │   └── model2/
    │       ├── *_memories.jsonl
    │       └── *_results.json
    └── dataset2/
        └── ...
"""

import json
import os
from pathlib import Path
from datetime import datetime
import html


def load_memories(jsonl_path: str) -> dict:
    """加载memories jsonl文件"""
    memories = {}
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                mem = json.loads(line)
                memories[mem['task_id']] = mem
    return memories


def load_results(json_path: str) -> dict:
    """加载results json文件"""
    with open(json_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def find_dataset_files(base_dir: str) -> dict:
    """查找各数据集的文件（新目录结构：dataset/model/files）"""
    datasets = {}
    
    for dataset_dir in Path(base_dir).iterdir():
        if not dataset_dir.is_dir() or dataset_dir.name.startswith('.'):
            continue
        
        dataset_name = dataset_dir.name
        
        # 检查是否有模型子目录
        has_model_subdirs = False
        for item in dataset_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                has_model_subdirs = True
                break
        
        if has_model_subdirs:
            # 新结构：dataset/model/files
            for model_dir in dataset_dir.iterdir():
                if not model_dir.is_dir() or model_dir.name.startswith('.'):
                    continue
                
                model_name = model_dir.name
                memories_file = None
                results_file = None
                
                for file in model_dir.iterdir():
                    if file.suffix == '.jsonl' and ('memories' in file.name or 'mems' in file.name):
                        memories_file = str(file)
                    elif file.suffix == '.json' and 'results' in file.name:
                        results_file = str(file)
                
                if memories_file and results_file:
                    key = f"{dataset_name}/{model_name}"
                    datasets[key] = {
                        'dataset': dataset_name,
                        'model': model_name,
                        'memories': memories_file,
                        'results': results_file
                    }
        else:
            # 旧结构：dataset/files（兼容）
            memories_file = None
            results_file = None
            
            for file in dataset_dir.iterdir():
                if file.suffix == '.jsonl' and ('memories' in file.name or 'mems' in file.name):
                    memories_file = str(file)
                elif file.suffix == '.json' and 'results' in file.name:
                    results_file = str(file)
            
            if memories_file and results_file:
                datasets[dataset_name] = {
                    'dataset': dataset_name,
                    'model': 'default',
                    'memories': memories_file,
                    'results': results_file
                }
    
    return datasets


def escape_html(text: str) -> str:
    """转义HTML特殊字符"""
    return html.escape(str(text))


def generate_html(datasets_data: dict) -> str:
    """生成HTML页面"""
    
    html_content = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Memory Bank Visualizer</title>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0d1117;
            --bg-secondary: #161b22;
            --bg-tertiary: #21262d;
            --bg-card: #1c2128;
            --border-color: #30363d;
            --text-primary: #e6edf3;
            --text-secondary: #8b949e;
            --text-muted: #6e7681;
            --accent-green: #3fb950;
            --accent-green-dim: #238636;
            --accent-red: #f85149;
            --accent-red-dim: #da3633;
            --accent-blue: #58a6ff;
            --accent-purple: #a371f7;
            --accent-orange: #d29922;
            --accent-cyan: #39c5cf;
            --accent-pink: #f778ba;
            --gradient-1: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            --gradient-2: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            --gradient-3: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Noto Sans SC', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(ellipse at 20% 20%, rgba(102, 126, 234, 0.15) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 80%, rgba(118, 75, 162, 0.1) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 50%, rgba(79, 172, 254, 0.05) 0%, transparent 70%);
            pointer-events: none;
            z-index: -1;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 2rem;
        }

        header {
            text-align: center;
            margin-bottom: 3rem;
            padding: 2rem;
            background: var(--bg-secondary);
            border-radius: 16px;
            border: 1px solid var(--border-color);
            position: relative;
            overflow: hidden;
        }

        header::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: var(--gradient-1);
        }

        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: var(--gradient-1);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
        }

        .subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }

        .tabs {
            display: flex;
            gap: 0.5rem;
            margin-bottom: 2rem;
            background: var(--bg-secondary);
            padding: 0.5rem;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            flex-wrap: wrap;
        }

        .tab {
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.2s ease;
            border: none;
            background: transparent;
            color: var(--text-secondary);
            font-size: 0.9rem;
            font-family: inherit;
        }

        .tab:hover {
            background: var(--bg-tertiary);
            color: var(--text-primary);
        }

        .tab.active {
            background: var(--gradient-1);
            color: white;
        }

        .tab .model-badge {
            font-size: 0.75rem;
            opacity: 0.8;
            display: block;
            margin-top: 2px;
        }

        .dataset-content {
            display: none;
        }

        .dataset-content.active {
            display: block;
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        }

        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            font-family: 'JetBrains Mono', monospace;
        }

        .stat-value.success { color: var(--accent-green); }
        .stat-value.warning { color: var(--accent-orange); }
        .stat-value.info { color: var(--accent-blue); }
        .stat-value.danger { color: var(--accent-red); }
        .stat-value.pink { color: var(--accent-pink); }

        .stat-label {
            color: var(--text-secondary);
            font-size: 0.9rem;
            margin-top: 0.5rem;
        }

        .config-panel {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }

        .config-panel h3 {
            color: var(--accent-purple);
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
        }

        .config-item {
            background: var(--bg-tertiary);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }

        .config-key {
            color: var(--accent-cyan);
        }

        .config-value {
            color: var(--text-primary);
            margin-left: 0.5rem;
        }

        .task-type-stats {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }

        .task-type-stats h3 {
            color: var(--accent-orange);
            margin-bottom: 1rem;
        }

        .task-type-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1rem;
        }

        .task-type-card {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 1rem;
            border-left: 3px solid var(--accent-purple);
        }

        .task-type-name {
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: var(--accent-blue);
        }

        .task-type-detail {
            display: flex;
            justify-content: space-between;
            font-size: 0.85rem;
            color: var(--text-secondary);
            padding: 0.25rem 0;
        }

        .results-section h2 {
            color: var(--text-primary);
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }

        .result-card {
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            margin-bottom: 1.5rem;
            overflow: hidden;
            transition: box-shadow 0.2s ease;
        }

        .result-card:hover {
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.3);
        }

        .result-header {
            padding: 1.25rem 1.5rem;
            background: var(--bg-tertiary);
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: pointer;
            border-bottom: 1px solid var(--border-color);
        }

        .result-header:hover {
            background: var(--bg-card);
        }

        .result-title {
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .result-id {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }

        .status-badge.success {
            background: var(--accent-green-dim);
            color: var(--accent-green);
        }

        .status-badge.fail {
            background: var(--accent-red-dim);
            color: var(--accent-red);
        }

        .result-meta {
            display: flex;
            gap: 1.5rem;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }

        .meta-item {
            display: flex;
            align-items: center;
            gap: 0.25rem;
        }

        .result-body {
            padding: 1.5rem;
            display: none;
        }

        .result-body.expanded {
            display: block;
            animation: slideDown 0.3s ease;
        }

        @keyframes slideDown {
            from { opacity: 0; max-height: 0; }
            to { opacity: 1; max-height: 5000px; }
        }

        .goal-box {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1.5rem;
            border-left: 3px solid var(--accent-blue);
        }

        .goal-label {
            color: var(--accent-blue);
            font-weight: 600;
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
        }

        .goal-text {
            color: var(--text-primary);
            white-space: pre-wrap;
        }

        .trajectory-section {
            margin-bottom: 1.5rem;
        }

        .section-title {
            color: var(--accent-cyan);
            font-weight: 600;
            margin-bottom: 1rem;
            font-size: 0.95rem;
        }

        .trajectory-item {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
            margin-bottom: 1rem;
            padding: 1rem;
            background: var(--bg-tertiary);
            border-radius: 8px;
        }

        .action-box, .observation-box, .thought-box {
            padding: 0.75rem;
            border-radius: 6px;
            font-size: 0.85rem;
            font-family: 'JetBrains Mono', monospace;
        }

        .action-box {
            background: rgba(163, 113, 247, 0.15);
            border: 1px solid rgba(163, 113, 247, 0.3);
        }

        .observation-box {
            background: rgba(57, 197, 207, 0.15);
            border: 1px solid rgba(57, 197, 207, 0.3);
        }

        .thought-box {
            background: rgba(210, 153, 34, 0.15);
            border: 1px solid rgba(210, 153, 34, 0.3);
            grid-column: 1 / -1;
        }

        .box-label {
            font-size: 0.75rem;
            text-transform: uppercase;
            margin-bottom: 0.5rem;
            font-weight: 600;
        }

        .action-box .box-label { color: var(--accent-purple); }
        .observation-box .box-label { color: var(--accent-cyan); }
        .thought-box .box-label { color: var(--accent-orange); }

        .box-content {
            color: var(--text-primary);
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 200px;
            overflow-y: auto;
        }

        .memories-section {
            margin-top: 1.5rem;
            padding-top: 1.5rem;
            border-top: 1px solid var(--border-color);
        }

        .memory-card {
            background: var(--bg-tertiary);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
            border-left: 3px solid var(--accent-green);
        }

        .memory-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.5rem;
        }

        .memory-title {
            color: var(--accent-green);
            font-weight: 600;
        }

        .memory-stats {
            display: flex;
            gap: 0.5rem;
        }

        .ref-badge {
            font-size: 0.75rem;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-family: 'JetBrains Mono', monospace;
        }

        .ref-count {
            background: rgba(88, 166, 255, 0.2);
            color: var(--accent-blue);
        }

        .ref-success-rate {
            background: rgba(63, 185, 80, 0.2);
            color: var(--accent-green);
        }

        .ref-success-rate.low {
            background: rgba(248, 81, 73, 0.2);
            color: var(--accent-red);
        }

        .ref-success-rate.medium {
            background: rgba(210, 153, 34, 0.2);
            color: var(--accent-orange);
        }

        .memory-description {
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-bottom: 0.5rem;
            font-style: italic;
        }

        .memory-content {
            color: var(--text-primary);
            font-size: 0.9rem;
            line-height: 1.6;
        }

        .used-memories-section {
            margin-top: 1rem;
            padding: 1rem;
            background: rgba(88, 166, 255, 0.1);
            border: 1px solid rgba(88, 166, 255, 0.3);
            border-radius: 8px;
        }

        .used-memory-item-wrapper {
            margin-bottom: 0.5rem;
        }

        .used-memory-item-wrapper:last-child {
            margin-bottom: 0;
        }

        .used-memory-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem;
            background: var(--bg-tertiary);
            border-radius: 6px;
            cursor: pointer;
            transition: background 0.2s ease;
        }

        .used-memory-item:hover {
            background: var(--bg-card);
        }

        .used-mem-info {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
        }

        .used-mem-id {
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: var(--accent-blue);
        }

        .used-mem-query {
            font-size: 0.8rem;
            color: var(--text-secondary);
        }

        .used-mem-badges {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .expand-btn {
            font-size: 0.75rem;
            color: var(--text-muted);
            transition: transform 0.2s ease;
        }

        .used-memory-item-wrapper.expanded .expand-btn {
            transform: rotate(180deg);
        }

        .similarity-badge {
            background: var(--accent-blue);
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-family: 'JetBrains Mono', monospace;
        }

        .used-memory-detail {
            display: none;
            padding: 1rem;
            margin-top: 0.5rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            animation: slideDown 0.3s ease;
        }

        .used-memory-detail.expanded {
            display: block;
        }

        .used-mem-task-info {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 0.5rem;
            padding: 0.25rem 0;
        }

        .detail-label {
            color: var(--accent-cyan);
            font-weight: 500;
        }

        .used-mem-items-title {
            color: var(--accent-green);
            font-weight: 600;
            margin: 1rem 0 0.5rem 0;
            padding-top: 0.5rem;
            border-top: 1px dashed var(--border-color);
        }

        .used-mem-item-card {
            background: var(--bg-tertiary);
            border-radius: 6px;
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            border-left: 3px solid var(--accent-purple);
        }

        .used-mem-item-card:last-child {
            margin-bottom: 0;
        }

        .used-mem-item-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 0.5rem;
            flex-wrap: wrap;
        }

        .used-mem-item-title {
            color: var(--accent-purple);
            font-weight: 600;
            flex: 1;
        }

        .used-mem-item-desc {
            color: var(--text-secondary);
            font-size: 0.85rem;
            font-style: italic;
            margin-bottom: 0.5rem;
        }

        .used-mem-item-content {
            color: var(--text-primary);
            font-size: 0.85rem;
            line-height: 1.5;
        }

        .expand-icon {
            transition: transform 0.2s ease;
            color: var(--text-secondary);
        }

        .result-card.expanded .expand-icon {
            transform: rotate(180deg);
        }

        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-tertiary);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb {
            background: var(--border-color);
            border-radius: 4px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-muted);
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }

            h1 {
                font-size: 1.75rem;
            }

            .trajectory-item {
                grid-template-columns: 1fr;
            }

            .result-header {
                flex-direction: column;
                gap: 1rem;
                align-items: flex-start;
            }

            .result-meta {
                flex-wrap: wrap;
            }
        }

        .step-indicator {
            width: 28px;
            height: 28px;
            background: var(--gradient-1);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.75rem;
            font-weight: 600;
            color: white;
            flex-shrink: 0;
        }

        .trajectory-step {
            display: flex;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .trajectory-step-content {
            flex: 1;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🧠 Memory Bank Visualizer</h1>
            <p class="subtitle">测试结果与记忆库可视化分析工具</p>
        </header>

        <div class="tabs">
'''
    
    # 生成标签页
    for i, (key, data) in enumerate(datasets_data.items()):
        active = 'active' if i == 0 else ''
        dataset_name = data['info']['dataset']
        model_name = data['info']['model']
        safe_key = key.replace('/', '_')
        html_content += f'''            <button class="tab {active}" onclick="showDataset('{safe_key}')">
                <span>{escape_html(dataset_name)}</span>
                <span class="model-badge">{escape_html(model_name)}</span>
            </button>
'''
    
    html_content += '''        </div>

'''
    
    # 为每个数据集生成内容
    for i, (key, data) in enumerate(datasets_data.items()):
        results_data = data['results']
        memories_data = data['memories']
        summary = results_data.get('summary', {})
        config = results_data.get('config', {})
        
        active = 'active' if i == 0 else ''
        safe_key = key.replace('/', '_')
        
        total = summary.get('total_games', summary.get('total_episodes', 0))
        successes = summary.get('successes', 0)
        success_rate = summary.get('success_rate', 0)
        avg_steps = summary.get('avg_steps', 0)
        avg_score = summary.get('avg_score', None)
        
        # 计算记忆统计
        total_memories = len(memories_data)
        total_ref_count = 0
        total_ref_success = 0
        for mem in memories_data.values():
            for item in mem.get('memory_items', []):
                ref_count = item.get('reference_count', 0)
                ref_success = item.get('reference_success_count', 0)
                total_ref_count += ref_count
                total_ref_success += ref_success
        
        overall_ref_success_rate = (total_ref_success / total_ref_count * 100) if total_ref_count > 0 else 0
        
        html_content += f'''        <div class="dataset-content {active}" id="dataset-{safe_key}">
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value info">{total}</div>
                    <div class="stat-label">总任务数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value success">{successes}</div>
                    <div class="stat-label">成功数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value {"success" if success_rate >= 50 else "warning" if success_rate >= 20 else "danger"}">{success_rate:.1f}%</div>
                    <div class="stat-label">成功率</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value info">{avg_steps:.1f}</div>
                    <div class="stat-label">平均步数</div>
                </div>
'''
        
        if avg_score is not None:
            html_content += f'''                <div class="stat-card">
                    <div class="stat-value warning">{avg_score:.1f}</div>
                    <div class="stat-label">平均分数</div>
                </div>
'''
        
        html_content += f'''                <div class="stat-card">
                    <div class="stat-value info">{total_memories}</div>
                    <div class="stat-label">记忆条目</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value pink">{total_ref_count}</div>
                    <div class="stat-label">总被引次数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value {"success" if overall_ref_success_rate >= 50 else "warning" if overall_ref_success_rate >= 20 else "danger"}">{overall_ref_success_rate:.1f}%</div>
                    <div class="stat-label">总被引成功率</div>
                </div>
            </div>

            <div class="config-panel">
                <h3>⚙️ 配置信息</h3>
                <div class="config-grid">
                    <div class="config-item"><span class="config-key">模型:</span><span class="config-value">{escape_html(results_data.get("model", "N/A"))}</span></div>
                    <div class="config-item"><span class="config-key">时间:</span><span class="config-value">{escape_html(results_data.get("timestamp", "N/A"))}</span></div>
                    <div class="config-item"><span class="config-key">温度:</span><span class="config-value">{config.get("llm", {}).get("temperature", "N/A")}</span></div>
                    <div class="config-item"><span class="config-key">记忆模式:</span><span class="config-value">{escape_html(config.get("memory", {}).get("mode", "N/A"))}</span></div>
                    <div class="config-item"><span class="config-key">Top-K:</span><span class="config-value">{config.get("memory", {}).get("top_k", "N/A")}</span></div>
                    <div class="config-item"><span class="config-key">相似度阈值:</span><span class="config-value">{config.get("memory", {}).get("similarity_threshold", "N/A")}</span></div>
                </div>
            </div>

'''
        
        by_task = summary.get('by_task_type', summary.get('by_task_id', {}))
        if by_task:
            html_content += '''            <div class="task-type-stats">
                <h3>📊 按任务类型统计</h3>
                <div class="task-type-grid">
'''
            for task_name, task_stats in by_task.items():
                task_total = task_stats.get('total', 0)
                task_successes = task_stats.get('successes', 0)
                task_rate = task_stats.get('success_rate', 0)
                task_avg_steps = task_stats.get('avg_steps', 0)
                
                html_content += f'''                    <div class="task-type-card">
                        <div class="task-type-name">{escape_html(task_name)}</div>
                        <div class="task-type-detail"><span>总数:</span><span>{task_total}</span></div>
                        <div class="task-type-detail"><span>成功:</span><span>{task_successes}</span></div>
                        <div class="task-type-detail"><span>成功率:</span><span>{task_rate:.1f}%</span></div>
                        <div class="task-type-detail"><span>平均步数:</span><span>{task_avg_steps:.1f}</span></div>
                    </div>
'''
            html_content += '''                </div>
            </div>

'''
        
        html_content += '''            <div class="results-section">
                <h2>📋 任务实例详情</h2>
'''
        
        for idx, result in enumerate(results_data.get('results', [])):
            game_id = result.get('game_id', result.get('episode_id', f'task_{idx}'))
            task_type = result.get('task_type', result.get('task_name', 'unknown'))
            success = result.get('success', False)
            steps = result.get('steps', 0)
            goal = result.get('goal', 'N/A')
            actions = result.get('actions', [])
            observations = result.get('observations', [])
            thoughts = result.get('thoughts', [])
            used_memories = result.get('used_memories', [])
            score = result.get('score')
            
            memory_entry = memories_data.get(game_id)
            
            status_class = 'success' if success else 'fail'
            status_text = '成功' if success else '失败'
            
            html_content += f'''                <div class="result-card" id="result-{idx}-{safe_key}">
                    <div class="result-header" onclick="toggleResult('result-{idx}-{safe_key}')">
                        <div class="result-title">
                            <span class="status-badge {status_class}">{status_text}</span>
                            <span class="result-id">{escape_html(game_id[:60])}...</span>
                        </div>
                        <div class="result-meta">
                            <span class="meta-item">📂 {escape_html(task_type)}</span>
                            <span class="meta-item">👣 {steps} 步</span>
'''
            if score is not None:
                html_content += f'''                            <span class="meta-item">⭐ {score} 分</span>
'''
            html_content += f'''                            <span class="expand-icon">▼</span>
                        </div>
                    </div>
                    <div class="result-body">
                        <div class="goal-box">
                            <div class="goal-label">🎯 任务目标</div>
                            <div class="goal-text">{escape_html(goal)}</div>
                        </div>

'''
            
            if used_memories:
                html_content += '''                        <div class="used-memories-section">
                            <div class="section-title">💡 使用的记忆</div>
'''
                for mem_idx, mem in enumerate(used_memories):
                    mem_id = mem.get("memory_id", "N/A")
                    # 查找记忆详情
                    mem_detail = None
                    for task_mem in memories_data.values():
                        if task_mem.get('memory_id') == mem_id:
                            mem_detail = task_mem
                            break
                    
                    detail_id = f"used-mem-{idx}-{mem_idx}-{safe_key}"
                    html_content += f'''                            <div class="used-memory-item-wrapper">
                                <div class="used-memory-item" onclick="toggleUsedMemory('{detail_id}')">
                                    <span class="used-mem-info">
                                        <span class="used-mem-id">{escape_html(mem_id)}</span>
                                        <span class="used-mem-query">"{escape_html(str(mem.get("query", ""))[:50])}..."</span>
                                    </span>
                                    <span class="used-mem-badges">
                                        <span class="similarity-badge">相似度: {mem.get("similarity", 0):.4f}</span>
                                        <span class="expand-btn">展开 ▼</span>
                                    </span>
                                </div>
'''
                    if mem_detail:
                        html_content += f'''                                <div class="used-memory-detail" id="{detail_id}">
                                    <div class="used-mem-task-info">
                                        <span class="detail-label">来源任务:</span> {escape_html(mem_detail.get("task_id", "")[:60])}...
                                    </div>
                                    <div class="used-mem-task-info">
                                        <span class="detail-label">任务类型:</span> {escape_html(mem_detail.get("task_type", "N/A"))}
                                    </div>
                                    <div class="used-mem-task-info">
                                        <span class="detail-label">原始查询:</span> {escape_html(mem_detail.get("query", ""))}
                                    </div>
                                    <div class="used-mem-items-title">记忆内容:</div>
'''
                        for item in mem_detail.get('memory_items', []):
                            ref_count = item.get('reference_count', 0)
                            ref_success = item.get('reference_success_count', 0)
                            ref_rate = (ref_success / ref_count * 100) if ref_count > 0 else 0
                            rate_class = 'low' if ref_rate < 30 else ('medium' if ref_rate < 60 else '')
                            
                            html_content += f'''                                    <div class="used-mem-item-card">
                                        <div class="used-mem-item-header">
                                            <span class="used-mem-item-title">{escape_html(item.get("title", ""))}</span>
'''
                            if ref_count > 0:
                                html_content += f'''                                            <span class="ref-badge ref-count">被引: {ref_count}</span>
                                            <span class="ref-badge ref-success-rate {rate_class}">{ref_rate:.0f}%</span>
'''
                            html_content += f'''                                        </div>
                                        <div class="used-mem-item-desc">{escape_html(item.get("description", ""))}</div>
                                        <div class="used-mem-item-content">{escape_html(item.get("content", ""))}</div>
                                    </div>
'''
                        html_content += '''                                </div>
'''
                    html_content += '''                            </div>
'''
                html_content += '''                        </div>
'''
            
            html_content += '''                        <div class="trajectory-section">
                            <div class="section-title">📜 执行轨迹</div>
'''
            
            max_len = max(len(actions), len(observations), len(thoughts)) if actions or observations or thoughts else 0
            for step_idx in range(min(max_len, 30)):  # 限制显示30步
                action = actions[step_idx] if step_idx < len(actions) else ''
                obs = observations[step_idx] if step_idx < len(observations) else ''
                thought = thoughts[step_idx] if step_idx < len(thoughts) else ''
                
                html_content += f'''                            <div class="trajectory-step">
                                <div class="step-indicator">{step_idx + 1}</div>
                                <div class="trajectory-step-content">
                                    <div class="trajectory-item">
'''
                if action:
                    html_content += f'''                                        <div class="action-box">
                                            <div class="box-label">🎮 动作</div>
                                            <div class="box-content">{escape_html(action)}</div>
                                        </div>
'''
                if obs:
                    html_content += f'''                                        <div class="observation-box">
                                            <div class="box-label">👁️ 观察</div>
                                            <div class="box-content">{escape_html(obs[:500])}{"..." if len(obs) > 500 else ""}</div>
                                        </div>
'''
                if thought:
                    html_content += f'''                                        <div class="thought-box">
                                            <div class="box-label">💭 思考</div>
                                            <div class="box-content">{escape_html(thought)}</div>
                                        </div>
'''
                html_content += '''                                    </div>
                                </div>
                            </div>
'''
            
            if max_len > 30:
                html_content += f'''                            <div style="text-align: center; color: var(--text-muted); padding: 1rem;">... 还有 {max_len - 30} 步省略 ...</div>
'''
            
            html_content += '''                        </div>
'''
            
            if memory_entry and memory_entry.get('memory_items'):
                html_content += '''                        <div class="memories-section">
                            <div class="section-title">🧠 提取的记忆</div>
'''
                for mem_item in memory_entry['memory_items']:
                    ref_count = mem_item.get('reference_count', 0)
                    ref_success = mem_item.get('reference_success_count', 0)
                    ref_rate = (ref_success / ref_count * 100) if ref_count > 0 else 0
                    
                    rate_class = 'low' if ref_rate < 30 else ('medium' if ref_rate < 60 else '')
                    
                    html_content += f'''                            <div class="memory-card">
                                <div class="memory-header">
                                    <div class="memory-title">{escape_html(mem_item.get("title", ""))}</div>
                                    <div class="memory-stats">
'''
                    if ref_count > 0:
                        html_content += f'''                                        <span class="ref-badge ref-count">被引: {ref_count}</span>
                                        <span class="ref-badge ref-success-rate {rate_class}">成功率: {ref_rate:.1f}%</span>
'''
                    html_content += f'''                                    </div>
                                </div>
                                <div class="memory-description">{escape_html(mem_item.get("description", ""))}</div>
                                <div class="memory-content">{escape_html(mem_item.get("content", ""))}</div>
                            </div>
'''
                html_content += '''                        </div>
'''
            
            html_content += '''                    </div>
                </div>
'''
        
        html_content += '''            </div>
        </div>

'''
    
    html_content += '''    </div>

    <script>
        function showDataset(name) {
            document.querySelectorAll('.dataset-content').forEach(el => {
                el.classList.remove('active');
            });
            document.querySelectorAll('.tab').forEach(el => {
                el.classList.remove('active');
            });
            document.getElementById('dataset-' + name).classList.add('active');
            event.target.closest('.tab').classList.add('active');
        }

        function toggleResult(id) {
            const card = document.getElementById(id);
            const body = card.querySelector('.result-body');
            card.classList.toggle('expanded');
            body.classList.toggle('expanded');
        }

        function toggleUsedMemory(id) {
            event.stopPropagation();
            const detail = document.getElementById(id);
            const wrapper = detail.closest('.used-memory-item-wrapper');
            detail.classList.toggle('expanded');
            wrapper.classList.toggle('expanded');
        }
    </script>
</body>
</html>'''
    
    return html_content


def main():
    base_dir = Path(__file__).parent
    
    print("🔍 扫描数据集...")
    datasets = find_dataset_files(base_dir)
    
    if not datasets:
        print("❌ 未找到数据集文件！")
        return
    
    print(f"✅ 找到 {len(datasets)} 个数据集配置:")
    for key in datasets:
        print(f"   - {key}")
    
    datasets_data = {}
    for key, files in datasets.items():
        print(f"📖 加载 {key}...")
        memories = load_memories(files['memories'])
        results = load_results(files['results'])
        datasets_data[key] = {
            'info': files,
            'memories': memories,
            'results': results
        }
    
    print("🎨 生成可视化页面...")
    html_content = generate_html(datasets_data)
    
    output_file = base_dir / 'visualization.html'
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✨ 可视化页面已生成: {output_file}")
    print(f"🌐 请在浏览器中打开查看")


if __name__ == '__main__':
    main()
