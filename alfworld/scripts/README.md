# 进入 alfworld 目录
cd /home/bmt/evo/mem_banks/alfworld

# 生成训练数据（只成功案例）
python scripts/generate_sft_data.py qwen3-8b --only-success

# 可视化查看
python scripts/visualize_sft_data.py qwen3-8b/sft_data.jsonl