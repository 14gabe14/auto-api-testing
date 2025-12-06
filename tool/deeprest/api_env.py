import os
from pathlib import Path

import gymnasium as gym
import numpy as np
from gymnasium import spaces

PRINT_LOG = False
OBS_MAX = 20  # It's an uint8! Choose 0-255


class ApiEnv(gym.Env):
    actions_count = 0
    observation = []

    def __init__(self):
        super(ApiEnv, self).__init__()

        pipes_dir = Path(os.getenv("DEEPREST_PIPES_DIR", Path.cwd()))
        self.j2p = pipes_dir / "j2p"
        self.p2j = pipes_dir / "p2j"

        for fifo in (self.j2p, self.p2j):
            try:
                os.mkfifo(fifo)
            except FileExistsError:
                pass

        print("Waiting for size of action space from Java.")
        with open(self.j2p, "r") as read_fifo:
            line = read_fifo.read()

        self.actions_count = int(line)
        print(f"Received number of actions: {self.actions_count}")
        if self.actions_count > 999:
            print("WARNING: more than 999 actions! Fix string encoding in step method.")

        self.action_space = spaces.Discrete(self.actions_count)
        self.observation_space = spaces.Box(
            low=0,
            high=OBS_MAX,
            shape=(1, self.actions_count),
            dtype=np.uint8,
        )

    def step(self, action):
        if PRINT_LOG:
            print(f"Next action is: {action}")

        with open(self.p2j, "w") as write_fifo:
            write_fifo.write(f"{action:04}")

        if PRINT_LOG:
            print("Action sent! Waiting for outcome from Java.")

        with open(self.j2p, "r") as read_fifo:
            line = read_fifo.read().strip()
        
        # Handle empty/null responses from RestTestGen (timeouts/errors)
        if not line or line.upper() == "NULL":
            # Use 0 as a sentinel for failed requests (not a valid HTTP status)
            status_code = 0
        else:
            try:
                status_code = int(line)
            except ValueError:
                # If we can't parse it, treat as failure
                print(f"WARNING: Received invalid status code '{line}', treating as failure")
                status_code = 0

        if PRINT_LOG:
            print(f"Operation tested with status code: {status_code}")

        observation, reward, terminated, truncated = self.compute_observation_and_reward(
            action, status_code
        )

        if PRINT_LOG:
            print(observation)

        info = {}
        return observation, reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        self.observation = np.zeros(
            shape=(1, self.actions_count),
            dtype=np.uint8,
        )
        info = {}
        return self.observation, info

    def render(self):
        return

    def close(self):
        return

    def compute_observation_and_reward(self, action, status_code):
        is_already_covered = self.observation[0][action] > 0
        # Status code 0 indicates timeout/failure (not a valid HTTP status)
        is_successful = status_code > 0 and 200 <= status_code < 300
        truncated = False

        if is_successful:
            if self.observation[0][action] < OBS_MAX:
                self.observation[0][action] += 1
            else:
                truncated = True

            reward = -100 if is_already_covered else 1000
        else:
            reward = -100 if is_already_covered else -1

        terminated = True
        i = 0
        while i < self.actions_count:
            if self.observation[0][i] == 0:
                terminated = False
                break
            i += 1

        return self.observation, reward, terminated, truncated
