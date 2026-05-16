"""GitHub API 工具模块，提供仓库信息获取功能。"""

import logging
import os
from typing import TypedDict

import requests

logger = logging.getLogger(__name__)


class RepoInfo(TypedDict):
    """仓库基本信息结构。"""

    full_name: str
    stars: int
    forks: int
    description: str


def get_repo_info(owner: str, repo: str) -> RepoInfo:
    """从 GitHub API 获取指定仓库的基本信息。

    Args:
        owner: 仓库所有者（用户名或组织名）。
        repo: 仓库名称。

    Returns:
        包含仓库全名、Star 数、Fork 数、描述的字典。

    Raises:
        ValueError: 缺少 GitHub Token 环境变量时抛出。
        requests.RequestException: API 请求失败时抛出。
    """
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        raise ValueError(
            "GITHUB_TOKEN 环境变量未设置，请先设置 GitHub Personal Access Token"
        )

    url = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    logger.info("正在获取仓库 %s/%s 的信息", owner, repo)
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()

    data = response.json()
    result: RepoInfo = {
        "full_name": data["full_name"],
        "stars": data["stargazers_count"],
        "forks": data["forks_count"],
        "description": data.get("description") or "",
    }

    logger.info("成功获取 %s 的信息：%d Stars, %d Forks", result["full_name"], result["stars"], result["forks"])
    return result
