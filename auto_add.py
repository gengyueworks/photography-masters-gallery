#!/usr/bin/env python3
"""
Daily auto-add photographers to gallery.
  python3 auto_add.py --count 5

Logs to daily_progress.log when run via launchd.
"""
import json, os, sys, argparse, subprocess, hashlib, concurrent.futures, tempfile, shutil
from PIL import Image

BASE = "/Volumes/拓展坞 1T2022/2 Codex-Workspace/Codex-Workspace-Main/32-AI高质量阅读库/摄影大师画廊"
LOG = os.path.join(BASE, "daily_progress.log")
TEMPLATE = os.path.join(BASE, ".portfolio_template.html")

PENDING = [
    ("Larry Burrows", "larry-burrows", ["Larry Burrows Vietnam war photographer", "Larry Burrows Life magazine"], "1926–1971 · 英国", ["Larry Burrows 是战争摄影史上最重要的名字之一。他 1926 年出生于伦敦，在越南战争中度过了最漫长的九年——从 1962 年到 1971 年，他反复往返于越南战场。", "他的彩色照片在 1960 年代是革命性的——当大多数战争摄影还是黑白时，他用柯达反转片记录下战场的颜色：绿色的丛林、红色的血、橙色的火焰。他最具标志性的作品《Reaching Out》拍下了一名受伤的美军士兵向直升机伸出手臂——这张照片成为越战最有力的反战宣言之一。", "1971 年，他在老挝乘坐的直升机被击落。与他一同遇难的还有三名摄影师同行。他留下了 20 万张底片。"]),
    ("Eve Arnold", "eve-arnold", ["Eve Arnold photography Magnum", "Eve Arnold Marilyn Monroe"], "1912–2012 · 美国", ["Eve Arnold 是 Magnum 第一位女性正式成员。她 1912 年出生于宾夕法尼亚州一个犹太移民家庭，摄影起步很晚——直到 30 多岁才拿起相机。", "她最出名的作品是 Marilyn Monroe 的肖像——在片场、在后台、在游泳池边、在阳光下睡着。她拍到了 Monroe 从未在人前展现的放松和脆弱。Arnold 说：'Marilyn 和别人不一样——她在镜头前反而比平时更自在。'", "她不只拍名人。她拍了中国 1979 年——文革结束后的中国——那是西方摄影师第一次深入内陆的记录。她也拍美国南部的种族隔离、拍阿富汗的难民、拍哈莱姆区的产房。她的信条：'去拍那些你自己不了解的人和事。'"]),
    ("Don McCullin", "don-mccullin", ["Don McCullin war photography", "Don McCullin conflict photographer"], "1935– · 英国", ["Don McCullin 是 20 世纪最伟大的战争摄影师之一。他 1935 年出生于伦敦一个贫困家庭。他的摄影始于街头斗殴——他拍了本地帮派的照片卖给了报纸。", "此后的 30 年里，他跑了全世界最危险的地方——塞浦路斯、越南、刚果、柬埔寨、北爱尔兰、黎巴嫩。他的照片充满了对战争刻骨的愤怒。他用镜头直直地对着痛苦：一个刚果士兵正在审问一个颤抖的男人，一个北爱尔兰的男孩拿着玩具枪对着英国装甲车。", "晚年他不再去战场了。他拍了英格兰的风景、静物、教堂。他说过一句话：'战争摄影师没有老年——不是因为会死，而是因为那些画面永远不会放过你。'"]),
    ("Martin Parr", "martin-parr", ["Martin Parr photography Magnum", "Martin Parr British life"], "1952– · 英国", ["Martin Parr 是当代英国最辛辣的摄影师。他 1952 年出生于埃普瑟姆。他拍的不是英国——他拍的是英国人的吃相。", "Parr 的镜头永远对准那些'不太体面'的瞬间：在海滩上吃薯条吃到满脸油的游客、在展会上张大嘴打哈欠的中产阶级、把英国国旗穿在身上的足球迷。他用鲜艳到刺眼的色彩拍下了消费主义最荒诞的画面。", "1994 年他加入 Magnum 时，老一辈成员激烈反对——他们认为 Parr 的照片'太低级了'。这些反对本身就被 Parr 拍了下来。他一生都在问同一件事：我们到底是人，还是消费的机器？"]),
]

