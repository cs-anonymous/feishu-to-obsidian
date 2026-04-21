#!/usr/bin/env python3
"""
获取飞书知识库完整目录树
"""
import requests, json, os, time

APP_ID = 'cli_a93bb4aca4f85cc9'
APP_SECRET = 'EYrNOBjQIhxfYCs2DMWgzekL48BoZQib'

# Read token
if os.path.exists('.feishu_token'):
    with open('.feishu_token') as f:
        USER_TOKEN = f.read().strip()
else:
    print("❌ 找不到 .feishu_token 文件")
    exit(1)

u_headers = {'Authorization': f'Bearer {USER_TOKEN}'}
_NO_PROXY = {'http': None, 'https': None}

def get_space_nodes(space_id):
    """获取 space 下的根节点"""
    time.sleep(0.1)
    r = requests.get(
        f'https://open.feishu.cn/open-apis/wiki/v2/spaces/{space_id}/nodes',
        headers=u_headers,
        params={'page_size': 50},
        proxies=_NO_PROXY
    )
    data = r.json()
    if data.get('code') == 0:
        return data.get('data', {}).get('items', [])
    print(f"  ⚠️ 获取 space 节点失败: {data.get('msg')}")
    return []

def get_child_nodes(space_id, parent_token):
    """获取指定父节点的子节点"""
    time.sleep(0.1)
    r = requests.get(
        f'https://open.feishu.cn/open-apis/wiki/v2/spaces/{space_id}/nodes',
        headers=u_headers,
        params={'parent_node_token': parent_token, 'page_size': 50},
        proxies=_NO_PROXY
    )
    data = r.json()
    if data.get('code') == 0:
        return data.get('data', {}).get('items', [])
    print(f"  ⚠️ 获取子节点失败: {data.get('msg')}")
    return []

def build_tree(space_id, node_token, depth=0):
    """递归构建目录树"""
    # 添加延迟避免限流
    time.sleep(0.2)

    # 获取节点详情
    node_info = requests.get(
        'https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node',
        headers=u_headers,
        params={'token': node_token},
        proxies=_NO_PROXY
    ).json()

    if node_info.get('code') != 0:
        print(f"{'  ' * depth}⚠️ 获取节点失败: {node_token}")
        return None

    node_data = node_info.get('data', {}).get('node', {})
    node = {
        'title': node_data.get('title', ''),
        'obj_type': node_data.get('obj_type', ''),
        'obj_token': node_data.get('node_token', ''),
        'has_child': node_data.get('has_child', False),
    }

    # 递归获取子节点
    if node['has_child']:
        children = get_child_nodes(space_id, node['obj_token'])
        node['children'] = []
        for child in children:
            child_node = build_tree(space_id, child.get('node_token', ''), depth + 1)
            if child_node:
                node['children'].append(child_node)

    return node

def count_nodes(nodes):
    """统计节点总数"""
    count = len(nodes)
    for n in nodes:
        if 'children' in n:
            count += count_nodes(n['children'])
    return count

def main():
    print("获取知识库完整目录树...")

    # 获取所有 spaces
    r = requests.get(
        'https://open.feishu.cn/open-apis/wiki/v2/spaces',
        headers=u_headers,
        proxies=_NO_PROXY
    )
    data = r.json()

    if data.get('code') != 0:
        print(f"❌ 获取失败: {data.get('msg')}")
        return

    tree = []
    for space in data.get('data', {}).get('items', []):
        space_id = space.get('space_id', '')
        print(f"\n处理知识库: {space.get('name')} ({space_id})")

        # 获取根节点
        root_nodes = get_space_nodes(space_id)
        print(f"  根节点: {len(root_nodes)} 个")

        for node in root_nodes:
            tree_node = build_tree(space_id, node.get('node_token', ''))
            if tree_node:
                tree.append(tree_node)

    # 保存树
    with open('.feishu_tree.json', 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    total = count_nodes(tree)
    print(f"\n✅ 完成! 共 {total} 个节点")
    print(f"已保存到 .feishu_tree.json")

if __name__ == '__main__':
    main()
