#!/usr/bin/env python3
"""
generate.py - Builds a self-contained SPA from Claude Code docs markdown files.
Run from: scripts/claude-code-docs/
Output: index.html
"""

import re, json
from pathlib import Path
import markdown as md_lib

BASE = Path(__file__).parent

BLOG_CATEGORIES = {
    'multi-agent': [
        'multi-agent-coordination-patterns', 'the-advisor-strategy',
        'claude-managed-agents-memory', 'claude-managed-agents',
        'building-agents-that-reach-production-systems-with-mcp',
    ],
    'product': [
        'claude-code-desktop-redesign', 'introducing-routines-in-claude-code',
        'connectors-for-everyday-life', 'claude-builds-visuals', 'cowork-for-enterprise',
    ],
    'dev': [
        'best-practices-for-using-claude-opus-4-7-with-claude-code',
        'using-claude-code-session-management-and-1m-context', 'seeing-like-an-agent',
        'improving-frontend-design-through-skills',
        'meet-the-winners-of-our-built-with-opus-4-6-claude-code-hackathon',
    ],
    'guide': [
        'harnessing-claudes-intelligence', 'building-ai-agents-in-financial-services',
    ],
    'case': [
        'carta-healthcare-clinical-abstractor',
        'how-enterprises-are-building-ai-agents-in-2026',
    ],
    'security': [
        'preparing-your-security-program-for-ai-accelerated-offense',
    ],
}

CATEGORY_LABELS = {
    'multi-agent': 'Multi-Agent',
    'product': '产品功能',
    'dev': '开发者',
    'guide': '指南',
    'case': '客户案例',
    'security': '安全',
}

