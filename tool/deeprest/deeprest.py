import os
import time

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback

from api_env import ApiEnv


def _get_int_env(name: str, default: int) -> int:
    """Parse an integer environment variable with a safe fallback."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


class TimeLimitCallback(BaseCallback):
    """Stops training once a wall-clock budget is reached."""

    def __init__(self, max_seconds: float):
        super().__init__()
        self.max_seconds = max_seconds
        self._start = time.time()

    def _on_step(self) -> bool:
        if self.max_seconds and (time.time() - self._start) >= self.max_seconds:
            return False
        return True


def main() -> None:
    episode_multiplier = _get_int_env("DEEPREST_EPISODE_MULTIPLIER", 20)
    total_timesteps = _get_int_env("DEEPREST_TOTAL_TIMESTEPS", 102_400)
    max_seconds = float(os.getenv("DEEPREST_MAX_SECONDS", "0") or 0)

    env = ApiEnv()
    env.reset()

    steps = episode_multiplier * env.actions_count
    if steps % 64 != 0:
        steps = steps - (steps % 64) + 64

    callback = TimeLimitCallback(max_seconds) if max_seconds else None

    model = PPO(
        policy="MlpPolicy",
        env=env,
        verbose=1,
        n_steps=steps,
    )

    model.learn(total_timesteps=total_timesteps, callback=callback)
    env.close()


if __name__ == "__main__":
    main()
