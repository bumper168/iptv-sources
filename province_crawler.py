#!/usr/bin/env python3
"""
省级卫视直播源抓取脚本 v2.0
支持：江苏卫视、东方卫视、北京卫视、广东卫视、安徽卫视、山东卫视、四川卫视、重庆卫视、深圳卫视等
使用Playwright浏览器自动化抓取带token验证的直播源
"""

import asyncio
import re
import json
import hashlib
import base64
import time
import urllib.parse
from datetime import datetime
from pathlib import Path
import sys

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("请先安装 playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

# 购物频道关键词黑名单
SHOPPING_KEYWORDS = [
    '购物', '好易购', '快乐购', '家有购物', '优购物', '购物频道',
    '东方购物', 'CCTV购物', '风尚购物', '家购', '电视购物',
    '优购物', '天天购物', '聚惠购物'
]

def is_shopping_channel(name):
    """判断是否为购物频道"""
    for keyword in SHOPPING_KEYWORDS:
        if keyword in name:
            return True
    return False


class JiangsuCrawler:
    """
    江苏卫视爬虫 - 荔枝网
    API分析:
    - 直播页面: http://live.jstv.com/
    - 频道列表API: http://api.jstv.com/v2/live/channel 或类似接口
    - m3u8格式: 通常包含auth_key参数进行验证
    """
    
    BASE_URL = "http://live.jstv.com/"
    
    # 频道ID映射 (根据荔枝网页面分析)
    CHANNELS = {
        "jsws": "江苏卫视",
        "jscs": "江苏城市",
        "jszy": "江苏综艺",
        "jsys": "江苏影视",  # 注意: 不是"江苏公共"
        "jsxw": "江苏新闻",
        "jsjy": "江苏教育",
        "jsxx": "体育休闲",
        "ymkt": "优漫卡通",  # 少儿频道
        "jsgj": "江苏国际",
        # "js4k": "江苏卫视4K",  # 4K超高清频道
    }
    
    async def crawl(self, page):
        """抓取江苏卫视直播源"""
        print("\n📺 [江苏卫视] 开始抓取...")
        results = {}
        captured_urls = {}
        
        # 网络请求监听
        async def handle_response(response):
            url = response.url
            if '.m3u8' in url and 'auth' in url.lower() or '.m3u8' in url:
                # 尝试匹配频道
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() or ch_name.replace("江苏", "js") in url.lower():
                        if ch_name not in captured_urls:
                            captured_urls[ch_name] = url
                            print(f"  🎯 捕获网络请求: {ch_name}")
                        break
                # 也保存未匹配的m3u8供后续分析
                if '.m3u8' in url and url not in captured_urls.values():
                    captured_urls[f"未知_{len(captured_urls)}"] = url
        
        page.on("response", handle_response)
        
        try:
            print(f"  访问: {self.BASE_URL}")
            await page.goto(self.BASE_URL, wait_until="networkidle", timeout=45000)
            await asyncio.sleep(5)  # 等待视频播放器加载
            
            # 获取页面内容
            content = await page.content()
            
            # 从页面源码提取m3u8地址和API配置
            # 荔枝网通常在JavaScript中嵌入播放配置
            m3u8_pattern = r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)'
            matches = re.findall(m3u8_pattern, content)
            
            for url in matches:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() and ch_name not in results:
                        results[ch_name] = url
                        print(f"  ✅ 页面提取: {ch_name}")
            
            # 尝试通过API获取
            # 荔枝网可能使用不同的API端点
            api_endpoints = [
                "http://api.jstv.com/v2/live/channel",
                "http://api.jstv.com/live/channel",
                "http://litchi.jstv.com/api/live/channel",
            ]
            
            for api_url in api_endpoints:
                try:
                    response = await page.evaluate(f'''
                        async () => {{
                            try {{
                                const r = await fetch("{api_url}", {{
                                    headers: {{
                                        'Accept': 'application/json',
                                        'Referer': 'http://live.jstv.com/'
                                    }}
                                });
                                return await r.text();
                            }} catch(e) {{
                                return null;
                            }}
                        }}
                    ''')
                    
                    if response:
                        data = json.loads(response)
                        if isinstance(data, dict) and 'data' in data:
                            channels = data.get('data', [])
                        elif isinstance(data, list):
                            channels = data
                        else:
                            channels = []
                            
                        for item in channels:
                            name = item.get('name', '') or item.get('channelName', '')
                            url = item.get('url', '') or item.get('m3u8', '') or item.get('playUrl', '')
                            if url and '.m3u8' in url and not is_shopping_channel(name):
                                if '江苏' in name or '优漫' in name:
                                    results[name] = url
                                    print(f"  ✅ API获取: {name}")
                except Exception as e:
                    pass
            
            # 合并网络捕获的结果
            for name, url in captured_urls.items():
                if name.startswith("未知"):
                    continue
                if name not in results:
                    results[name] = url
            
            # Token时效性分析
            if results:
                print("\n  📊 Token验证分析:")
                for name, url in results.items():
                    if 'auth' in url.lower() or 'token' in url.lower() or 'key' in url.lower():
                        # 解析token参数
                        parsed = urllib.parse.urlparse(url)
                        params = urllib.parse.parse_qs(parsed.query)
                        auth_params = {k: v for k, v in params.items() 
                                       if 'auth' in k.lower() or 'token' in k.lower() or 'key' in k.lower()}
                        if auth_params:
                            print(f"    {name}: Token参数 {list(auth_params.keys())}")
                            # 分析token格式 - 通常是时间戳+签名
                            for key, val in auth_params.items():
                                val_str = val[0] if isinstance(val, list) else val
                                if val_str.isdigit() or len(val_str) > 20:
                                    print(f"      {key}: 可能是动态Token (长度: {len(val_str)})")
                        else:
                            print(f"    {name}: 无明显Token参数")
                    else:
                        print(f"    {name}: 无Token验证")
                        
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
        
        print(f"  [江苏卫视] 完成: {len(results)} 个频道")
        return results


