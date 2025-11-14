#!/usr/bin/env python3
"""
Script to publish trained models to HuggingFace Hub.

Usage:
    python scripts/publish_policy.py outputs/train/pretrained_model
"""

from argparse import ArgumentParser
from pathlib import Path

from huggingface_hub import HfApi
from lerobot.configs.policies import PreTrainedConfig
from lerobot.configs.train import TrainPipelineConfig
from lerobot.policies.factory import get_policy_class


def publish_model_to_hub(model_dir: Path) -> None:
    """
    Publish a trained model to HuggingFace Hub.

    Args:
        model_dir: Path to the directory containing the trained model files
    """
    model_dir = Path(model_dir)

    config = PreTrainedConfig.from_pretrained(model_dir)
    train_config = TrainPipelineConfig.from_pretrained(model_dir)
    policy = get_policy_class(config.type).from_pretrained(model_dir, config=config)

    repo_id = config.repo_id
    print(f"Publishing model to HuggingFace Hub: {repo_id}")

    api = HfApi()
    repo_url = api.create_repo(repo_id=repo_id, private=config.private, exist_ok=True)
    print(f"Repository created/accessed: {repo_url.repo_id}")

    print("Generating model card...")
    card = policy.generate_model_card(
        train_config.dataset.repo_id,
        model_type=config.type,
        license=config.license,
        tags=config.tags,
    )
    card.save(model_dir / "README.md")

    print("Uploading to HuggingFace Hub...")
    commit_info = api.upload_folder(
        repo_id=repo_id,
        repo_type="model",
        folder_path=model_dir,
        commit_message="Upload policy weights, configs and model card",
        allow_patterns=["*.safetensors", "*.json", "*.yaml", "*.md"],
        ignore_patterns=["*.tmp", "*.log"],
    )

    print(f"✅ Model successfully pushed to {commit_info.commit_url}")
    print(f"🔗 View your model at: https://huggingface.co/{repo_id}")


def main() -> None:
    parser = ArgumentParser(description="Publish trained model to HuggingFace Hub")
    parser.add_argument(
        "model_dir",
        type=str,
        help="Path to the directory containing the trained model files",
    )

    args = parser.parse_args()
    publish_model_to_hub(model_dir=Path(args.model_dir))


if __name__ == "__main__":
    main()
