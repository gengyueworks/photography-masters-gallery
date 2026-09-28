#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
摄影大师独立画廊自动构建与部署流水线
使用示例：
  python3 scripts/pipeline_build_master_archive.py --id okuyama --name_zh "奥山由之" --name_en "Yoshiyuki Okuyama"
"""
import os, sys, json, shutil, subprocess, argparse
from PIL import Image

PHOTOS_DIR = "/Volumes/视频素材剪辑区/摄影大师画廊-图片库/photographers"
PROJ_BASE = "/Volumes/拓展坞 1T2022/2 Codex-Workspace/Codex-Workspace-Main/30-项目-网站/gengyueworks-Github"

def build_master_archive(src_name, repo_name, name_zh, name_en, country, years, equipment, masterpieces, quote, style_desc):
    dest_dir = os.path.join(PROJ_BASE, repo_name)
    img_dest_dir = os.path.join(dest_dir, "images")
    os.makedirs(img_dest_dir, exist_ok=True)
    
    src_dir = os.path.join(PHOTOS_DIR, src_name, "images")
    if not os.path.exists(src_dir):
        src_dir = os.path.join(PHOTOS_DIR, src_name)
        
    files = [f for f in os.listdir(src_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
    high_res_files = []
    
    for f in sorted(files):
        src_fp = os.path.join(src_dir, f)
        try:
            with Image.open(src_fp) as img:
                w, h = img.size
                if w >= 500 and h >= 500:
                    dest_fp = os.path.join(img_dest_dir, f)
                    if not os.path.exists(dest_fp):
                        shutil.copy2(src_fp, dest_fp)
                    high_res_files.append({"filename": f, "width": w, "height": h, "aspect": round(w / h, 2)})
        except Exception:
            pass
            
    print(f"[{name_zh}] Cleaned & Filtered {len(high_res_files)} high-res images.")
    
    with open(os.path.join(dest_dir, "images_meta.json"), "w", encoding="utf-8") as f:
        json.dump(high_res_files, f, ensure_ascii=False, indent=2)
    with open(os.path.join(dest_dir, ".nojekyll"), "w") as f:
        f.write("")
        
    print(f"✓ Standalone repository ready at {dest_dir}")
    return len(high_res_files)

if __name__ == '__main__':
    print("Master Archive Automation Pipeline Loaded.")
