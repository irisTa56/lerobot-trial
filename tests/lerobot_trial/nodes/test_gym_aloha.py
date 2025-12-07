from lerobot.envs.configs import AlohaEnv
from lerobot.utils.constants import ACTION

from lerobot_trial.nodes.gym_aloha import make_env, observation_to_dora_outputs


def test_observation_to_dora_outputs() -> None:
    cfg = AlohaEnv()
    env = make_env(cfg)
    obs, _info = env.reset()
    assert {k for k, _ in observation_to_dora_outputs(obs)} == {
        cfg.features_map[k] for k in cfg.features if k != ACTION
    }