DOC_SECTION_LABELS = {
    'getting-started': 'Getting Started',
    'core-concepts': 'Core Concepts',
    'build-with': 'Build With',
    'configuration': 'Configuration',
    'deployment': 'Deployment',
    'administration': 'Administration',
    'outside-terminal': 'Outside Terminal',
    'reference': 'Reference',
    'resources': 'Resources',
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def make_processor():
    return md_lib.Markdown(extensions=['fenced_code', 'tables'])

def slugify(text):
    text = text.lower().strip()
    text = re.sub(r'[一-鿿　-〿＀-￯]+', '-', text)
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    return text.strip('-') or 'heading'

def add_heading_ids(html):
    seen = {}
    def replacer(m):
        tag, inner = m.group(1), m.group(2)
        text = re.sub(r'<[^>]+>', '', inner)
        base = slugify(text)
        count = seen.get(base, 0)
        seen[base] = count + 1
        id_ = f'{base}-{count}' if count else base
        return f'<{tag} id="{id_}">{inner}</{tag}>'
    return re.sub(r'<(h[2-4])>(.*?)</h[2-4]>', replacer, html, flags=re.DOTALL)

def extract_toc(html):
    # Only search headings outside of pre/code blocks
    # Strip pre blocks first to avoid picking up code content
    stripped = re.sub(r'<pre>.*?</pre>', '', html, flags=re.DOTALL)
    toc = []
    for m in re.finditer(r'<(h[2-4]) id="([^"]+)"[^>]*>(.*?)</h[2-4]>', stripped, re.DOTALL):
        tag, id_, inner = m.group(1), m.group(2), m.group(3)
        text = re.sub(r'<[^>]+>', '', inner).strip()
        # Skip entries that look like code fence artifacts (start with backtick)
        if text.startswith('`'):
            continue
        # Skip very long headings (likely garbled content)
        if len(text) > 80:
            continue
        toc.append({'level': int(tag[1]), 'id': id_, 'text': text})
    return toc

def clean_content(content):
    # Remove {theme=...} and similar MDX-style attributes from code fences
    content = re.sub(r'```(\w+)\s*\{[^}]*\}', r'```\1', content)
    # Remove BOM
    content = content.lstrip('﻿')
    return content

def convert_to_html(content):
    content = clean_content(content)
    proc = make_processor()
    html = proc.convert(content)
    html = add_heading_ids(html)
    return html

def infer_blog_category(slug):
    for cat, slugs in BLOG_CATEGORIES.items():
        if any(s in slug for s in slugs):
            return cat
    return 'guide'

def extract_blog_meta(content):
    url, date = '', ''
    m = re.search(r'原文链接:\s*(https?://\S+)', content)
    if m: url = m.group(1).strip().rstrip(')')
    m = re.search(r'发布日期:\s*([^\n\r]+)', content)
    if m: date = m.group(1).strip()
    return url, date

def extract_first_h1(content):
    m = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
    return m.group(1).strip() if m else ''

def extract_first_para(html):
    # Remove blockquotes (metadata headers) before searching for first paragraph
    stripped = re.sub(r'<blockquote>.*?</blockquote>', '', html, flags=re.DOTALL)
    # Also skip the h1
    stripped = re.sub(r'<h1[^>]*>.*?</h1>', '', stripped, flags=re.DOTALL)
    m = re.search(r'<p>(.*?)</p>', stripped, re.DOTALL)
    if m:
        text = re.sub(r'<[^>]+>', '', m.group(1)).strip()
        return text[:130] + ('…' if len(text) > 130 else '')
    return ''

# ── Loaders ────────────────────────────────────────────────────────────────────

def load_blogs():
    articles = []
    for fp in sorted((BASE / 'blogs' / 'content').glob('*.zh.md')):
        content = fp.read_text(encoding='utf-8-sig')
        slug = fp.name.replace('.zh.md', '')
        url, date = extract_blog_meta(content)
        title = extract_first_h1(content)
        html = convert_to_html(content)
        toc = extract_toc(html)
        snippet = extract_first_para(html)
        articles.append({
            'id': f'blog-{slug}',
            'slug': slug,
            'title': title or slug,
            'date': date,
            'url': url,
            'section': 'blog',
            'category': infer_blog_category(slug),
            'lang': 'zh',
            'toc': toc,
            'snippet': snippet,
            'html': html,
        })
        print(f'  blog: {title[:50] if title else slug}')
    return articles

def load_docs():
    articles = []
    # translated/ overrides getting-started/{overview,changelog}
    translated_overrides = {}
    for fp in (BASE / 'translated').glob('*.md'):
        translated_overrides[fp.stem] = fp

    for section in DOC_SECTION_LABELS:
        section_dir = BASE / 'docs-cleaned' / section
        if not section_dir.exists():
            continue
        for fp in sorted(section_dir.glob('*.md')):
            # skip fragmented files (clean1-8, zh1-8 etc.)
            if re.match(r'^(clean|zh)\d+$', fp.stem):
                continue
            # use translated version if available
            actual_fp = translated_overrides.get(fp.stem, fp)
            content = actual_fp.read_text(encoding='utf-8-sig')
            slug = fp.stem
            title = extract_first_h1(content) or slug.replace('-', ' ').title()
            html = convert_to_html(content)
            toc = extract_toc(html)
            snippet = extract_first_para(html)
            lang = 'zh' if actual_fp in translated_overrides.values() else 'en'
            articles.append({
                'id': f'docs-{section}-{slug}',
                'slug': slug,
                'title': title,
                'date': '',
                'url': '',
                'section': f'docs-{section}',
                'category': section,
                'lang': lang,
                'toc': toc,
                'snippet': snippet,
                'html': html,
            })
            print(f'  docs/{section}: {title[:50]}')
    return articles

# ── HTML Template ──────────────────────────────────────────────────────────────

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,600;0,700;1,400;1,600&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&family=Lora:ital,wght@0,400;0,500;1,400&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --bg: #06080C;
  --surface: #0B0E14;
  --surface2: #111620;
  --surface3: #181E2A;
  --border: #1C2333;
  --border2: #252E40;
  --text: #C8D4E8;
  --text-muted: #5A6880;
  --text-faint: #2E3A4C;
  --accent: #F09040;
  --accent-dim: rgba(240,144,64,0.08);
  --c-multi: #A78BFA;
  --c-product: #60A5FA;
  --c-dev: #34D399;
  --c-guide: #FBBF24;
  --c-case: #22D3EE;
  --c-security: #F87171;
  --sidebar-w: 216px;
  --toc-w: 224px;
  --reader-max: 700px;
  --topbar-h: 56px;
}
*{margin:0;padding:0;box-sizing:border-box;}
html{scroll-behavior:smooth;}
body{background:var(--bg);color:var(--text);font-family:'Plus Jakarta Sans','PingFang SC',sans-serif;font-size:14px;line-height:1.7;min-height:100vh;-webkit-font-smoothing:antialiased;}

/* ── Topbar ── */
.topbar{position:sticky;top:0;z-index:200;background:rgba(6,8,12,0.92);backdrop-filter:blur(12px);border-bottom:1px solid var(--border);display:flex;align-items:center;gap:20px;padding:0 28px;height:var(--topbar-h);}
.logo{display:flex;align-items:center;gap:11px;flex-shrink:0;}
.logo-mark{width:26px;height:26px;display:flex;align-items:center;justify-content:center;}
.logo-mark svg{width:26px;height:26px;}
.logo-text{font-family:'Cormorant Garamond',Georgia,serif;font-size:17px;font-weight:600;letter-spacing:0.3px;color:var(--text);}
.logo-sep{color:var(--text-faint);font-size:16px;font-weight:300;}
.logo-sub{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-faint);letter-spacing:0.5px;}
.search-wrap{flex:1;max-width:280px;position:relative;}
.search-wrap input{width:100%;background:var(--surface2);border:1px solid var(--border);border-radius:6px;color:var(--text);font-family:'Plus Jakarta Sans',sans-serif;font-size:13px;padding:7px 12px 7px 32px;outline:none;transition:border-color .2s,background .2s;}
.search-wrap input:focus{border-color:rgba(240,144,64,.4);background:var(--surface3);}
.search-wrap input::placeholder{color:var(--text-faint);}
.search-wrap svg{position:absolute;left:10px;top:50%;transform:translateY(-50%);opacity:.3;}
.topbar-stats{margin-left:auto;display:flex;align-items:center;gap:24px;}
.stat{text-align:right;}
.stat-num{font-family:'Cormorant Garamond',serif;font-size:22px;font-weight:600;color:var(--accent);line-height:1;letter-spacing:-0.5px;}
.stat-lbl{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-faint);text-transform:uppercase;letter-spacing:1px;margin-top:1px;}

