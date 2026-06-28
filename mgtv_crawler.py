#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
芒果TV直播源抓取器
使用Playwright模拟浏览器访问芒果TV直播页，从网络请求中提取m3u8直播源
"""
import asyncio
import re
import os
import sys
from urllib.parse import unquote

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("请先安装playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

# 目标频道列表（名称: 选择器文本）
# 根据芒果TV直播页面的频道列表配置
TARGET_CHANNELS = [
    ("湖南经视", "湖南经视"),
    ("湖南娱乐", "湖南娱乐"),
    ("湖南都市", "湖南都市"),
    ("金鹰纪实", "金鹰纪实"),
    ("金鹰卡通", "金鹰卡通"),
    ("湖南电影", "湖南电影"),
    ("湖南电视剧", "湖南电视剧"),
    ("湖南爱晚", "湖南爱晚"),
]

# 直播页面URL
LIVE_URL = "http://www.mgtv.com/live/?_source_=C"


async def crawl_mgtv_sources():
    """抓取芒果TV直播源"""
    channels = {}  # name -> url
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        
        # 监听网络请求，捕获m3u8地址
        captured_m3u8 = []
        
        async def handle_response(response):
            url = response.url
            # 只捕获真正的m3u8播放地址（包含qing.mgtv.com和nn_live）
            if ".m3u8" in url and "qing.mgtv.com" in url and "nn_live" in url:
                # 过滤掉p2p和.ts请求
                if ".p2p?" not in url and ".ts?" not in url:
                    if url not in captured_m3u8:
                        captured_m3u8.append(url)
                        print(f"  捕获到m3u8: {url[:80]}...")
        
        page.on("response", handle_response)
        
        print(f"访问直播页面: {LIVE_URL}")
        await page.goto(LIVE_URL, wait_until="networkidle", timeout=30000)
        
        # 等待页面加载
        await asyncio.sleep(3)
        
        # 获取所有频道链接（class=channel的a标签）
        channel_links = await page.query_selector_all("a.channel")
        
        print(f"\n找到 {len(channel_links)} 个频道")
        
        # 打印所有频道名
        print("\n=== 频道列表 ===")
        for idx, link in enumerate(channel_links):
            try:
                text = await link.inner_text()
                print(f"  [{idx}] {text.strip()}")
            except:
                pass
        print("================\n")
        
        for channel_name, keyword in TARGET_CHANNELS:
            if channel_name in channels:
                continue
                
            print(f"\n尝试切换到: {channel_name}")
            
            # 查找包含频道名的链接
            found = False
            for link in channel_links:
                try:
                    text = await link.inner_text()
                    text = text.strip()
                    if keyword == text or keyword in text:
                        # 点击切换频道
                        captured_before = len(captured_m3u8)
                        await link.click()
                        # 等待新的m3u8请求
                        await asyncio.sleep(5)
                        
                        # 检查是否捕获到新的m3u8
                        if len(captured_m3u8) > captured_before:
                            # 取最新的m3u8
                            new_urls = captured_m3u8[captured_before:]
                            best_url = None
                            # 优先选清晰度高的
                            for u in new_urls:
                                if "m3u8" in u:
                                    best_url = u
                                    break
                            
                            if best_url:
                                channels[channel_name] = best_url
                                print(f"  ✅ {channel_name}: {best_url[:70]}...")
                                found = True
                                break
                        else:
                            print(f"  ⚠️ 未捕获到新的m3u8请求")
                except Exception as e:
                    continue
            
            if not found:
                print(f"  ❌ 未找到频道: {channel_name}")
        
        await browser.close()
    
    return channels


def write_m3u(channels, output_path, group_name="芒果TV"):
    """写入M3U文件"""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for name, url in channels.items():
            line = f'#EXTINF:-1 tvg-name="{name}" tvg-logo="" group-title="{group_name}",{name}\n'
            f.write(line)
            f.write(url + "\n")
    print(f"\n写入 {len(channels)} 个频道 → {output_path}")


def update_direct_sources(mgtv_channels, direct_sources_path):
    """更新direct_sources.m3u中的芒果TV频道"""
    if not os.path.exists(direct_sources_path):
        print(f"direct_sources.m3u 不存在，跳过更新")
        return
    
    with open(direct_sources_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    lines = content.split("\n")
    new_lines = []
    i = 0
    updated_count = 0
    
    while i < len(lines):
        line = lines[i]
        if line.startswith("#EXTINF"):
            # 提取频道名
            match = re.search(r',(.+)$', line)
            if match:
                channel_name = match.group(1).strip()
                # 检查是否是芒果TV频道
                if channel_name in mgtv_channels:
                    new_url = mgtv_channels[channel_name]
                    new_lines.append(line)
                    # 下一行是URL，替换掉
                    if i + 1 < len(lines):
                        old_url = lines[i + 1].strip()
                        if old_url != new_url:
                            print(f"  更新: {channel_name}")
                            updated_count += 1
                        new_lines.append(new_url)
                        i += 2
                        continue
        
        new_lines.append(line)
        i += 1
    
    with open(direct_sources_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))
    
    print(f"\n已更新 direct_sources.m3u 中的 {updated_count} 个芒果TV频道")


async def main():
    print("=" * 60)
    print("芒果TV直播源抓取器")
    print("=" * 60)
    
    # 抓取直播源
    channels = await crawl_mgtv_sources()
    
    print(f"\n{'=' * 60}")
    print(f"抓取完成，共获取 {len(channels)} 个频道")
    print("=" * 60)
    for name, url in channels.items():
        print(f"  {name}: {url[:60]}...")
    
    # 输出到output目录
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "mgtv.m3u")
    write_m3u(channels, output_path, "芒果TV")
    
    # 更新direct_sources.m3u
    direct_sources_path = "direct_sources.m3u"
    if os.path.exists(direct_sources_path):
        update_direct_sources(channels, direct_sources_path)


if __name__ == "__main__":
    asyncio.run(main())
