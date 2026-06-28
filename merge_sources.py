#!/usr/bin/env python3
"""
省级卫视直播源整合脚本
- 从浙江卫视和省级卫视抓取脚本中提取直播源
- 整合到精选源文件中
- 排除所有购物频道
"""

import os
import sys
from datetime import datetime

# 购物频道关键词黑名单
SHOPPING_KEYWORDS = [
    '购物', '好易购', '快乐购', '家有购物', '优购物', '购物频道',
    '东方购物', 'CCTV购物', '风尚购物', '家购', '电视购物',
    '天天购物', '聚惠购物', '惠购物', '易购物'
]

def is_shopping_channel(name):
    """判断是否为购物频道"""
    for keyword in SHOPPING_KEYWORDS:
        if keyword in name:
            return True
    return False

def parse_m3u(file_path):
    """解析M3U文件"""
    channels = []
    if not os.path.exists(file_path):
        return channels
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    current_name = None
    current_url = None
    current_group = None
    
    for line in lines:
        if line.startswith('#EXTINF:'):
            # 解析频道名称和分组
            parts = line.split(',')
            if len(parts) >= 2:
                current_name = parts[-1].strip()
                # 解析分组
                if 'group-title=' in line:
                    group_match = line.split('group-title="')
                    if len(group_match) >= 2:
                        current_group = group_match[1].split('"')[0]
        elif line.startswith('http') or line.startswith('https'):
            current_url = line.strip()
            if current_name and current_url:
                channels.append({
                    'name': current_name,
                    'url': current_url,
                    'group': current_group or '未知'
                })
                current_name = None
                current_url = None
    
    return channels

def main():
    print("=" * 70)
    print("  省级卫视直播源整合")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    all_channels = []
    
    # 1. 央视频道（永久有效）
    print("\n[1] 央视频道...")
    cctv_channels = parse_m3u('direct_sources.m3u')
    cctv_count = 0
    for ch in cctv_channels:
        if '央视' in ch['group'] or 'CCTV' in ch['name']:
            if not is_shopping_channel(ch['name']):
                all_channels.append(ch)
                cctv_count += 1
    print(f"  ✅ 央视频道: {cctv_count} 个")
    
    # 2. 芒果TV（湖南台）
    print("\n[2] 芒果TV...")
    mgtv_channels = parse_m3u('direct_sources.m3u')
    mgtv_count = 0
    for ch in mgtv_channels:
        if '芒果' in ch['group'] or '湖南' in ch['name']:
            if not is_shopping_channel(ch['name']):
                all_channels.append(ch)
                mgtv_count += 1
    print(f"  ✅ 芒果TV: {mgtv_count} 个")
    
    # 3. 浙江卫视
    print("\n[3] 浙江卫视...")
    zj_channels = parse_m3u('zhejiang.m3u')
    zj_count = 0
    for ch in zj_channels:
        if not is_shopping_channel(ch['name']):
            all_channels.append(ch)
            zj_count += 1
    print(f"  ✅ 浙江卫视: {zj_count} 个")
    
    # 4. 省级卫视
    print("\n[4] 省级卫视...")
    province_channels = parse_m3u('province.m3u')
    province_count = 0
    for ch in province_channels:
        if not is_shopping_channel(ch['name']):
            all_channels.append(ch)
            province_count += 1
    print(f"  ✅ 省级卫视: {province_count} 个")
    
    # 生成整合后的M3U文件
    print("\n" + "=" * 70)
    print(f"  整合完成！共 {len(all_channels)} 个频道")
    print("=" * 70)
    
    if all_channels:
        # 按分组排序
        groups = {}
        for ch in all_channels:
            group = ch['group']
            if group not in groups:
                groups[group] = []
            groups[group].append(ch)
        
        # 生成M3U内容
        m3u_content = "#EXTM3U\n\n"
        
        # 央视频道
        if '央视频道' in groups:
            m3u_content += "# 央视频道（官方源，永久有效）\n"
            for ch in groups['央视频道']:
                m3u_content += f'#EXTINF:-1 tvg-name="{ch["name"]}" tvg-logo="" group-title="央视频道",{ch["name"]}\n'
                m3u_content += f'{ch["url"]}\n'
            m3u_content += "\n"
        
        # 芒果TV
        if '芒果TV' in groups:
            m3u_content += "# 芒果TV（湖南台，每6小时更新）\n"
            for ch in groups['芒果TV']:
                m3u_content += f'#EXTINF:-1 tvg-name="{ch["name"]}" tvg-logo="" group-title="芒果TV",{ch["name"]}\n'
                m3u_content += f'{ch["url"]}\n'
            m3u_content += "\n"
        
        # 浙江卫视
        if '卫视频道' in groups:
            m3u_content += "# 浙江卫视（官方源，每6小时更新）\n"
            for ch in groups['卫视频道']:
                if '浙江' in ch['name']:
                    m3u_content += f'#EXTINF:-1 tvg-name="{ch["name"]}" tvg-logo="" group-title="浙江卫视",{ch["name"]}\n'
                    m3u_content += f'{ch["url"]}\n'
            m3u_content += "\n"
        
        # 省级卫视
        if '省级卫视' in groups:
            m3u_content += "# 省级卫视（官方源，每6小时更新）\n"
            for ch in groups['省级卫视']:
                if '浙江' not in ch['name']:  # 避免重复
                    m3u_content += f'#EXTINF:-1 tvg-name="{ch["name"]}" tvg-logo="" group-title="省级卫视",{ch["name"]}\n'
                    m3u_content += f'{ch["url"]}\n'
        
        # 保存文件
        output_file = 'direct_sources.m3u'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(m3u_content)
        
        print(f"\n✅ 已保存到 {output_file}")
        
        # 打印频道列表
        print("\n频道列表:")
        for group_name in ['央视频道', '芒果TV', '浙江卫视', '省级卫视']:
            if group_name in groups or any(group_name in ch['group'] for ch in all_channels):
                channels_in_group = [ch for ch in all_channels if group_name in ch['group'] or group_name == ch['group']]
                if channels_in_group:
                    print(f"\n  [{group_name}]:")
                    for ch in channels_in_group:
                        print(f"    - {ch['name']}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())