#!/usr/bin/env python3
"""
获取飞书 OAuth 授权 URL
"""
import requests, urllib.parse

APP_ID = 'cli_a93bb4aca4f85cc9'      # 飞书应用 App ID
APP_SECRET = 'EYrNOBjQIhxfYCs2DMWgzekL48BoZQib'  # 飞书应用 App Secret

# Get app_access_token
r = requests.post(
    'https://open.feishu.cn/open-apis/auth/v3/app_access_token/internal',
    json={'app_id': APP_ID, 'app_secret': APP_SECRET}
)
app_token = r.json()['app_access_token']
print(f'app_access_token: {app_token[:30]}...')

# Generate OAuth URL
REDIRECT_URI = 'https://open.feishu.cn/connect/landing/authorize'
params = {
    'app_id': APP_ID,
    'redirect_uri': REDIRECT_URI,
    'scope': 'docx:document:readonly docx:document wiki:wiki:readonly bitable:app:readonly drive:drive:readonly',
    'state': 'obsidian_export',
    'response_type': 'code',
}
url = 'https://open.feishu.cn/open-apis/authen/v1/authorize?' + urllib.parse.urlencode(params)
print(f'\n请在浏览器打开：')
print(url)
print(f'\n授权后，浏览器会跳转到错误页面（这是正常的）')
print(f'请复制浏览器地址栏 URL 中 code= 后面的值')
print(f'\n然后运行: python3 exchange_token.py <code>')
