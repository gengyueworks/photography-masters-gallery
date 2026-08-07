#!/usr/bin/env python3
"""
Daily auto-add photographers to gallery + write book essay for each.
  python3 auto_add.py --count 5

Pipeline: scrape URLs → download → filter/dedup → portfolio.html → index.html → book essay
Then scripts/sync_github.sh pushes PROGRESS + book/ to GitHub.
"""
import json, os, sys, argparse, subprocess, hashlib, concurrent.futures, tempfile, shutil
from datetime import date
from PIL import Image

BASE = "/Volumes/拓展坞 1T2022/2 Codex-Workspace/Codex-Workspace-Main/32-AI高质量阅读库/摄影大师画廊"
PHOTOS = os.path.join(BASE, "photographers")
LOG = os.path.join(BASE, "daily_progress.log")
TEMPLATE = os.path.join(BASE, ".portfolio_template.html")
BOOK = os.path.join(BASE, "book")

# PENDING entries: dict with gallery info + book essay content.
# "chapter" must match an existing folder name in book/.
PENDING = [
    dict(name="Larry Burrows", slug="larry-burrows",
         queries=["Larry Burrows Vietnam war photographer", "Larry Burrows Life magazine"],
         subtitle="1926–1971 · 英国",
         bio_lines=["Larry Burrows 是战争摄影史上最重要的名字之一。他 1926 年出生于伦敦，在越南战争中度过了最漫长的九年——从 1962 年到 1971 年，他反复往返于越南战场。",
                    "他的彩色照片在 1960 年代是革命性的——当大多数战争摄影还是黑白时，他用柯达反转片记录下战场的颜色：绿色的丛林、红色的血、橙色的火焰。他最具标志性的作品《Reaching Out》拍下了一名受伤的美军士兵向直升机伸出手臂——这张照片成为越战最有力的反战宣言之一。",
                    "1971 年，他在老挝乘坐的直升机被击落。与他一同遇难的还有三名摄影师同行。他留下了 20 万张底片。"],
         chapter="02-纪实的重量",
         essay=dict(
             headline="拉里·伯罗斯（1926—1971）：越战的彩色",
             bio=["拉里·伯罗斯，1926年出生于伦敦。他早年在杂志社做暗房助理，1962年首次赴越南报道。", "1962-1971年，他九年间反复往返越南战场，是报道越战时间最长的摄影记者之一。", "1971年2月，他在老挝坠机身亡，年仅44岁。"],
             history=["1960年代，越战成为美国介入最深的战争，也是彩色胶片首次大规模用于战地报道。", "伯罗斯是少数全程用彩色报道越战的摄影师——他用柯达反转片记录战场的颜色。", "1971年他遇难时，与他同机的还有三位摄影记者。"],
             method=["相机：35mm相机，彩色胶片。", "拍摄对象：美军士兵、战场、伤员、越南平民。", "方法：随军行动，长时间驻留战区，与士兵同吃同住。"],
             technique=["彩色战地摄影的先驱：当多数战争摄影仍是黑白时，他用彩色记录战场的绿色丛林与橙色火焰。", "《Reaching Out》（1966）：受伤士兵向直升机伸出手臂——越战最著名的影像之一。", "他坚持近距离拍摄——他的照片带有'在场的重量'。"],
             works=["《Reaching Out》（1966）", "《越南》系列（1962-1971）", "《Operation Hastings》（1966）", "《A Day in the Life of a Marine》（1960s）"],
             honors=["1962-1971年，他的越战报道被《生活》等杂志大量刊载。", "1971年，他死后获得罗伯特·卡帕金奖。", "他留下的20万张底片成为越战影像的重要档案。"],
             place=["伯罗斯证明了彩色可以承载战争的重量——他的照片是'彩色的反战宣言'。", "他与卡帕、纳赫特维构成战地摄影的三代传承：卡帕黑白近身，伯罗斯彩色在场，纳赫特维黑白永恒。", "他是战地记者中'最长情的在场者'——九年的越南，直到生命的最后一天。"])),
    dict(name="Eve Arnold", slug="eve-arnold",
         queries=["Eve Arnold photography Magnum", "Eve Arnold Marilyn Monroe"],
         subtitle="1912–2012 · 美国",
         bio_lines=["Eve Arnold 是 Magnum 第一位女性正式成员。她 1912 年出生于宾夕法尼亚州一个犹太移民家庭，摄影起步很晚——直到 30 多岁才拿起相机。",
                    "她最出名的作品是 Marilyn Monroe 的肖像——在片场、在后台、在游泳池边、在阳光下睡着。她拍到了 Monroe 从未在人前展现的放松和脆弱。Arnold 说：'Marilyn 和别人不一样——她在镜头前反而比平时更自在。'",
                    "她不只拍名人。她拍了中国 1979 年——文革结束后的中国——那是西方摄影师第一次深入内陆的记录。她也拍美国南部的种族隔离、拍阿富汗的难民、拍哈莱姆区的产房。她的信条：'去拍那些你自己不了解的人和事。'"],
         chapter="03-房间里的人",
         essay=dict(
             headline="伊芙·阿诺德（1912—2012）：镜头的温柔",
             bio=["伊芙·阿诺德，1912年出生于美国宾夕法尼亚州。她30多岁才拿起相机，1951年加入马格南，是第一位女性正式成员。", "她拍摄了玛丽莲·梦露、中国、阿富汗、哈莱姆。", "2012年1月，她在伦敦去世，享年99岁。"],
             history=["1950年代，马格南几乎全是男性成员——阿诺德是第一位女性正式成员。", "1960-1970年代，她用'长期驻留'的方式拍摄社会题材：美国南部种族隔离、哈莱姆的产房。", "1979年，她成为首批深入中国内陆拍摄的西方摄影师。"],
             method=["相机：35mm相机，黑白与彩色胶片。", "拍摄对象：玛丽莲·梦露、中国社会、美国南部、阿富汗。", "方法：长时间驻留，与被摄者建立信任——她拍梦露时与梦露相处数月。"],
             technique=["《梦露》系列：她拍摄的梦露——在片场、后台、泳池边——拍出梦露从未示人的放松与脆弱。", "《中国》系列（1979）：文革后的中国——她记录了改革开放前夕的中国社会。", "她的信条：'去拍那些你自己不了解的人和事'——她的镜头永远朝向'陌生'。"],
             works=["《梦露》系列（1950s）", "《中国》（1979）", "《美国南部》（1960s）", "《阿富汗》（1970s）"],
             honors=["1951年，加入马格南，成为第一位女性正式成员。", "1980年，获得美国杂志摄影师协会奖。", "2003年，获得英国皇家摄影学会百年纪念奖章。"],
             place=["阿诺德证明了'温柔'可以是纪实的力量——她的镜头从不猎奇，只记录'人的真实'。", "她是马格南女性摄影传统的开端——后来的英格·莫拉特、苏珊·梅塞拉斯都继承了她的路径。", "她的梦露肖像，是'明星与摄影师之间信任'的经典案例。"])),
    dict(name="Don McCullin", slug="don-mccullin",
         queries=["Don McCullin war photography", "Don McCullin conflict photographer"],
         subtitle="1935– · 英国",
         bio_lines=["Don McCullin 是 20 世纪最伟大的战争摄影师之一。他 1935 年出生于伦敦一个贫困家庭。他的摄影始于街头斗殴——他拍了本地帮派的照片卖给了报纸。",
                    "此后的 30 年里，他跑了全世界最危险的地方——塞浦路斯、越南、刚果、柬埔寨、北爱尔兰、黎巴嫩。他的照片充满了对战争刻骨的愤怒。他用镜头直直地对着痛苦：一个刚果士兵正在审问一个颤抖的男人，一个北爱尔兰的男孩拿着玩具枪对着英国装甲车。",
                    "晚年他不再去战场了。他拍了英格兰的风景、静物、教堂。他说过一句话：'战争摄影师没有老年——不是因为会死，而是因为那些画面永远不会放过你。'"],
         chapter="02-纪实的重量",
         essay=dict(
             headline="唐·麦卡林（1935—）：战争的愤怒",
             bio=["唐·麦卡林，1935年出生于伦敦贫民区。他早年拍摄街头帮派照片卖给报纸，1960年代成为战地记者。", "三十年间，他报道了塞浦路斯、越南、刚果、柬埔寨、北爱尔兰、黎巴嫩。", "晚年他转向拍摄英格兰风景，至今在世。"],
             history=["1960-1980年代，全球冲突密集：越战、尼日利亚内战、柬埔寨内战。", "麦卡林是'愤怒的战地记者'——他称自己的照片是'对战争的控诉'。", "他的报道多刊于英国《星期日泰晤士报》。"],
             method=["相机：35mm相机，黑白胶片。", "拍摄对象：战场、士兵、难民、平民。", "方法：深入冲突最前线，用近距离的镜头记录战争的残酷。"],
             technique=["《刚果》系列（1964）：士兵审问颤抖的男人——他拍出'恐惧的解剖'。", "《北爱尔兰》系列（1971）：男孩手持玩具枪对着装甲车——战争的荒诞。", "他坚持黑白——他说彩色会'美化'战争。"],
             works=["《刚果》（1964）", "《越南》（1960s）", "《北爱尔兰》（1971）", "《英格兰风景》（1990s-2000s）"],
             honors=["1964年，获得世界新闻摄影奖。", "1992年，获得英国皇家摄影学会金质奖章。", "2017年，获得英国爵士称号。"],
             place=["麦卡林是'战争摄影的愤怒者'——他不用客观隐藏立场，他的照片就是控诉。", "他与卡帕（近身）、伯罗斯（彩色）并列，但他独有'刻骨的愤怒'。", "他晚年拍摄英格兰风景——'战后余生'的摄影。"])),
    dict(name="Weegee", slug="weegee",
         queries=["Weegee photography New York", "Weegee crime scene photography"],
         subtitle="1899–1968 · 美国",
         bio_lines=["Weegee（本名 Arthur Fellig）是纽约最著名的犯罪现场摄影师。他 1899 年出生于奥地利，10 岁移居纽约。",
                    "他在 1930-1940 年代拍摄纽约的犯罪、火灾、事故——他第一个到达现场，拍下尸体、凶手、围观者。他称自己的车是'我的暗房'。",
                    "他的照片带着幽默与残忍：死者的鞋、围观者的笑、夜晚的霓虹。他的《裸城》（Naked City，1945）是纽约夜生活的经典。"],
         chapter="02-纪实的重量",
         essay=dict(
             headline="维基（1899—1968）：第一个到达现场",
             bio=["维基（本名亚瑟·费利格），1899年出生于奥地利，10岁移居纽约。", "他1920年代做暗房助手，1930年代成为自由摄影师。", "他专拍纽约的犯罪、火灾与事故——他是'第一到达现场'的摄影师。", "1968年12月，他在纽约去世。"],
             history=["1930-1940年代，纽约小报（tabloid）兴起——犯罪照片是报纸的核心卖点。", "维基与纽约警察局保持紧密联系——他常在警方之前到达现场。", "1945年，他出版《裸城》——纽约夜生活的影像集。"],
             method=["相机：4×5大画幅配闪光灯，黑白胶片。", "拍摄对象：犯罪现场、火灾、事故、围观人群。", "方法：开车在纽约街头巡游，监听警方电台，第一时间赶到现场。"],
             technique=["'第一到达'的新闻摄影：他用闪光灯直射现场——尸体、凶手、围观者的脸同时被照亮。", "《裸城》（1945）：他拍摄的纽约夜晚——犯罪、人群、霓虹——城市夜生活的'野兽'。", "他的照片带黑色幽默——他拍死者的鞋、围观者的表情——'悲剧中的喜剧'。"],
             works=["《裸城》（1945）", "《犯罪现场》（1930s-1940s）", "《火灾》（1930s-1940s）", "《纽约之夜》（1940s）"],
             honors=["1945年，《裸城》出版并畅销。", "1947年，《裸城》被改编为电影。", "他的作品在1990年代被重新发现，被视为'街头摄影的先驱'。"],
             place=["维基是'小报摄影'（tabloid photography）的开创者——他的犯罪照片定义了1930-40年代纽约小报的视觉。", "他影响了后来的街头摄影师——闪光灯直射、近距离、人群中的幽默。", "他的《裸城》是'城市夜生活摄影'的早期经典。"])),
    dict(name="August Sander", slug="august-sander",
         queries=["August Sander portrait photography", "August Sander people of the 20th century"],
         subtitle="1876–1964 · 德国",
         bio_lines=["奥古斯特·桑德是'德国人'肖像的摄影师。他 1876 年出生于德国科隆附近的村庄。",
                    "他 1910 年代开始拍摄《20世纪的人》——按职业分类的德国人肖像：农民、工人、商人、艺术家、贵族。",
                    "纳粹上台后，他的作品因'不够美化德国人'被禁，他的儿子被关进集中营。他的项目最终未完成——但这组作品成为类型学肖像的奠基之作。"],
         chapter="03-房间里的人",
         essay=dict(
             headline="奥古斯特·桑德（1876—1964）：20世纪的人",
             bio=["奥古斯特·桑德，1876年出生于德国科隆附近。他早年在矿区工作，后成为职业摄影师。", "1910年代，他开始拍摄《20世纪的人》——按职业分类的德国人肖像。", "1964年，他在德国去世。"],
             history=["1910-1930年代，德国处于魏玛共和国时期——社会阶层复杂多元。", "桑德计划用600多张肖像记录'德国社会'——农民、工人、艺术家、贵族。", "1934年，纳粹禁印他的作品——他的儿子因政治原因被关进集中营。"],
             method=["相机：大画幅相机，黑白胶片。", "拍摄对象：德国社会各阶层的人。", "方法：正面、自然光、统一构图——被摄者直视镜头。"],
             technique=["类型学肖像：他按职业分类拍摄——农民、铁匠、面包师、艺术家——'人如其业'。", "《年轻的农民》（1914）：三个农民走在路上——20世纪最著名的肖像之一。", "他的方法影响了后来的贝歇夫妇、里内克·迪克斯特拉。"],
             works=["《年轻的农民》（1914）", "《20世纪的人》（1910s-1930s）", "《失业者》（1930s）", "《科隆》系列（1920s）"],
             honors=["1930年代，他的作品在科隆展出。", "1950年代，他的作品被重新发现。", "2000年代，他的《20世纪的人》被视为'肖像摄影的圣经'。"],
             place=["桑德是'类型学肖像'的奠基人——他的《20世纪的人》是'社会的人类学'。", "他的意义在于：肖像可以成为'社会的档案'——一个人的职业、阶层、时代。", "他影响了贝歇夫妇（类型学）、迪克斯特拉（阶段肖像）等一代人。"])),
    dict(name="Yousuf Karsh", slug="yousuf-karsh",
         queries=["Yousuf Karsh portrait photography", "Yousuf Karsh Winston Churchill"],
         subtitle="1908–2002 · 加拿大",
         bio_lines=["优素福·卡什是20世纪最著名的名人肖像摄影师。他 1908 年出生于土耳其，1924 年移居加拿大。",
                    "1941 年，他拍摄了丘吉尔——这张照片成为'英国精神'的象征，也是摄影史上最著名的肖像之一。",
                    "他拍摄了 50 多位世界领袖：爱因斯坦、海明威、肯尼迪、教皇。他的名言：'每个伟大的人，内心都有一个秘密。'"],
         chapter="03-房间里的人",
         essay=dict(
             headline="优素福·卡什（1908—2002）：伟人的秘密",
             bio=["优素福·卡什，1908年出生于土耳其，1924年移居加拿大。", "他1930年代在渥太华开设工作室，1941年拍摄丘吉尔成名。", "他一生拍摄了50多位世界领袖与艺术家。", "2002年，他在加拿大去世。"],
             history=["1941年，二战期间——丘吉尔访问加拿大议会。", "卡什在丘吉尔演讲后为他拍摄——他上前拿走丘吉尔的雪茄，拍下丘吉尔愤怒的表情。", "这张照片成为'英国精神'的象征，也被视为'领袖肖像'的标准。"],
             method=["相机：大画幅相机，黑白胶片，戏剧化的布光。", "拍摄对象：丘吉尔、爱因斯坦、海明威、肯尼迪、教皇。", "方法：精心布光，突出人物手部与眼神——他拍'手的姿势'与'眼神的力量'。"],
             technique=["《丘吉尔》（1941）：他拿走雪茄激怒丘吉尔，拍下'愤怒的狮子'——20世纪最著名的肖像。", "他的布光强调'戏剧性'——侧光、深背景、手部特写。", "他说'每个伟大的人内心都有秘密'——他的肖像试图揭示这个秘密。"],
             works=["《丘吉尔》（1941）", "《爱因斯坦》（1948）", "《海明威》（1957）", "《教皇约翰二十三世》（1960s）"],
             honors=["1941年，丘吉尔肖像全球刊载。", "1960年代，他的作品在各大美术馆展出。", "1996年，他获得国际摄影中心终身成就奖。"],
             place=["卡什是'领袖肖像'的标准——他的丘吉尔定义了'伟人的摄影'。", "他的戏剧化布光影响了后来的名人肖像摄影。", "他是'肖像即权力'这一传统的代表。"])),
    dict(name="Robert Mapplethorpe", slug="robert-mapplethorpe",
         queries=["Robert Mapplethorpe photography", "Robert Mapplethorpe flowers"],
         subtitle="1946–1989 · 美国",
         bio_lines=["罗伯特·梅普尔索普是20世纪最具争议的摄影师之一。他 1946 年出生于纽约皇后区。",
                    "他 1970 年代开始拍摄——黑人男性裸体、花卉、自画像。他的照片以极致的黑白和完美的构图著称。",
                    "1989 年他因艾滋病去世，年仅 42 岁。他的遗作展览在美国引发'艺术与审查'的大讨论。"],
         chapter="06-先锋与实验",
         essay=dict(
             headline="罗伯特·梅普尔索普（1946—1989）：完美的形式",
             bio=["罗伯特·梅普尔索普，1946年出生于纽约皇后区。", "他1970年代学习艺术，与歌手帕蒂·史密斯是好友。", "1980年代，他拍摄黑人裸体、花卉、名人。", "1989年，他因艾滋病去世，年仅42岁。"],
             history=["1970-1980年代，纽约的地下艺术圈——同性恋文化、先锋艺术。", "梅普尔索普用'古典的形式'拍摄'禁忌的题材'——他的黑人裸体是'形式与争议'的结合。", "1989年他死后，其遗作展在美国引发'艺术与审查'的全国讨论。"],
             method=["相机：中画幅与大画幅相机，黑白胶片。", "拍摄对象：黑人男性裸体、花卉、名人、自画像。", "方法：影棚布光，极致精确的构图——他的照片像'雕塑的照片'。"],
             technique=["黑白的极致：他的照片影调完美、构图精确——每一张都像古典雕塑。", "《花卉》系列（1980s）：他拍摄的花卉——兰花、百合——'肉体的隐喻'。", "《裸体》系列：他的黑人男性裸体——'形式与欲望'——引发巨大争议。"],
             works=["《花卉》（1980s）", "《黑人裸体》（1980s）", "《自画像》（1980s）", "《名人肖像》（1980s）"],
             honors=["1980年代，他的作品在纽约展出。", "1989年，他去世后作品在惠特尼美术馆展出。", "2016年，伦敦泰特美术馆为他举办回顾展。"],
             place=["梅普尔索普是'形式主义摄影'与'争议摄影'的交汇——他的照片完美，题材禁忌。", "他的遗作展引发'艺术与审查'的大讨论——这是摄影伦理史的重要章节。", "他的花卉与裸体，是20世纪后期最著名的黑白影像。"])),
    dict(name="Slim Aarons", slug="slim-aarons",
         queries=["Slim Aarons photography", "Slim Aarons poolside celebrities"],
         subtitle="1916–2006 · 美国",
         bio_lines=["斯利姆·阿伦斯是'富人的生活方式'摄影师。他 1916 年出生于纽约。",
                    "他 1940-1970 年代拍摄好莱坞明星与富人：泳池边、滑雪场、游艇上、豪宅里。",
                    "他的名言：'我拍的是有钱人过得好不好。'他的照片是'战后美国梦'的视觉档案。"],
         chapter="04-时尚的剧场",
         essay=dict(
             headline="斯利姆·阿伦斯（1916—2006）：富人的午后",
             bio=["斯利姆·阿伦斯，1916年出生于纽约。他1940年代开始摄影，为杂志拍摄名人。", "他专拍'富人的生活方式'——泳池、滑雪场、游艇、豪宅。", "2006年，他在美国去世。"],
             history=["1940-1970年代，美国战后繁荣——富人阶层的生活方式成为杂志题材。", "阿伦斯是'生活方式摄影'的代表——他拍的不是新闻，是'度假与休闲'。", "他的照片是'美国梦'的视觉档案。"],
             method=["相机：中画幅相机，彩色胶片。", "拍摄对象：好莱坞明星、富人、度假场景。", "方法：在名人的私人场合拍摄——泳池边、滑雪场——他的照片'像朋友拍的'。"],
             technique=["《泳池边》（Poolside Gossip，1970）：好莱坞名人围在泳池边——'富人的午后'。", "他的彩色照片色彩明亮、构图松弛——'度假感'。", "他的名言：'我拍的是有钱人过得好不好。'"],
             works=["《泳池边》（1970）", "《好莱坞》（1950s-1970s）", "《滑雪》（1960s）", "《游艇》（1970s）"],
             honors=["1940-1970年代，他是《生活》《Vogue》等杂志的摄影师。", "1990年代，他的作品被重新发现并畅销。", "2010年代，他的作品集成为'生活方式摄影'的经典。"],
             place=["阿伦斯是'生活方式摄影'（aspirational photography）的开创者。", "他的泳池边系列是20世纪后期最著名的'富裕影像'。", "他的作品在当代被大量收藏与模仿——'度假美学'的源头。"])),
    dict(name="Bill Brandt", slug="bill-brandt",
         queries=["Bill Brandt photography", "Bill Brandt nudes perspective"],
         subtitle="1904–1983 · 英国",
         bio_lines=["比尔·布兰特是20世纪英国最重要的摄影师之一。他 1904 年出生于德国汉堡。",
                    "他 1930 年代拍摄英国社会——上流社会与工人阶级的对比。1940-1950 年代，他拍摄了著名的《裸体》系列——用超广角镜头让身体变形。",
                    "他是'超现实主义'与'社会纪实'的结合者。"],
         chapter="06-先锋与实验",
         essay=dict(
             headline="比尔·布兰特（1904—1983）：变形的身体",
             bio=["比尔·布兰特，1904年出生于德国汉堡。他1920年代在巴黎做过曼·雷的助手。", "1930年代他在英国拍摄社会纪实。", "1940-1950年代，他拍摄了《裸体》系列。", "1983年，他在伦敦去世。"],
             history=["1930年代，英国社会阶级分明——布兰特记录了上流社会与工人阶级的对比。", "1940年代，他转向'主观摄影'——裸体、风景、梦境。", "他的《裸体》系列用超广角镜头——身体在房间中变形。"],
             method=["相机：大画幅与35mm相机，黑白胶片。", "拍摄对象：英国社会、裸体、风景。", "方法：早期纪实，后期用超广角与极端透视拍摄裸体。"],
             technique=["《英国生活》系列（1930s）：上流社会的客厅与矿工的晚餐——'阶级的对比'。", "《裸体》系列（1945-1960s）：超广角镜头下的身体——手、脚、乳房被放大变形——'肉体的抽象'。", "超现实主义的影响：他做过曼·雷的助手——他的作品带'梦境'色彩。"],
             works=["《英国生活》（1930s）", "《裸体》（1945-1960s）", "《雾中的伦敦》（1940s）", "《风景》（1950s）"],
             honors=["1930年代，他是英国最重要的纪实摄影师之一。", "1960年代，他的作品在MoMA展出。", "2004年，伦敦泰特美术馆为他举办回顾展。"],
             place=["布兰特连接了'社会纪实'与'先锋实验'——他先记录英国，再变形身体。", "他的《裸体》是'超现实身体摄影'的经典。", "他是英国摄影从纪实转向主观的关键人物。"])),
    dict(name="Graciela Iturbide", slug="graciela-iturbide",
         queries=["Graciela Iturbide photography", "Graciela Iturbide Mexico"],
         subtitle="1942– · 墨西哥",
         bio_lines=["格拉谢拉·伊图尔维德是墨西哥最重要的女摄影师。她 1942 年出生于墨西哥城。",
                    "她 1970 年代开始拍摄墨西哥的原住民文化——瓦哈卡的萨波特克人、沙漠的塞里人。",
                    "她的照片黑白、诗意、带着魔幻现实主义的色彩。她至今仍在拍摄。"],
         chapter="02-纪实的重量",
         essay=dict(
             headline="格拉谢拉·伊图尔维德（1942—）：墨西哥的魔幻",
             bio=["格拉谢拉·伊图尔维德，1942年出生于墨西哥城。", "她1960年代学习电影，1970年代转向摄影。", "她长期拍摄墨西哥的原住民文化。", "她至今仍在拍摄。"],
             history=["1970年代，墨西哥的'原住民文化'开始被重新认识。", "伊图尔维德拍摄瓦哈卡的萨波特克人、索诺拉沙漠的塞里人。", "她的照片带'魔幻现实主义'——日常与神话交融。"],
             method=["相机：35mm相机，黑白胶片。", "拍摄对象：墨西哥原住民、街头、宗教仪式。", "方法：长期驻留，融入社区，拍摄'文化的日常'。"],
             technique=["《妇女的力量》（1979）：瓦哈卡妇女的照片——她拍出'女性的尊严'。", "《沙漠中的山羊》（1979）：塞里人的山羊——魔幻的日常。", "她的照片诗意而神秘——'墨西哥的魔幻现实主义'。"],
             works=["《妇女的力量》（1979）", "《塞里人》（1970s-1980s）", "《墨西哥》（1970s-2000s）", "《鸟》（1990s）"],
             honors=["1988年，获得古根海姆奖金。", "1990年代，她的作品在国际展出。", "2008年，获得哈苏基金会国际摄影奖。"],
             place=["伊图尔维德是'墨西哥原住民摄影'的代表。", "她的意义在于：她用'诗意的镜头'记录'被忽视的文化'。", "她是拉美女性摄影师的象征人物。"])),
    dict(name="Eikoh Hosoe", slug="eikoh-hosoe",
         queries=["Eikoh Hosoe photography", "Eikoh Hosoe Kamaitachi"],
         subtitle="1933–2024 · 日本",
         bio_lines=["细江英公是日本战后最重要的摄影家之一。他 1933 年出生于日本山形县。",
                    "他 1960 年代拍摄了《蔷薇刑》（Ordeal by Roses，1963）——作家三岛由纪夫的身体。",
                    "他与舞者土方巽合作拍摄《镰鼬》（Kamaitachi，1968）——前卫舞蹈与摄影的结合。他是日本'主观摄影'的代表。"],
         chapter="06-先锋与实验",
         essay=dict(
             headline="细江英公（1933—2024）：身体的神话",
             bio=["细江英公，1933年出生于日本山形县。他1950年代开始摄影。", "1960年代，他拍摄了三岛由纪夫的《蔷薇刑》。", "他与舞者土方巽合作《镰鼬》。", "2024年，他在日本去世。"],
             history=["1950-1960年代，日本战后前卫艺术兴起。", "细江英公是'主观摄影'的代表——他拍的不是现实，是'神话与身体'。", "1960年代，他与作家三岛由纪夫、舞者土方巽合作——'艺术家的摄影'。"],
             method=["相机：中画幅相机，黑白胶片。", "拍摄对象：三岛由纪夫、舞者土方巽、身体、神话。", "方法：戏剧化的布光与摆拍——他的照片像'能剧的舞台'。"],
             technique=["《蔷薇刑》（1963）：三岛由纪夫的身体——蔷薇、绳索、阴影——'身体的神话'。", "《镰鼬》（1968）：土方巽的舞蹈——在稻田、村庄中——'前卫舞蹈的摄影'。", "他的照片融合日本美学（能剧、歌舞伎）与前卫艺术。"],
             works=["《蔷薇刑》（1963）", "《镰鼬》（1968）", "《西蒙》（1970s）", "《蝴蝶梦》（1970s）"],
             honors=["1960年代，他是日本前卫摄影的核心。", "1970年代，他的作品在国际展出。", "1990年代，他获得日本政府颁发的紫绶褒章。"],
             place=["细江英公是'身体摄影'与'主观摄影'的日本代表。", "他的《蔷薇刑》是20世纪最著名的'艺术家肖像'之一。", "他与森山大道、东松照明共同塑造了1960年代日本前卫摄影。"])),
    dict(name="Joel Sternfeld", slug="joel-sternfeld",
         queries=["Joel Sternfeld photography", "Joel Sternfeld American prospects"],
         subtitle="1944– · 美国",
         bio_lines=["乔尔·斯特恩菲尔德是美国'新地形摄影'的代表。他 1944 年出生于纽约。",
                    "他 1978-1986 年拍摄《美国前景》——彩色胶片记录美国的日常风景：加油站、火灾后的房屋、荒芜的街道。",
                    "他的照片表面平静，内里藏着社会与环境的议题——他被称为'彩色摄影的哲学家'。"],
         chapter="05-风景的秩序",
         essay=dict(
             headline="乔尔·斯特恩菲尔德（1944—）：平静的危机",
             bio=["乔尔·斯特恩菲尔德，1944年出生于纽约。他1960年代开始摄影。", "1970年代，他转向彩色胶片拍摄美国风景。", "他至今仍在拍摄。"],
             history=["1970年代，美国'新地形摄影'兴起——拍摄'人造风景'。", "斯特恩菲尔德是其中的代表——他用8×10大画幅拍摄美国的日常。", "他的《美国前景》（1978-1986）是'彩色风景摄影'的里程碑。"],
             method=["相机：8×10大画幅相机，彩色胶片。", "拍摄对象：美国的日常风景——加油站、小镇、火灾现场。", "方法：驾驶穿越美国，等待光线，用大画幅拍摄'场景'。"],
             technique=["《美国前景》（1987）：他拍摄的美国风景——表面平静，内藏危机。", "《麦克莱恩的火灾》（1978）：消防员摘南瓜——房子在燃烧——'日常中的灾难'。", "他的照片'平静而沉重'——他被称为'彩色摄影的哲学家'。"],
             works=["《美国前景》（1987）", "《麦克莱恩的火灾》（1978）", "《陌生之地》（1990s）", "《徒步》（2000s）"],
             honors=["1987年，《美国前景》出版。", "1990年代，他获得古根海姆奖金。", "2004年，他获得国际摄影中心无限奖。"],
             place=["斯特恩菲尔德是'新地形摄影'与'彩色风景'的代表。", "他的意义在于：他用'平静的画面'记录'社会的危机'。", "他与肖尔共同定义了1970年代美国的彩色风景摄影。"])),
    dict(name="Trent Parke", slug="trent-parke",
         queries=["Trent Parke photography", "Trent Parke Sydney street"],
         subtitle="1971– · 澳大利亚",
         bio_lines=["特伦特·帕克是澳大利亚最重要的当代摄影师。他 1971 年出生于纽卡斯尔。",
                    "他是马格南唯一的澳大利亚成员。他 2000 年代拍摄了悉尼街头——《时光》（Minutes to Midnight，2003）——用黑白记录了澳大利亚的日常与光线。",
                    "他的照片带有'澳洲的阳光与阴影'——他至今仍在拍摄。"],
         chapter="01-街头的等待",
         essay=dict(
             headline="特伦特·帕克（1971—）：澳洲的光",
             bio=["特伦特·帕克，1971年出生于澳大利亚纽卡斯尔。", "他1990年代开始摄影，2000年代成为马格南成员。", "他是马格南唯一的澳大利亚成员。", "他至今仍在拍摄。"],
             history=["1990年代，澳大利亚摄影在国际上崭露头角。", "帕克是其中代表——他是马格南唯一的澳大利亚成员。", "2003年，他出版《时光》——澳洲日常的黑白影像。"],
             method=["相机：35mm相机，黑白胶片。", "拍摄对象：悉尼街头、澳洲日常、光与影。", "方法：在街头行走拍摄，等待'澳洲特有的光线'。"],
             technique=["《时光》（2003）：他拍摄的澳洲——阳光、阴影、日常——'澳洲的光线'。", "他的黑白照片带'南方之光'——强烈的对比、锐利的阴影。", "《梦想》（2013）：他与妻子共同完成的项目——关于澳洲的梦。"],
             works=["《时光》（2003）", "《梦想》（2013）", "《悉尼》（2000s）", "《澳洲》（2000s-2010s）"],
             honors=["2003年，《时光》获得多个国际奖项。", "2004年，他加入马格南。", "2010年代，他在国际举办展览。"],
             place=["帕克是'澳洲街头摄影'的代表——他把澳洲的光线带入马格南。", "他是马格南最年轻的成员之一——代表澳洲摄影的当代崛起。", "他的《时光》是'南半球街头摄影'的经典。"])),
    dict(name="Alexey Titarenko", slug="alexey-titarenko",
         queries=["Alexey Titarenko photography", "Alexey Titarenko St Petersburg"],
         subtitle="1962– · 俄罗斯",
         bio_lines=["阿列克谢·季塔连科是'长曝光街头摄影'的代表。他 1962 年出生于圣彼得堡。",
                    "他 1990 年代拍摄了《城市之影》——用长曝光让行人变成幽灵般的影子。他的照片记录了苏联解体后的圣彼得堡。",
                    "他至今仍在拍摄，是'观念街头摄影'的代表。"],
         chapter="01-街头的等待",
         essay=dict(
             headline="阿列克谢·季塔连科（1962—）：城市的幽灵",
             bio=["阿列克谢·季塔连科，1962年出生于圣彼得堡。", "他1980年代开始摄影。", "1990年代，他拍摄了《城市之影》系列。", "他至今仍在拍摄。"],
             history=["1990年代，苏联解体——圣彼得堡陷入混乱与贫困。", "季塔连科用长曝光拍摄街头——行人变成'幽灵'。", "他的照片记录了'历史的转型期'。"],
             method=["相机：35mm相机，黑白胶片。", "拍摄对象：圣彼得堡街头、行人、地铁。", "方法：长曝光（数秒）——让移动的人群变成模糊的影子。"],
             technique=["《城市之影》（1991-1994）：长曝光下的行人——'时间的幽灵'。", "《列宁的告别》（1990s）：圣彼得堡的转型期——雕像被移除、街头的混乱。", "他的长曝光'观念化'了街头摄影——时间是主角。"],
             works=["《城市之影》（1991-1994）", "《列宁的告别》（1990s）", "《地铁》（2000s）", "《古巴》（2010s）"],
             honors=["1990年代，他在俄罗斯及欧洲展出。", "2000年代，他的作品在国际获奖。", "2010年代，他的作品集全球出版。"],
             place=["季塔连科是'长曝光街头摄影'的代表。", "他的意义在于：他把'时间'带入街头摄影——行人成为时间的痕迹。", "他与杉本博司（影院）并列，是'时间的摄影'的东方代表。"])),
    dict(name="Pentti Sammallahti", slug="pentti-sammallahti",
         queries=["Pentti Sammallahti photography", "Pentti Sammallahti Finland birds"],
         subtitle="1950– · 芬兰",
         bio_lines=["彭蒂·萨马拉赫蒂是芬兰最重要的风景摄影师。他 1950 年出生于赫尔辛基。",
                    "他拍摄北欧的风景——雪、海、鸟、荒原——他的黑白照片安静而辽阔。",
                    "他的照片被称为'北欧的寂静'——他至今仍在拍摄。"],
         chapter="05-风景的秩序",
         essay=dict(
             headline="彭蒂·萨马拉赫蒂（1950—）：北欧的寂静",
             bio=["彭蒂·萨马拉赫蒂，1950年出生于赫尔辛基。", "他1970年代开始摄影。", "他拍摄北欧的风景与动物。", "他至今仍在拍摄。"],
             history=["1970-1990年代，北欧摄影以'自然的寂静'著称。", "萨马拉赫蒂是其中的代表——他拍摄芬兰、俄罗斯、北极的风景。", "他的照片被称为'北欧的寂静'。"],
             method=["相机：中画幅相机，黑白胶片。", "拍摄对象：雪、海、鸟、荒原、村庄。", "方法：长途旅行，等待光线，拍摄'辽阔的寂静'。"],
             technique=["《北方》系列：他拍摄的芬兰与俄罗斯北方——雪原、海、孤鸟。", "他的照片'安静而辽阔'——大面积的留白、微小的动物。", "《白鸟》（1990s）：雪地中的鸟——'自然的诗'。"],
             works=["《北方》（1980s-2000s）", "《白鸟》（1990s）", "《赫尔辛基》（1970s-1980s）", "《旅程》（2000s）"],
             honors=["1990年代，他的作品在欧洲展出。", "2000年代，他获得芬兰国家摄影奖。", "2010年代，他的作品集全球出版。"],
             place=["萨马拉赫蒂是'北欧风景摄影'的代表。", "他的意义在于：他把'寂静'变成摄影的题材——北欧的辽阔与孤独。", "他与迈克尔·肯纳并列，是'极简风景'的当代代表。"])),
    dict(name="Manuel Álvarez Bravo", slug="manuel-alvarez-bravo",
         queries=["Manuel Alvarez Bravo photography", "Manuel Alvarez Bravo Mexico surreal"],
         subtitle="1902–2002 · 墨西哥",
         bio_lines=["曼努埃尔·阿尔瓦雷斯·布拉沃是20世纪墨西哥最重要的摄影师。他 1902 年出生于墨西哥城。",
                    "他 1920-1970 年代拍摄墨西哥——街头、裸体、宗教、超现实。他的照片融合了'墨西哥文化'与'超现实主义'。",
                    "他与弗里达·卡罗、迭戈·里维拉同时代——他的照片是'墨西哥魔幻现实主义'的视觉。"],
         chapter="06-先锋与实验",
         essay=dict(
             headline="曼努埃尔·阿尔瓦雷斯·布拉沃（1902—2002）：墨西哥的超现实",
             bio=["曼努埃尔·阿尔瓦雷斯·布拉沃，1902年出生于墨西哥城。", "他1920年代开始摄影。", "他拍摄墨西哥的街头、文化、超现实。", "2002年，他在墨西哥城去世，享年100岁。"],
             history=["1920-1930年代，墨西哥革命后的文化复兴——壁画运动、艺术复兴。", "布拉沃是其中的摄影代表——他记录'墨西哥的日常与神话'。", "他与超现实主义者（布勒东）交往——他的照片带'魔幻现实主义'。"],
             method=["相机：大画幅与35mm相机，黑白胶片。", "拍摄对象：墨西哥街头、裸体、宗教、静物。", "方法：在街头与室内之间——他的照片'介于纪实与梦境之间'。"],
             technique=["《两个女人》（1929）：窗边的两个女人——'日常的超现实'。", "《好笑的玩笑》（1938）：缠绕的身体——情欲与超现实。", "他的照片融合墨西哥文化（宗教、死亡、街头）与超现实主义。"],
             works=["《两个女人》（1929）", "《好笑的玩笑》（1938）", "《墨西哥》（1920s-1970s）", "《裸体》（1930s-1940s）"],
             honors=["1930年代，他与超现实主义运动交往。", "1970年代，他在国际举办展览。", "1990年代，他获得哈苏基金会国际摄影奖。"],
             place=["布拉沃是'墨西哥摄影'的奠基人——他把墨西哥文化带入世界摄影史。", "他的意义在于：'纪实与超现实'的结合——墨西哥的魔幻现实主义。", "他与弗里达·卡罗、迭戈·里维拉同时代——他是'墨西哥文艺复兴'的摄影之眼。"])),
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
    log(f"  {name}: dedup {rm}, final {final}")
    if final == 0:
        shutil.rmtree(img_dir)
        log(f"  ❌ {name}: zero images, removed")
        return
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
