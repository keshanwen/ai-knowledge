#!/usr/bin/env python3
"""知识条目 5 维度质量评分工具。

用法:
    python hooks/check_quality.py <json_file> [json_file2 ...]
    python hooks/check_quality.py knowleadge/articles/*.json
"""

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("check_quality")

# ============================================================
# Dataclass 定义
# ============================================================


@dataclass
class DimensionScore:
    """单个维度的评分结果。

    Attributes:
        name: 维度名称。
        score: 实际得分。
        max_score: 该维度满分。
        details: 评分说明。
    """

    name: str
    score: float
    max_score: int
    details: str = ""


@dataclass
class QualityReport:
    """单文件质量评分报告。

    Attributes:
        filepath: 文件路径。
        dimensions: 各维度评分列表。
    """

    filepath: Path
    dimensions: list[DimensionScore] = field(default_factory=list)

    @property
    def total_score(self) -> float:
        """总分（各维度得分之和）。"""
        return sum(d.score for d in self.dimensions)

    @property
    def grade(self) -> str:
        """评级：A >= 80, B >= 60, C < 60。"""
        s = self.total_score
        if s >= 80:
            return "A"
        elif s >= 60:
            return "B"
        return "C"


# ============================================================
# 常量定义
# ============================================================

GRADE_A_THRESHOLD = 80
GRADE_B_THRESHOLD = 60

# 摘要-技术关键词奖励列表
TECH_KEYWORDS = frozenset({
    "AI", "LLM", "Agent", "RAG", "fine-tuning", "微调", "推理",
    "多模态", "multimodal", "transformer", "embedding", "向量",
    "API", "开源", "open source", "部署", "deployment",
    "prompt", "token", "模型", "model", "训练", "training",
    "GPU", "推理引擎", "inference", "ONNX", "量化", "quantization",
    "蒸馏", "distillation", "MoE", "扩散", "diffusion",
    "生成式", "generative", "RLHF", "DPO", "alignment", "对齐",
    "安全", "safety", "幻觉", "hallucination",
    "function calling", "tool use", "MCP", "A2A",
    "text-to-speech", "TTS", "语音", "speech",
})

# 标准标签列表
STANDARD_TAGS = frozenset({
    "AI", "LLM", "Agent", "Open Source", "Tool", "Code Gen",
    "RAG", "Fine-tuning", "Prompt Engineering", "Inference",
    "Multimodal", "Embedding", "Vector DB", "OpenAI",
    "API", "Framework", "Deployment", "Evaluation",
    "Safety", "Alignment", "MoE", "Multilingual",
    "Text-to-Speech", "TTS",
    "DeepSeek", "Anthropic", "Paper", "Diffusion",
    "Computer Vision",
    "推理", "多模态", "开源", "工具", "智能体",
    "检索增强", "微调", "部署", "评测",
})

# 有效 status 值
VALID_STATUSES = frozenset({
    "draft", "review", "reviewed", "published", "archived",
})

# 空洞词黑名单-中文
BUZZWORDS_CN = frozenset({
    "赋能", "抓手", "闭环", "打通", "全链路", "底层逻辑",
    "颗粒度", "对齐", "拉通", "沉淀", "强大",
})

# 空洞词黑名单-英文
BUZZWORDS_EN = frozenset({
    "groundbreaking", "revolutionary", "game-changing",
    "cutting-edge", "state-of-the-art", "best-in-class",
    "disruptive", "paradigm-shift", "world-class",
    "next-generation",
})

SUMMARY_MIN_CHARS = 20
SUMMARY_FULL_CHARS = 50
SUMMARY_BASE_SCORE = 10
SUMMARY_MAX_BONUS = 15
KEYWORD_BONUS_PER_HIT = 1
KEYWORD_BONUS_CAP = 5

TECH_SCORE_MIN = 1
TECH_SCORE_MAX = 10
TECH_SCORE_MULTIPLIER = 2.5

FORMAT_ITEMS = ("id", "title", "source_url", "status", "created_at")
FORMAT_PER_ITEM = 4

TAGS_OPTIMAL_MIN = 1
TAGS_OPTIMAL_MAX = 3
TAGS_FAIR_MAX = 5
TAGS_COUNT_OPTIMAL = 10
TAGS_COUNT_FAIR = 7
TAGS_COUNT_EXCESS = 4
TAGS_MATCH_ALL = 5
TAGS_MATCH_PARTIAL = 3

