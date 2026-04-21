#!/usr/bin/env python3
"""
将 feishu_export 中的 wiki 链接替换为外部 URL
"""
import re
import os
from urllib.parse import quote

BASE_URL_FIGS = "https://n.ye-sun.com/gallery/2026/figs"
BASE_URL_FILES = "https://n.ye-sun.com/gallery/2026/feishu_files"

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content

    # 处理 [[feishu_files/xxx]] -> [xxx](url)
    def replace_files_link(match):
        filename = match.group(1)
        encoded_filename = quote(filename, safe='/')
        return f"[{filename}]({BASE_URL_FILES}/{encoded_filename})"

    content = re.sub(r'\[\[feishu_files/([^\]]+)\]\]', replace_files_link, content)

    # 处理 [[figs/xxx]] -> ![xxx](url) (单行格式)
    def replace_figs_link(match):
        filename = match.group(1)
        encoded_filename = quote(filename, safe='/')
        return f"![{filename}]({BASE_URL_FIGS}/{encoded_filename})"

    # 处理 ![[figs/xxx]] -> ![xxx](url) (嵌入格式)
    content = re.sub(r'!\[\[figs/([^\]]+)\]\]', replace_figs_link, content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# 处理 feishu_export 目录
export_dir = "./feishu_export"
count_files = 0
count_replaced = 0

for root, dirs, files in os.walk(export_dir):
    for file in files:
        if file.endswith('.md'):
            filepath = os.path.join(root, file)
            count_files += 1
            if process_file(filepath):
                count_replaced += 1
                print(f"✓ {filepath}")

print(f"\n处理完成: {count_replaced}/{count_files} 个文件已修改")
