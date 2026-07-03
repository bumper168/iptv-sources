#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动收集、整理、测试直播源并推送到GitHub
- 从多个公开上游源收集
- 过滤购物台/广告台/广播台
- 分类整理（央视/卫视/地方/港台/国外）
- 测试可用性
- 推送到 GitHub 仓库
"""
import requests
import re
import os
import json
import time
import base64
import hashlib
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urlencode

# ========== 咪咕视频签名密钥 ==========
MIGU_KEYS = [
    "7c8ddcab45b340ecbb02bc979c7f58c8", "7a5d79ed05ed48c4908b0179d5a5eb2c",
    "2195d5312d114db397bcfb5ade3784cf", "5454203c18274e8a961efe328a59d1f9",
    "aa4688fcf6844e809cb428dc4bd5f265", "96f3d14a9fe144589f10c775e0c9b4b0",
    "fbc05527db71425f8094e659d62eb878", "c8e65a8b8b3d46f89397573bfa06f68a",
    "a1ef732fa53846c3ba96ada1dcf2513d", "48172134576c43889a5b82f0e2809779",
    "b7334bae489846ccb5b04574e62c9b7c", "5e6c8bee9ad449488d6a60a82ae6e2dc",
    "78c979d58cdb4caa849229a11363bd7c", "5889ccde4570438790be07ee2d8ecde0",
    "f3ebbe5ad4cf42569d1450780789fa2d", "60e57db48d1c4a0f9d614d1ce43fa865",
    "ee892b1bd1074dd7bbd6ab84c3b21fc4", "df0d80d82df84a9590469ad943a758c2",
    "7ce5870b296d42119dea1b0780892167", "0637030a22db41c78615d67cfc42da04",
    "803b409a8df045f990b4cabde9e3cce5", "869973ee8f3543599600cd838503475a",
    "6c83090c16f84d57a987edd3bdd11599", "926ca9cb02674db69e50afde57d8c67b",
    "3ce941cc3cbc40528bfd1c64f9fdf6c0", "eb3de9fccd40429ab7480d857308612d",
    "980ff7db262f49e1820075a7d932deb5", "906c7c50da224618",
    "f81d1140ebb94bbba74baf5858cf132e", "dbfd1cfe66ee4bbc8cdb13ba8758b8fc",
    "fe57125553fe4cbdbe12abf7c7cd6ed1", "5be7f5b3331f4a6e95f6976d7aaeaa28",
    "68979e717f0b424ba64c8e53ecbcc8ac", "4e61f98facc64fb2a4b91eaea736a5c7",
    "f05aa2f4f2124faa89802fd01d3ba436", "32f3994485ff48b3bce430ba3618ba39",
    "be0ff8b380444ef69f775729c0c191b0", "b30ccc7e48ec469c945aa546757e9ab4",
    "bc1deb4002b44ddf8d181f1972a3cb6a", "4bcc96256014c4172878",
    "37856b8633a841aebfb76d0ff596b9df", "ab2fcbf4d28c4ac9897f867af6c25f9d",
    "535200fa8b5d41db8f95ad6bd9033b48", "75a9af00d3da4ceebc2a70018aea842c",
    "08398753dbdb4bcab39a5ce820d220bd", "2d0dc516945f4c03b462571bca898234",
    "c3f3f929917547af8b8dd76b7eafbfa8", "2c5190bb4e244501a4f1be0e8de5015e",
    "035f814657c44324bc4fe073898f0789", "df6d1836cf7b4a118cbca68a5103dc7b",
    "a27aceb56688403fa5163c0ae02987dc", "a8ef203282724897a707d8c3f264f7ad",
    "16264f8569764a5b932c5a6e4206f487", "fea3a87c09bb406182796c08943713ae",
    "85b14746e58c4b33a56abec13cd3290b", "61e74ad5375f479d86c4997336bbc459",
    "b3991eed9c734f06a721ba97e43024a1", "11fba116b6474a16955b738490f8983f",
    "f8a5e365c8a448888dce771e27d0a6c7", "773a341ae0e542088c9655dbd232d1bd",
    "863f85c3032e4012b3c87d5b52d5fb8c", "3e6098467d6c40828e6412293148648f",
    "c5d2cc3c27aa44ec9c2daca6045d7e8e", "4ead9ffe0aa04f8c93a7",
    "29748e6741b142ffa67a9f9c7411eece", "932dcb4ba6084e1eb4d2639cf7c64d9c",
    "c0e6340469604cf7ae3cc7c9e5db0f66", "c387dbdaf30d496aa1b7a3dda102bf08",
    "3281503f3dfe4ed3b474cd550d229cd7", "10187fd2e6504a8bbd4e1c1b88d9a0f1",
    "608489b77e6f4d1c8e90f5c60003a698", "2992342e0cb74c7491a7480d97041dcc",
    "e14825a4dcaa45ffb222a519f292a61f", "bc648171ed0b46ff93396746e3d96a88",
    "44a41389e4df4f7da6c7c48eff751266", "14db12bdfdc94c92941b7df55e8e5d15",
    "a23350dfdb2247aa832c3251ccc560b2", "c1a62f301b6e4f119f4c6a278d660e68",
    "f458f40c3d1c44ef833a8a5e933df839", "a1bcb6ca2ebd4f5497d0e83c3534c319",
    "068d8051a7324a5bbf9fbe0e1c199062", "da2e57efa74a4eca847a346513f66c9d",
    "e4876dd41a5d4136886ded262ae7d522", "60e88c6eb37e4edbb1014e3785e64a1b",
    "fe996131d5e0429688cb7e8c990cf6a9", "e8ba509d0d094c068f9d00d627c59c6e",
    "66f1f4a79c8c4cdfaf8f27a12b1625fc", "865002edf65543abb23b0177da39d602",
    "d1196d8595cb459f82e7ae5bc460441d", "55ce840e78e04c28951fa5ebac61e66f",
    "4ad156b75be24f8a9732d516079ce872", "e1d757845a4c4a6690f640ca817675ba",
    "dd8982151e9b4be4b1324cb59b24f5de", "1d7ff52f2bf046b09d08731587459c0d",
    "4bb5342486844c1689d9ba7a676bab87", "5d6936ea19004c698739e2cfe82fc968",
    "a8e968e5cf934cd29197c2bfa5186cc1", "11422727790b4f29a356ac2730aa2d0b",
    "1842dbb5cec54267b9ed05ec64fd59b6", "58cf465392214c91bc18bd8c46d3b109",
]

def generate_migu_sign(cont_id, app_version="2600037000"):
    """生成咪咕视频签名参数"""
    current_time = str(int(time.time() * 1000))
    cY = hashlib.md5((current_time + cont_id + app_version[:8]).encode()).hexdigest()
    
    index = int(current_time[6:]) % 100
    key = MIGU_KEYS[index]
    
    sign = hashlib.md5((str(cY) + key + "migu" + current_time[:4]).encode()).hexdigest()
    salt = str(int(random.random() * 88888888 + 10000000))
    
    return {
        'timestamp': current_time,
        'sign': sign,
        'salt': salt
    }

def build_migu_url(cont_id):
    """构建咪咕视频直播URL"""
    params = generate_migu_sign(cont_id)
    url = "https://play.miguvideo.com/playurl/v1/play/playurl"
    query = {
        'xavs2': 'true', 'vr4k': '1', 'nt': '4',
        'sign': params['sign'], 'xh265': 'true', 'ua': '22041216C',
        'shortPlay': 'true', 'vivid': '0', 'scene': '02-00-lcp',
        'rateType': '3', 'contId': cont_id, 'drm': 'true',
        'timestamp': params['timestamp'], 'super4k': 'false', 'avs': 'false',
        'drmN': 'true', 'chip': 'Redmi', 'salt': params['salt'],
        'os': '12', 'startPlay': 'true', '2Kvivid': 'false',
        'multiViewN': '0', 'superPlay': '1', 'sessionId': 'f6214e9ba16b5cfb',
        'dolby': 'false', '4kvivid': 'false', 'ott': 'false',
        'hdrversion': '87', 'trackSubtitle': 'true', 'isRaming': '0',
        'h265N': 'true' if cont_id == '608831231' else 'false',
        '4kDifinition': 'false', 'isMultiView': 'true', 'vr': 'true',
        'avsvivid': 'false', 'hdrmode': '22041216C'
    }
    return f"{url}?{urlencode(query)}"

# ========== GitHub 配置 ==========
GITHUB_USER = "bumper168"
GITHUB_REPO = "iptv-sources"
# 从环境变量读取 token（GitHub Actions 自动注入，本地运行需手动设置）
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_API = "https://api.github.com"

# ========== 上游源列表 ==========
UPSTREAM_SOURCES = [
    # iptv-org 开源项目
    "https://iptv-org.github.io/iptv/countries/cn.m3u",
    # 国内常用源
    "https://gh-proxy.com/raw.githubusercontent.com/vbskycn/iptv/refs/heads/master/tv/iptv4.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/billy21/Tvlist-awesome-m3u-m3u8/master/m3u/%E5%9B%BD%E5%86%85.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/hujingguang/ChinaIPTV/main/cnTV_AutoUpdate.m3u8",
    # 更多源
    "https://gh-proxy.com/raw.githubusercontent.com/kimcrowing/IPTV/main/cn.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/YueChan/Live/main/IPTV.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/ssili126/tv/main/itvlist.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/Guovin/TV/gd/latest.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/joevess/IPTV/main/zhihu.m3u8",
    "https://gh-proxy.com/raw.githubusercontent.com/Alvin9999/new-pac/master/iptv.md",
    "https://gh-proxy.com/raw.githubusercontent.com/iptv-sources/iptv-sources.github.io/main/sources/cn.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/imdjm/iptv/main/TV.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/lalifeier/IPTV/main/channels/cn.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/Meroser/IPTV/main/IPTV.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/bestpika/iptv/master/cn.m3u",
    # 新增稳定源 - 央广移动等
    "https://gh-proxy.com/raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/ray3699/ray3699.github.io/main/m3u/radio.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/frankwuzp/iptv/main/cn.m3u8",
    "https://gh-proxy.com/raw.githubusercontent.com/EvilCult/iptv-m3u-maker/master/m3u/chinamobile.m3u",
    "https://gh-proxy.com/raw.githubusercontent.com/haoit/iptv/main/migu.m3u",
]

# ========== 自定义频道源（手动添加，跳过测试强制加入） ==========
# 仅添加无过期参数的官方稳定源，避免塞入短期失效的死链
# migu://前缀表示动态生成URL的咪咕频道
CUSTOM_CHANNELS = [
    # 港台频道
    {"name": "港台测试频道", "url": "http://212.102.38.45/live/test_dorcel_hd_hevc/playlist.m3u8", "category": "gangtai", "logo": ""},
    # 卫视官方稳定源（从电视直播pro抓取，电视台自有域名，无签名过期参数）
    {"name": "浙江卫视", "url": "http://ali-xwl.cztv.com/live/channel011080Plxw.m3u8", "category": "weishi", "logo": ""},
    {"name": "陕西卫视", "url": "http://stream.snrtv.com/sxbc-star-nvDEQ9.m3u8", "category": "weishi", "logo": ""},
    # 咪咕动态频道（migu://前缀，播放时实时生成URL）
    {"name": "湖南卫视", "url": "migu://5500167521", "category": "weishi", "logo": ""},
    {"name": "东方卫视", "url": "migu://5500469363", "category": "weishi", "logo": ""},
    {"name": "江苏卫视", "url": "migu://5500469365", "category": "weishi", "logo": ""},
    {"name": "北京卫视", "url": "migu://5500469357", "category": "weishi", "logo": ""},
    {"name": "安徽卫视", "url": "migu://5500469367", "category": "weishi", "logo": ""},
    {"name": "山东卫视", "url": "migu://5500469369", "category": "weishi", "logo": ""},
    {"name": "四川卫视", "url": "migu://5500469375", "category": "weishi", "logo": ""},
    {"name": "湖北卫视", "url": "migu://5500469377", "category": "weishi", "logo": ""},
    {"name": "河南卫视", "url": "migu://5500469379", "category": "weishi", "logo": ""},
    {"name": "辽宁卫视", "url": "migu://5500469383", "category": "weishi", "logo": ""},
    {"name": "黑龙江卫视", "url": "migu://5500469385", "category": "weishi", "logo": ""},
    {"name": "天津卫视", "url": "migu://5500469359", "category": "weishi", "logo": ""},
    {"name": "江西卫视", "url": "migu://5500469371", "category": "weishi", "logo": ""},
    {"name": "福建东南卫视", "url": "migu://5500469373", "category": "weishi", "logo": ""},
    {"name": "重庆卫视", "url": "migu://5500469381", "category": "weishi", "logo": ""},
    {"name": "吉林卫视", "url": "migu://5500469387", "category": "weishi", "logo": ""},
    {"name": "云南卫视", "url": "migu://5500469389", "category": "weishi", "logo": ""},
    {"name": "贵州卫视", "url": "migu://5500469391", "category": "weishi", "logo": ""},
    {"name": "广西卫视", "url": "migu://5500469393", "category": "weishi", "logo": ""},
    {"name": "山西卫视", "url": "migu://5500469395", "category": "weishi", "logo": ""},
    {"name": "新疆卫视", "url": "migu://5500469397", "category": "weishi", "logo": ""},
    {"name": "内蒙古卫视", "url": "migu://5500469399", "category": "weishi", "logo": ""},
    {"name": "甘肃卫视", "url": "migu://5500469401", "category": "weishi", "logo": ""},
    {"name": "海南卫视", "url": "migu://5500469403", "category": "weishi", "logo": ""},
    {"name": "宁夏卫视", "url": "migu://5500469405", "category": "weishi", "logo": ""},
    {"name": "青海卫视", "url": "migu://5500469407", "category": "weishi", "logo": ""},
    {"name": "西藏卫视", "url": "migu://5500469409", "category": "weishi", "logo": ""},
]

# ========== 黑名单关键词 ==========
BLACKLIST_KEYWORDS = [
    "radio", "广播", "电台",  # 广播电台
    "test", "测试",  # 测试频道
    "广告", "购物", "欢乐购", "好物推荐", "跟我学养生", "颐养有道", "热门推荐",  # 购物/广告
    "买卖", "商城", "销售", "推销", "电商",
    "4K测试", "8K测试",
]

# ========== 分类规则 ==========
CATEGORY_RULES = {
    "yangshi": [
        "cctv", "央视", "中央", "CGTN",
        "cctv-", "cctv+", "风云足球", "风云剧场", "第一剧场", "怀旧剧场", "国防军事",
        "世界地理", "女性时尚", "高尔夫·网球", "兵器科技", "文化精品",
        "健康之路", "社会与法", "新闻频道", "财经频道", "综艺频道", "电视剧频道",
        "电影频道", "少儿频道", "体育频道", "纪录频道", "科教频道", "戏曲频道",
        "音乐频道",
        "CHC家庭影院", "CHC电影", "CHC动作电影",
        "央视台球", "央视风云",
    ],
    "weishi": [
        "卫视",
        "北京卫视", "上海卫视", "东方卫视", "湖南卫视", "浙江卫视", "江苏卫视", "广东卫视", "深圳卫视",
        "安徽卫视", "山东卫视", "江西卫视", "福建卫视", "东南卫视", "四川卫视", "重庆卫视", "天津卫视",
        "湖北卫视", "河南卫视", "河北卫视", "陕西卫视", "辽宁卫视", "黑龙江卫视", "吉林卫视",
        "广西卫视", "云南卫视", "贵州卫视", "山西卫视", "新疆卫视", "西藏卫视", "宁夏卫视", "青海卫视",
        "甘肃卫视", "内蒙古卫视", "海南卫视", "厦门卫视", "兵团卫视",
        "山东教育卫视", "中国教育", "CETV",
        "金鹰卡通", "卡酷少儿", "炫动卡通", "优漫卡通", "嘉佳卡通",
        # 英文名称匹配
        "hunan tv", "zhejiang tv", "jiangsu tv", "guangdong tv", "shenzhen tv",
        "beijing tv", "shanghai tv", "dragon tv", "dongfang tv", "anhui tv",
        "shandong tv", "jiangxi tv", "fujian tv", "southeast tv", "sichuan tv",
        "chongqing tv", "tianjin tv", "hubei tv", "henan tv", "hebei tv",
        "shaanxi tv", "liaoning tv", "heilongjiang tv", "jilin tv", "guangxi tv",
        "yunnan tv", "guizhou tv", "shanxi tv", "xinjiang tv", "tibet tv",
        "ningxia tv", "qinghai tv", "gansu tv", "inner mongolia tv", "hainan tv",
        "xiamen tv", "btv", "brtv",
        "大湾区卫视", "农林卫视", "延边卫视", "安多卫视", "康巴卫视",
        "人间卫视",
    ],
    "difang": [
        "电视台", "新闻综合", "都市频道", "影视频道", "娱乐频道", "生活频道", "教育频道",
        "新闻频道", "综合频道", "公共频道", "经济频道", "法治频道", "科技频道",
        "comprehensive news", "news channel", "tv station",
        "广州", "深圳", "杭州", "南京", "武汉", "成都", "西安", "沈阳", "大连",
        "青岛", "济南", "哈尔滨", "长春", "石家庄", "太原", "郑州", "合肥",
        "南昌", "福州", "厦门", "长沙", "南宁", "桂林", "昆明", "贵阳",
        "兰州", "西宁", "银川", "乌鲁木齐", "呼和浩特", "拉萨", "海口", "三亚",
        "苏州", "无锡", "常州", "宁波", "温州", "绍兴", "嘉兴", "金华", "台州",
        "东莞", "佛山", "珠海", "中山", "惠州", "汕头", "江门", "湛江", "茂名",
        "桂林", "柳州", "北海", "梧州",
    ],
    "gangtai": [
        "香港", "澳门", "台湾", "tvb", "凤凰", "atv", "now tv", "星空", "卫视中文",
        "hong kong", "macau", "taiwan", "phoenix", "star tv",
    ],
    "guowai": [
        "cnn", "bbc", "fox", "nhk", "kbs", "sbs", "hbo", "disney", "国家地理", "探索",
        "national geographic", "discovery",
    ],
}

CATEGORY_NAMES = {
    "yangshi": "央视频道",
    "weishi": "卫视频道",
    "difang": "地方频道",
    "gangtai": "港台频道",
    "guowai": "国外频道",
}

# ========== 画质优先级 ==========
QUALITY_ORDER = {
    "8K": 80, "4K": 70, "FHD": 60, "1080": 60, "BD": 50,
    "HD": 40, "720": 40, "SD": 20, "576": 20, "UNKNOWN": 30,
}

# ========== 地方频道省份分类规则 ==========
PROVINCE_KEYWORDS = {
    "广东": ["广东", "广州", "深圳", "东莞", "佛山", "珠海", "中山", "惠州", "汕头", "江门", "湛江", "茂名", "肇庆", "揭阳"],
    "北京": ["北京"],
    "上海": ["上海"],
    "天津": ["天津"],
    "重庆": ["重庆"],
    "江苏": ["江苏", "南京", "苏州", "无锡", "常州", "南通", "扬州", "徐州", "镇江", "淮安"],
    "浙江": ["浙江", "杭州", "宁波", "温州", "绍兴", "嘉兴", "台州", "金华", "湖州", "丽水"],
    "山东": ["山东", "济南", "青岛", "烟台", "潍坊", "淄博", "济宁", "临沂", "泰安"],
    "四川": ["四川", "成都", "绵阳", "德阳", "泸州", "宜宾", "南充"],
    "湖北": ["湖北", "武汉", "宜昌", "襄阳", "荆州", "黄石", "十堰"],
    "湖南": ["湖南", "长沙", "株洲", "湘潭", "衡阳", "常德", "岳阳"],
    "河南": ["河南", "郑州", "洛阳", "开封", "安阳", "新乡", "许昌"],
    "河北": ["河北", "石家庄", "唐山", "秦皇岛", "邯郸", "保定"],
    "安徽": ["安徽", "合肥", "芜湖", "蚌埠", "淮南", "马鞍山", "安庆"],
    "福建": ["福建", "福州", "厦门", "泉州", "漳州", "莆田", "龙岩"],
    "江西": ["江西", "南昌", "九江", "赣州", "上饶", "景德镇"],
    "陕西": ["陕西", "西安", "宝鸡", "咸阳", "渭南"],
    "辽宁": ["辽宁", "沈阳", "大连", "鞍山", "抚顺", "锦州"],
    "黑龙江": ["黑龙江", "哈尔滨", "齐齐哈尔", "牡丹江", "佳木斯"],
    "吉林": ["吉林", "长春", "吉林", "四平", "通化"],
    "云南": ["云南", "昆明", "曲靖", "玉溪", "大理"],
    "贵州": ["贵州", "贵阳", "遵义", "六盘水"],
    "广西": ["广西", "南宁", "柳州", "桂林", "梧州", "北海"],
    "山西": ["山西", "太原", "大同", "阳泉", "长治"],
    "新疆": ["新疆", "乌鲁木齐", "喀什", "伊犁"],
    "内蒙古": ["内蒙古", "呼和浩特", "包头", "鄂尔多斯"],
    "甘肃": ["甘肃", "兰州", "天水", "酒泉"],
    "海南": ["海南", "海口", "三亚"],
    "宁夏": ["宁夏", "银川", "石嘴山"],
    "青海": ["青海", "西宁"],
    "西藏": ["西藏", "拉萨"],
}

# 默认当前省份（用于排序）
DEFAULT_PROVINCE = "广东"

# ========== 超时设置 ==========
CONNECT_TIMEOUT = 10
READ_TIMEOUT = 10
TEST_PARALLEL = 15


def parse_m3u(content):
    """解析 m3u 内容，返回频道列表"""
    channels = []
    lines = content.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            channel = {"name": "", "logo": "", "group": "", "url": "", "quality": ""}
            match = re.search(r'tvg-logo="([^"]*)"', line)
            if match:
                channel["logo"] = match.group(1)
            match = re.search(r'group-title="([^"]*)"', line)
            if match:
                channel["group"] = match.group(1)
            comma_match = re.search(r',(.+)$', line)
            if comma_match:
                channel["name"] = comma_match.group(1).strip()
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith("#"):
                    channel["url"] = url
                    channels.append(channel)
            i += 2
        else:
            i += 1
    return channels


def test_channel(channel):
    """测试单个频道是否可用"""
    url = channel["url"]
    try:
        parsed = urlparse(url)
        if not parsed.hostname:
            return False
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Connection": "close",
        }
        # 先尝试HEAD请求
        try:
            resp = requests.head(url, headers=headers, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), allow_redirects=True)
            if 200 <= resp.status_code < 400:
                # 检查content-type
                ct = resp.headers.get("content-type", "").lower()
                if ct and ("html" in ct or "text" in ct) and "mpegurl" not in ct:
                    return False
                return True
        except:
            pass
        # 再尝试GET请求，读取内容验证是m3u8
        try:
            resp = requests.get(url, headers=headers, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), stream=True)
            if 200 <= resp.status_code < 400:
                # 读取前几KB内容验证
                try:
                    content = b""
                    for chunk in resp.iter_content(chunk_size=2048):
                        content += chunk
                        if len(content) >= 4096:
                            break
                    text = content.decode("utf-8", errors="ignore").lower()
                    # 验证是否是m3u8或ts流
                    if "#extm3u" in text or "#ext-x" in text:
                        return True
                    # 如果是重定向到m3u8的html，跳过
                    if "<html" in text or "<head" in text:
                        return False
                    # 二进制内容可能是ts流，也算通过
                    return True
                except:
                    return True
        except:
            pass
        return False
    except:
        return False


def detect_quality(name):
    """从频道名判断画质"""
    name_lower = name.lower()
    if "8k" in name_lower:
        return "8K"
    if "4k" in name_lower:
        return "4K"
    if "1080" in name_lower or "fhd" in name_lower:
        return "FHD"
    if "720" in name_lower or "hd" in name_lower:
        return "HD"
    if "576" in name_lower or "sd" in name_lower:
        return "SD"
    return "UNKNOWN"


def classify_channel(name):
    """根据频道名分类（按优先级：央视 > 卫视 > 港台 > 国外 > 地方）"""
    name_lower = name.lower()
    
    priority_order = ["yangshi", "weishi", "gangtai", "guowai", "difang"]
    for category in priority_order:
        keywords = CATEGORY_RULES.get(category, [])
        for kw in keywords:
            if kw.lower() in name_lower:
                return category
    return "other"


def detect_province(name):
    """从频道名判断所属省份"""
    name_lower = name.lower()
    for province, keywords in PROVINCE_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return province
    return "其他"


def is_blacklisted(name):
    """检查是否在黑名单中"""
    name_lower = name.lower()
    return any(kw.lower() in name_lower for kw in BLACKLIST_KEYWORDS)


def write_m3u(channels, filepath, group_title):
    """写入 m3u 文件"""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            name = ch["name"]
            logo = ch.get("logo", "")
            url = ch["url"]
            # 每个频道使用自己的分类作为group-title
            cat = ch.get("_category", group_title)
            cat_name = CATEGORY_NAMES.get(cat, group_title)
            line = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{cat_name}",{name}\n'
            f.write(line)
            f.write(url + "\n")
    print(f"  写入 {len(channels)} 个频道 → {os.path.basename(filepath)}")


def write_direct_sources(channels, filepath):
    """写入 direct_sources.m3u（seetv app专用，使用正确的分组名）"""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        f.write(f"# 直播源 - SeeTV\n")
        f.write(f"# 更新时间: {time.strftime('%Y-%m-%d %H:%M')}\n")
        f.write(f"# 分类: 央视频道, 卫视频道, 地方频道(按省), 港台频道\n\n")
        
        # 按分类分组写入
        for cat_key, cat_name in CATEGORY_NAMES.items():
            cat_channels = [ch for ch in channels if ch.get("_category") == cat_key]
            if not cat_channels:
                continue
            
            # 地方频道特殊处理：按省份分组
            if cat_key == "difang":
                # 按省份分组
                province_groups = {}
                for ch in cat_channels:
                    province = detect_province(ch["name"])
                    if province not in province_groups:
                        province_groups[province] = []
                    province_groups[province].append(ch)
                
                # 排序：当前省份优先，其他按字母排序
                province_order = sorted(province_groups.keys(), key=lambda p: (0 if p == DEFAULT_PROVINCE else 1, p))
                
                for province in province_order:
                    prov_channels = province_groups[province]
                    f.write(f"\n# ============ 地方频道 - {province} ============\n")
                    for ch in prov_channels:
                        name = ch["name"]
                        logo = ch.get("logo", "")
                        url = ch["url"]
                        line = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="地方频道-{province}",{name}\n'
                        f.write(line)
                        f.write(url + "\n")
            else:
                # 其他分类正常写入
                f.write(f"\n# ============ {cat_name} ============\n")
                for ch in cat_channels:
                    name = ch["name"]
                    logo = ch.get("logo", "")
                    url = ch["url"]
                    line = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{cat_name}",{name}\n'
                    f.write(line)
                    f.write(url + "\n")
        
        # 其他频道
        other_channels = [ch for ch in channels if ch.get("_category") not in CATEGORY_NAMES]
        if other_channels:
            f.write(f"\n# ============ 其他频道 ============\n")
            for ch in other_channels:
                name = ch["name"]
                logo = ch.get("logo", "")
                url = ch["url"]
                line = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="其他",{name}\n'
                f.write(line)
                f.write(url + "\n")
    
    print(f"  写入 {len(channels)} 个频道 → {os.path.basename(filepath)}")


def github_get_file_sha(path):
    """获取GitHub文件的SHA"""
    url = f"{GITHUB_API}/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{path}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, dict):
            return data.get("sha")
    return None


def github_upload_file(local_path, github_path, message):
    """上传文件到GitHub"""
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")
    
    url = f"{GITHUB_API}/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{github_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    sha = github_get_file_sha(github_path)
    data = {"message": message, "content": content}
    if sha:
        data["sha"] = sha
    
    resp = requests.put(url, headers=headers, data=json.dumps(data), timeout=30)
    if resp.status_code in (200, 201):
        return True
    else:
        print(f"    GitHub上传失败: {resp.status_code} {resp.text[:200]}")
        return False


def main():
    print("=" * 60)
    print("  直播源自动收集 & 更新工具")
    print("=" * 60)
    start_time = time.time()

    # 1. 下载所有上游源
    print("\n[1/6] 下载上游源...")
    all_channels = []
    for idx, source_url in enumerate(UPSTREAM_SOURCES, 1):
        print(f"  [{idx}/{len(UPSTREAM_SOURCES)}] {source_url[:60]}...")
        try:
            resp = requests.get(source_url, timeout=30)
            if resp.status_code == 200:
                channels = parse_m3u(resp.text)
                print(f"    ✓ 解析到 {len(channels)} 个频道")
                all_channels.extend(channels)
            else:
                print(f"    ✗ 下载失败: {resp.status_code}")
        except Exception as e:
            print(f"    ✗ 异常: {e}")

    # 添加自定义频道源（标记为自定义，跳过测试）
    custom_channel_list = []
    if CUSTOM_CHANNELS:
        print(f"\n  添加 {len(CUSTOM_CHANNELS)} 个自定义频道...")
        for ch in CUSTOM_CHANNELS:
            custom_ch = {
                "name": ch["name"],
                "url": ch["url"],
                "logo": ch.get("logo", ""),
                "group": CATEGORY_NAMES.get(ch.get("category", ""), ""),
                "quality": detect_quality(ch["name"]),
                "_category": ch.get("category", "other"),
                "_custom": True  # 标记为自定义频道
            }
            all_channels.append(custom_ch)
            custom_channel_list.append(custom_ch)  # 同时保存一份用于强制添加

    print(f"\n  总计收集: {len(all_channels)} 个频道")

    # 2. 过滤黑名单（自定义频道跳过）
    print("\n[2/6] 过滤购物台/广告台/广播台...")
    before = len(all_channels)
    all_channels = [ch for ch in all_channels if ch.get("_custom") or not is_blacklisted(ch["name"])]
    print(f"  过滤掉 {before - len(all_channels)} 个，剩余 {len(all_channels)} 个")

    # 3. URL去重（自定义频道优先保留）
    print("\n[3/6] URL去重...")
    seen_urls = set()
    unique_channels = []
    custom_channels = [ch for ch in all_channels if ch.get("_custom")]
    for ch in custom_channels:
        url = ch["url"]
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_channels.append(ch)
    normal_channels = [ch for ch in all_channels if not ch.get("_custom")]
    for ch in normal_channels:
        url = ch["url"]
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_channels.append(ch)
    print(f"  去重后: {len(unique_channels)} 个")

    # 4. 智能去重（同名保留画质最好的，自定义频道优先）
    print("\n[4/6] 智能去重（同名保留高画质）...")
    name_to_channel = {}
    for ch in unique_channels:
        q = detect_quality(ch["name"])
        ch["quality"] = q
        base_name = re.sub(r'\[.*?\]', '', ch["name"]).strip().lower()
        base_name = re.sub(r'\(.*?\)', '', base_name).strip()
        
        if base_name not in name_to_channel:
            name_to_channel[base_name] = ch
        else:
            if ch.get("_custom"):
                name_to_channel[base_name] = ch
            elif not name_to_channel[base_name].get("_custom"):
                old_q = name_to_channel[base_name].get("quality", "UNKNOWN")
                if QUALITY_ORDER.get(q, 0) > QUALITY_ORDER.get(old_q, 0):
                    name_to_channel[base_name] = ch
    deduped = list(name_to_channel.values())
    print(f"  去重后: {len(deduped)} 个")

    # 5. 分类 & 测试可用性
    print(f"\n[5/6] 分类 & 测试可用性 (并行 {TEST_PARALLEL})...")
    classified = {cat: [] for cat in CATEGORY_RULES}
    classified["other"] = []
    
    for ch in deduped:
        if ch.get("_custom"):
            cat = ch.get("_category", "other")
        else:
            cat = classify_channel(ch["name"])
        ch["_category"] = cat
        classified[cat].append(ch)
    
    print("\n  分类统计:")
    for cat, channels in classified.items():
        cat_name = CATEGORY_NAMES.get(cat, cat)
        print(f"    {cat_name}: {len(channels)} 个")

    # 测试可用性
    print("\n  开始测试...")
    tested_by_category = {}
    total_tested = 0
    total_passed = 0
    
    for cat, channels in classified.items():
        if not channels:
            tested_by_category[cat] = []
            continue
        cat_name = CATEGORY_NAMES.get(cat, cat)
        print(f"\n  测试 {cat_name} ({len(channels)} 个)...")
        passed = []
        # 分离自定义频道（跳过测试，直接加入passed）
        custom_chs = [ch for ch in channels if ch.get("_custom")]
        normal_chs = [ch for ch in channels if not ch.get("_custom")]
        
        if custom_chs:
            print(f"    自定义频道: {len(custom_chs)} 个（跳过测试，强制添加）")
            passed.extend(custom_chs)
        
        with ThreadPoolExecutor(max_workers=TEST_PARALLEL) as executor:
            futures = {executor.submit(test_channel, ch): ch for ch in normal_chs}
            for fut in as_completed(futures):
                ch = futures[fut]
                total_tested += 1
                if fut.result():
                    passed.append(ch)
                    total_passed += 1
        print(f"    通过: {len(passed)}/{len(channels)}")
        tested_by_category[cat] = passed

    # 6. 输出 & 上传
    print("\n[6/6] 生成文件 & 上传到GitHub...")
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    all_tested = []
    for cat, channels in tested_by_category.items():
        if cat in CATEGORY_NAMES and channels:
            filepath = os.path.join(output_dir, f"{cat}.m3u")
            write_m3u(channels, filepath, CATEGORY_NAMES[cat])
            all_tested.extend(channels)
    
    # 全部频道（带正确分组）
    all_file = os.path.join(output_dir, "all.m3u")
    write_m3u(all_tested, all_file, "全部频道")

    # direct_sources.m3u（seetv app专用格式，带正确分组）
    direct_file = os.path.join(output_dir, "direct_sources.m3u")
    write_direct_sources(all_tested, direct_file)

    # 上传到GitHub
    print(f"\n  上传到 GitHub: {GITHUB_USER}/{GITHUB_REPO}")
    files_to_upload = []
    for cat in CATEGORY_NAMES:
        local_path = os.path.join(output_dir, f"{cat}.m3u")
        if os.path.exists(local_path):
            files_to_upload.append((local_path, f"{cat}.m3u"))
    files_to_upload.append((all_file, "all.m3u"))
    files_to_upload.append((direct_file, "direct_sources.m3u"))

    success_count = 0
    for local_path, github_path in files_to_upload:
        size_kb = os.path.getsize(local_path) / 1024
        print(f"  上传 {github_path} ({size_kb:.1f} KB)...", end=" ")
        if github_upload_file(local_path, github_path, f"自动更新 {github_path} - {time.strftime('%Y-%m-%d %H:%M')}"):
            print("✓")
            success_count += 1
        else:
            print("✗")

    elapsed = time.time() - start_time
    print("\n" + "=" * 60)
    print(f"  完成! 用时 {elapsed:.1f} 秒")
    print(f"  总测试: {total_tested} 个, 通过: {total_passed} 个")
    print(f"  上传成功: {success_count}/{len(files_to_upload)} 个文件")
    print(f"  仓库: https://github.com/{GITHUB_USER}/{GITHUB_REPO}")
    print(f"  直链: https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/main/direct_sources.m3u")
    print("=" * 60)

    # 同步更新app内置源
    app_source = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "app", "src", "main", "assets", "direct_sources.m3u")
    if os.path.exists(os.path.dirname(app_source)):
        import shutil
        shutil.copy2(direct_file, app_source)
        print(f"  已同步更新app内置源: {app_source}")


if __name__ == "__main__":
    main()
