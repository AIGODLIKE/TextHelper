"""Find zh_Hant entries that still look simplified or untranslated."""
import json
import re
from pathlib import Path

I18N = Path(__file__).resolve().parent
SIMPLIFIED_HINTS = set(
    "国发开关门头无书长见车东丝两严丧个丰临为举义乌乐乔习乡书买乱了云亚产亩亲亿仅从仓仪们价众优会伞伟传伤伦伪体余佣侠侧侨侬侯便促俄俊俗保信俭修俱俩债值倾假偏做停健偶偷偿储儿兑党兰关兴养兽内册军农冬冯冲决况冷冻净准减凤凭凯出击函刀刃分切划列刘则创删别到制刷券刹刺刻剂剃削前剑剧剩剪副割劝办功加务动助努励劳势勇勉勋勒勤勾勿匀包化北区医十半华协单卖南博占卡卫印危即却卷厂厅历压厌厕厘厚原去参又及友双反发取受变叙口古句另只叫召可台史右叶号叹各合吉同名后向吗君否吧含启吴吸吹吾呀呆告员呜呢周味呼命和咨咬咱品哈响哥哪唤售商善喜喝喷嗓嘉嘛嘴器四回因团园困围固国图圆圈土在地场圾址均坏坐块坚坛坝坞坟坠坡坤坦坪垂型垒城域培基堂堆堡堪塑塔塞填境增墨壁壤士壮声壳壶处备复外多夜大够梦头夸夺奇奋女奴好如妈始姐姑姓委姿威娃娱媒嫌子字存学它宁宇安宋完宏宗官定宜宝实宠审客宣室宫害家容宽宾宿密富寒寝对寻导寿封射将尊小少尔尖尘尚尝就尺尽局层屋屏展属山岗岛岩岭岸峰崇崩川州巡工左巧巨差己已巴巷币市布师希带帧帮常幅幕干平年并幸广庄庆床序库应底店庙府度座庭康延建开异弃弄弊式引张强当录形彩影彻征径待很径徒得从复心必忆忌忍志忘忙忠快念忽态怎怒怕思急性怪总恋恐恒恢恨恩恭息恰恶恼悉患您悬情惊惯想愈愉意感愤愧愿慈慢懂懒成我战户所扁扇手才打托扣执扩扫扬扭扮扰找承技抄把抓投抗折抛抢护报抱抵抽担拉拍拐拒拓拔拖招拟拥择括拭拯拳拿持挂指按挑挖挡挣挤挥挨挪挫振挺挽捂捲损捡换据捷授掉掌排掘掠探接控推掩措掰掷揉描提插握搜搞搬搭摄摆摇摊摔摘摧摸撑撒撞播操擎擦支收改攻放政故效敌敏救教散数整文斗料斜斩断斯新方施旁旅旋族旗无既日旧早时明易星映春是显晃晋晒晓晚普景智暂暗暴曲更曾替最月有朋服望朝期木未末本术机杀杂权杆条来杨杯板极构析林枚果枝架柜查标栈树校样核根格框案桌桑档桥梁梅梦检棋棍棒棚森椅植椰楚楼概榜模横樱欠次欢欧欲欺款歉歌止正此步武歧死残段毁毅每比毕毙毛毫氏民气水永求汇汉污汤汪汽沃沉没沙沟河油治沿泄泉泊法泛泡波泥注泪泰洁洋洒洗洛洞津洪洲活流浅测济浓浪浮海消涉涛润涨液深混清渐渡温港游湖湾源溜满滤滥滨滴漏演漠漫潜潮激灌火灭灯灰灵灶灾炉炮点炼烂烟烤热焦然照熊熟燃爆爱父爷爽片版牌物特状犹狗独狮狱狼猛献玄率王玩环现球理瑞瓜瓦瓶甘生用由电男画畅异疆疗疯登白百的皆皇皮益监盖盘盛目直相省看真眼着睡督矛知短石码破础硬确碍碎碰示礼社神票禁福离秀私秋种科秒秘租积称移程税稳空穿突窗窝立站竞竟章童端笔符第等筋答策签简算管箱篮类粉粗精系素索紧紫累繁红约级纯纲纳纵线练组细终经结绕绘给统继绩绪续维绵绿缓编缘缝缠缩缺网罪置羊美群义羽翔翘老考而耐耗耳联聪肉肠股肤肥肩肯育胀胆背胎胜胡能脚脱脸腊腾腿自至致舌舍航般良色艺节花苍苏苦英范荐荡药获菜营落著蒙蒸蓝虑虽虾蚕行街衡补表被装西要覆见观规视览觉览触言誉计订认让训议记讲许论设访证评识诉词试诗诚话该详语误说请读调谈谢谨谱谷豆象豪负财责贤败账货质贩贪购贯贴贵费贺资赋赏赔赖赛赞走起超越足跃践踪身车轨转轮软轰轻载较辅辆辈辉输辨辩边达迁过迈运近返还这进远违连迟述追退送适选透逐递途通速造逢逸逻遗避邀那邮邻部都配酒酷酸醉醒里重野量金针钟钢钱铁铜银铺链销锁锅锋锐错锦键镜长门闪闭问间闻阅队阳阴阵阶际陆陈降限院除险陪随隐隔难雄集雨雪零雷雾需震露青静非靠面革音页顶项顺须预领频题颜额风飞食餐饥饭饮饰饱饼馆首马驱验骑骗骨高鬼魂魔鱼鸟鸡鸣鸭黄黑默鼓鼠齐齿龄龙"
)
# Common chars that differ in TW vs CN but OpenCC s2twp should handle - scan for simplified-only chars in output

catalog = json.loads((I18N / "_catalog.json").read_text(encoding="utf-8"))
hant = json.loads((I18N / "zh_Hant.json").read_text(encoding="utf-8"))
hans_by_id = {(i["context"], i["msgid"]): i.get("zh_HANS", "") for i in catalog}
issues = []
same_as_hans = []
ascii_only = []
for item in hant:
    key = (item["context"], item["msgid"])
    zh = item.get("zh_Hant", "")
    hans = hans_by_id.get(key, "")
    if not zh:
        issues.append(("empty", key, item["msgid"]))
        continue
    if zh == hans and re.search(r"[\u4e00-\u9fff]", zh):
        same_as_hans.append((key, zh))
    # chars in simplified hint set appearing in hant (likely missed conversion)
    missed = sorted({c for c in zh if c in SIMPLIFIED_HINTS})
    if missed:
        issues.append(("simplified_chars", key, item["msgid"], "".join(missed), zh))
    if re.fullmatch(r"[A-Za-z0-9\s\.\,\:\;\-\+\(\)\[\]\{\}/\\&\#\*\_\|\"\'\`\~\@\$\%\^\=\<\>\?！？。，、·…]+", zh or ""):
        if re.search(r"[A-Za-z]{3,}", zh):
            ascii_only.append((key, item["msgid"], zh))

print("=== same as zh_HANS (possibly not converted) ===")
for key, zh in same_as_hans[:40]:
    print(f"  [{key[0]}] {key[1]!r} -> {zh!r}")
print(f"  total: {len(same_as_hans)}")

print("\n=== simplified char hints in zh_Hant ===")
for row in issues[:50]:
    print(" ", row)
print(f"  total: {len(issues)}")

print("\n=== mostly ASCII (brand/ok) ===")
for row in ascii_only[:20]:
    print(" ", row)
print(f"  total: {len(ascii_only)}")