class ShanghaiCrawler:
    """
    东方卫视爬虫 - 看看新闻
    API分析:
    - 直播页面: https://live.kankanews.com/huikan/
    - SMG旗下频道: 东方卫视、上海都市、上海娱乐等
    - 可能使用SMGBB的播放系统
    """
    
    BASE_URL = "https://live.kankanews.com/huikan/"
    
    # 频道映射 (根据看看新闻页面)
    CHANNELS = {
        "dfws": "东方卫视",
        "shds": "上海都市",
        "shyl": "上海娱乐",
        "shxw": "上海新闻",
        "shcj": "上海财经",
        "shjs": "上海纪实",
        "kktv": "上海Knews",
        "shmrt": "第一财经",
    }
    
    async def crawl(self, page):
        """抓取上海卫视直播源"""
        print("\n📺 [东方卫视] 开始抓取...")
        results = {}
        captured_urls = {}
        
        async def handle_response(response):
            url = response.url
            if '.m3u8' in url:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() or 'smg' in url.lower() or 'kankanews' in url.lower():
                        if ch_name not in captured_urls:
                            captured_urls[ch_name] = url
        
        page.on("response", handle_response)
        
        try:
            print(f"  访问: {self.BASE_URL}")
            await page.goto(self.BASE_URL, wait_until="networkidle", timeout=45000)
            await asyncio.sleep(5)
            
            content = await page.content()
            
            # 提取m3u8地址
            m3u8_pattern = r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)'
            matches = re.findall(m3u8_pattern, content)
            
            for url in matches:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() and ch_name not in results:
                        results[ch_name] = url
                        print(f"  ✅ 页面提取: {ch_name}")
            
            # 尝试从JavaScript配置中提取
            # 看看新闻可能在页面JS中配置播放器
            js_config_pattern = r'playUrl["\']?\s*[:=]\s*["\']([^"\']+\.m3u8[^"\']*)["\']'
            js_matches = re.findall(js_config_pattern, content)
            for url in js_matches:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() and ch_name not in results:
                        results[ch_name] = url
                        print(f"  ✅ JS配置提取: {ch_name}")
            
            # 合并网络捕获
            for name, url in captured_urls.items():
                if name not in results:
                    results[name] = url
                    
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
        
        print(f"  [东方卫视] 完成: {len(results)} 个频道")
        return results


