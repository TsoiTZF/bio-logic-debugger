# 🌾 让邺城燃烧 — Bio-Logic Debugger

**在播种前筛掉注定失败的育种方向。**

Bio-Logic Debugger 是一个育种目标**预筛规则引擎**，不是 QTL / 育种值 / 多环境试验模型。它对照示例知识库里的范围、关联、表达式和反模式，标出教科书里反复被警告的组合。不能替代育种家判断、田间试验或品种审定。

## 快速开始

```bash
pip install -e .
bld            # 命令行（pyproject 里已定义 bld = cli:main）
streamlit run bio_logic_debugger/app.py
```

浏览器打开 `http://localhost:8501`。单次验证：

```bash
bld --validate rice_yield_per_plant >= 50
```

跑测试：

```bash
pip install -e ".[dev]"
pytest
```

## 功能

- **🎯 育种目标验证** — 设定目标性状，系统检查拮抗关系、生理约束和反模式
- **🔬 性状浏览器** — 浏览知识库中的所有性状及其关联网络
- **📚 反模式库** — 历史上反复验证的育种死胡同，附带失败案例和替代方向
- **📜 约束规则** — FATAL 生理极限；SEVERE 极难突破；WARNING 已知冲突，可能缓解
- **📚 文献与知识库** — 上传论文 PDF / 搜索 DOI 提取知识；社区库需手动同步

## 新增功能

### 📄 文献导入分析
支持上传 PDF 论文或通过 DOI / 标题搜索，自动提取：
- **性状**（Traits） — 数值范围、单位、分类
- **关联**（Correlations） — 正/负相关、权衡关系
- **约束**（Constraints） — 生理极限规则

提取引擎采用 **规则匹配 + 可选 LLM** 双模式，结果合并去重。提取后用户可逐条审核勾选，确认后一键导入知识库。

### 📊 图表分析（可选）
文献页可上传图表，配置 API Key 后手动点「解读图表」。未配置密钥时规则验证仍可用。

### 🌐 社区知识库
默认**不**在启动时自动覆盖本地知识。需要时在侧边栏或知识库页手动同步。
缓存写到用户目录 `~/.bio-logic-debugger/community/`，内置 JSON 不会被覆盖。

- **社区仓库**：[TsoiTZF/bio-logic-knowledge](https://github.com/TsoiTZF/bio-logic-knowledge)
- 合并：**用户可覆盖同 id**；**社区只新增**，过时社区条目不能改掉内置
- 负相关/权衡在报告里最高为警告，不是「生理不可能」

## 项目结构

```
bio_logic_debugger/
├── app.py                    # Streamlit 入口
├── ui/                       # 页面与侧边栏（与引擎解耦）
├── cli.py                    # 命令行界面
├── requirements.txt          # 依赖
├── core/
│   ├── domain.py             # 核心数据模型
│   ├── engine.py             # 验证引擎
│   └── anti_pattern.py       # 反模式匹配器
├── knowledge/
│   ├── rice_knowledge.py     # 水稻知识库（内置兜底）
│   ├── knowledge_store.py    # 知识库加载/合并/同步
│   ├── paper_analyzer.py     # 论文分析编排器
│   ├── pdf_parser.py         # PDF 文本提取
│   ├── doi_fetcher.py        # DOI/标题检索
└── llm/
    └── reasoner.py           # LLM 深度分析（可选，含 Vision）
```

## 内置知识库

内置知识在 `bio_logic_debugger/knowledge/builtin/*.json`（随包分发）。
社区同步缓存写在用户目录 `~/.bio-logic-debugger/community/`，不进软件包。

当前是 **水稻 (Oryza sativa) 示例库**：性状 40、关联 30、约束 9、反模式 7。
相关系数多为示意量级，不是从某张表逐格抄来的；没有 URL 的证据不会标 CONFIRMED。基因克隆论文不再拿去撑无关的 r。

FATAL 表示当前规则下的生理极限；SEVERE/WARNING 是反复被提到的冲突，不是「绝对不可能」。

## 软著底稿

登记用名称、功能说明、操作说明书和源码交存顺序见 [`docs/ruanzhu/`](docs/ruanzhu/00-填写说明.md)。

## 扩展

创建新的知识库，参考 `knowledge/rice_knowledge.py` 的格式定义你的作物：

```python
from bio_logic_debugger.core.domain import Trait, TraitCorrelation, AntiPattern

TRAITS = [
    Trait("my_crop_yield", "产量", "描述", "产量", "kg", (100, 500)),
]
```

## 可选：LLM 深度分析

在 Web 界面中启用 LLM 分析，或在环境变量中配置：

```bash
export BIO_LLM_API_KEY="sk-xxx"
export BIO_LLM_BASE_URL="https://api.deepseek.com/v1"
export BIO_LLM_MODEL="deepseek-chat"
```
