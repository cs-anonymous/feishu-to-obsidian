#!/usr/bin/env python3
"""
飞书知识库 → Obsidian 导出 v12
关键修复：使用随机哈希名称保存图片，避免文件名冲突
"""
import os, re, json, time, requests, shutil, urllib.parse, uuid, hashlib
from pathlib import Path

# ============================================================
# 配置
# ============================================================
APP_ID = 'cli_a93bb4aca4f85cc9'      # 飞书应用 App ID
APP_SECRET = 'EYrNOBjQIhxfYCs2DMWgzekL48BoZQib'  # 飞书应用 App Secret
USER_TOKEN = ''                  # 用户 Token（从 get_auth_url.py 和 exchange_token.py 获取）

# 如果 USER_TOKEN 为空，从文件读取
if not USER_TOKEN and os.path.exists('.feishu_token'):
    with open('.feishu_token') as f:
        USER_TOKEN = f.read().strip()

OUTPUT_DIR = './feishu_export'
FIG_DIR = './figs'
FILES_DIR = './feishu_files'

# Token → 文件名映射（确保同一 token 使用同一文件名）
TOKEN_FILE_MAP = 'feishu_token_file_map.json'
# ============================================================

# 绕过系统代理（如需要）
import socket
try:
    # 测试连接
    socket.create_connection(('open.feishu.cn', 443), timeout=2)
except:
    os.environ['no_proxy'] = '*'
    os.environ['NO_PROXY'] = '*'

u_headers = {'Authorization': f'Bearer {USER_TOKEN}'}

# Get tenant token for downloads
_r = requests.post('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
                    json={'app_id': APP_ID, 'app_secret': APP_SECRET})
TENANT_TOKEN = _r.json()['tenant_access_token']
t_headers = {'Authorization': f'Bearer {TENANT_TOKEN}'}
print(f'[OK] user_token: {USER_TOKEN[:20]}...')
print(f'[OK] tenant_token: {TENANT_TOKEN[:20]}...')

def sanitize(name, fb='unnamed'):
    name = str(name).strip()
    if not name: return fb
    name = re.sub(r'[\\/:*?"<>|]', '_', name)
    name = re.sub(r'\s+', ' ', name)
    return name.strip('. ') or fb

def unique_path(path):
    if not os.path.exists(path): return path
    n, e = os.path.splitext(path)
    c = 1
    while os.path.exists(f"{n}_{c}{e}"): c += 1
    return f"{n}_{c}{e}"

