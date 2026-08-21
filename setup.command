#!/bin/bash
# ============================================================
#  一键配置环境（等价于 run.command 首次运行时自动做的事）
# ============================================================
cd "$(dirname "$0")"

if command -v python3.11 >/dev/null 2>&1; then
  PY=python3.11
else
  PY=python3
fi

echo "▶ 正在创建虚拟环境并安装依赖..."
"$PY" -m venv .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt

echo "✅ 配置完成！以后双击 run.command 或在 VS Code 里按 F5 即可运行游戏。"