/* ── Reader topbar ── */
.reader-bar{display:none;align-items:center;gap:14px;}
.topbar.reader-mode .list-bar{display:none;}
.topbar.reader-mode .reader-bar{display:flex;flex:1;}
.back-btn{display:flex;align-items:center;gap:7px;color:var(--text-muted);font-size:12px;font-weight:500;cursor:pointer;background:none;border:none;padding:5px 10px;border-radius:5px;transition:background .12s,color .15s;flex-shrink:0;letter-spacing:0.2px;}
.back-btn:hover{background:var(--surface2);color:var(--text);}
.back-btn svg{opacity:.6;}
.reader-title{font-family:'Cormorant Garamond',serif;font-size:16px;font-weight:600;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;letter-spacing:0.1px;}
.reader-meta{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-faint);flex-shrink:0;letter-spacing:0.5px;}

/* ── Layout ── */
.layout{display:grid;grid-template-columns:var(--sidebar-w) 1fr;min-height:calc(100vh - var(--topbar-h));}

/* ── Sidebar ── */
aside{background:var(--surface);border-right:1px solid var(--border);position:sticky;top:var(--topbar-h);height:calc(100vh - var(--topbar-h));overflow-y:auto;padding:20px 0 32px;}
aside::-webkit-scrollbar{width:3px;}
aside::-webkit-scrollbar-thumb{background:var(--border);}
.nav-group{margin-bottom:6px;}
.nav-group-label{font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:500;text-transform:uppercase;letter-spacing:1.5px;color:var(--text-faint);padding:12px 18px 6px;}
.nav-item{display:flex;align-items:center;gap:9px;padding:6px 18px;cursor:pointer;color:var(--text-muted);font-size:12px;font-weight:400;border-left:1.5px solid transparent;transition:color .15s,background .15s,border-left-color .15s;user-select:none;}
.nav-item:hover{background:rgba(240,144,64,.03);color:var(--text);border-left-color:var(--border2);}
.nav-item.active{background:var(--accent-dim);color:var(--accent);border-left-color:var(--accent);}
.nav-dot{width:6px;height:6px;border-radius:50%;flex-shrink:0;opacity:.85;}
.nav-count{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-faint);padding:0 5px;}
.nav-divider{height:1px;background:var(--border);margin:10px 14px;}

/* ── Main ── */
main{padding:32px 40px 64px;min-width:0;}

/* ── Section heading ── */
.sec-head{display:flex;align-items:center;gap:12px;margin-bottom:24px;padding-bottom:14px;border-bottom:1px solid var(--border);}
.sec-title{font-family:'Cormorant Garamond',serif;font-size:20px;font-weight:600;letter-spacing:0.2px;color:var(--text);}
.sec-path{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-faint);background:var(--surface2);border:1px solid var(--border);padding:2px 8px;border-radius:3px;}
.sec-meta{margin-left:auto;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-faint);}

/* ── Blog cards ── */
.blog-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:1px;background:var(--border);}
.card{background:var(--bg);padding:0;cursor:pointer;transition:background .18s;display:block;position:relative;overflow:hidden;}
.card:hover{background:var(--surface);}
.card.hidden{display:none;}
.card-inner{padding:22px 22px 18px;}
.card-accent{height:2px;width:0;transition:width .35s cubic-bezier(.16,1,.3,1);}
.card:hover .card-accent{width:100%;}
.c-multi-agent{background:var(--c-multi);}
.c-product{background:var(--c-product);}
.c-dev{background:var(--c-dev);}
.c-guide{background:var(--c-guide);}
.c-case{background:var(--c-case);}
.c-security{background:var(--c-security);}
.card-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:13px;}
.card-cat{font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:500;text-transform:uppercase;letter-spacing:1.2px;}
.card-arrow{font-size:13px;color:var(--text-faint);transition:color .15s,transform .2s;}
.card:hover .card-arrow{color:var(--text-muted);transform:translate(2px,-2px);}
.card-title{font-family:'Cormorant Garamond',serif;font-size:19px;font-weight:600;line-height:1.32;color:var(--text);margin-bottom:10px;letter-spacing:0.1px;}
.card-snippet{font-size:12px;color:var(--text-muted);line-height:1.65;margin-bottom:14px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}
.card-date{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-faint);letter-spacing:0.5px;}

