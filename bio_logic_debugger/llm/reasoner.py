"""
LLM 生物推理模块

调用外部大语言模型对育种目标做更深层的生物合理性分析。
LLM 层是可选的插件式模块，默认通过 HTTP 调用 OpenAI 兼容 API。

输入：育种目标 + 知识库中的相关约束
输出：自由文本分析意见，注入到 ValidationReport.llm_comment
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Callable, Optional

from bio_logic_debugger.core.domain import BreedingGoal, ValidationContext
from bio_logic_debugger.core.engine import BioLogicEngine

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# 提示词模板
# ═══════════════════════════════════════════════════════════════

BREEDING_ANALYST_SYSTEM_PROMPT = """你是一位拥有 40 年经验的作物育种顾问专家，精通作物生理学、遗传学和育种实践。

你的任务是分析用户的育种目标，从生物学合理性角度给出评估意见。

你需要关注：
1. 性状组合是否违反已知的生理规律
2. 是否存在历史上被反复验证的育种死胡同
3. 是否有潜在的权衡（trade-off）被忽略了
4. 育种目标是否在物种的生理极限范围内
5. 可能忽略的间接效应或连锁效应

请用中文回答。语气要像一个经验丰富的老育种家在给年轻育种家提建议：
有依据、有分寸、有建设性。指出问题时要给出原因，否定时要给出替代方向。

不要重复系统已经给出的约束违反信息，而是要提供更深层的分析。"""


def build_analysis_prompt(goal: BreedingGoal, context_summary: str) -> str:
    """构建 LLM 分析提示词"""
    targets_str = "\n".join(
        f"  - {t.trait_id}: "
        f"{'≥' if t.direction == '>=' else '≤' if t.direction == '<=' else '=' if t.direction == '==' else t.direction} "
        f"{t.desired_value or f'[{t.range_min}, {t.range_max}]'} "
        f"(优先级: {t.priority}/10)"
        for t in goal.targets
    )

    return f"""## 育种目标

名称：{goal.name}
物种：{goal.species}

### 目标性状：
{targets_str}

### 育种背景：
{goal.context or '（未提供）'}

### 知识库中相关约束：
{context_summary or '（无）'}