class BeijingCrawler:
    """
    北京卫视爬虫 - 北京时间
    API分析:
    - 官网: https://www.btime.com/
    - 北京广播电视台旗下频道
    - BRTV频道系统
    """
    
    BASE_URL = "https://www.btime.com/"
    
    CHANNELS = {
        "bjws": "北京卫视",
        "bjwy": "北京文艺",
        "bjkj": "北京科教",
        "bjys": "北京影视",
        "bjcj": "北京财经",
        "bjty": "北京体育",
        "bjsh": "北京生活",
        "bjqn": "北京青年",
        "bjxw": "北京新闻",
        "kket": "北京卡酷少儿",
    }
    
    async def crawl(self, page):
        """抓取北京卫视直播源"""
        print("\n📺 [北京卫视] 开始抓取...")
        results = {}
        captured_urls = {}
        
        async def handle_response(response):
            url = response.url
            if '.m3u8' in url:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() or 'btime' in url.lower() or 'brtv' in url.lower():
                        if ch_name not in captured_urls:
                            captured_urls[ch_name] = url
        
        page.on("response", handle_response)
        
        try:
            # 尝试访问直播专区
            live_urls = [
                "https://www.btime.com/",
                "https://live.btime.com/",
                "https://www.btime.com/live",
            ]
            
            for live_url in live_urls:
                try:
                    print(f"  访问: {live_url}")
                    await page.goto(live_url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(3)
                except:
                    continue
            
            content = await page.content()
            
            # 提取m3u8地址
            m3u8_pattern = r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)'
            matches = re.findall(m3u8_pattern, content)
            
            for url in matches:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() and ch_name not in results:
                        results[ch_name] = url
                        print(f"  ✅ 提取: {ch_name}")
            
            # 合并网络捕获
            for name, url in captured_urls.items():
                if name not in results:
                    results[name] = url
                    
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
        
        print(f"  [北京卫视] 完成: {len(results)} 个频道")
        return results


class GuangdongCrawler:
    """
    广东卫视爬虫
    API分析:
    - 官网: https://live.gdtv.cn/ 或 http://www.gdtv.cn/
    - 广东广播电视台旗下频道
    """
    
    BASE_URL = "https://www.gdtv.cn/"
    
    CHANNELS = {
        "gdws": "广东卫视",
        "gdzj": "广东珠江",
        "gdty": "广东体育",
        "gdgg": "广东公共",
        "gdxw": "广东新闻",
        "gdys": "广东影视",
        "gdyl": "广东娱乐",
        "gdse": "广东少儿",
        "gdkj": "广东科教",
    }
    
    async def crawl(self, page):
        """抓取广东卫视直播源"""
        print("\n📺 [广东卫视] 开始抓取...")
        results = {}
        captured_urls = {}
        
        async def handle_response(response):
            url = response.url
            if '.m3u8' in url:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() or 'gdtv' in url.lower():
                        if ch_name not in captured_urls:
                            captured_urls[ch_name] = url
        
        page.on("response", handle_response)
        
        try:
            # 尝试多个入口
            urls_to_try = [
                "https://www.gdtv.cn/",
                "http://www.gdtv.cn/",
                "https://live.gdtv.cn/",
            ]
            
            for url_to_try in urls_to_try:
                try:
                    print(f"  访问: {url_to_try}")
                    await page.goto(url_to_try, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(3)
                    break
                except:
                    continue
            
            content = await page.content()
            
            # 提取m3u8地址
            m3u8_pattern = r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)'
            matches = re.findall(m3u8_pattern, content)
            
            for url in matches:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() and ch_name not in results:
                        results[ch_name] = url
                        print(f"  ✅ 提取: {ch_name}")
            
            # 合并网络捕获
            for name, url in captured_urls.items():
                if name not in results:
                    results[name] = url
                    
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
        
        print(f"  [广东卫视] 完成: {len(results)} 个频道")
        return results


