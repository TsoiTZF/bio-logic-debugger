# Changelog

All notable changes to Bio-Logic Debugger will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