BUZZWORD_DEDUCTION = 3

BAR_WIDTH = 10
PROGRESS_WIDTH = 20

# ============================================================
# 评分函数
# ============================================================


def _extract_text(data: dict[str, Any]) -> tuple[str, str, str, list[Any]]:
    """从 JSON 数据提取常用字段，统一处理缺失和类型问题。

    Args:
        data: 解析后的 JSON 对象。

    Returns:
        (title, summary, status, tags) 元组，缺失时返回空值。
    """
    title = str(data.get("title", ""))
    summary = str(data.get("summary", ""))
    status = str(data.get("status", ""))
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        tags = []
    return title, summary, status, tags


def _score_summary_quality(data: dict[str, Any]) -> DimensionScore:
    """摘要质量评分（满分 25）。

    评分逻辑：
        - >= 50 字：满分 25
        - >= 20 字：基本分 10 + 长度奖励（最高 15 分）
        - < 20 字：0 分
        - 含技术关键词额外加分（最多 +5，总分不超过 25）

    Args:
        data: 解析后的 JSON 对象。

    Returns:
        DimensionScore 实例。
    """
    summary = str(data.get("summary", ""))
    length = len(summary)

    if length < SUMMARY_MIN_CHARS:
        return DimensionScore(
            "摘要质量", 0, 25,
            f"摘要仅 {length} 字，不满足最低 {SUMMARY_MIN_CHARS} 字要求",
        )

    if length >= SUMMARY_FULL_CHARS:
        length_score = 25
    else:
        extra_range = SUMMARY_FULL_CHARS - SUMMARY_MIN_CHARS
        length_score = SUMMARY_BASE_SCORE + round(
            (length - SUMMARY_MIN_CHARS) * SUMMARY_MAX_BONUS / extra_range
        )

    keyword_hits = sum(
        1 for kw in TECH_KEYWORDS if kw.lower() in summary.lower()
    )
    keyword_bonus = min(KEYWORD_BONUS_CAP, keyword_hits * KEYWORD_BONUS_PER_HIT)

    score = min(25, length_score + keyword_bonus)
    parts = [f"长度 {length} 字"]
    if keyword_hits > 0:
        parts.append(f"命中 {keyword_hits} 个技术关键词 (+{keyword_bonus})")
    return DimensionScore("摘要质量", score, 25, "，".join(parts))


def _score_tech_depth(data: dict[str, Any]) -> DimensionScore:
    """技术深度评分（满分 25），基于 score 字段映射。

    score 1-10 → 2.5-25（线性映射，四舍五入）。

    Args:
        data: 解析后的 JSON 对象。

    Returns:
        DimensionScore 实例。
    """
    raw_score = data.get("score")
    if raw_score is None:
        return DimensionScore("技术深度", 0, 25, "缺少 score 字段")

    try:
        s = float(raw_score)
    except (ValueError, TypeError):
        return DimensionScore(
            "技术深度", 0, 25, f"score 值无法解析: {raw_score}"
        )

    if s < TECH_SCORE_MIN or s > TECH_SCORE_MAX:
        return DimensionScore(
            "技术深度", 0, 25, f"score 值超出 {TECH_SCORE_MIN}-{TECH_SCORE_MAX} 范围: {s}"
        )

    mapped = round(s * TECH_SCORE_MULTIPLIER)
    return DimensionScore("技术深度", mapped, 25, f"score={s} → {mapped}/25")


def _score_format(data: dict[str, Any]) -> DimensionScore:
    """格式规范评分（满分 20），逐项检查 5 个字段。

    每项 4 分：id / title / source_url / status / created_at。

    Args:
        data: 解析后的 JSON 对象。

    Returns:
        DimensionScore 实例。
    """
    def _checks() -> list[tuple[str, bool]]:
        _id = data.get("id")
        yield "id", bool(_id and isinstance(_id, str) and _id.strip())

        title = data.get("title")
        yield "title", bool(title and isinstance(title, str) and title.strip())

        url = data.get("source_url")
        yield "source_url", bool(
            url and isinstance(url, str) and re.match(r"^https?://", url)
        )

        status = str(data.get("status", ""))
        yield "status", status in VALID_STATUSES

        created = data.get("created_at")
        yield "created_at", bool(created and isinstance(created, str) and created.strip())

    items = list(_checks())
    passed = sum(1 for _, ok in items if ok)
    score = passed * FORMAT_PER_ITEM
    failed = [name for name, ok in items if not ok]
    details = f"{passed}/5 项通过"
    if failed:
        details += f"，缺失: {', '.join(failed)}"
    return DimensionScore("格式规范", score, 20, details)


