#!/usr/bin/env python3
"""
获取飞书知识库目录树
需要先配置好 .feishu_token
"""
import requests, json

APP_ID = 'YOUR_APP_ID'
APP_SECRET = 'YOUR_APP_SECRET'
WIKI_SPACE_ID = 'YOUR_WIKI_SPACE_ID'  # 知识库 space ID

# Read token
with open('.feishu_token') as f:
    USER_TOKEN = f.read().strip()

u_headers = {'Authorization': f'Bearer {USER_TOKEN}'}

def get_wiki_nodes():
    """获取知识库根节点"""
    r = requests.get(
        'https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node',
        headers=u_headers,
        params={'token': WIKI_SPACE_ID}
    )
    return r.json()

def get_child_nodes(parent_token):
    """获取子节点"""
    r = requests.get(
        'https://open.feishu.cn/open-apis/wiki/v2/spaces/' + parent_token + '/children',
        headers=u_headers,
        params={'page_size': 500}
    )
    data = r.json()
    if data.get('code') == 0:
        return data.get('data', {}).get('items', [])
    return []

def build_tree(node_token, depth=0):
    """递归构建目录树"""
    node_info = requests.get(
        'https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node',
        headers=u_headers,
        params={'token': node_token}
    ).json()

    if node_info.get('code') != 0:
        return None

    data = node_info.get('data', {}).get('node', {})
    node = {
        'title': data.get('title', ''),
        'obj_type': data.get('obj_type', ''),
        'obj_token': data.get('node_token', ''),
        'has_child': data.get('has_child', False),
    }

    if node['has_child']:
        children = get_child_nodes(node['obj_token'])
        node['children'] = []
        for child in children:
            child_node = build_tree(child.get('node_token', ''), depth+1)
            if child_node:
                node['children'].append(child_node)

    return node

def main():
    print("获取知识库目录树...")

    # Get root nodes
    r = requests.get(
        'https://open.feishu.cn/open-apis/wiki/v2/spaces',
        headers=u_headers
    )
    data = r.json()
    print(f"Spaces response: {data}")

    if data.get('code') != 0:
        print(f"❌ 获取失败: {data.get('msg')}")
        print("可能原因: Token 过期或权限不足")
        return

    # Build tree from all spaces
    tree = []
    for space in data.get('data', {}).get('spaces', []):
        root_nodes = get_child_nodes(space.get('space_id', ''))
        for node in root_nodes:
            tree_node = build_tree(node.get('node_token', ''))
            if tree_node:
                tree.append(tree_node)

    # Save tree
    with open('.feishu_tree.json', 'w', encoding='utf-8') as f:
        json.dump(tree, f, ensure_ascii=False, indent=2)

    # Count
    def count_nodes(nodes):
        count = len(nodes)
        for n in nodes:
            if 'children' in n:
                count += count_nodes(n['children'])
        return count

    total = count_nodes(tree)
    print(f"✅ 完成! 共 {total} 个节点")
    print(f"已保存到 .feishu_tree.json")

if __name__ == '__main__':
    main()
