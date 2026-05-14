# Claude Code 知识库

> 35 篇官方博客文章 + 50 页技术文档，整合为一个自包含的可阅读 SPA。

**在线阅读 →** https://viy1204.github.io/claude-code-docs/

---

## 内容

### 博客文章（中文译版）

抓取自 [claude.com/blog](https://claude.com/blog)，涵盖 6 个主题，共 35 篇：

| 分类 | 代表文章 |
|---|---|
| Multi-Agent | 多智能体协调模式：五种方法及适用场景 |
| Multi-Agent | Claude Managed Agents：生产部署速度提升 10 倍 |
| 产品功能 | Claude Code 推出 Routines 例行任务功能 |
| 产品功能 | Agent View in Claude Code |
| 开发者 | 在 Claude Code 中使用 Claude Opus 4.7 的最佳实践 |
| 开发者 | 构建 Claude Code 的经验：Prompt Caching 是关键 |
| 客户案例 | Claude 在法律行业的应用 |
| 客户案例 | Kepler 用 Claude 构建金融服务可验证 AI |
| 指南 | 指南：为金融服务构建 AI 智能体 |
| 安全 | Claude Security 功能公测发布 |

### 官方文档（英文原版）

抓取自 [code.claude.com/docs](https://code.claude.com/docs)，共 50 页，按章节分类：

- **Getting Started** — 概览、快速入门、更新日志
- **Core Concepts** — 工作原理、最佳实践、常见工作流
- **Build With** — Sub-agents、MCP、Hooks、Skills、Plugins
- **Configuration** — 设置、记忆、模型配置、状态栏
- **Deployment** — Amazon Bedrock、Google Vertex AI、Microsoft Foundry 等
- **Administration** — IAM、费用管理、安全、分析
- **Outside Terminal** — VS Code、JetBrains、GitHub Actions、Slack 等
- **Reference** — CLI 参考、Hooks 参考、交互模式、检查点

---

## 使用

直接打开链接即可，无需安装任何工具：

```
https://viy1204.github.io/claude-code-docs/
```

- **搜索**：顶部搜索框支持中英文实时过滤
- **分类筛选**：点击左侧侧边栏按分类浏览
- **阅读**：点击任意文章/文档直接在页面内渲染阅读
- **目录**：长文章自动生成 TOC，支持滚动高亮

---

## 本地构建与内容更新

需要 Python 3 + `markdown` 库：

```bash
pip install markdown
cd scripts/claude-code-docs
```

**首次或同步最新文章：**

```bash
python fetch-new-blogs.py   # 抓取 claude.com/blog 上的新文章
python translate-blogs.py   # 用 Claude Haiku 自动翻译为中文
python generate.py          # 重新生成 SPA
```

**仅重新生成（内容无更新时）：**

```bash
python generate.py
```

生成的 `index.html` 是完全自包含的单文件 SPA（约 2.2 MB），可直接用浏览器打开，也可部署到任意静态托管服务。

---

*内容抓取自 Anthropic 官方渠道，仅供学习参考。*