请从以下角度分析这个育种目标的生物学合理性：
1. 最可能遇到什么问题？
2. 有没有被忽略的间接效应？
3. 如果要实现这个目标，最关键的风险点是什么？
4. 你的建议是什么？"""


# ═══════════════════════════════════════════════════════════════
# LLM 调用后端
# ═══════════════════════════════════════════════════════════════

@dataclass
class LLMConfig:
    """LLM 连接配置"""
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 2048

    @classmethod
    def from_env(cls) -> "LLMConfig":
        """从环境变量加载配置"""
        return cls(
            api_key=os.getenv("BIO_LLM_API_KEY", ""),
            base_url=os.getenv("BIO_LLM_BASE_URL", "https://api.openai.com/v1"),
            model=os.getenv("BIO_LLM_MODEL", "gpt-4o"),
        )


class LLMReasoner:
    """
    LLM 生物推理器。

    支持两种模式：
      1. HTTP 模式：直接调用 OpenAI 兼容的 API
      2. 回调模式：用户提供自定义回调函数
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        callback: Callable | None = None,
    ):
        self.config = config or LLMConfig.from_env()
        self._callback = callback

    def analyze(self, goal: BreedingGoal, engine: BioLogicEngine) -> str:
        """执行 LLM 分析"""
        if self._callback:
            return self._callback(goal, engine)

        if not self.config.api_key:
            logger.warning("未配置 LLM API Key，跳过 LLM 分析")
            return "[LLM 分析未启用：未配置 API Key]"

        return self._http_analyze(goal, engine)

    def as_validation_layer(self, engine: BioLogicEngine) -> Callable:
        """返回一个适合注册到引擎的验证层回调"""
        def layer(ctx: ValidationContext) -> ValidationContext:
            try:
                ctx.llm_comment = self.analyze(ctx.goal, engine)
            except Exception as e:
                logger.error(f"LLM 分析失败: {e}")
                ctx.llm_comment = f"[LLM 分析异常: {e}]"
            return ctx
        return layer

    def _http_analyze(self, goal: BreedingGoal, engine: BioLogicEngine) -> str:
        """通过 HTTP 调用 LLM API"""
        import httpx

        # 收集知识库中的上下文
        context_parts = []
        for corr in engine._correlations:
            if corr.trait_a in goal.trait_ids() or corr.trait_b in goal.trait_ids():
                context_parts.append(
                    f"[关联] {corr.trait_a} ↔ {corr.trait_b}: "
                    f"{corr.corr_type.name} (r={corr.strength}), "
                    f"机制: {corr.mechanism[:100] if corr.mechanism else '无'}"
                )
        for ap in engine._anti_patterns._patterns.values():
            if any(t in goal.trait_ids() for t in ap.trigger_traits):
                context_parts.append(
                    f"[反模式] {ap.name}: {ap.description[:150]}"
                )

        context_summary = "\n".join(context_parts) if context_parts else "无相关约束"

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": BREEDING_ANALYST_SYSTEM_PROMPT},
                {"role": "user", "content": build_analysis_prompt(goal, context_summary)},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }

        try:
            resp = httpx.post(
                f"{self.config.base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=120,
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.exception("LLM API 调用失败")
            return f"[LLM 分析失败: {e}]"


# ═══════════════════════════════════════════════════════════════
# 语义反模式匹配器（通过 LLM）
# ═══════════════════════════════════════════════════════════════

class SemanticAntiPatternMatcher:
    """
    通过 LLM 进行语义级别的反模式匹配。

    当性状组合不完全匹配已知反模式时，LLM 可以根据语义判断
    育种方向是否与某个已知的历史死胡同相似。
    """

    def __init__(self, reasoner: LLMReasoner):
        self.reasoner = reasoner

    def match(
        self,
        goal: BreedingGoal,
        candidates: list,
    ) -> list[tuple[str, float, str]]:
        """
        对候选反模式进行语义匹配。

        返回：[(反模式ID, 匹配度, 解释), ...]
        """
        if not candidates:
            return []

        patterns_text = "\n\n".join(
            f"ID: {p.id}\n名称: {p.name}\n描述: {p.description[:200]}"
            for p in candidates
        )

        targets_str = "\n".join(
            f"  - {t.trait_id}: {'≥' if t.direction == '>=' else '≤' if t.direction == '<=' else '=='} {t.desired_value}"
            for t in goal.targets if t.desired_value
        )

        prompt = f"""育种目标：
名称：{goal.name}
目标性状：
{targets_str}

以下是候选的历史反模式（已知的育种死胡同）：

{patterns_text}

请判断：这个育种目标在语义上与哪些反模式相似？
对于每个匹配的反模式，给出：
1. ID
2. 匹配度（0.0 - 1.0）
3. 匹配的理由

以JSON格式输出：[{{"id": "...", "score": 0.0, "reason": "..."}}]
只输出 JSON，不要其他内容。"""

        messages = [
            {"role": "system", "content": "你是一位育种专家助手。请严格按 JSON 格式输出分析结果。"},
            {"role": "user", "content": prompt},
        ]

        try:
            import httpx
            headers = {
                "Authorization": f"Bearer {self.reasoner.config.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.reasoner.config.model,
                "messages": messages,
                "temperature": 0.3,
                "max_tokens": 1024,
            }
            resp = httpx.post(
                f"{self.reasoner.config.base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            # 提取 JSON
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("\n", 1)[0]
                if content.endswith("```"):
                    content = content[:-3]

            results = json.loads(content)
            return [
                (r["id"], float(r["score"]), r["reason"])
                for r in results
                if r["score"] >= 0.4
            ]
        except Exception as e:
            logger.warning(f"语义匹配失败: {e}")
            return []
