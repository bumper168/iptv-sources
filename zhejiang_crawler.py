#!/usr/bin/env python3
"""
浙江卫视直播源抓取脚本
- 使用Playwright从浙江卫视官网获取直播源
- 从浏览器网络请求中捕获带auth_key的m3u8地址
- 排除购物频道
"""

import asyncio
import re
import json
from playwright.async_api import async_playwright
from datetime import datetime

# 浙江广电所有频道（排除购物频道）
# channelId从直播列表页面获取
CHANNELS = {
    101: "浙江卫视",
    102: "钱江都市",
    103: "经济生活",
    104: "教科影视",
    105: "民生休闲",
    106: "新闻",
    107: "少儿频道",
    108: "浙江国际",
    # 好易购 - 购物频道，不要
    110: "之江纪录",
}

def get_channel_urls(channel_id):
    """生成频道的m3u8 URL模板"""
    cid_str = str(channel_id).zfill(3)
    return [
        f"channel{cid_str}720Pnew",  # 720P
        f"channel{cid_str}1080Pnew", # 1080P
        f"channel{cid_str}knew",       # 音频
    ]

async def main():
    print("=" * 60)
    print("  浙江卫视直播源抓取")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    results = {}
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # 设置网络请求监听
        async def handle_response(response):
            url = response.url
            # 捕获带auth_key的m3u8地址
            if '.m3u8' in url and 'auth_key=' in url:
                for cid, name in CHANNELS.items():
                    patterns = get_channel_urls(cid)
                    for pattern in patterns:
                        if pattern in url:
                            if name not in results:
                                # 只保存720P或1080P，不保存音频
                                if '720P' in url or '1080P' in url:
                                    print(f"  ✅ 捕获到 {name}: {url[:90]}...")
                                    results[name] = url
                            break
        
        page.on("response", handle_response)
        
        # 逐个访问频道播放页面
        for cid, name in CHANNELS.items():
            print(f"\n📺 正在抓取: {name} (channelId={cid})")
            
            try:
                # 直接访问频道播放页面
                url = f"https://www.cztv.com/liveTV/{cid}.html"
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await asyncio.sleep(2)
            except Exception as e:
                print(f"  ⚠️ 页面加载超时: {e}")
        
        await browser.close()
    
    print("\n" + "=" * 60)
    print(f"  抓取完成: {len(results)}/{len(CHANNELS)} 个频道")
    print("=" * 60)
    
    if results:
        # 生成M3U文件
        m3u_content = "#EXTM3U\n"
        for name, url in results.items():
            m3u_content += f'#EXTINF:-1 tvg-name="{name}" tvg-logo="" group-title="卫视频道",{name}\n'
            m3u_content += f"{url}\n"
        
        with open("zhejiang.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        
        print(f"\n✅ 已保存到 zhejiang.m3u")
        print("\n频道列表:")
        for name, url in results.items():
            print(f"  {name}")
    else:
        print("\n❌ 未捕获到任何直播源，可能需要调整URL格式")
    
    return len(results)

if __name__ == "__main__":
    count = asyncio.run(main())
    exit(0 if count > 0 else 1)
