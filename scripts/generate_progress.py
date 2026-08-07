#!/usr/bin/env python3
"""Regenerate PROGRESS.md from disk truth and fix index.html counts."""
import os, re, sys
from datetime import date

BASE = "/Volumes/拓展坞 1T2022/2 Codex-Workspace/Codex-Workspace-Main/32-AI高质量阅读库/摄影大师画廊"

idx_path = os.path.join(BASE, "index.html")
with open(idx_path, encoding="utf-8") as f:
    idx = f.read()
m = re.search(r"const photographers\s*=\s*\[(.*?)\];", idx, re.S)
if not m:
    print("ERROR: photographers array not found in index.html")
    sys.exit(1)
entries = re.findall(r"\{[^{}]*\}", m.group(1))

fixed = 0
rows = []
for e in entries:
    nm = re.search(r'name:\s*"([^"]+)"', e)
    sl = re.search(r'slug:\s*"([^"]+)"', e)
    ct = re.search(r"count:\s*(\d+)", e)
    if not (nm and sl and ct):
        continue
    imd = os.path.join(BASE, "photographers", sl.group(1), "images")
    n = len(os.listdir(imd)) if os.path.isdir(imd) else 0
    rows.append((nm.group(1), sl.group(1), n))
    if n != int(ct.group(1)):
        idx = idx.replace("count: " + ct.group(1) + ", label", "count: " + str(n) + ", label", 1)
        fixed += 1

if fixed:
    with open(idx_path, "w", encoding="utf-8") as f:
        f.write(idx)
    print(f"fixed {fixed} counts in index.html")

rows.sort(key=lambda x: -x[2])
total = sum(r[2] for r in rows)
today = date.today().isoformat()

lines = [
    "# 摄影大师画廊 · 进度总览",
    "",
    f"> 自动生成：`python3 scripts/generate_progress.py` ｜ 最近更新：{today}",
    "",
    "## 当前状态",
    "",
    "| 指标 | 数值 |",
    "|------|------|",
    f"| 摄影师总数 | **{len(rows)}** |",
    f"| 作品图总数 | **{total}** |",
    "| 数据存放 | 本地移动硬盘（约 6.3G），GitHub 只存代码/文档/进度 |",
    "",
    "## 全部摄影师（按作品数排序）",
    "",
    "| # | 摄影师 | 作品数 |",
    "|---|--------|--------|",
]
for i, (n, s, c) in enumerate(rows, 1):
    lines.append(f"| {i} | {n} | {c} |")

with open(os.path.join(BASE, "PROGRESS.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"PROGRESS.md updated: {len(rows)} photographers, {total} images")