class AnhuiCrawler:
    """
    安徽卫视爬虫
    API分析:
    - 官网: http://www.ahtv.cn/
    - 直播地址已知部分: http://zbbf2.ahtv.cn/live/
    """
    
    CHANNELS = {
        "ahws": "安徽卫视",
        "ahys": "安徽影视",
        "ahkj": "安徽科教",
        "ahyw": "安徽经视",
        "ahgg": "安徽公共",
        "ahnf": "安徽农业科教",
        "ahse": "安徽少儿",
    }
    
    # 已知的m3u8模板
    KNOWN_PATTERNS = [
        "http://zbbf2.ahtv.cn/live/ahws.m3u8",
        "http://zbbf2.ahtv.cn/live/ahys.m3u8",
        "http://zbbf2.ahtv.cn/live/ahkj.m3u8",
        "http://zbbf2.ahtv.cn/live/ahyw.m3u8",
    ]
    
    async def crawl(self, page):
        """抓取安徽卫视直播源"""
        print("\n📺 [安徽卫视] 开始抓取...")
        results = {}
        captured_urls = {}
        
        async def handle_response(response):
            url = response.url
            if '.m3u8' in url:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() or 'ahtv' in url.lower():
                        if ch_name not in captured_urls:
                            captured_urls[ch_name] = url
        
        page.on("response", handle_response)
        
        try:
            print(f"  访问: http://www.ahtv.cn/")
            await page.goto("http://www.ahtv.cn/", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            
            content = await page.content()
            
            # 提取m3u8地址
            m3u8_pattern = r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)'
            matches = re.findall(m3u8_pattern, content)
            
            for url in matches:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() and ch_name not in results:
                        results[ch_name] = url
                        print(f"  ✅ 提取: {ch_name}")
            
            # 尝试已知的模板地址
            for pattern in self.KNOWN_PATTERNS:
                try:
                    # 验证地址是否可用
                    status = await page.evaluate(f'''
                        async () => {{
                            try {{
                                const r = await fetch("{pattern}", {{method: 'HEAD'}});
                                return r.status;
                            }} catch(e) {{
                                return 0;
                            }}
                        }}
                    ''')
                    if status == 200:
                        ch_id = pattern.split('/')[-1].replace('.m3u8', '')
                        if ch_id in self.CHANNELS:
                            results[self.CHANNELS[ch_id]] = pattern
                            print(f"  ✅ 已知地址验证成功: {self.CHANNELS[ch_id]}")
                except:
                    pass
            
            # 合并网络捕获
            for name, url in captured_urls.items():
                if name not in results:
                    results[name] = url
                    
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
        
        print(f"  [安徽卫视] 完成: {len(results)} 个频道")
        return results


class ShandongCrawler:
    """
    山东卫视爬虫
    API分析:
    - 官网: https://www.iqilu.com/
    - 直播地址已知部分: http://livealone.iqilu.com/tv/
    """
    
    CHANNELS = {
        "sdws": "山东卫视",
        "sdys": "山东影视",
        "sdkj": "山东科教",
        "sdgg": "山东公共",
        "sdty": "山东体育",
        "sdnf": "山东农科",
        "sdse": "山东少儿",
        "sdqn": "山东青年",
    }
    
    async def crawl(self, page):
        """抓取山东卫视直播源"""
        print("\n📺 [山东卫视] 开始抓取...")
        results = {}
        captured_urls = {}
        
        async def handle_response(response):
            url = response.url
            if '.m3u8' in url:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() or 'iqilu' in url.lower():
                        if ch_name not in captured_urls:
                            captured_urls[ch_name] = url
        
        page.on("response", handle_response)
        
        try:
            urls_to_try = [
                "https://www.iqilu.com/",
                "http://livealone.iqilu.com/tv/",
            ]
            
            for url_to_try in urls_to_try:
                try:
                    print(f"  访问: {url_to_try}")
                    await page.goto(url_to_try, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(2)
                except:
                    continue
            
            content = await page.content()
            
            # 提取m3u8地址
            m3u8_pattern = r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)'
            matches = re.findall(m3u8_pattern, content)
            
            for url in matches:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() and ch_name not in results:
                        results[ch_name] = url
                        print(f"  ✅ 提取: {ch_name}")
            
            # 合并网络捕获
            for name, url in captured_urls.items():
                if name not in results:
                    results[name] = url
                    
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
        
        print(f"  [山东卫视] 完成: {len(results)} 个频道")
        return results


