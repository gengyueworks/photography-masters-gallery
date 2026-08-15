#!/usr/bin/env python3
"""
Daily auto-add photographers to gallery + write book essay for each.
  python3 auto_add.py --count 5

Pipeline: scrape URLs → download → filter/dedup → portfolio.html → index.html → book essay
Then scripts/sync_github.sh pushes PROGRESS + book/ to GitHub.
"""
import json, os, sys, argparse, subprocess, hashlib, concurrent.futures, tempfile, shutil, time, base64
from datetime import date
from PIL import Image

BASE = "/Volumes/拓展坞 1T2022/2 Codex-Workspace/Codex-Workspace-Main/32-AI高质量阅读库/摄影大师画廊"
PHOTOS = os.path.join(BASE, "photographers")
LOG = os.path.join(BASE, "daily_progress.log")
TEMPLATE = os.path.join(BASE, ".portfolio_template.html")
BOOK = os.path.join(BASE, "book")

# PENDING entries: dict with gallery info + book essay content.
# "chapter" must match an existing folder name in book/.
from pending_pool import PENDING

def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{msg}\n")
    print(msg)

def scrape_urls(name, queries):
    tmp = tempfile.mktemp(suffix='.json')
    # JS 提取代码：base64 传输，彻底避免多层字符串转义问题
    extract_code = "(()=>{const i=document.querySelectorAll('a.iusc');return[...i].map(a=>{try{return JSON.parse(a.getAttribute('m').replace(/'/g,'\"')).murl;}catch(e){return null;}}).filter(Boolean);})()"
    b64 = base64.b64encode(extract_code.encode()).decode()
    script = f"""
const fs=require('fs');(async()=>{{
const t=await useOrCreateTaskSpace('scrape-{int(time.time()%100000)}');let a=new Set();
async function sq(q){{
await openOrReuseTab('https://www.bing.com/images/search?q='+encodeURIComponent(q)+'&count=100&qft=+filterui:imagesize-large&form=IRFLTR',{{wait:true,timeout:30}});
for(let i=0;i<6;i++){{await scrollBy(2500);await wait(2);
const u=await js(Buffer.from('{b64}','base64').toString());
u.forEach(x=>a.add(x));}}
}}
for(const q of {json.dumps(queries)}){{await sq(q);}}
const arr=[...a];fs.writeFileSync('{tmp}',JSON.stringify(arr));
cliLog(arr.length+' URLs');
try{{await completeTaskSpace(t.id,{{keep:false}});}}catch(e){{}}
}})();
"""
    r = subprocess.run(["ego-browser", "nodejs"], input=script, capture_output=True, text=True, timeout=300)
    if not os.path.exists(tmp):
        log(f"  ⚠️  scrape failed for {name}: {r.stderr[-300:]}")
        return []
    with open(tmp) as f:
        urls = list(set(json.load(f)))
    os.unlink(tmp)
    return urls

def download_urls(urls, img_dir):
    os.makedirs(img_dir, exist_ok=True)
    existing = set(os.listdir(img_dir))
    def dl(url):
        try:
            md5 = hashlib.md5(url.encode()).hexdigest() + ".jpg"
            fp = os.path.join(img_dir, md5)
            if md5 in existing and os.path.getsize(fp) > 50000:
                return "skip"
            r = subprocess.run(["curl", "-sL", "--connect-timeout", "8", "--max-time", "20",
                               "-w", "%{http_code}", "-o", fp, url], capture_output=True, timeout=25)
            c = r.stdout.decode().strip()
            if os.path.exists(fp):
                sz = os.path.getsize(fp)
                if sz < 5000: os.remove(fp); return f"tiny({sz}B)"
                return f"ok({sz//1024}KB)"
            return f"fail({c})"
        except: return "err"
    with concurrent.futures.ThreadPoolExecutor(8) as p:
        return list(p.map(dl, urls))

def filter_dedup(img_dir):
    """质量过滤 + 去重。删除过小/损坏/模糊图，按感知哈希去重。"""
    Res = Image.Resampling
    removed = []
    for f in os.listdir(img_dir):
        fp = os.path.join(img_dir, f)
        try:
            img = Image.open(fp)
            img.load()
            w, h = img.size
            # 过小图（长边 < 600 或短边 < 400）删除
            if min(w, h) < 400 or max(w, h) < 600:
                removed.append(fp)
                continue
            # 模糊检测：转灰度缩小后算拉普拉斯方差，过低视为模糊
            small = img.convert('L').resize((64, 64), Res.LANCZOS)
            px = list(small.getdata())
            var = sum((p - sum(px)/len(px)) ** 2 for p in px) / len(px)
            if var < 15:
                removed.append(fp)
        except:
            removed.append(fp)
    for fp in removed:
        try: os.remove(fp)
        except: pass
    # 感知哈希去重
    hashes = {}
    for f in os.listdir(img_dir):
        fp = os.path.join(img_dir, f)
        try:
            img = Image.open(fp).convert('L').resize((8, 8), Res.LANCZOS)
            px = list(img.getdata())
            avg = sum(px) / len(px)
            h = ''.join('1' if p > avg else '0' for p in px)
            hashes.setdefault(h, []).append(fp)
        except: pass
    rm = 0
    for h, g in hashes.items():
        if len(g) > 1:
            g.sort(key=lambda fp: os.path.getsize(fp), reverse=True)
            for fp in g[1:]:
                try: os.remove(fp); rm += 1
                except: pass
    return len(removed) + rm