def log(msg):
    with open(LOG, "a") as f:
        f.write(f"{msg}\n")
    print(msg)

def scrape_urls(name, queries):
    tmp = tempfile.mktemp(suffix='.json')
    script = f"""
const fs=require('fs');(async()=>{{const t=await useOrCreateTaskSpace('da');let a=new Set();
async function sq(q){{
await openOrReuseTab('https://www.bing.com/images/search?q='+encodeURIComponent(q)+'&count=100&qft=+filterui:imagesize-large&form=IRFLTR',{{wait:true,timeout:30}});
for(let i=0;i<6;i++){{await scrollBy(2500);await wait(2);
const u=await js(String.raw`(()=>{{const i=document.querySelectorAll('a.iusc');return[...i].map(a=>{{try{{return JSON.parse(a.getAttribute('m').replace(/'/g,'"')).murl;}}catch(e){{return null;}}}}).filter(Boolean);}})()`);
u.forEach(x=>a.add(x));}}
for(const q of {json.dumps(queries)}){{await sq(q);}}
const arr=[...a];fs.writeFileSync('{tmp}',JSON.stringify(arr));
cliLog(arr.length+' URLs');
}})();
"""
    r = subprocess.run(["ego-browser", "nodejs"], input=script, capture_output=True, text=True, timeout=300)
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
    for f in os.listdir(img_dir):
        fp = os.path.join(img_dir, f)
        try:
            img = Image.open(fp)
            if min(img.size) < 400: os.remove(fp)
        except: os.remove(fp)
    hashes = {}
    for f in os.listdir(img_dir):
        fp = os.path.join(img_dir, f)
        try:
            img = Image.open(fp).convert('L').resize((8,8), Image.LANCZOS)
            px = list(img.getdata())
            avg = sum(px) / len(px)
            h = ''.join('1' if p > avg else '0' for p in px)
            hashes.setdefault(h, []).append(f)
        except: os.remove(fp)
    rm = 0
    for h, g in hashes.items():
        if len(g) > 1:
            g.sort(key=lambda f: os.path.getsize(os.path.join(img_dir, f)), reverse=True)
            for f in g[1:]: os.remove(os.path.join(img_dir, f)); rm += 1
    return rm

def create_portfolio(name, subtitle, slug, files, bio_lines):
    img_dir = os.path.join(BASE, slug, "images")
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
    # Insert at end of array, before the last item's comma closure
    # Find the array closing bracket
    insert_pos = html.find("];", html.find("const photographers ="))
    html = html[:insert_pos] + entry + "\n" + html[insert_pos:]
    with open(ip, "w") as f:
        f.write(html)

def add_one(name, subtitle, slug, queries, bio_lines):
    img_dir = os.path.join(BASE, slug, "images")
    if os.path.exists(img_dir) and len(os.listdir(img_dir)) > 0:
        log(f"  ⏭️  {name}: exists ({len(os.listdir(img_dir))} images)")
        return
    log(f"  {name}: scraping...")
    urls = scrape_urls(name, queries)
    log(f"  {name}: {len(urls)} URLs, downloading...")
    results = download_urls(urls, img_dir)
    ok = sum(1 for r in results if r.startswith("ok"))
    log(f"  {name}: {ok} OK")
    rm = filter_dedup(img_dir)
    final = len(os.listdir(img_dir))
    log(f"  {name}: dedup {rm}, final {final}")
    if final == 0:
        shutil.rmtree(img_dir)
        log(f"  ❌ {name}: zero images, removed")
        return
    files = sorted(os.listdir(img_dir))
    create_portfolio(name, subtitle, slug, files, bio_lines)
    update_index(name, slug, final, files[0])
    log(f"  ✅ {name}: {final} images → index updated")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    already = set(os.listdir(BASE))
    added = 0
    for name, slug, queries, subtitle, bio_lines in PENDING:
        if added >= args.count:
            break
        if slug in already and os.path.exists(os.path.join(BASE, slug, "images")):
            continue
        add_one(name, subtitle, slug, queries, bio_lines)
        added += 1
    log(f"Done. Added {added} today.")