class SichuanCrawler:
    """
    四川卫视爬虫
    API分析:
    - 官网: https://www.sctv.cn/ 或 https://www.sctv.com/
    - 直播地址已知: https://m3u8.sctv.cn/sctv/hls/
    """
    
    CHANNELS = {
        "sctv": "四川卫视",
        "scgg": "四川公共",
        "scys": "四川影视",
        "scxw": "四川新闻",
        "scyw": "四川经视",
        "scfn": "四川妇女儿童",
        "scwl": "四川文化旅游",
        "scty": "四川体育",
    }
    
    async def crawl(self, page):
        """抓取四川卫视直播源"""
        print("\n📺 [四川卫视] 开始抓取...")
        results = {}
        captured_urls = {}
        
        async def handle_response(response):
            url = response.url
            if '.m3u8' in url:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() or 'sctv' in url.lower():
                        if ch_name not in captured_urls:
                            captured_urls[ch_name] = url
        
        page.on("response", handle_response)
        
        try:
            urls_to_try = [
                "https://www.sctv.cn/",
                "https://www.sctv.com/",
            ]
            
            for url_to_try in urls_to_try:
                try:
                    print(f"  访问: {url_to_try}")
                    await page.goto(url_to_try, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(2)
                except:
                    continue
            
            content = await page.content()
            
            # 提取m3u8地址
            m3u8_pattern = r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)'
            matches = re.findall(m3u8_pattern, content)
            
            for url in matches:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() and ch_name not in results:
                        results[ch_name] = url
                        print(f"  ✅ 提取: {ch_name}")
            
            # 合并网络捕获
            for name, url in captured_urls.items():
                if name not in results:
                    results[name] = url
                    
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
        
        print(f"  [四川卫视] 完成: {len(results)} 个频道")
        return results


class ChongqingCrawler:
    """
    重庆卫视爬虫
    API分析:
    - 官网: http://www.cbg.cn/
    """
    
    CHANNELS = {
        "cqws": "重庆卫视",
        "cqys": "重庆影视",
        "cqxw": "重庆新闻",
        "cqse": "重庆少儿",
        "cqkj": "重庆科教",
        "cqsh": "重庆生活",
        "cqyl": "重庆娱乐",
    }
    
    async def crawl(self, page):
        """抓取重庆卫视直播源"""
        print("\n📺 [重庆卫视] 开始抓取...")
        results = {}
        captured_urls = {}
        
        async def handle_response(response):
            url = response.url
            if '.m3u8' in url:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() or 'cbg' in url.lower() or 'cqtv' in url.lower():
                        if ch_name not in captured_urls:
                            captured_urls[ch_name] = url
        
        page.on("response", handle_response)
        
        try:
            print(f"  访问: http://www.cbg.cn/")
            await page.goto("http://www.cbg.cn/", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            
            content = await page.content()
            
            # 提取m3u8地址
            m3u8_pattern = r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)'
            matches = re.findall(m3u8_pattern, content)
            
            for url in matches:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() and ch_name not in results:
                        results[ch_name] = url
                        print(f"  ✅ 提取: {ch_name}")
            
            # 合并网络捕获
            for name, url in captured_urls.items():
                if name not in results:
                    results[name] = url
                    
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
        
        print(f"  [重庆卫视] 完成: {len(results)} 个频道")
        return results


