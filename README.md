# Feishu 飞书文档导出为 Obsidian Vault

将飞书知识库文档批量导出为 Obsidian Vault，保留目录结构、标题格式、图片和文件附件。

## 功能特性

- ✅ 保留飞书目录结构
- ✅ 目录型文档保存为 `README.md`
- ✅ 正确的标题格式（`#` 标题层级）
- ✅ 下载图片到 `figs/` 文件夹
- ✅ 下载文件附件到 `feishu_files/` 文件夹
- ✅ 从 HTTP 响应头提取真实文件名和扩展名

## Block Type 与 Markdown 元素对应关系

通过逆向工程发现的飞书 Block 类型映射：

| Block Type | 元素类型 | Markdown 格式 |
|------------|----------|---------------|
| 1 | page root | (忽略) |
| 2 | 正文段落 (text) | 普通文本 |
| 3 | heading1 | `# 标题` |
| 4 | heading2 | `## 标题` |
| 5 | heading3 | `### 标题` |
| 6 | heading4 | `#### 标题` |
| 7 | heading5 | `##### 标题` |
| 8 | heading6 | `###### 标题` |
| 12 | bullet | `- 列表项` |
| 13 | ordered | `1. 有序列表` |
| 14 | code | ` ```语言\n代码\n``` ` |
| 17 | todo | `- [ ] 待办` / `- [x] 已完成` |
| 19 | callout | `> [!NOTE] 提示框` |
| 23 | file | `[[附件]]` |
| 24 | grid | 递归处理子块 |
| 25 | grid_column | 递归处理子块 |
| 27 | image | `![[图片]]` |
| 31 | table | Markdown 表格 |
| 32 | table_cell | (由表格处理) |
| 34 | quote_container | `> 引用` |
| 43 | board (看板) | `_[看板，需在飞书中查看]_` |

## 导出方法

### 1. 认证配置

本项目使用飞书 Open Platform API，需要配置：

1. **创建飞书应用**：https://open.feishu.cn/app
2. **获取 App ID 和 App Secret**
3. **配置重定向 URL**：在应用设置中添加 `https://open.feishu.cn/connect/landing/authorize`
4. **获取用户 Token (OAuth)**：

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
python3 export_v11.py
```

## 文件结构

```
feishu-to-obsidian/
├── README.md                    # 本文件
├── export_v11.py               # 主导出脚本（最终版）
├── build_tree.py               # 获取目录树
├── get_auth_url.py             # OAuth 授权 URL 生成
├── exchange_token.py           # 交换 access_token
├── .feishu_token               # 用户 Token（需手动创建）
└── .feishu_tree.json           # 知识库目录树（自动生成）
```

## 关键代码说明

### 文件下载：从 HTTP 头提取真实文件名

飞书 API 返回的 `Content-Disposition` 头包含真实文件名：

```python
import re, urllib.parse

def extract_filename_from_cd(cd_header):
    """从 Content-Disposition header 提取真实文件名"""
    if not cd_header:
        return None
    # Try RFC 5987 encoded filename*
    m = re.search(r"filename\*=(?:UTF-8''|UTF-8'')(.+?)(?:;|$)", cd_header, re.IGNORECASE)
    if m:
        return urllib.parse.unquote(m.group(1).strip())
    # Try regular filename
    m = re.search(r'filename="(.+?)"', cd_header, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None
```

### 关键发现

1. **Block Type 2 不是标题**：飞书的 Type 2 是普通正文段落，Type 3-8 才是各级标题
2. **图片 token 下载**：使用 `tenant_access_token` 下载图片/文件
3. **文件名提取**：必须从 `Content-Disposition` 头提取，不能依赖 `file_extension` 字段（可能为空或不准确）

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

## License

MIT
