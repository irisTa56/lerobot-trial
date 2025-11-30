from lerobot.envs.configs import AlohaEnv

from lerobot_trial.nodes.gym_aloha import OBSERVATION_CHANNELS_MAP


def test_observation_name_compatibility() -> None:
    cfg = AlohaEnv()
    for key, channel in OBSERVATION_CHANNELS_MAP.items():
        assert cfg.features_map[key] == channel
