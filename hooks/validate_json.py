#!/usr/bin/env python3
"""知识条目 JSON 文件校验工具。

用法:
    python hooks/validate_json.py <json_file> [json_file2 ...]
    python hooks/validate_json.py knowleadge/articles/*.json
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

logger = logging.getLogger("validate_json")

REQUIRED_FIELDS: dict[str, type] = {
    "id": str,
    "title": str,
    "source_url": str,
    "summary": str,
    "tags": list,
    "status": str,
}

VALID_STATUSES = frozenset({"draft", "review", "published", "archived"})
VALID_AUDIENCES = frozenset({"beginner", "intermediate", "advanced"})
ID_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{3}$")
URL_PATTERN = re.compile(r"^https?://")
MIN_SUMMARY_LENGTH = 20
MIN_TAGS_COUNT = 1
SCORE_MIN = 1
SCORE_MAX = 10


def resolve_files(patterns: list[str]) -> list[Path]:
    """解析输入模式，返回所有匹配的 JSON 文件路径列表。

    Args:
        patterns: 文件路径模式列表（支持通配符和目录）。

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


def validate_file(filepath: Path) -> list[str]:
    """校验单个 JSON 文件，返回错误信息列表。

    Args:
        filepath: JSON 文件路径。

    Returns:
        错误信息字符串列表，无错误时为空列表。
    """
    errors: list[str] = []

    try:
        raw = filepath.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"无法读取文件: {exc}"]

    try:
        data: Any = json.loads(raw)
    except json.JSONDecodeError as exc:
        return [f"JSON 解析失败: {exc}"]

    if not isinstance(data, dict):
        return ["根元素必须是 JSON 对象"]

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in data:
            errors.append(f"缺少必填字段: {field}")
            continue
        actual = data[field]
        if not isinstance(actual, expected_type):
            errors.append(
                f"字段 {field} 类型错误: "
                f"期望 {expected_type.__name__}，"
                f"实际 {type(actual).__name__}"
            )

    if errors:
        return errors

    if not ID_PATTERN.match(str(data["id"])):
        errors.append(
            f"ID 格式错误: {data['id']}，"
            f"期望格式 {{YYYY}}-{{MM}}-{{DD}}-{{NNN}}"
            f"（如 2026-03-17-001）"
        )

    status = str(data["status"])
    if status not in VALID_STATUSES:
        errors.append(
            f"status 值无效: {status}，"
            f"允许值: {', '.join(sorted(VALID_STATUSES))}"
        )

    url = str(data["source_url"])
    if not URL_PATTERN.match(url):
        errors.append(
            f"source_url 格式无效: {url}，"
            f"应以 http:// 或 https:// 开头"
        )

    summary = str(data["summary"])
    if len(summary) < MIN_SUMMARY_LENGTH:
        errors.append(
            f"summary 过短: {len(summary)} 字，"
            f"最少需要 {MIN_SUMMARY_LENGTH} 字"
        )

    tags = data["tags"]
    if len(tags) < MIN_TAGS_COUNT:
        errors.append(f"tags 至少需要 {MIN_TAGS_COUNT} 个标签")

    if "score" in data:
        score = data["score"]
        if isinstance(score, bool) or not isinstance(score, (int, float)):
            errors.append(
                f"score 类型错误: "
                f"期望 int/float，实际 {type(score).__name__}"
            )
        elif score < SCORE_MIN or score > SCORE_MAX:
            errors.append(
                f"score 值无效: {score}，"
                f"应在 {SCORE_MIN}-{SCORE_MAX} 范围内"
            )

    if "audience" in data:
        audience = str(data["audience"])
        if audience not in VALID_AUDIENCES:
            errors.append(
                f"audience 值无效: {audience}，"
                f"允许值: {', '.join(sorted(VALID_AUDIENCES))}"
            )

    return errors


def main() -> None:
    """CLI 入口。"""
    parser = argparse.ArgumentParser(
        description="校验知识条目 JSON 文件",
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
    passed = 0
    failed = 0

    for filepath in all_files:
        file_errors = validate_file(filepath)
        if file_errors:
            failed += 1
            logger.error("[FAIL] %s", filepath)
            for err in file_errors:
                logger.error("  - %s", err)
        else:
            passed += 1
            logger.info("[PASS] %s", filepath)

    logger.info("")
    logger.info("=== 校验汇总 ===")
    logger.info("总计: %d 个文件", total)
    logger.info("通过: %d", passed)
    logger.info("失败: %d", failed)

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
        stream=sys.stdout,
    )
    main()