def _score_tags(data: dict[str, Any]) -> DimensionScore:
    """标签精度评分（满分 15）。

    评分逻辑：
        - 1-3 个标签：最优（10 分）
        - 4-5 个标签：可接受（7 分）
        - >5 或 0 个：较差（4 分/0 分）
        - 全部为标准标签：+5，部分为：+3，无：+0

    Args:
        data: 解析后的 JSON 对象。

    Returns:
        DimensionScore 实例。
    """
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        return DimensionScore("标签精度", 0, 15, "tags 不是列表类型")

    tag_count = len(tags)
    if tag_count == 0:
        return DimensionScore("标签精度", 0, 15, "标签为空")

    if TAGS_OPTIMAL_MIN <= tag_count <= TAGS_OPTIMAL_MAX:
        count_score = TAGS_COUNT_OPTIMAL
    elif tag_count <= TAGS_FAIR_MAX:
        count_score = TAGS_COUNT_FAIR
    else:
        count_score = TAGS_COUNT_EXCESS

    str_tags = [str(t) for t in tags]
    standard_count = sum(1 for t in str_tags if t in STANDARD_TAGS)
    if standard_count == tag_count:
        match_score = TAGS_MATCH_ALL
    elif standard_count > 0:
        match_score = TAGS_MATCH_PARTIAL
    else:
        match_score = 0

    score = count_score + match_score
    non_standard = [t for t in str_tags if t not in STANDARD_TAGS]
    detail_parts = [f"{tag_count} 个标签，{standard_count}/{tag_count} 标准"]
    if non_standard:
        detail_parts.append(f"非标准: {', '.join(non_standard)}")
    return DimensionScore("标签精度", score, 15, "，".join(detail_parts))


def _score_buzzwords(data: dict[str, Any]) -> DimensionScore:
    """空洞词检测评分（满分 15）。

    检查 title + summary 中是否包含空洞词，每命中一个扣 3 分，最低 0 分。

    Args:
        data: 解析后的 JSON 对象。

    Returns:
        DimensionScore 实例。
    """
    title = str(data.get("title", ""))
    summary = str(data.get("summary", ""))
    text = f"{title} {summary}"

    hits: list[str] = []
    for word in BUZZWORDS_CN:
        if word in text:
            hits.append(word)
    for word in BUZZWORDS_EN:
        if word.lower() in text.lower():
            hits.append(word)

    deduction = len(hits) * BUZZWORD_DEDUCTION
    score = max(0, 15 - deduction)

    if hits:
        return DimensionScore(
            "空洞词检测", score, 15,
            f"命中 {len(hits)} 个: {', '.join(hits)} (扣 {deduction} 分)",
        )
    return DimensionScore("空洞词检测", score, 15, "未命中空洞词")


SCORERS = [
    _score_summary_quality,
    _score_tech_depth,
    _score_format,
    _score_tags,
    _score_buzzwords,
]

# ============================================================
# 文件解析
# ============================================================


def resolve_files(patterns: list[str]) -> list[Path]:
    """解析输入模式，返回所有匹配的 JSON 文件路径列表。

    支持：
        - 单个文件路径
        - 通配符（如 *.json, knowleadge/articles/*.json）
        - 目录（自动扫描目录下所有 *.json）

    Args:
        patterns: 文件路径模式列表。

    Returns:
        去重并排序后的文件路径列表。
    """
    result: list[Path] = []
    for pattern in patterns:
        path = Path(pattern)
        if path.exists():
            if path.is_file():
                result.append(path.resolve())
            elif path.is_dir():
                found = sorted(path.resolve().glob("*.json"))
                if not found:
                    logger.warning("目录下无 JSON 文件: %s", pattern)
                result.extend(found)
        else:
            matched = list(Path().glob(pattern))
            if not matched:
                logger.warning("未匹配到文件: %s", pattern)
            result.extend(p.resolve() for p in matched)

    seen: set[str] = set()
    unique: list[Path] = []
    for fp in result:
        key = str(fp)
        if key not in seen:
            seen.add(key)
            unique.append(fp)
    return sorted(unique)