/* ── Doc list ── */
.doc-cat-head{font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:500;text-transform:uppercase;letter-spacing:1.5px;color:var(--text-faint);margin:28px 0 10px;display:flex;align-items:center;gap:10px;}
.doc-cat-head::after{content:'';flex:1;height:1px;background:var(--border);}
.doc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:1px;background:var(--border);border:1px solid var(--border);}
.doc-item{display:flex;align-items:center;justify-content:space-between;background:var(--bg);padding:12px 16px;cursor:pointer;transition:background .15s;}
.doc-item:hover{background:var(--surface2);}
.doc-item.hidden{display:none;}
.doc-item-left{display:flex;align-items:center;gap:10px;min-width:0;}
.doc-item-dot{width:5px;height:5px;border-radius:50%;flex-shrink:0;}
.doc-item-name{font-size:12px;font-weight:500;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}
.doc-item-arr{font-size:11px;color:var(--text-faint);flex-shrink:0;transition:color .15s,transform .2s;}
.doc-item:hover .doc-item-arr{color:var(--text-muted);transform:translateX(2px);}
.section-hidden{display:none;}

/* ── Reader ── */
#reader-view{display:none;grid-template-columns:var(--toc-w) 1fr;gap:0;}
#reader-view.active{display:grid;}
.toc-panel{padding:28px 0;position:sticky;top:var(--topbar-h);height:calc(100vh - var(--topbar-h));overflow-y:auto;border-right:1px solid var(--border);background:var(--surface);}
.toc-panel::-webkit-scrollbar{width:3px;}
.toc-panel::-webkit-scrollbar-thumb{background:var(--border);}
.toc-label{font-family:'JetBrains Mono',monospace;font-size:9px;font-weight:500;text-transform:uppercase;letter-spacing:1.5px;color:var(--text-faint);padding:0 18px 12px;display:block;}
.toc-item{display:block;padding:5px 18px;font-size:11px;color:var(--text-muted);font-weight:400;cursor:pointer;transition:color .12s,background .12s;line-height:1.45;text-decoration:none;border-left:1.5px solid transparent;}
.toc-item:hover{color:var(--text);background:rgba(255,255,255,.02);}
.toc-item.active{color:var(--accent);border-left-color:var(--accent);}
.toc-item.level-3{padding-left:30px;font-size:10.5px;}
.toc-item.level-4{padding-left:42px;font-size:10px;color:var(--text-faint);}
.article-scroll{padding:44px 56px 80px;max-width:calc(var(--reader-max) + 112px);overflow-y:auto;max-height:calc(100vh - var(--topbar-h));}
.article-scroll::-webkit-scrollbar{width:4px;}
.article-scroll::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px;}

