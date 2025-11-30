"""Script to duplicate a repository on HuggingFace Hub.

Usage:
    python scripts/duplicate_repo.py <source_repo_id> <target_repo_id> [--repo_type model|dataset|space]
"""

from argparse import ArgumentParser

import requests
from huggingface_hub import HfFolder
from huggingface_hub.utils import (  # type: ignore[attr-defined]
    build_hf_headers,
    hf_raise_for_status,
)


def duplicate_repo(source_repo: str, target_repo: str, repo_type: str = "model") -> str:
    """Duplicate a repository on HuggingFace Hub.

    Args:
        source_repo: Source repository ID (e.g., 'username/repo-name')
        target_repo: Target repository ID (e.g., 'username/new-repo-name')
        repo_type: Type of repository ('model', 'dataset', or 'space')

    Returns:
        str: URL of the duplicated repository

    """
    token = HfFolder.get_token()
    print(f"Duplicating {repo_type} '{source_repo}' to '{target_repo}'...")

    r = requests.post(
        f"https://huggingface.co/api/{repo_type}s/{source_repo}/duplicate",
        headers=build_hf_headers(token=token),
        json={"repository": target_repo},
        timeout=10,
    )
    hf_raise_for_status(r)

    repo_url: str = r.json().get("url")
    print(f"✅ Successfully duplicated to {repo_url}")

    return repo_url


def main() -> None:
    parser = ArgumentParser(description="Duplicate a repository on HuggingFace Hub")
    parser.add_argument("source_repo", type=str, help="Source repository ID")
    parser.add_argument("target_repo", type=str, help="Target repository ID")
    parser.add_argument(
        "--repo_type",
        type=str,
        choices=["model", "dataset", "space"],
        default="model",
        help="Type of repository (default: model)",
    )

    args = parser.parse_args()
    duplicate_repo(
        source_repo=args.source_repo,
        target_repo=args.target_repo,
        repo_type=args.repo_type,
    )


if __name__ == "__main__":
    main()
