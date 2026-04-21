# Feishu 飞书文档导出为 Obsidian Vault

将飞书知识库文档批量导出为 Obsidian Vault，保留目录结构、标题格式、图片和文件附件。

## 功能特性

- ✅ 保留飞书目录结构
- ✅ 目录型文档保存为 `README.md`
- ✅ 正确的标题格式（`#` 标题层级）
- ✅ 下载图片到 `figs/` 文件夹（使用哈希文件名，避免冲突）
- ✅ 下载文件附件到 `feishu_files/` 文件夹
- ✅ Token → 文件名映射，确保同一文件只下载一次
- ✅ 支持画板/白板导出为图片
- ✅ 自动处理 API 限流
- ✅ 支持表格导出（新版 docx/v1 API）

## Block Type 与 Markdown 元素对应关系

| Block Type | 元素类型 | Markdown 格式 |
|------------|----------|---------------|
| 1 | page root | (忽略) |
| 2 | 正文段落 (text) | 普通文本 |
| 3-8 | heading1-6 | `#` 标题 |
| 12 | bullet | `- 列表项` |
| 13 | ordered | `1. 有序列表` |
| 14 | code | ` ```语言\n代码\n``` ` |
| 17 | todo | `- [ ] 待办` / `- [x] 已完成` |
| 19 | callout | `> [!NOTE] 提示框` |
| 23 | file | `[[附件]]` |
| 24, 25 | grid | 递归处理子块 |
| 27 | image | `![[图片]]` |
| 31 | table | Markdown 表格 |
| 32 | table_cell | (由表格处理) |
| 34 | quote | `> 引用` |
| **502** | **minder (画板/白板)** | `![[图片]]` |
| 43 | board (看板) | `_[看板，需在飞书中查看]_` |

## 导出方法

### 1. 认证配置

本项目使用飞书 Open Platform API，需要配置：

1. **创建飞书应用**：https://open.feishu.cn/app
2. **获取 App ID 和 App Secret**
3. **配置重定向 URL**：在应用设置中添加 `https://open.feishu.cn/connect/landing/authorize`
4. **添加权限**：
   - `docx:document:readonly`
   - `wiki:wiki:readonly`
   - `bitable:app:readonly`
   - `drive:drive:readonly`
5. **获取用户 Token (OAuth)**：

```bash
python3 get_auth_url.py
# 浏览器打开生成的链接，授权后复制 URL 中的 code 参数
python3 exchange_token.py <code>
# 将返回的 token 保存到 .feishu_token 文件
```

### 2. 运行导出

```bash
# 1. 获取知识库目录树（只需运行一次）
python3 build_tree.py

# 2. 运行导出
python3 export.py
```

## 文件结构

```
feishu-to-obsidian/
├── README.md                    # 本文件
├── export.py                   # 主导出脚本 (v12)
├── build_tree.py               # 获取目录树
├── get_auth_url.py            # OAuth 授权 URL 生成
├── exchange_token.py           # 交换 access_token
├── replace_urls.py            # 替换为外部 URL（可选）
├── .feishu_token             # 用户 Token
├── .feishu_tree.json         # 知识库目录树
└── feishu_token_file_map.json # Token → 文件名映射
```

## 输出文件

```
feishu_export/     # 导出的 Markdown 文档
figs/              # 图片文件（哈希命名）
feishu_files/      # 附件文件
```

## 关键代码说明

### 哈希文件名

为避免文件名冲突，图片使用哈希命名：

```python
import hashlib, uuid

def generate_hash_filename(token, ext):
    """基于 token 生成唯一哈希文件名"""
    token_hash = hashlib.md5(token.encode()).hexdigest()[:12]
    random_suffix = uuid.uuid4().hex[:8]
    return f"{token_hash}_{random_suffix}.{ext}"
```

### 画板导出

Block Type 502（画板/白板）通过飞书导出 API 获取 PNG：

```python
def export_minder_to_image(minder_token, save_dir):
    # 1. 创建导出任务
    r = requests.post(
        'https://open.feishu.cn/open-apis/suite/docs-api/minder/export',
        json={"type": "png", "minder_token": minder_token}
    )
    # 2. 轮询导出状态
    # 3. 下载 PNG
```

### API 限流处理

为避免触发飞书 API 限流，添加了适当的延迟：

```python
time.sleep(0.1)  # 获取子节点时
time.sleep(0.2)  # 获取节点详情时
```

## 环境要求

- Python 3.8+
- requests 库

```bash
pip install requests
```

## 注意事项

- 用户 Token 有效期约 2 小时，超时需重新授权
- 部分文件/图片可能因权限问题返回 403（需确认应用有权限访问）
- 导出前会清空 `feishu_export/`、`figs/`、`feishu_files/` 目录
- Token 映射文件用于记录已下载的文件，避免重复下载

## License

MIT