def extract_filename_from_cd(cd_header):
    """从 Content-Disposition header 提取真实文件名"""
    if not cd_header:
        return None
    # Try filename*=UTF-8''xxx (RFC 5987 encoding)
    m = re.search(r"filename\*=(?:UTF-8''|UTF-8'')(.+?)(?:;|$)", cd_header, re.IGNORECASE)
    if m:
        decoded = urllib.parse.unquote(m.group(1).strip())
        if decoded:
            return decoded
    # Try filename="xxx"
    m = re.search(r'filename="(.+?)"', cd_header, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    # Try filename=xxx (unquoted)
    m = re.search(r'filename=([^\s;"]+)', cd_header, re.IGNORECASE)
    if m:
        return m.group(1).strip().strip('"\'')
    return None

# ============================================================
# 下载：使用随机哈希名称，避免文件名冲突
# ============================================================
_NO_PROXY = {'http': None, 'https': None}

# 全局 token → 文件名映射
_token_file_map = {}

def load_token_map():
    """加载已有的 token → 文件名映射"""
    global _token_file_map
    if os.path.exists(TOKEN_FILE_MAP):
        with open(TOKEN_FILE_MAP, 'r', encoding='utf-8') as f:
            _token_file_map = json.load(f)

def save_token_map():
    """保存 token → 文件名映射"""
    with open(TOKEN_FILE_MAP, 'w', encoding='utf-8') as f:
        json.dump(_token_file_map, f, ensure_ascii=False, indent=2)

def generate_hash_filename(token, ext):
    """生成基于 token 的哈希文件名，确保同一 token 总是生成相同文件名"""
    if token in _token_file_map:
        return _token_file_map[token]
    # 使用 token 的 MD5 前 16 位 + 随机 UUID 后缀
    token_hash = hashlib.md5(token.encode()).hexdigest()[:12]
    random_suffix = uuid.uuid4().hex[:8]
    filename = f"{token_hash}_{random_suffix}.{ext}"
    _token_file_map[token] = filename
    return filename

def download_media(token, ext, save_dir):
    """下载文件/图片，使用哈希文件名"""
    # 检查是否已下载过
    if token in _token_file_map:
        filename = _token_file_map[token]
        filepath = os.path.join(save_dir, filename)
        if os.path.exists(filepath):
            return filename  # 已存在，直接返回

    r = requests.get(
        f'https://open.feishu.cn/open-apis/drive/v1/medias/{token}/download',
        headers=t_headers, stream=True, proxies=_NO_PROXY
    )
    if r.status_code == 200:
        os.makedirs(save_dir, exist_ok=True)
        # 生成哈希文件名
        filename = generate_hash_filename(token, ext)
        filepath = os.path.join(save_dir, filename)

        # 确保文件名唯一
        if os.path.exists(filepath):
            n, e = os.path.splitext(filename)
            c = 1
            while os.path.exists(f"{save_dir}/{n}_{c}{e}"): c += 1
            filename = f"{n}_{c}{e}"
            _token_file_map[token] = filename
            filepath = os.path.join(save_dir, filename)

        with open(filepath, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return filename
    return None

def export_minder_to_image(minder_token, save_dir):
    """
    导出画板/白板为图片
    使用飞书套件导出 API
    """
    global _token_file_map

    # 检查是否已导出过
    if minder_token in _token_file_map:
        filename = _token_file_map[minder_token]
        filepath = os.path.join(save_dir, filename)
        if os.path.exists(filepath):
            return filename

    try:
        # 1. 创建导出任务
        create_url = 'https://open.feishu.cn/open-apis/suite/docs-api/minder/export'
        create_data = {
            "type": "png",
            "minder_token": minder_token
        }
        r = requests.post(create_url, headers=t_headers, json=create_data, proxies=_NO_PROXY)

        if r.status_code != 200:
            print(f"      ⚠️ 画板导出创建任务失败: {r.status_code}")
            return None

        result = r.json()
        if result.get('code') != 0:
            print(f"      ⚠️ 画板导出 API 错误: {result.get('msg')}")
            return None

        task_token = result.get('data', {}).get('task_token')
        if not task_token:
            print(f"      ⚠️ 画板导出任务 token 为空")
            return None

        # 2. 轮询导出状态（最多等待 30 秒）
        status_url = f'https://open.feishu.cn/open-apis/suite/docs-api/minder/export/{task_token}'
        for i in range(30):
            time.sleep(1)
            r = requests.get(status_url, headers=t_headers, proxies=_NO_PROXY)
            result = r.json()

            if result.get('code') != 0:
                break

            status = result.get('data', {}).get('status')
            if status == 'success':
                # 3. 下载导出的图片
                export_token = result.get('data', {}).get('export_token')
                if export_token:
                    filename = download_media(export_token, 'png', save_dir)
                    if filename:
                        _token_file_map[minder_token] = filename
                        return filename
                break
            elif status == 'failed':
                print(f"      ⚠️ 画板导出失败")
                break

    except Exception as e:
        print(f"      ⚠️ 画板导出异常: {e}")

    return None

# ============================================================
# API
# ============================================================
def get_blocks(doc_token):
    r = requests.get(f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}', headers=u_headers, proxies=_NO_PROXY)
    d = r.json()
    if d.get('code') != 0: return None
    rev_id = d['data']['document']['revision_id']
    all_b = {}
    pt = None
    while True:
        p = {'document_revision_id': rev_id, 'page_size': 500}
        if pt: p['page_token'] = pt
        r = requests.get(f'https://open.feishu.cn/open-apis/docx/v1/documents/{doc_token}/blocks', headers=u_headers, params=p, proxies=_NO_PROXY)
        data = r.json().get('data', {})
        for i in data.get('items', []): all_b[i.get('block_id','')] = i
        if not data.get('has_more', False): break
        pt = data.get('page_token')
    return all_b

def get_doc_blocks(doc_token):
    all_b = {}
    pt = None
    while True:
        p = {'page_size': 500}
        if pt: p['page_token'] = pt
        r = requests.get(f'https://open.feishu.cn/open-apis/doc/v2/{doc_token}/blocks', headers=u_headers, params=p, proxies=_NO_PROXY)
        data = r.json().get('data', {})
        if r.json().get('code') != 0: break
        for i in data.get('items', []): all_b[i.get('block_id','')] = i
        if not data.get('has_more', False): break
        pt = data.get('page_token')
    return all_b

# ============================================================
# Block → Markdown
# ============================================================
class Converter:
    def __init__(self, doc_token):
        self.doc_token = doc_token
        self.stats = {'images': 0, 'files': 0, 'file_errors': []}

    def to_md(self, blocks_dict):
        if not blocks_dict: return ""
        root = blocks_dict.get(self.doc_token)
        if not root: return ""
        return self._ids(root.get('children', []), blocks_dict, 0)

    def _ids(self, bids, bd, depth):
        lines = []
        for bid in bids:
            b = bd.get(bid)
            if b:
                r = self._block(b, bd, depth)
                if r: lines.append(r)
        return "\n\n".join(lines).strip()

    def _block(self, b, bd, depth):
        bt = b.get('block_type', 0)
        kids = b.get('children', [])
        indent = "  " * depth
        result = None

        if bt == 1:
            result = None
        elif bt == 2:
            # 正文段落
            t = self._ext(b, 'text')
            result = t if t.strip() else None
        elif bt in (3,4,5,6,7,8):
            # heading1-6
            lv = bt - 2
            t = self._ext(b, f'heading{lv}')
            result = f"{'#'*lv} {t.strip()}" if t.strip() else None
        elif bt == 12:
            t = self._ext(b, 'bullet')
            result = f"{indent}- {t.strip()}" if t.strip() else None
        elif bt == 13:
            t = self._ext(b, 'ordered')
            result = f"{indent}1. {t.strip()}" if t.strip() else None
        elif bt == 14:
            lang = b.get('code',{}).get('language','')
            t = self._ext(b, 'code')
            result = f"```{lang}\n{t.strip()}\n```" if t.strip() else None
        elif bt == 17:
            t = self._ext(b, 'todo')
            if t.strip():
                ch = "x" if b.get('todo',{}).get('done') else " "
                result = f"{indent}- [{ch}] {t.strip()}"
        elif bt == 19:
            e = b.get('callout',{}).get('emoji_id','')
            t = self._ext(b, 'callout')
            if t.strip():
                result = f"> [!NOTE] {e+' ' if e else ''}{t.strip()}"
        elif bt == 23:
            result = self._file_ref(b)
        elif bt == 27:
            result = self._image(b)
        elif bt == 31:
            result = self._table(b, bd)
        elif bt == 502:
            # 画板/白板 (MinderBlock)
            minder_token = b.get('minder', {}).get('minder_token', '')
            if minder_token:
                fn = export_minder_to_image(minder_token, FIG_DIR)
                if fn:
                    self.stats['images'] += 1
                    result = f"![[figs/{fn}]]"
                else:
                    result = f"_[画板导出失败，请在飞书中查看]_"
            else:
                result = f"_[画板，需在飞书中查看]_"
        elif bt in (24, 25):
            kids = b.get('children',[])
            if kids:
                result = self._ids(kids, bd, depth)
        elif bt == 32:
            result = None
        elif bt == 34:
            t = self._ext(b, 'quote_container')
            if t.strip():
                result = "\n".join(f"> {l}" for l in t.strip().split("\n"))
        elif bt == 43:
            result = "_[看板，需在飞书中查看]_"
        else:
            # Fallback: try to extract any text
            for fk in ['text', 'heading1', 'heading2', 'bullet', 'ordered', 'todo']:
                t = self._ext(b, fk)
                if t.strip():
                    result = t
                    break

        if kids:
            child = self._ids(kids, bd, depth+1)
            if result and child: result += "\n\n" + child
            elif child: result = child
        return result

    def _image(self, b):
        t = b.get('image',{}).get('token','')
        if not t: return None
        ext = b.get('image',{}).get('file_extension','png')
        fn = download_media(t, ext, FIG_DIR)
        if fn:
            self.stats['images'] += 1
            return f"![[figs/{fn}]]"
        return f"![图片](feishu://{t})"

    def _file_ref(self, b):
        n = b.get('file',{}).get('name','')
        t = b.get('file',{}).get('token','')
        if not n: return None
        # 文件保留原始名称，但使用 token 哈希避免冲突
        ext = os.path.splitext(n)[1] if '.' in n else ''
        fn = download_media(t, ext, FILES_DIR) if ext else download_media(t, '', FILES_DIR)
        if fn:
            self.stats['files'] += 1
            return f"[[feishu_files/{fn}]]"
        else:
            self.stats['file_errors'].append(n)
            return f"[{n}](feishu-file://{t})"

    def _table(self, b, bd):
        """处理表格 block (新版 docx/v1 API)"""
        # 新版 API：表格是嵌套 blocks 结构
        # table block 包含 table_rows，每个 row 包含 table_cells
        table_data = b.get('table', {})
        children = b.get('children', [])

        if not children:
            # 尝试旧版格式
            cells = table_data.get('cells', [])
            cc = table_data.get('column_size', 0)
            if not cells or not cc:
                return None
            rows, cur = [], []
            for c in cells:
                m = self._ids(c.get('blocks', []), bd, 0)
                cur.append(m.strip().replace("\n", " ") or " ")
                if len(cur) == cc:
                    rows.append(cur)
                    cur = []
            if cur:
                rows.append(cur)
            if not rows:
                return None
            return "\n".join(
                ["| " + " | ".join(rows[0]) + " |", "| " + " | ".join(["---"] * len(rows[0])) + " |"]
                + ["| " + " | ".join(r) + " |" for r in rows[1:]]
            )

        # 新版 API：遍历 table_rows
        rows = []
        for row_id in children:
            row_block = bd.get(row_id, {})
            row_children = row_block.get('children', [])
            cells = []
            for cell_id in row_children:
                cell_block = bd.get(cell_id, {})
                cell_text = self._ids(cell_block.get('children', []), bd, 0)
                cells.append(cell_text.strip().replace("\n", " ") or " ")
            if cells:
                rows.append(cells)

        if not rows:
            return None

        # 生成 Markdown 表格
        header = "| " + " | ".join(rows[0]) + " |"
        separator = "| " + " | ".join(["---"] * len(rows[0])) + " |"
        body = ["| " + " | ".join(r) + " |" for r in rows[1:]]
        return "\n".join([header, separator] + body)

    def _ext(self, b, field_name):
        field = b.get(field_name, {})
        if isinstance(field, dict):
            els = field.get('elements', [])
            if els: return self._proc_els(els)
        return ""

    def _proc_els(self, els):
        parts = []
        for e in els:
            run = e.get('text_run',{})
            if run:
                c = run.get('content','')
                s = run.get('text_element_style',{})
                if s.get('inline_code'): c = f"`{c}`"
                if s.get('italic'): c = f"*{c}*"
                if s.get('bold'): c = f"**{c}**"
                if s.get('strikethrough'): c = f"~~{c}~~"
                if s.get('underline'): c = f"<u>{c}</u>"
                parts.append(c)
                continue
            m = e.get('mention',{})
            if m:
                u = m.get('mention_user',{})
                if u: parts.append(f"@{u.get('name','')}")
                d = m.get('mention_doc',{})
                if d: parts.append(f"[[{d.get('title','文档')}]]")
                continue
            eq = e.get('equation',{})
            if eq: parts.append(f"${eq.get('content','')}$")
        return "".join(parts)

# ============================================================
# 文档收集
# ============================================================
def collect(tree, parent=None):
    if parent is None: parent = []
    docs = []
    for node in tree:
        title = node.get('title','Untitled')
        ot = node.get('obj_type','')
        token = node.get('obj_token','')
        has_child = node.get('has_child', False)
        children = node.get('children',[])
        st = sanitize(title)
        if ot in ('docx','doc'):
            if has_child:
                docs.append({'title':title, 'obj_type':ot, 'obj_token':token,
                            'doc_path':list(parent)+[st], 'filename':'README.md'})
            else:
                docs.append({'title':title, 'obj_type':ot, 'obj_token':token,
                            'doc_path':list(parent), 'filename':f'{st}.md'})
        if children:
            docs.extend(collect(children, list(parent)+[st]))
    return docs

def main():
    print("="*50)
    print("飞书知识库 → Obsidian v12")
    print("="*50)

    # 加载 token → 文件名映射（如果是全新导出则清空）
    load_token_map()

    # 清理旧导出
    for d in [OUTPUT_DIR, FIG_DIR, FILES_DIR]:
        if os.path.exists(d):
            print(f"🗑️  清理: {d}")
            shutil.rmtree(d)
    # 清空 token 映射（全新导出）
    _token_file_map.clear()

    with open('.feishu_tree.json','r',encoding='utf-8') as f:
        tree = json.load(f)

    all_docs = collect(tree)
    print(f"\n📊 总文档: {len(all_docs)}")

    obase = Path(OUTPUT_DIR)
    obase.mkdir(parents=True, exist_ok=True)
    os.makedirs(FIG_DIR, exist_ok=True)
    os.makedirs(FILES_DIR, exist_ok=True)

    print(f"\n📥 开始导出...")
    ok = fail = total_md = 0
    all_file_errors = []

    for i, doc in enumerate(all_docs, 1):
        title = doc['title']
        ot = doc['obj_type']
        token = doc['obj_token']
        dp = doc['doc_path']
        fn = doc['filename']

        dpath = obase
        for p in dp:
            dpath = dpath / p
        dpath.mkdir(parents=True, exist_ok=True)
        fpath = str(dpath / fn)

        if i <= 3 or i % 20 == 0 or i == len(all_docs):
            print(f"  [{i}/{len(all_docs)}] {'📁' if fn=='README.md' else '📄'} {title[:45]}...")

        try:
            blocks_dict = get_blocks(token) if ot == 'docx' else get_doc_blocks(token)
            conv = Converter(token)
            md = conv.to_md(blocks_dict)

            fm = f"---\ntitle: '{title}'\nsource: feishu\ntype: {ot}\nfeishu_token: {token}\nexported_at: {time.strftime('%Y-%m-%d')}\n---\n\n"
            fpath = unique_path(fpath)
            with open(fpath, 'w', encoding='utf-8') as f:
                f.write(fm + md)
            total_md += len(md)
            ok += 1
            if conv.stats['file_errors']:
                all_file_errors.extend(conv.stats['file_errors'])
            if not md and blocks_dict:
                print(f"    ⚠️ 内容为空")
        except Exception as e:
            print(f"    [✗] {e}")
            fail += 1

        if i % 50 == 0: time.sleep(0.5)

    img_count = len([f for f in os.listdir(FIG_DIR) if not f.startswith('.')])
    file_count = len([f for f in os.listdir(FILES_DIR) if not f.startswith('.')])

    # 保存 token → 文件名映射
    save_token_map()

    print(f"\n{'='*50}")
    print(f"✅ 完成!")
    print(f"   文档: {ok} 成功, {fail} 失败")
    print(f"   Markdown: {total_md:,} 字符")
    print(f"   图片: {img_count} 张 → figs/")
    print(f"   文件: {file_count} 个 → feishu_files/")
    print(f"   Token 映射: {TOKEN_FILE_MAP}")
    if all_file_errors:
        print(f"\n⚠️  无法下载的文件 ({len(all_file_errors)} 个):")
        for fe in all_file_errors:
            print(f"   - {fe}")

if __name__ == '__main__':
    main()
