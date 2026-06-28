"""
央视频直播源抓取脚本 v4 - Playwright浏览器内验证
利用浏览器环境批量验证m3u8地址，绕过CDN限制
"""

import asyncio
import re
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("请先安装 playwright: pip install playwright && playwright install chromium")
    sys.exit(1)

CCTV_LIVE_URL = "https://tv.cctv.com/live/"

CCTV_CHANNELS = [
    ("CCTV-1 综合", "cctv1"),
    ("CCTV-2 财经", "cctv2"),
    ("CCTV-3 综艺", "cctv3"),
    ("CCTV-4 中文国际", "cctv4"),
    ("CCTV-5 体育", "cctv5"),
    ("CCTV-5+ 体育赛事", "cctv5plus"),
    ("CCTV-6 电影", "cctv6"),
    ("CCTV-7 国防军事", "cctv7"),
    ("CCTV-8 电视剧", "cctv8"),
    ("CCTV-9 纪录", "cctvjilu"),
    ("CCTV-10 科教", "cctv10"),
    ("CCTV-11 戏曲", "cctv11"),
    ("CCTV-12 社会与法", "cctv12"),
    ("CCTV-13 新闻", "cctv13"),
    ("CCTV-14 少儿", "cctvchild"),
    ("CCTV-15 音乐", "cctv15"),
    ("CCTV-16 奥林匹克", "cctv16"),
    ("CCTV-17 农业农村", "cctv17"),
]

CDN_PATTERNS = [
    ("https://{cdn}/ldncctvwbcd/cdrmld{id}_1/index.m3u8?BR=td", [
        "ldncctvwbcdbyte.volcfcdn.com",
        "ldncctvwbcdcnc.v.wscdns.com",
    ]),
    ("https://{cdn}/ldocctvwbcd/cdrmld{id}_1/index.m3u8?wsApp=HLS", [
        "ldocctvwbcdcnc.v.wscdns.com",
        "ldocctvwbcdbyte.volcfcdn.com",
    ]),
]


async def crawl_cctv_sources(output_file="direct_sources.m3u"):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )

        page = await context.new_page()
        
        print(f"正在访问央视频直播页...")
        await page.goto(CCTV_LIVE_URL, wait_until="domcontentloaded", timeout=60000)
        await page.wait_for_timeout(2000)

        all_urls = []
        for pattern, cdns in CDN_PATTERNS:
            for cdn in cdns:
                for name, ch_id in CCTV_CHANNELS:
                    url = pattern.format(cdn=cdn, id=ch_id)
                    all_urls.append((name, ch_id, url))

        print(f"共 {len(CCTV_CHANNELS)} 个频道，{len(CDN_PATTERNS)*2} 种CDN组合，开始验证...\n")

        results = {}
        
        js_code = """
        async (urls) => {
            const results = [];
            for (const [name, id, url] of urls) {
                try {
                    const ctrl = new AbortController();
                    const timeout = setTimeout(() => ctrl.abort(), 10000);
                    const r = await fetch(url, { signal: ctrl.signal, cache: 'no-store' });
                    clearTimeout(timeout);
                    const text = await r.text();
                    const ok = r.status === 200 && text.includes('#EXTM3U');
                    results.push([name, id, url, ok, r.status]);
                } catch (e) {
                    results.push([name, id, url, false, e.message]);
                }
            }
            return results;
        }
        """
        
        batch_size = 4
        for i in range(0, len(all_urls), batch_size):
            batch = all_urls[i:i+batch_size]
            batch_results = await page.evaluate(js_code, batch)
            
            for name, ch_id, url, ok, status in batch_results:
                if ok and ch_id not in results:
                    results[ch_id] = (name, url)
                    print(f"✅ {name} ({ch_id}): 可用")

        await browser.close()

    print(f"\n{'='*50}")
    print(f"验证完成！成功 {len(results)}/{len(CCTV_CHANNELS)} 个频道")
    print(f"{'='*50}")
    
    for ch_id, (name, url) in sorted(results.items()):
        print(f"  {name}: {url[:100]}...")

    if results and output_file:
        update_m3u_file(results, output_file)
    
    return results


def update_m3u_file(results, output_file):
    m3u_path = Path(output_file)
    existing_content = ""
    if m3u_path.exists():
        existing_content = m3u_path.read_text(encoding="utf-8")
    
    cctv_entries = []
    cctv_entries.append("# 央视频道（官方源）")
    for ch_id, (name, url) in sorted(results.items()):
        cctv_entries.append(f'#EXTINF:-1 tvg-name="{name}" tvg-logo="" group-title="央视频道",{name}')
        cctv_entries.append(url)
    cctv_entries.append("")
    
    cctv_block = "\n".join(cctv_entries)
    
    if "# 央视频道" in existing_content:
        pattern = r"# 央视频道.*?(?=\n# |\n#EXTM3U|$)"
        new_content = re.sub(pattern, cctv_block, existing_content, flags=re.DOTALL)
    else:
        lines = existing_content.split("\n")
        insert_idx = 1
        new_lines = lines[:insert_idx] + [""] + cctv_entries + lines[insert_idx:]
        new_content = "\n".join(new_lines)
    
    m3u_path.write_text(new_content, encoding="utf-8")
    print(f"\n已更新 {output_file} 中的央视频道")


if __name__ == "__main__":
    output = sys.argv[1] if len(sys.argv) > 1 else "direct_sources.m3u"
    asyncio.run(crawl_cctv_sources(output))
