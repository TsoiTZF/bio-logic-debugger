# Changelog

All notable changes to Bio-Logic Debugger will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.8] - 2026-09-12

### Fixed
- 快速开始改为 `pip install -e .` / `bld` / `streamlit run bio_logic_debugger/app.py`
- 约束页按 FATAL/SEVERE/WARNING 分档，不再一律「生理上不可能」
- 停止打包和跟踪 `knowledge/data/`
- 引擎兜底不再二次 import 损坏的模块级 JSON
- 界面验证用 `validate(llm_layer=...)`，权重走 `set_confidence`
- 用户用旧别名覆盖时改写为规范 id
- 正相关输出顺风/联动 INFO
- 早熟、收获指数降 SEVERE，干旱产量损失降 WARNING
- 文献提取默认不勾选、分块送 LLM、去掉 HTML 原文渲染

## [0.2.7] - 2026-09-12

### Fixed
- 社区合并改为只新增，过时社区条目不再覆盖内置约束/性状
- 高产低质改为高产+高垩白+低整精米；垩白 higher_is_better=false
- 其余反模式补 better/worse 意图，晚熟高产不再打成早熟陷阱
- 补 Fukuoka 2009、Khanna 2015 的 DOI；对不上的仍空着

## [0.2.6] - 2026-09-12

### Fixed
- SES 约束按 1 抗 9 感改方向：高秆+真高抗才 FATAL，高秆+易倒不触发
- 反模式可声明 better/worse 意图；优质籼稻（高产+长粒+高直链）不再打成高产低质
- 关联层用 |r|×confidence，权重滑条能关掉弱拮抗
- validate() 不再改写调用方的 trait_id
- 证据 URL 去掉官网首页/检索页；DOI 年份与文献对齐

## [0.2.5] - 2026-09-12

### Changed
- 亩产正式 id 改为 `rice_yield_per_mu`，保留 `rice_yield_per_ha` 别名
- 能核对的文献证据补上 DOI/URL，其余仍空着不编造

## [0.2.4] - 2026-09-12

### Changed
- 负相关最高 WARNING，去掉虚假「达成率」；FATAL 不再截断后续层
- 反模式按覆盖率匹配，额外性状不再把已命中模式打下去
- 约束按目标区间求值；环境变量（干旱/温度/氮肥）可绑定
- `_wants_high` 对照典型范围中位；SES 1–9 级越大越差
- 社区同步改为手动、写入用户目录并校验 schema
- 用户知识持久化到 `~/.bio-logic-debugger/`
- LLM 接线改为 `as_validation_layer` / `chat(system, user)`

### Added
- MIT License
- 内置约束变量必须属于性状或已声明环境变量的测试

## [0.2.3] - 2026-09-12

### Added
- GitHub Actions：Python 3.10 / 3.12 跑 pytest

### Changed
- Streamlit 拆到 `ui/runtime.py` 与 `ui/pages/*`，`app.py` 只做入口
- 界面不再访问 `engine._traits` 等私有字段

## [0.2.2] - 2026-09-12

### Changed
- 内置知识改为 `knowledge/builtin/*.json` 唯一数据源，`rice_knowledge.py` 只做加载
- 序列化补齐 evidence / failed_approaches 字段，社区同步不再覆盖内置目录

## [0.2.1] - 2026-09-12

### Added
- 约束条件表达式求值（AND/OR/NOT/比较），缺变量不误报
- 引擎/表达式/知识合并的 pytest 用例
- CLI 入口 `bld`，与 App 共用 `load_and_merge`

### Fixed
- 约束层只要目标里出现相关性状就会触发的误报
- `_wants_high` 把任意正区间当成「同时追高」
- Python 3.10 不支持的 `type` 语句
- `ValidationContext` 错误地从 domain 导入
- `pyproject.toml` 与 `requirements.txt` 依赖不一致（pypdf / PyMuPDF）

### Changed
- 知识库优先级文档与实现对齐：用户扩充 > 社区 > 内置

## [0.2.0] - 2026-04-28

### Added
- **自动论文检索功能**：从知识库关键词自动搜索 CrossRef，分析摘要提取性状/关联/约束
  - 关键词自动提取（从性状名称、分类、标签）
  - 批量检索去重（基于 DOI）
  - 已检索论文持久化记录
- **数据权重调整系统**：用户可调整每条知识的置信度，影响验证结果
  - 性状/关联/约束权重滑动条（0.0-1.0）
  - 权重持久化到本地 JSON
  - 验证引擎自动应用权重（有效强度 = 强度 × 置信度）
- **Trait 置信度字段**：补齐 Trait 缺失的 confidence 字段，与其他模型保持一致
- **版本管理系统**：pyproject.toml + CHANGELOG.md + 侧边栏版本号显示

### Changed
- 验证引擎引入置信度影响：
  - 关联检查：有效强度 = abs(strength) × confidence
  - 约束检查：低置信度自动降级严重等级
  - 范围检查：低置信度性状的范围警告降级为 INFO
- 社区知识库同步通知改为仅首次显示，避免重复弹窗
- 最后同步时间显示改为单独一行，避免 metric 组件截断

### Fixed
- 修复社区知识库同步通知重复弹出的问题
- 修复最后同步时间显示被截断为 "2026-0" 的问题

## [0.1.0] - 2026-04-20

### Added
- 初始版本发布
- 育种目标验证核心引擎
- 性状浏览器、反模式库、约束规则查看
- 文献 PDF 上传与 DOI 搜索
- 社区知识库同步机制
- 用户知识扩充与导出
