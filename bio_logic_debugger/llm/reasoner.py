"""
LLM 生物推理模块

调用外部大语言模型对育种目标做更深层的生物合理性分析。
LLM 层是可选的插件式模块，默认通过 HTTP 调用 OpenAI 兼容 API。

输入：育种目标 + 知识库中的相关约束
输出：自由文本分析意见，注入到 ValidationReport.llm_comment

v2: 新增 vision 分析和知识提取功能
"""
from __future__ import annotations

import base64
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

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


# ═══════════════════════════════════════════════════════════════
# 图表分析提示词
# ═══════════════════════════════════════════════════════════════

CHART_ANALYSIS_PROMPT = """你是一位作物育种领域的图表分析专家。请解读这张科学图表。

关注以下方面：
1. 图表的坐标轴含义和单位
2. 显示的主要趋势和关系（正相关、负相关、曲线关系等）
3. 关键数值范围和重要数据点
4. 可以提取的育种相关约束或关联
5. 图表中的显著差异或异常

请用中文回答，简明扼要。"""


# ═══════════════════════════════════════════════════════════════
# 知识提取提示词（供 paper_analyzer 使用）
# ═══════════════════════════════════════════════════════════════

EXTRACT_SYSTEM_PROMPT = """你是一位作物育种知识提取专家。从以下论文片段中提取所有与育种相关的信息。

请严格按照 JSON 格式输出，只输出 JSON，不要其他内容。

提取三类信息：

1. traits（性状）：有数值范围、测量单位、分类归属的可测量生物学性状
   格式：{"name": "性状名称", "range": [最小值, 最大值], "unit": "单位", "category": "分类"}

2. correlations（关联）：两个性状之间的相关性描述
   格式：{"trait_a": "性状A", "trait_b": "性状B", "type": "positive/negative/trade_off/curvilinear", "strength": 相关系数, "mechanism": "生理机制描述"}

3. constraints（约束）：生理极限或不可兼得的规则
   格式：{"name": "约束名称", "description": "约束描述", "severity": "FATAL/SEVERE/WARNING/INFO", "condition": "条件表达式"}

注意：
- 只提取论文中明确提到的信息，不要臆造
- name 等中文名称使用论文中的原文术语
- 如果没有相关信息，对应字段返回空列表 []"""


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


def build_extract_prompt(text: str) -> str:
    """构建知识提取提示词"""
    truncated = text[:8000]
    return f"""论文片段：
{truncated}

请提取其中的育种相关知识，以 JSON 格式输出：
{{
  "traits": [{{"name": "...", "range": [min, max], "unit": "...", "category": "..."}}],
  "correlations": [{{"trait_a": "...", "trait_b": "...", "type": "positive/negative/trade_off", "strength": 0.0, "mechanism": "..."}}],
  "constraints": [{{"name": "...", "description": "...", "severity": "FATAL/SEVERE/WARNING", "condition": "..."}}]
}}"""


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

    支持三种模式：
      1. HTTP 模式：直接调用 OpenAI 兼容的 API
      2. 回调模式：用户提供自定义回调函数
      3. Vision 模式：分析图表图片
    """

    def __init__(
        self,
        config: LLMConfig | None = None,
        callback: Callable | None = None,
    ):
        self.config = config or LLMConfig.from_env()
        self._callback = callback
        self._vision_model = "gpt-4o"  # vision 模型需支持多模态

    def set_vision_model(self, model: str) -> None:
        self._vision_model = model

    def analyze(self, goal: BreedingGoal, engine: BioLogicEngine) -> str:
        """执行 LLM 分析"""
        if self._callback:
            return self._callback(goal, engine)

        if not self.config.api_key:
            logger.warning("未配置 LLM API Key，跳过 LLM 分析")
            return "[LLM 分析未启用：未配置 API Key]"

        return self._http_analyze(goal, engine)

    def analyze_vision(self, image_bytes: bytes, prompt: str = "") -> str:
        """
        分析图表图片。

        参数：
            image_bytes: 图片的字节数据（PNG/JPG）
            prompt: 可选的附加提示词

        返回：
            图表分析文本
        """
        if not image_bytes:
            return "[错误：未提供图片]"

        if not self.config.api_key:
            return "[LLM 分析未启用：未配置 API Key]"

        return self._http_vision_analyze(image_bytes, prompt or CHART_ANALYSIS_PROMPT)

    def extract_knowledge(self, text: str) -> str:
        """
        从论文文本中提取结构化知识。

        参数：
            text: 论文文本内容

        返回：
            JSON 字符串，包含 traits / correlations / constraints
        """
        if not text.strip():
            return json.dumps({"traits": [], "correlations": [], "constraints": []}, ensure_ascii=False)

        if not self.config.api_key:
            logger.warning("未配置 LLM API Key，无法提取知识")
            return json.dumps({"traits": [], "correlations": [], "constraints": []}, ensure_ascii=False)

        prompt = build_extract_prompt(text)
        return self._http_chat(EXTRACT_SYSTEM_PROMPT, prompt)

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

    # ──── HTTP 调用 ────

    def _http_chat(self, system_prompt: str, user_prompt: str) -> str:
        """通用的 HTTP chat 调用"""
        import httpx

        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
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
            return f"[LLM 调用失败: {e}]"

    def _http_analyze(self, goal: BreedingGoal, engine: BioLogicEngine) -> str:
        """通过 HTTP 调用 LLM API 进行育种分析"""
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
        user_prompt = build_analysis_prompt(goal, context_summary)

        return self._http_chat(BREEDING_ANALYST_SYSTEM_PROMPT, user_prompt)

    def _http_vision_analyze(self, image_bytes: bytes, prompt: str) -> str:
        """通过 HTTP 调用支持 vision 的模型分析图表"""
        import httpx

        # 将图片转为 base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        # 检测图片格式
        ext = "png"
        if image_bytes[:4] == b"\xff\xd8\xff":
            ext = "jpeg"
        elif image_bytes[:6] in (b"GIF87a", b"GIF89a"):
            ext = "gif"
        elif image_bytes[:4] == b"RIFF":
            ext = "webp"

        data_url = f"data:image/{ext};base64,{image_b64}"

        payload = {
            "model": self._vision_model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": data_url, "detail": "high"},
                        },
                    ],
                }
            ],
            "temperature": 0.3,
            "max_tokens": 2048,
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
            logger.exception("Vision API 调用失败")
            return f"[图表分析失败: {e}]"


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