class ShenzhenCrawler:
    """
    深圳卫视爬虫
    API分析:
    - 官网: http://www.sztv.com.cn/
    """
    
    CHANNELS = {
        "szws": "深圳卫视",
        "szds": "深圳都市",
        "szcj": "深圳财经",
        "szyl": "深圳娱乐",
        "szty": "深圳体育",
        "szse": "深圳少儿",
        "szgg": "深圳公共",
    }
    
    async def crawl(self, page):
        """抓取深圳卫视直播源"""
        print("\n📺 [深圳卫视] 开始抓取...")
        results = {}
        captured_urls = {}
        
        async def handle_response(response):
            url = response.url
            if '.m3u8' in url:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() or 'sztv' in url.lower():
                        if ch_name not in captured_urls:
                            captured_urls[ch_name] = url
        
        page.on("response", handle_response)
        
        try:
            print(f"  访问: http://www.sztv.com.cn/")
            await page.goto("http://www.sztv.com.cn/", wait_until="networkidle", timeout=30000)
            await asyncio.sleep(2)
            
            content = await page.content()
            
            # 提取m3u8地址
            m3u8_pattern = r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)'
            matches = re.findall(m3u8_pattern, content)
            
            for url in matches:
                for ch_id, ch_name in self.CHANNELS.items():
                    if ch_id in url.lower() and ch_name not in results:
                        results[ch_name] = url
                        print(f"  ✅ 提取: {ch_name}")
            
            # 合并网络捕获
            for name, url in captured_urls.items():
                if name not in results:
                    results[name] = url
                    
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
        
        print(f"  [深圳卫视] 完成: {len(results)} 个频道")
        return results


class OtherProvinceCrawler:
    """
    其他省级卫视爬虫
    收集一些常见卫视的已知地址或通过官网抓取
    """
    
    # 其他卫视频道配置
    CHANNELS_CONFIG = {
        "hubei": {
            "url": "http://www.hbtv.com.cn/",
            "channels": {"hbws": "湖北卫视", "hbgg": "湖北公共", "hbys": "湖北影视"}
        },
        "henan": {
            "url": "http://www.hntv.tv/",
            "channels": {"hnws": "河南卫视", "hnds": "河南都市", "hnys": "河南影视"}
        },
        "hebei": {
            "url": "http://www.hebtv.com/",
            "channels": {"hbws": "河北卫视", "hbds": "河北都市", "hbys": "河北影视"}
        },
        "jiangxi": {
            "url": "http://www.jxntv.cn/",
            "channels": {"jxws": "江西卫视", "jxds": "江西都市", "jxgg": "江西公共"}
        },
        "guizhou": {
            "url": "http://www.gzstv.com/",
            "channels": {"gzws": "贵州卫视", "gzgg": "贵州公共", "gzys": "贵州影视"}
        },
        "yunnan": {
            "url": "http://www.yntv.cn/",
            "channels": {"ynws": "云南卫视", "ynds": "云南都市", "ynys": "云南影视"}
        },
        "fujian": {
            "url": "http://www.fjtv.net/",
            "channels": {"fjws": "福建卫视", "fjds": "福建都市", "fjys": "福建影视"}
        },
    }
    
    async def crawl(self, page):
        """抓取其他省级卫视直播源"""
        print("\n📺 [其他省级卫视] 开始抓取...")
        results = {}
        
        for province, config in self.CHANNELS_CONFIG.items():
            captured_urls = {}
            
            async def handle_response(response):
                url = response.url
                if '.m3u8' in url:
                    for ch_id, ch_name in config["channels"].items():
                        if ch_id in url.lower():
                            if ch_name not in captured_urls:
                                captured_urls[ch_name] = url
            
            page.on("response", handle_response)
            
            try:
                print(f"  访问 [{province}]: {config['url']}")
                await page.goto(config["url"], wait_until="networkidle", timeout=20000)
                await asyncio.sleep(2)
                
                content = await page.content()
                
                # 提取m3u8地址
                m3u8_pattern = r'(https?://[^"\'>\s]+\.m3u8[^"\'>\s]*)'
                matches = re.findall(m3u8_pattern, content)
                
                for url in matches:
                    for ch_id, ch_name in config["channels"].items():
                        if ch_id in url.lower() and ch_name not in results:
                            results[ch_name] = url
                            print(f"  ✅ [{province}] {ch_name}")
                
                # 合并网络捕获
                for name, url in captured_urls.items():
                    if name not in results:
                        results[name] = url
                        
            except Exception as e:
                print(f"  ⚠️ [{province}] 抓取失败: {e}")
            
            await asyncio.sleep(1)
        
        print(f"  [其他省级卫视] 完成: {len(results)} 个频道")
        return results


