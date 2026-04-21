#!/usr/bin/env python3
"""
交换 OAuth code 为 access_token
用法: python3 exchange_token.py <code>
"""
import requests, sys

APP_ID = 'YOUR_APP_ID'
APP_SECRET = 'YOUR_APP_SECRET'

if len(sys.argv) < 2:
    print("用法: python3 exchange_token.py <code>")
    print("从浏览器 URL 中复制 code= 后面的值")
    sys.exit(1)

code = sys.argv[1]

# Exchange code for user access token
r = requests.post(
    'https://open.feishu.cn/open-apis/authen/v1/oidc/access_token',
    json={
        'grant_type': 'authorization_code',
        'code': code,
        'app_id': APP_ID,
        'app_secret': APP_SECRET,
    }
)
data = r.json()
print(f"Response: {data}")

if data.get('code') == 0:
    token = data['data']['access_token']
    print(f'\n✅ 获取成功!')
    print(f'access_token: {token}')
    print(f'\n将 token 保存到 .feishu_token 文件:')
    with open('.feishu_token', 'w') as f:
        f.write(token)
    print('已保存到 .feishu_token')
    print(f'\n注意: Token 有效期约 2 小时，超时需重新授权')
else:
    print(f'❌ 获取失败: {data.get("msg")}')