/* ── Article typography ── */
.article-content{max-width:var(--reader-max);}
.article-content h1{font-family:'Cormorant Garamond',serif;font-size:36px;font-weight:700;line-height:1.2;color:var(--text);margin-bottom:16px;letter-spacing:0.2px;}
.article-content h2{font-family:'Cormorant Garamond',serif;font-size:24px;font-weight:600;color:var(--text);margin:44px 0 14px;letter-spacing:0.1px;}
.article-content h2::before{content:'';display:block;width:28px;height:1.5px;background:var(--accent);margin-bottom:12px;opacity:.7;}
.article-content h3{font-family:'Plus Jakarta Sans',sans-serif;font-size:15px;font-weight:600;color:var(--text);margin:28px 0 10px;letter-spacing:-.1px;}
.article-content h4{font-family:'JetBrains Mono',monospace;font-size:11px;font-weight:500;color:var(--text-muted);margin:20px 0 8px;text-transform:uppercase;letter-spacing:1px;}
.article-content p{margin-bottom:18px;color:var(--text);line-height:1.85;font-size:15px;font-family:'Lora',Georgia,serif;}
.article-content ul,.article-content ol{margin:0 0 18px 22px;font-family:'Lora',Georgia,serif;font-size:15px;}
.article-content li{margin-bottom:7px;line-height:1.75;color:var(--text);}
.article-content li>ul,.article-content li>ol{margin-top:7px;margin-bottom:0;}
.article-content strong{font-weight:700;color:var(--text);}
.article-content em{font-style:italic;color:inherit;}
.article-content a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(240,144,64,.25);}
.article-content a:hover{border-bottom-color:var(--accent);}
.article-content blockquote{border-left:2px solid var(--accent);padding:12px 20px;margin:20px 0;color:var(--text-muted);background:rgba(240,144,64,.04);font-style:italic;}
.article-content blockquote p{margin-bottom:5px;color:var(--text-muted);font-size:14px;}
.article-content blockquote p:last-child{margin-bottom:0;}
.article-content blockquote strong{color:var(--text);}
.article-content hr{border:none;border-top:1px solid var(--border);margin:36px 0;}
.article-content img{max-width:100%;border-radius:6px;display:block;margin:24px auto;box-shadow:0 4px 24px rgba(0,0,0,.4);}
.article-content code{font-family:'JetBrains Mono',monospace;font-size:12.5px;background:var(--surface2);border:1px solid var(--border2);padding:1px 6px;border-radius:3px;color:#A9C8E8;}
.article-content pre{background:#0A0E14;border:1px solid var(--border2);border-radius:6px;padding:20px 22px;overflow-x:auto;margin:20px 0;position:relative;}
.article-content pre::before{content:'';display:block;width:6px;height:6px;border-radius:50%;background:rgba(240,144,64,.5);position:absolute;top:10px;right:14px;}
.article-content pre::-webkit-scrollbar{height:3px;}
.article-content pre::-webkit-scrollbar-thumb{background:var(--border2);}
.article-content pre code{background:none;border:none;padding:0;font-size:13px;line-height:1.7;color:#B8C8D8;}
.article-content table{width:100%;border-collapse:collapse;margin:20px 0;font-size:13.5px;}
.article-content th{background:var(--surface2);border:1px solid var(--border2);padding:10px 14px;text-align:left;font-family:'Plus Jakarta Sans',sans-serif;font-weight:600;font-size:12px;color:var(--text);letter-spacing:.1px;}
.article-content td{border:1px solid var(--border);padding:9px 14px;color:var(--text-muted);font-family:'Plus Jakarta Sans',sans-serif;font-size:13px;line-height:1.5;}
.article-content tr:nth-child(even) td{background:var(--surface);}
.article-content tr:hover td{background:var(--surface2);}

/* ── Article nav ── */
.article-nav{display:flex;justify-content:space-between;align-items:stretch;gap:12px;margin-top:56px;padding-top:24px;border-top:1px solid var(--border);}
.art-nav-btn{display:flex;flex-direction:column;gap:4px;cursor:pointer;padding:14px 18px;background:var(--surface);border:1px solid var(--border);transition:border-color .15s,background .15s;max-width:280px;flex:1;}
.art-nav-btn:hover{border-color:var(--border2);background:var(--surface2);}
.art-nav-btn.next{text-align:right;align-items:flex-end;}
.art-nav-label{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-faint);text-transform:uppercase;letter-spacing:1px;}
.art-nav-title{font-family:'Cormorant Garamond',serif;font-size:15px;font-weight:600;color:var(--text);line-height:1.3;}

/* ── Load animation ── */
@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
.card{animation:fadeUp .4s ease both;}
.card:nth-child(1){animation-delay:.05s}
.card:nth-child(2){animation-delay:.09s}
.card:nth-child(3){animation-delay:.13s}
.card:nth-child(4){animation-delay:.17s}
.card:nth-child(5){animation-delay:.21s}
.card:nth-child(6){animation-delay:.25s}
.card:nth-child(n+7){animation-delay:.28s}

/* ── No results ── */
.no-results{color:var(--text-faint);font-family:'JetBrains Mono',monospace;font-size:12px;padding:24px 0;display:none;}
.no-results.visible{display:block;}

::-webkit-scrollbar{width:5px;}
::-webkit-scrollbar-track{background:transparent;}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:2px;}
::-webkit-scrollbar-thumb:hover{background:var(--border2);}
"""

APP_JS = r"""
const LIST_VIEW = document.getElementById('list-view');
const READER_VIEW = document.getElementById('reader-view');
const TOPBAR = document.querySelector('.topbar');
const LIST_BAR = document.querySelector('.list-bar');

let currentId = null;
let articleIndex = [];

function init() {
  articleIndex = ARTICLES.map(a => a.id);
  renderNavCounts();
  // handle hash on load
  const hash = location.hash.slice(1);
  if (hash && ARTICLES.find(a => a.id === hash)) {
    openArticle(hash, false);
  }
}

function renderNavCounts() {
  document.querySelectorAll('[data-count-section]').forEach(el => {
    const sec = el.dataset.countSection;
    const count = ARTICLES.filter(a => a.section === sec || a.section.startsWith(sec)).length;
    el.textContent = count;
  });
}

// ── List view ──────────────────────────────────────────────────────────────────

function filterSection(sec, el) {
  // Scroll to section if it's a doc section
  const target = document.getElementById('sec-' + sec);
  if (target) {
    target.scrollIntoView({behavior: 'smooth'});
    setNavActive(el);
    return;
  }
  setNavActive(el);
}

function filterTag(tag, el) {
  setNavActive(el);
  document.querySelectorAll('.card').forEach(c => {
    if (tag === 'all') c.classList.remove('hidden');
    else c.classList.toggle('hidden', c.dataset.cat !== tag);
  });
  // reset doc grid visibility
  document.querySelectorAll('.doc-item').forEach(c => c.classList.remove('hidden'));
  document.querySelectorAll('.doc-section-group').forEach(s => s.classList.remove('section-hidden'));
  document.getElementById('search-input').value = '';
}

function setNavActive(el) {
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  if (el) el.classList.add('active');
}

function handleSearch(q) {
  const query = q.toLowerCase().trim();
  let blogVisible = 0, docVisible = 0;
  document.querySelectorAll('.card').forEach(c => {
    const match = !query || c.dataset.search.includes(query);
    c.classList.toggle('hidden', !match);
    if (match) blogVisible++;
  });
  document.querySelectorAll('.doc-item').forEach(c => {
    const match = !query || c.dataset.search.includes(query);
    c.classList.toggle('hidden', !match);
    if (match) docVisible++;
  });
  // hide empty doc section groups
  document.querySelectorAll('.doc-section-group').forEach(g => {
    const anyVisible = [...g.querySelectorAll('.doc-item')].some(i => !i.classList.contains('hidden'));
    g.classList.toggle('section-hidden', !anyVisible);
  });
  document.querySelectorAll('.no-results').forEach(el => el.classList.remove('visible'));
  if (query) {
    if (!blogVisible) document.getElementById('no-results-blog') && document.getElementById('no-results-blog').classList.add('visible');
    if (!docVisible) document.getElementById('no-results-doc') && document.getElementById('no-results-doc').classList.add('visible');
  }
  setNavActive(null);
}

// ── Reader view ────────────────────────────────────────────────────────────────

function openArticle(id, pushState = true) {
  const art = ARTICLES.find(a => a.id === id);
  if (!art) return;
  currentId = id;

  // switch views
  LIST_VIEW.style.display = 'none';
  READER_VIEW.classList.add('active');
  TOPBAR.classList.add('reader-mode');

  // render topbar
  document.getElementById('reader-title').textContent = art.title;
  document.getElementById('reader-meta').textContent = art.date || (art.lang === 'en' ? 'Documentation' : '');

  // render toc
  const tocEl = document.getElementById('toc-list');
  if (art.toc && art.toc.length > 2) {
    tocEl.innerHTML = '<div class="toc-label">目录</div>' +
      art.toc.map(t =>
        `<a class="toc-item level-${t.level}" href="#${t.id}" onclick="tocClick(event,this,'${t.id}')">${escapeHtml(t.text)}</a>`
      ).join('');
    document.getElementById('toc-panel').style.display = '';
    READER_VIEW.style.gridTemplateColumns = 'var(--toc-w) 1fr';
  } else {
    tocEl.innerHTML = '';
    document.getElementById('toc-panel').style.display = 'none';
    READER_VIEW.style.gridTemplateColumns = '0 1fr';
  }

  // render content
  document.getElementById('article-body').innerHTML = art.html;

  // render prev/next
  const idx = articleIndex.indexOf(id);
  const prevArt = idx > 0 ? ARTICLES.find(a => a.id === articleIndex[idx-1]) : null;
  const nextArt = idx < articleIndex.length-1 ? ARTICLES.find(a => a.id === articleIndex[idx+1]) : null;
  document.getElementById('prev-btn').innerHTML = prevArt
    ? `<div class="art-nav-label">← 上一篇</div><div class="art-nav-title">${escapeHtml(prevArt.title)}</div>`
    : '';
  document.getElementById('next-btn').innerHTML = nextArt
    ? `<div class="art-nav-label">下一篇 →</div><div class="art-nav-title">${escapeHtml(nextArt.title)}</div>`
    : '';
  if (prevArt) document.getElementById('prev-btn').onclick = () => openArticle(prevArt.id);
  if (nextArt) document.getElementById('next-btn').onclick = () => openArticle(nextArt.id);

  // scroll top
  document.getElementById('article-scroll').scrollTop = 0;

  if (pushState) history.pushState({id}, '', '#' + id);
  setupScrollSpy();
}

function backToList() {
  LIST_VIEW.style.display = '';
  READER_VIEW.classList.remove('active');
  TOPBAR.classList.remove('reader-mode');
  currentId = null;
  history.pushState({}, '', location.pathname);
}

function tocClick(e, el, id) {
  e.preventDefault();
  const target = document.getElementById(id);
  if (target) {
    document.getElementById('article-scroll').scrollTo({top: target.offsetTop - 20, behavior: 'smooth'});
  }
  document.querySelectorAll('.toc-item').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
}

function setupScrollSpy() {
  const scroll = document.getElementById('article-scroll');
  const tocItems = document.querySelectorAll('.toc-item');
  if (!tocItems.length) return;
  scroll.onscroll = () => {
    const scrollTop = scroll.scrollTop;
    let current = null;
    document.querySelectorAll('.article-content h2,.article-content h3,.article-content h4').forEach(h => {
      if (h.offsetTop - 60 <= scrollTop) current = h.id;
    });
    tocItems.forEach(t => {
      const href = t.getAttribute('href');
      t.classList.toggle('active', href === '#' + current);
    });
  };
}

function escapeHtml(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

window.addEventListener('popstate', e => {
  if (e.state && e.state.id) openArticle(e.state.id, false);
  else backToList();
});

document.addEventListener('DOMContentLoaded', init);
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Claude Code 知识库</title>
<style>{css}</style>
</head>
<body>

<!-- Topbar -->
<header class="topbar">
  <div class="logo">
    <div class="logo-mark">
      <svg viewBox="0 0 26 26" fill="none"><rect x="1" y="1" width="24" height="24" rx="5" stroke="#F09040" stroke-width="1.2"/><path d="M8 18V8h4a4 4 0 0 1 0 8H8" stroke="#F09040" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/><path d="M12 13h4" stroke="#F09040" stroke-width="1.2" stroke-linecap="round"/></svg>
    </div>
    <span class="logo-text">Claude Code</span>
    <span class="logo-sep">/</span>
    <span class="logo-sub">知识库</span>
  </div>

  <div class="list-bar" style="display:flex;align-items:center;gap:20px;flex:1;">
    <div class="search-wrap">
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><circle cx="5.5" cy="5.5" r="4" stroke="currentColor" stroke-width="1.2"/><path d="M9 9l2.5 2.5" stroke="currentColor" stroke-width="1.2" stroke-linecap="round"/></svg>
      <input type="text" id="search-input" placeholder="搜索文章或文档…" oninput="handleSearch(this.value)">
    </div>
    <div class="topbar-stats">
      <div class="stat"><div class="stat-num">{blog_count}</div><div class="stat-lbl">博客</div></div>
      <div class="stat"><div class="stat-num">{doc_count}</div><div class="stat-lbl">文档</div></div>
    </div>
  </div>

  <div class="reader-bar">
    <button class="back-btn" onclick="backToList()">
      <svg width="13" height="13" viewBox="0 0 13 13" fill="none"><path d="M8 2L3 6.5l5 4.5" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
      返回
    </button>
    <div id="reader-title" class="reader-title"></div>
    <div id="reader-meta" class="reader-meta"></div>
  </div>
</header>

<div class="layout">

<!-- Sidebar -->
<aside id="sidebar">
  <div class="nav-group">
    <div class="nav-group-label">博客</div>
    <div class="nav-item active" onclick="filterTag('all',this)">
      <span class="nav-dot" style="background:var(--accent)"></span>
      全部文章
      <span class="nav-count">{blog_count}</span>
    </div>
    <div class="nav-item" onclick="filterTag('multi-agent',this)">
      <span class="nav-dot" style="background:var(--purple)"></span>
      Multi-Agent
    </div>
    <div class="nav-item" onclick="filterTag('product',this)">
      <span class="nav-dot" style="background:var(--blue)"></span>
      产品功能
    </div>
    <div class="nav-item" onclick="filterTag('dev',this)">
      <span class="nav-dot" style="background:var(--green)"></span>
      开发者
    </div>
    <div class="nav-item" onclick="filterTag('guide',this)">
      <span class="nav-dot" style="background:var(--orange)"></span>
      指南
    </div>
    <div class="nav-item" onclick="filterTag('case',this)">
      <span class="nav-dot" style="background:var(--teal)"></span>
      客户案例
    </div>
    <div class="nav-item" onclick="filterTag('security',this)">
      <span class="nav-dot" style="background:var(--red)"></span>
      安全
    </div>
  </div>
  <div class="nav-divider"></div>
  <div class="nav-group">
    <div class="nav-group-label">文档</div>
    {doc_nav}
  </div>
</aside>

<!-- Main content area -->
<div style="min-width:0">

  <!-- List view -->
  <div id="list-view">
    <main>

      <!-- Blog section -->
      <section style="margin-bottom:40px" id="sec-blog">
        <div class="sec-head">
          <h2 class="sec-title">博客文章</h2>
          <span class="sec-path">blogs/content/*.zh.md</span>
          <span class="sec-meta">{blog_count} 篇 · 中文</span>
        </div>
        <div class="blog-grid" id="blog-grid">
          {blog_cards}
        </div>
        <div class="no-results" id="no-results-blog">没有找到匹配的博客文章</div>
      </section>

      <!-- Docs section -->
      <section id="sec-docs">
        <div class="sec-head">
          <h2 class="sec-title">官方文档</h2>
          <span class="sec-path">docs-cleaned/</span>
          <span class="sec-meta">{doc_count} 页 · 英文</span>
        </div>
        {doc_groups}
        <div class="no-results" id="no-results-doc">没有找到匹配的文档页面</div>
      </section>

    </main>
  </div>

  <!-- Reader view -->
  <div id="reader-view">
    <div id="toc-panel" class="toc-panel">
      <div id="toc-list"></div>
    </div>
    <div id="article-scroll" class="article-scroll">
      <article class="article-content" id="article-body"></article>
      <nav class="article-nav">
        <div class="art-nav-btn" id="prev-btn"></div>
        <div class="art-nav-btn next" id="next-btn"></div>
      </nav>
    </div>
  </div>

</div>
</div>

<script>
const ARTICLES = {articles_json};
{app_js}
</script>
</body>
</html>"""

# ── Card/item renderers ─────────────────────────────────────────────────────────

CAT_COLORS = {
    'multi-agent': 'var(--c-multi)',
    'product': 'var(--c-product)',
    'dev': 'var(--c-dev)',
    'guide': 'var(--c-guide)',
    'case': 'var(--c-case)',
    'security': 'var(--c-security)',
}

def render_blog_card(art):
    cat = art['category']
    cat_label = CATEGORY_LABELS.get(cat, cat).upper()
    color = CAT_COLORS.get(cat, 'var(--accent)')
    return (
        f'<div class="card" data-cat="{cat}" '
        f'data-search="{art["title"].lower()} {art["snippet"].lower()}" '
        f'onclick="openArticle(\'{art["id"]}\')">'
        f'<div class="card-accent c-{cat}"></div>'
        f'<div class="card-inner">'
        f'<div class="card-header">'
        f'<span class="card-cat" style="color:{color}">{cat_label}</span>'
        f'<span class="card-arrow">↗</span>'
        f'</div>'
        f'<div class="card-title">{art["title"]}</div>'
        f'<div class="card-snippet">{art["snippet"]}</div>'
        f'<div class="card-date">{art["date"]}</div>'
        f'</div></div>'
    )

DOC_SECTION_COLORS = {
    'getting-started': 'var(--c-dev)',
    'core-concepts': 'var(--c-product)',
    'build-with': 'var(--c-multi)',
    'configuration': 'var(--c-guide)',
    'deployment': 'var(--c-case)',
    'administration': 'var(--accent)',
    'outside-terminal': 'var(--c-dev)',
    'reference': 'var(--c-security)',
    'resources': 'var(--text-faint)',
}

def render_doc_item(art):
    color = DOC_SECTION_COLORS.get(art['category'], 'var(--text-faint)')
    return (
        f'<div class="doc-item" '
        f'data-search="{art["title"].lower()} {art["slug"].lower()}" '
        f'onclick="openArticle(\'{art["id"]}\')">'
        f'<div class="doc-item-left">'
        f'<span class="doc-item-dot" style="background:{color}"></span>'
        f'<span class="doc-item-name">{art["title"]}</span>'
        f'</div>'
        f'<span class="doc-item-arr">→</span>'
        f'</div>'
    )

def render_doc_section_nav(section, count):
    label = DOC_SECTION_LABELS.get(section, section.title())
    color = DOC_SECTION_COLORS.get(section, 'var(--text-faint)')
    return (
        f'<div class="nav-item" onclick="filterSection(\'docs-{section}\',this)">'
        f'<span class="nav-dot" style="background:{color}"></span>'
        f'{label}'
        f'<span class="nav-count">{count}</span>'
        f'</div>'
    )

# ── Builder ─────────────────────────────────────────────────────────────────────

def build():
    print('Loading blog articles...')
    blog_arts = load_blogs()
    print(f'  → {len(blog_arts)} articles\n')

    print('Loading docs...')
    doc_arts = load_docs()
    print(f'  → {len(doc_arts)} pages\n')

    all_articles = blog_arts + doc_arts

    # Blog cards HTML
    blog_cards_html = '\n'.join(render_blog_card(a) for a in blog_arts)

    # Doc groups HTML
    doc_groups_html = ''
    doc_nav_html = ''
    sections_seen = []
    SEC_COLORS = {
        'getting-started': '#6fcf97', 'core-concepts': '#7eb8e8',
        'build-with': '#b89af5', 'configuration': '#f0a060',
        'deployment': '#5dcfcf', 'administration': '#d4a574',
        'outside-terminal': '#6fcf97', 'reference': '#f28b82',
        'resources': '#8888aa',
    }
    for section in DOC_SECTION_LABELS:
        arts = [a for a in doc_arts if a['section'] == f'docs-{section}']
        if not arts:
            continue
        sections_seen.append(section)
        label = DOC_SECTION_LABELS[section]
        color = SEC_COLORS.get(section, '#888')
        items_html = '\n'.join(render_doc_item(a) for a in arts)
        doc_groups_html += (
            f'<div class="doc-section-group" id="sec-docs-{section}">\n'
            f'<div class="doc-cat-head" style="color:{color}">{label}</div>\n'
            f'<div class="doc-grid">{items_html}</div>\n</div>\n'
        )
        doc_nav_html += render_doc_section_nav(section, len(arts))

    # Serialize articles (without html for non-current, but we need to keep html)
    # For performance, include html for all (it's pre-rendered)
    # Escape </script> so it doesn't prematurely close the <script> block in HTML
    articles_json = json.dumps(all_articles, ensure_ascii=False).replace('</script>', '<\\/script>').replace('<!--', '<\\!--')

    html = HTML_TEMPLATE.format(
        css=CSS,
        blog_count=len(blog_arts),
        doc_count=len(doc_arts),
        blog_cards=blog_cards_html,
        doc_groups=doc_groups_html,
        doc_nav=doc_nav_html,
        articles_json=articles_json,
        app_js=APP_JS,
    )

    out = BASE / 'index.html'
    out.write_text(html, encoding='utf-8')
    size_mb = out.stat().st_size / 1024 / 1024
    print(f'\nGenerated: {out}')
    print(f'File size: {size_mb:.1f} MB')
    print(f'Total articles: {len(all_articles)} ({len(blog_arts)} blog + {len(doc_arts)} docs)')

if __name__ == '__main__':
    build()
