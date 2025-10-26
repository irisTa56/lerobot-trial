import shutil
from dataclasses import dataclass
from pathlib import Path

from lerobot.configs import parser
from lerobot.datasets.dataset_tools import delete_episodes
from lerobot.datasets.lerobot_dataset import LeRobotDataset


@dataclass
class DeleteEpisodesConfig:
    repo_id: str
    root: str  # If `root is None`, you can use `lerobot-edit-dataset` command instead.
    episode_indices: list[int] | None = None


@parser.wrap()  # type: ignore[misc]
def main(cfg: DeleteEpisodesConfig) -> None:
    root = Path(cfg.root)
    old_root = root.parent / (root.name + "_old")

    if old_root.exists():
        raise RuntimeError(f"Old dataset path already exists: {old_root}")

    shutil.move(cfg.root, old_root)

    dataset_before = LeRobotDataset(repo_id=cfg.repo_id, root=old_root)
    num_episodes_before = dataset_before.num_episodes

    delete_episodes(
        dataset=dataset_before,
        episode_indices=cfg.episode_indices,
        repo_id=cfg.repo_id,
        output_dir=cfg.root,
    )

    dataset_after = LeRobotDataset(repo_id=cfg.repo_id, root=cfg.root)
    num_episodes_after = dataset_after.num_episodes

    print(f"Number of episodes changed: {num_episodes_before} -> {num_episodes_after}")

    if (
        input(f"Do you want to delete the backup directory '{old_root}'? [y/N]: ")
        .strip()
        .lower()
    ) == "y":
        shutil.rmtree(old_root)


if __name__ == "__main__":
    main()