async def main():
    """主函数"""
    print("=" * 70)
    print("  省级卫视直播源抓取脚本 v2.0")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    all_results = {}
    
    # 输出文件路径
    output_dir = Path(__file__).parent
    output_file = output_dir / "province.m3u"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--allow-running-insecure-content',
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="zh-CN",
        )
        page = await context.new_page()
        
        # 执行各省份爬虫
        crawlers = [
            ("江苏卫视", JiangsuCrawler()),
            ("东方卫视", ShanghaiCrawler()),
            ("北京卫视", BeijingCrawler()),
            ("广东卫视", GuangdongCrawler()),
            ("安徽卫视", AnhuiCrawler()),
            ("山东卫视", ShandongCrawler()),
            ("四川卫视", SichuanCrawler()),
            ("重庆卫视", ChongqingCrawler()),
            ("深圳卫视", ShenzhenCrawler()),
            ("其他卫视", OtherProvinceCrawler()),
        ]
        
        for name, crawler in crawlers:
            try:
                results = await crawler.crawl(page)
                # 过滤购物频道
                results = {k: v for k, v in results.items() if not is_shopping_channel(k)}
                all_results.update(results)
            except Exception as e:
                print(f"  ❌ [{name}] 爬虫出错: {e}")
            
            # 每个爬虫之间等待
            await asyncio.sleep(2)
        
        await browser.close()
    
    # 生成M3U文件
    print("\n" + "=" * 70)
    print(f"  抓取完成！共获取 {len(all_results)} 个频道")
    print("=" * 70)
    
    # Token验证分析汇总
    print("\n📊 Token验证机制分析汇总:")
    token_channels = []
    for name, url in all_results.items():
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        auth_params = [k for k in params.keys() 
                       if any(x in k.lower() for x in ['auth', 'token', 'key', 'sign', 'time'])]
        if auth_params:
            token_channels.append((name, auth_params))
    
    if token_channels:
        print(f"  发现 {len(token_channels)} 个频道需要Token验证:")
        for name, params in token_channels:
            print(f"    - {name}: 验证参数 [{', '.join(params)}]")
        print("\n  ⚠️ Token时效性说明:")
        print("    - 大多数Token基于时间戳生成，时效通常为几小时到24小时")
        print("    - 需要定期重新抓取以更新Token")
        print("    - 部分平台Token可能包含设备指纹，需在相同环境下播放")
    else:
        print("  ✅ 所有抓取的频道均无明显Token验证")
    
    if all_results:
        # 生成M3U文件
        m3u_content = "#EXTM3U\n"
        m3u_content += f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        m3u_content += "# 省级卫视直播源（官方源）\n"
        m3u_content += "# 注意: 部分频道可能需要Token验证，时效有限\n\n"
        
        # 按省份分组
        province_groups = {
            "江苏": [],
            "上海": [],
            "北京": [],
            "广东": [],
            "安徽": [],
            "山东": [],
            "四川": [],
            "重庆": [],
            "深圳": [],
            "其他": [],
        }
        
        for name in sorted(all_results.keys()):
            for province in province_groups.keys():
                if province in name:
                    province_groups[province].append(name)
                    break
            else:
                province_groups["其他"].append(name)
        
        for province, channels in province_groups.items():
            if channels:
                m3u_content += f"\n# === {province}卫视 ===\n"
                for name in channels:
                    url = all_results[name]
                    m3u_content += f'#EXTINF:-1 tvg-name="{name}" tvg-logo="" group-title="省级卫视",{name}\n'
                    m3u_content += f"{url}\n"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(m3u_content)
        
        print(f"\n✅ 已保存到 {output_file}")
        print("\n频道列表:")
        
        for province, channels in province_groups.items():
            if channels:
                print(f"\n  [{province}卫视]:")
                for name in channels:
                    print(f"    - {name}")
    else:
        print("\n❌ 未抓取到任何直播源")
        print("\n💡 建议:")
        print("  1. 检查网络连接")
        print("  2. 尝试手动访问各卫视官网查看直播页面结构")
        print("  3. 部分平台可能有IP限制或需要登录")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)