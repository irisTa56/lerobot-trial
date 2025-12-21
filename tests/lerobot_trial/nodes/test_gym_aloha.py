from lerobot.envs.configs import AlohaEnv

from lerobot_trial.nodes.gym_aloha import make_env


def test_gym_aloha_observation() -> None:
    cfg = AlohaEnv()
    env = make_env(cfg)
    obs, _info = env.reset()

    assert obs["agent_pos"].shape == (14,)
    assert obs["pixels"]["top"].shape == (480, 640, 3)
