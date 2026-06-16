#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动在 GitHub 上创建仓库并上传所有文件
使用: python push_to_github.py --token ghp_你的token --repo 仓库名 --user 用户名
"""
import requests
import base64
import argparse
import os
import json

GITHUB_API = "https://api.github.com"

def create_repo(token, user, repo_name, description="我的直播源仓库"):
    """创建 GitHub 仓库"""
    url = f"{GITHUB_API}/user/repos"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }
    data = {
        "name": repo_name,
        "description": description,
        "private": False,
        "has_issues": True,
        "has_wiki": True,
        "auto_init": False,
    }
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 201:
        print(f"✅ 仓库创建成功: https://github.com/{user}/{repo_name}")
        return True
    elif resp.status_code == 422:
        # 仓库已存在
        print(f"ℹ️ 仓库已存在: https://github.com/{user}/{repo_name}")
        return True
    else:
        print(f"❌ 创建仓库失败: {resp.status_code} {resp.text}")
        return False

def get_file_sha(token, user, repo_name, path):
    """获取文件当前 SHA (用于判断是否需要更新)"""
    url = f"{GITHUB_API}/repos/{user}/{repo_name}/contents/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        if isinstance(data, dict):
            return data.get("sha")
    return None

def upload_file(token, user, repo_name, local_path, github_path, message="更新文件"):
    """上传单个文件到 GitHub"""
    url = f"{GITHUB_API}/repos/{user}/{repo_name}/contents/{github_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
    }

    # 读取并编码文件
    with open(local_path, "rb") as f:
        content = base64.b64encode(f.read()).decode("utf-8")

    # 检查是否已有同名文件
    sha = get_file_sha(token, user, repo_name, github_path)

    data = {
        "message": message,
        "content": content,
    }
    if sha:
        data["sha"] = sha  # 如果文件存在，需要提供 SHA 来更新

    method = "PUT"
    resp = requests.put(url, headers=headers, json=data)

    if resp.status_code in (200, 201):
        action = "更新" if sha else "新增"
        print(f"  ✅ {action}: {github_path}")
        return True
    else:
        print(f"  ❌ 失败: {github_path} - {resp.status_code}")
        return False

def main():
    parser = argparse.ArgumentParser(description="上传文件到 GitHub")
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token (ghp_开头)")
    parser.add_argument("--user", required=True, help="GitHub 用户名")
    parser.add_argument("--repo", default="iptv-sources", help="仓库名 (默认: iptv-sources)")
    parser.add_argument("--dir", default=".", help="要上传的本地目录 (默认: 当前目录)")
    args = parser.parse_args()

    token = args.token
    user = args.user
    repo_name = args.repo
    base_dir = args.dir

    print(f"{'='*60}")
    print(f"用户: {user}")
    print(f"仓库: {repo_name}")
    print(f"目录: {os.path.abspath(base_dir)}")
    print(f"{'='*60}")

    # 1. 创建仓库
    print("\n[1/3] 创建仓库...")
    if not create_repo(token, user, repo_name):
        return

    # 2. 收集要上传的文件
    print(f"\n[2/3] 收集文件...")
    files_to_upload = []
    for root, dirs, files in os.walk(base_dir):
        # 跳过 output 和缓存目录
        dirs[:] = [d for d in dirs if d not in ("output", "__pycache__", ".git")]
        for fname in files:
            local_full = os.path.join(root, fname)
            # 计算相对于 base_dir 的路径
            rel_path = os.path.relpath(local_full, base_dir)
            # 转换为 GitHub 路径 (正斜杠)
            github_path = rel_path.replace("\\", "/")
            files_to_upload.append((local_full, github_path))

    print(f"  发现 {len(files_to_upload)} 个文件")

    # 3. 上传文件
    print(f"\n[3/3] 上传文件...")
    success = 0
    for local_full, github_path in files_to_upload:
        if upload_file(token, user, repo_name, local_full, github_path, f"自动上传: {github_path}"):
            success += 1

    print(f"\n{'='*60}")
    print(f"完成! {success}/{len(files_to_upload)} 个文件已上传")
    print(f"查看: https://github.com/{user}/{repo_name}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
