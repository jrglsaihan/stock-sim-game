#!/bin/bash
# ============================================================
#  模拟炒股练习 —— 双击运行脚本
# ============================================================
cd "$(dirname "$0")"

# 优先使用 python3.11（Kivy 暂不支持 Python 3.13+）
if command -v python3.11 >/dev/null 2>&1; then
  PY=python3.11
else
  PY=python3
fi

if [ ! -d ".venv" ]; then
  echo "▶ 首次运行：正在创建虚拟环境并安装 Kivy（约 1-2 分钟，请稍候）..."
  "$PY" -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip
  ./.venv/bin/python -m pip install -r requirements.txt
  echo "✅ 环境就绪，正在启动游戏..."
fi

exec ./.venv/bin/python main.py