def compress_images(img_dir, max_side=1920, quality=82, max_bytes=900*1024):
    """压缩目录内所有图片：长边缩到 max_side、JPEG 质量 quality，目标单张 < max_bytes。
    保留原文件名（覆盖写）。返回 (压缩数, 节省字节)。"""
    Res = Image.Resampling
    n = 0; saved = 0
    for f in os.listdir(img_dir):
        fp = os.path.join(img_dir, f)
        try:
            old_sz = os.path.getsize(fp)
            if old_sz <= max_bytes:
                continue
            img = Image.open(fp)
            img.load()
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            if max(img.size) > max_side:
                img.thumbnail((max_side, max_side), Res.LANCZOS)
            tmp = fp + '.tmp'
            img.save(tmp, 'JPEG', quality=quality, optimize=True, progressive=True)
            new_sz = os.path.getsize(tmp)
            if new_sz < old_sz:
                os.replace(tmp, fp)
                saved += old_sz - new_sz
                n += 1
            else:
                os.remove(tmp)
        except:
            try:
                if os.path.exists(fp + '.tmp'): os.remove(fp + '.tmp')
            except: pass
    return n, saved

def create_portfolio(name, subtitle, slug, files, bio_lines):
    img_dir = os.path.join(PHOTOS, slug, "images")
    img_list = json.dumps(sorted(files))
    bio = "".join(f"<p>{p}</p>\n" for p in bio_lines)
    with open(TEMPLATE) as f:
        tpl = f.read()
    html = tpl.replace("__NAME__", name).replace("__SUBTITLE__", subtitle).replace("__BIO__", bio).replace("__IMAGES__", img_list)
    with open(os.path.join(img_dir, "..", "portfolio.html"), "w") as f:
        f.write(html)
    sl = os.path.join(img_dir, "..", "slideshow.html")
    if not os.path.exists(sl): os.symlink("portfolio.html", sl)

def update_index(name, slug, count, first_image):
    ip = os.path.join(BASE, "index.html")
    with open(ip) as f:
        html = f.read()
    entry = f'  {{ name: "{name}", slug: "{slug}", count: {count}, label: "张作品", href: "slideshow.html", image: "images/{first_image}" }},'
    insert_pos = html.find("];", html.find("const photographers ="))
    html = html[:insert_pos] + entry + "\n" + html[insert_pos:]
    with open(ip, "w") as f:
        f.write(html)

def write_book_essay(slug, essay, chapter):
    """Write/append book essay for a photographer. Returns True if written, False if exists."""
    ch_dir = os.path.join(BOOK, chapter)
    if not os.path.isdir(ch_dir):
        log(f"  ⚠️  chapter dir not found: {chapter}, skip essay")
        return False
    fp = os.path.join(ch_dir, slug + ".md")
    if os.path.exists(fp):
        log(f"  ⏭️  essay exists: {fp}")
        return False
    today = date.today().strftime("%Y-%m")
    lines = [
        f"# {essay['headline']}",
        "",
        f"*耿悦 · 摄影大师画廊 · {today}*",
        "",
        "---",
        "",
        "### 生平",
    ]
    for p in essay["bio"]:
        lines += [p, ""]
    lines += ["---", "", "### 历史背景", ""]
    for p in essay["history"]:
        lines += [p, ""]
    lines += ["---", "", "### 拍摄方式", ""]
    for p in essay["method"]:
        lines += [p, ""]
    lines += ["---", "", "### 技术特点", ""]
    for p in essay["technique"]:
        lines += [p, ""]
    lines += ["---", "", "### 代表作品", ""]
    for p in essay["works"]:
        lines += [f"- {p}", ""]
    lines += ["---", "", "### 成就", ""]
    for p in essay["honors"]:
        lines += [p, ""]
    lines += ["---", "", "### 在摄影史的位置", ""]
    for p in essay["place"]:
        lines += [p, ""]
    with open(fp, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    log(f"  📖 essay written: {fp}")
    return True

def add_one(item):
    name, slug = item["name"], item["slug"]
    img_dir = os.path.join(PHOTOS, slug, "images")
    if os.path.exists(img_dir) and len(os.listdir(img_dir)) > 0:
        log(f"  ⏭️  {name}: exists ({len(os.listdir(img_dir))} images)")
        return
    log(f"  {name}: scraping...")
    urls = scrape_urls(name, item["queries"])
    log(f"  {name}: {len(urls)} URLs, downloading...")
    results = download_urls(urls, img_dir)
    ok = sum(1 for r in results if r.startswith("ok"))
    log(f"  {name}: {ok} OK")
    rm = filter_dedup(img_dir)
    final = len(os.listdir(img_dir))
    log(f"  {name}: dedup+filter {rm}, final {final}")
    if final == 0:
        shutil.rmtree(img_dir)
        log(f"  ❌ {name}: zero images, removed")
        return
    n_comp, saved = compress_images(img_dir)
    log(f"  {name}: compressed {n_comp}, saved {saved//1024//1024}MB")
    files = sorted(os.listdir(img_dir))
    create_portfolio(name, item["subtitle"], slug, files, item["bio_lines"])
    update_index(name, slug, final, files[0])
    log(f"  ✅ {name}: {final} images → index updated")
    write_book_essay(slug, item["essay"], item["chapter"])

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    already = set(os.listdir(PHOTOS))
    added = 0
    for item in PENDING:
        if added >= args.count:
            break
        slug = item["slug"]
        if slug in already and os.path.exists(os.path.join(PHOTOS, slug, "images")):
            continue
        add_one(item)
        added += 1
    log(f"Done. Added {added} today.")