def analyze_file(filepath: Path) -> QualityReport | None:
    """分析单个 JSON 文件，返回质量报告。

    解析失败或无有效数据时返回 None。

    Args:
        filepath: JSON 文件路径。

    Returns:
        QualityReport 实例或 None。
    """
    try:
        raw = filepath.read_text(encoding="utf-8")
    except OSError as exc:
        logger.error("[SKIP] %s: 无法读取文件 (%s)", filepath.name, exc)
        return None

    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("[SKIP] %s: JSON 解析失败 (%s)", filepath.name, exc)
        return None

    if not isinstance(data, dict):
        logger.error("[SKIP] %s: 根元素不是 JSON 对象", filepath.name)
        return None

    dimensions = [scorer(data) for scorer in SCORERS]
    return QualityReport(filepath=filepath, dimensions=dimensions)


# ============================================================
# 可视化
# ============================================================


def format_bar(score: float, max_score: int, width: int = BAR_WIDTH) -> str:
    """生成单维度得分进度条。

    Args:
        score: 实际得分。
        max_score: 满分。
        width: 进度条字符宽度。

    Returns:
        可视化进度条字符串（█ 表示得分，░ 表示余量）。
    """
    if max_score <= 0:
        return "░" * width
    ratio = min(1.0, score / max_score)
    filled = round(ratio * width)
    return "█" * filled + "░" * (width - filled)


def format_progress(
    current: int, total: int, width: int = PROGRESS_WIDTH
) -> str:
    """生成文件处理进度条。

    Args:
        current: 当前处理序号（从 1 开始）。
        total: 文件总数。
        width: 进度条字符宽度。

    Returns:
        进度条字符串，如 [====>    ] 5/16。
    """
    ratio = current / total if total > 0 else 0
    filled = round(ratio * width)
    if filled == 0:
        inner = ">" + " " * (width - 1)
    elif filled >= width:
        inner = "=" * width
    else:
        inner = "=" * (filled - 1) + ">" + " " * (width - filled)
    return f"[{inner}] {current}/{total}"


# ============================================================
# CLI 入口
# ============================================================


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="知识条目 5 维度质量评分工具",
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="JSON 文件路径，支持通配符（如 *.json）",
    )
    args = parser.parse_args()

    all_files = resolve_files(args.files)
    if not all_files:
        logger.error("未找到任何 JSON 文件")
        sys.exit(1)

    total = len(all_files)
    reports: list[QualityReport] = []
    has_c_grade = False

    for idx, filepath in enumerate(all_files, 1):
        progress = format_progress(idx, total)
        logger.info("%s %s", progress, filepath.name)

        report = analyze_file(filepath)
        if report is None:
            continue
        reports.append(report)

        for dim in report.dimensions:
            bar = format_bar(dim.score, dim.max_score)
            logger.info(
                "  %s  %s %s/%s  %s",
                dim.name,
                bar,
                dim.score,
                dim.max_score,
                dim.details,
            )

        total_s = report.total_score
        grade = report.grade
        logger.info("  总分: %s/100  等级: %s", total_s, grade)
        logger.info("")

        if grade == "C":
            has_c_grade = True

    processed = len(reports)
    skipped = total - processed
    a_count = sum(1 for r in reports if r.grade == "A")
    b_count = sum(1 for r in reports if r.grade == "B")
    c_count = sum(1 for r in reports if r.grade == "C")

    logger.info("=== 评分汇总 ===")
    logger.info("处理文件: %d, 跳过: %d", processed, skipped)
    logger.info("A 级 (≥%d): %d", GRADE_A_THRESHOLD, a_count)
    logger.info("B 级 (≥%d): %d", GRADE_B_THRESHOLD, b_count)
    logger.info("C 级 (<%d): %d", GRADE_B_THRESHOLD, c_count)

    if skipped > 0:
        logger.info("注意: %d 个文件因读取或解析失败被跳过", skipped)
    if c_count > 0:
        logger.info("警告: %d 个文件评级为 C, 需关注", c_count)

    if has_c_grade:
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )
    main()
