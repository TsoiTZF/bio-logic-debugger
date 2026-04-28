# 🌾 让邺城燃烧 — Bio-Logic Debugger

**在播种前筛掉注定失败的育种方向。**

Bio-Logic Debugger 是一个育种目标预筛引擎。它用已知的生物学规律（性状关联、生理约束、历史反模式）在播种前评估你的育种目标是否可行，并给出顾问级的解释和建议。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动 Web 界面

```bash
cd bio_logic_debugger
streamlit run app.py
```

浏览器打开 `http://localhost:8501` 即可使用。

### 3. 或者用命令行

```bash
python cli.py
```

进入交互式控制台，或单次快速验证：

```bash
python cli.py --validate rice_yield_per_plant >= 50
```

## 功能

- **🎯 育种目标验证** — 设定目标性状，系统检查拮抗关系、生理约束和反模式
- **🔬 性状浏览器** — 浏览知识库中的所有性状及其关联网络
- **📚 反模式库** — 历史上反复验证的育种死胡同，附带失败案例和替代方向
- **📜 约束规则** — 普适的生理学法则（FATAL 级违反 = 生理上不可能）
- **📚 文献与知识库** — 上传论文 PDF / 搜索 DOI 提取知识，自动同步社区知识库

## 新增功能

### 📄 文献导入分析
支持上传 PDF 论文或通过 DOI / 标题搜索，自动提取：
- **性状**（Traits） — 数值范围、单位、分类
- **关联**（Correlations） — 正/负相关、权衡关系
- **约束**（Constraints） — 生理极限规则

提取引擎采用 **规则匹配 + 可选 LLM** 双模式，结果合并去重。提取后用户可逐条审核勾选，确认后一键导入知识库。

### 📊 图表分析（Vision）
支持上传科学图表图片（相关性热图、箱线图等），通过 LLM Vision 解读图表中的生物学含义。

### 🌐 社区知识库自动同步
项目启动时自动从社区知识库仓库拉取最新数据。

- **社区仓库**：[TsoiTZF/bio-logic-knowledge](https://github.com/TsoiTZF/bio-logic-knowledge)
- 知识库分三层，优先级从高到低：**用户扩充 > 社区数据 > 内置兜底**
- 用户可从 app 中导出扩充的 JSON 后提 PR 贡献到社区

## 项目结构

```
bio_logic_debugger/
├── app.py                    # Web 界面 (Streamlit)
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
│   └── data/                 # 社区知识库本地缓存
└── llm/
    └── reasoner.py           # LLM 深度分析（可选，含 Vision）
```

## 内置知识库

目前以 **水稻 (Oryza sativa)** 作为示例知识库，覆盖：

- **18 个性状**：产量、品质、株型、抗病、生育期等维度
- **13 条关联**：包括负相关连锁、权衡关系、曲线关系
- **5 个反模式**：高产低质陷阱、极端粒型代价、过度矮化陷阱等
- **3 条约束规则**：FATAL 级生理法则

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
