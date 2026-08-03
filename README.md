# 摄影大师画廊 · Photography Masters Gallery

一个持续增长的世界摄影大师作品库。每位大师一个独立目录，包含：
- `portfolio.html`：全屏作品浏览页（点按/←→切换、底部缩略图条、传记面板）
- `images/`：高清作品图（本地数据资产，不上传 GitHub）
- 中文传记与作品风格简介

## 项目结构

```
摄影大师画廊/
├── index.html                 # 画廊首页（全部摄影师网格）
├── PROGRESS.md                # 进度总览（摄影师 × 作品数，自动生成）
├── 00-摄影大师画廊-计划与规范.md  # 项目规范（收录标准、排除名单）
├── .portfolio_template.html   # 每位摄影师页面的 HTML 模板
├── auto_add.py                # 自动添加摄影师脚本（--count N）
├── daily_photographer.sh      # 每日定时任务包装脚本
└── <摄影师-slug>/             # 每位摄影师一个目录
    ├── portfolio.html
    ├── slideshow.html         # symlink -> portfolio.html
    └── images/                # 本地图片（gitignored）
```

## 数据来源与收录流程

1. **图片来源**：Bing 图片搜索（经 ego-browser 抓取高清图 URL，filterui:imagesize-large）
2. **下载**：curl 8 并发 → 文件名 = md5(url)
3. **清洗**：<400px 丢弃 → 扩展名按真实格式修正（jpg/png/gif/webp）→ 16×16 dHash 感知哈希去重（汉明距离 ≤12，保留最大图）
4. **生成页面**：`.portfolio_template.html` 模板注入摄影师名/传记/图片列表
5. **登记**：插入 index.html 的 `const photographers` 数组

## 每日自动化

每天 10:00 由 launchd 自动添加 5 位摄影师（`com.photogallery.daily`）：

```bash
# 手动触发（添加 5 位）：
python3 auto_add.py --count 5

# 查看计划任务：
launchctl list | grep photogallery

# 日志：
daily_progress.log / daily_error.log
```

候选名单在 `auto_add.py` 的 `PENDING` 列表中，已存在的目录自动跳过。

## 收录规范

- 收录：世界级摄影大师，覆盖纪实、街拍、人像、时尚、风景、野生动物、先锋实验等流派
- **排除：恐怖、暗黑、血腥、压抑风格**（如 深濑昌久 Masahisa Fukase 已移除，以后不再收录类似风格）
- 每位摄影师：中文传记 3 段左右 + 作品 100-300 张

详细规范见 `00-摄影大师画廊-计划与规范.md`。

## 本地运行

```bash
open index.html
```

> 图片数据约 6.3G（23000+ 张）保存在本地移动硬盘，未上传 GitHub。
> GitHub 仓库仅维护代码、模板、规范与进度文档。

## 进度

详见 [PROGRESS.md](PROGRESS.md) — 当前 **132 位摄影师 / 23090 张作品**，每日自动增长。
