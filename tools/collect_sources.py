#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
M3U 直播源收集器
从多个上游源收集、去重、分类、测试
"""
import requests
import re
import os
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse

# ========== 上游源列表 ==========
# 这些是公开可用的上游源，可按需增删
UPSTREAM_SOURCES = [
    # iptv-org 开源项目（国内可访问）
    "https://iptv-org.github.io/iptv/countries/cn.m3u",
    # 可选：添加更多上游源
    # "https://raw.githubusercontent.com/iptv-org/iptv/master/streams/cn.m3u8",
    # "https://另一个源地址/xxx.m3u",
]

# ========== 额外的上游源（用于分类和补充 ==========
# 可以在下面添加特定分类的源，这些会被直接归到指定分类
# 格式: (分类名, 源地址)
CATEGORY_SOURCES = [
    # ("yangshi", "https://xxx/cctv.m3u"),
    # ("weishi", "https://xxx/weishi.m3u"),
]

# ========== 频道名黑名单（不要的关键字 ==========
BLACKLIST_KEYWORDS = [
    "radio", "广播", "电台",  # 广播电台
    "test", "测试",  # 测试频道
    "广告",  # 广告频道
]

# ========== 画质优先级 ==========
# 从高到低排序，同名频道保留画质更好的
QUALITY_ORDER = {
    "8K": 80,
    "4K": 70,
    "FHD": 60,
    "BD": 50,
    "HD": 40,
    "SD": 20,
    "VGA": 10,
    "UNKNOWN": 30,
}

# ========== 分类规则 ==========
CATEGORY_RULES = {
    "yangshi": [
        "cctv", "央视", "中央",
    ],
    "weishi": [
        "卫视", "北京", "上海", "东方", "湖南", "浙江", "江苏", "广东", "深圳",
        "安徽", "山东", "江西", "福建", "东南", "四川", "重庆", "天津",
        "湖北", "河南", "河北", "陕西", "辽宁", "黑龙江", "吉林",
        "广西", "云南", "贵州", "山西", "新疆", "西藏", "宁夏", "青海", "甘肃", "内蒙古",
    ],
    "difang": [
        "电视台", "新闻", "都市", "影视", "娱乐", "生活", "教育",
    ],
    "gangtai": [
        "香港", "澳门", "台湾", "tvb", "凤凰", "atv", "now",
    ],
    "guowai": [
        "cnn", "bbc", "fox", "nhk", "kbs", "sbs",
    ],
}

# ========== 高清判断 ==========
HD_KEYWORDS = ["hd", "fhd", "4k", "8k", "超清", "蓝光", "1080", "720"]
SD_KEYWORDS = ["sd", "vga", "标清"]

# ========== 超时设置 ==========
CONNECT_TIMEOUT = 3  # 秒
READ_TIMEOUT = 3
TEST_PARALLEL = 10  # 并行测试数


def parse_m3u(content):
    """解析 m3u 内容，返回频道列表"""
    channels = []
    lines = content.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("#EXTINF"):
            channel = {
                "name": "",
                "logo": "",
                "group": "",
                "url": "",
                "quality": "",
            }
            # 提取属性
            match = re.search(r'tvg-logo="([^"]*)"', line)
            if match:
                channel["logo"] = match.group(1)
            match = re.search(r'group-title="([^"]*)"', line)
            if match:
                channel["group"] = match.group(1)
            # 提取频道名（逗号后面的部分）
            comma_match = re.search(r',(.+)$', line)
            if comma_match:
                channel["name"] = comma_match.group(1).strip()
            # 下一行应该是URL
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
        hostname = parsed.hostname
        if not hostname:
            return False
        # 快速测试：发送 HEAD 请求
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Connection": "close",
        }
        resp = requests.head(url, headers=headers, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), allow_redirects=True)
        # 如果HEAD请求返回2xx或3xx
        if 200 <= resp.status_code < 400:
            return True
        # HEAD 失败，试 GET（只读取一点点
        try:
            resp = requests.get(url, headers=headers, timeout=(CONNECT_TIMEOUT, READ_TIMEOUT), stream=True)
            if 200 <= resp.status_code < 400:
                return True
        except:
            pass
        return False
    except:
        return False


def detect_quality(name):
    """从频道名判断画质"""
    name_lower = name.lower()
    for kw in HD_KEYWORDS:
        if kw in name_lower:
            return "HD"
    for kw in SD_KEYWORDS:
        if kw in name_lower:
            return "SD"
    return "UNKNOWN"


def classify_channel(name):
    """根据频道名分类"""
    name_lower = name.lower()
    for category, keywords in CATEGORY_RULES.items():
        for kw in keywords:
            if kw.lower() in name_lower:
                return category
    return "other"


def is_chinese_channel(channel):
    """判断是否中文频道"""
    name = channel["name"].lower()
    # 检查是否为中文或含央视/卫视等关键词
    chinese_indicators = ["cctv", "央视", "卫视", "电视台", "凤凰", "tvb", "香港", "台湾", "澳门", "中国", "chinese"]
    return any(ind in name for ind in chinese_indicators)


def write_m3u(channels, filepath, category_name):
    """写入 m3u 文件"""
    os.makedirs(os.path.dirname(filepath) if os.path.dirname(filepath) else ".", exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for ch in channels:
            name = ch["name"]
            logo = ch["logo"]
            group = category_name
            url = ch["url"]
            line = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="{logo}" group-title="{group}",{name}\n'
            f.write(line)
            f.write(url + "\n")
    print(f"  写入 {len(channels)} 个频道 → {filepath}")


def main():
    print("=" * 60)
    print("开始收集直播源...")
    print("=" * 60)
    start_time = time.time()

    # 1. 下载所有上游源
    all_channels = []
    # 通用上游源
    for source_url in UPSTREAM_SOURCES:
        print(f"\n下载: {source_url}")
        try:
            resp = requests.get(source_url, timeout=30)
            if resp.status_code == 200:
                channels = parse_m3u(resp.text)
                print(f"  解析到 {len(channels)} 个频道")
                all_channels.extend(channels)
            else:
                print(f"  下载失败: {resp.status_code}")
        except Exception as e:
            print(f"  下载异常: {e}")

    # 分类特定源
    for cat, source_url in CATEGORY_SOURCES:
        print(f"\n下载 {cat} 源: {source_url}")
        try:
            resp = requests.get(source_url, timeout=30)
            if resp.status_code == 200:
                channels = parse_m3u(resp.text)
                # 强制分类
                for ch in channels:
                    ch["_force_category"] = cat
                print(f"  解析到 {len(channels)} 个频道")
                all_channels.extend(channels)
        except Exception as e:
            print(f"  下载异常: {e}")

    print(f"\n总共收集 {len(all_channels)} 个频道")

    # 2. 过滤黑名单
    before = len(all_channels)
    all_channels = [ch for ch in all_channels
                    if not any(kw.lower() in ch["name"].lower() for kw in BLACKLIST_KEYWORDS)]
    print(f"过滤黑名单: {before - len(all_channels)} 个被移除，剩余 {len(all_channels)}")

    # 3. 去重（按 URL 精确去重）
    seen_urls = set()
    unique_channels = []
    for ch in all_channels:
        url = ch["url"]
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_channels.append(ch)
    print(f"URL去重后: {len(unique_channels)} 个")

    # 4. 按频道名 + 画质 智能去重
    # 同名频道保留画质更好的
    name_to_channel = {}
    for ch in unique_channels:
        q = detect_quality(ch["name"])
        ch["quality"] = q
        base_name = ch["name"].lower()
        # 去除画质标记后的基础名
        base_name_clean = re.sub(r'\[.*?\]', '', base_name).strip()
        if base_name_clean not in name_to_channel:
            name_to_channel[base_name_clean] = ch
        else:
            old_q = name_to_channel[base_name_clean].get("quality", "UNKNOWN")
            if QUALITY_ORDER.get(q, 0) > QUALITY_ORDER.get(old_q, 0):
                name_to_channel[base_name_clean] = ch

    deduped = list(name_to_channel.values())
    print(f"智能去重后: {len(deduped)} 个")

    # 5. 分类
    classified = {
        "yangshi": [],
        "weishi": [],
        "difang": [],
        "gangtai": [],
        "guowai": [],
        "other": [],
    }
    for ch in deduped:
        if "_force_category" in ch:
            cat = ch["_force_category"]
        else:
            cat = classify_channel(ch["name"])
        classified[cat].append(ch)

    print("\n分类统计:")
    for cat, channels in classified.items():
        print(f"  {cat}: {len(channels)} 个")

    # 6. 测试可用性（并行测试）
    print(f"\n开始测试频道可用性 (并行 {TEST_PARALLEL})...")
    tested_channels = []

    for cat, channels in classified.items():
        if not channels:
            continue
        print(f"\n测试 {cat} ({len(channels)})...")
        passed = []
        with ThreadPoolExecutor(max_workers=TEST_PARALLEL) as executor:
            futures = {executor.submit(test_channel, ch): ch for ch in channels}
            for fut in as_completed(futures):
                ch = futures[fut]
                if fut.result():
                    passed.append(ch)
        print(f"  通过: {len(passed)}/{len(channels)}")
        tested_channels.extend([(cat, ch) for ch in passed])

    # 7. 按分类组织
    final_by_category = {cat: [] for cat in classified}
    for cat, ch in tested_channels:
        final_by_category[cat].append(ch)

    # 8. 输出
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n写入 m3u 到 {output_dir}/")

    category_names = {
        "yangshi": "央视频道",
        "weishi": "卫视频道",
        "difang": "地方频道",
        "gangtai": "港台频道",
        "guowai": "国外频道",
    }
    for cat, name in category_names.items():
        if final_by_category[cat]:
            filepath = os.path.join(output_dir, f"{cat}.m3u")
            write_m3u(final_by_category[cat], filepath, name)

    all_tested = [ch for cat, ch in tested_channels]
    write_m3u(all_tested, os.path.join(output_dir, "all.m3u"), "全部频道")

    elapsed = time.time() - start_time
    print(f"\n完成! 用时 {elapsed:.1f} 秒")
    print(f"总计 {len(all_tested)} 个可用频道")


if __name__ == "__main__":
    main()
