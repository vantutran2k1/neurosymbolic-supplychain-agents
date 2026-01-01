import os

from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor

from src.rl.callbacks import ViolationTrackingCallback
from src.rl.negotiation_env import ConstraintAwareNegotiationEnv


def run_experiment(exp_name, use_constraints=True, total_timesteps=100000):
    log_dir = f"logs/{exp_name}"
    os.makedirs(log_dir, exist_ok=True)

    env = ConstraintAwareNegotiationEnv()

    env = Monitor(env, log_dir)

    model = PPO("MlpPolicy", env, verbose=1, tensorboard_log=f"tensorboard/{exp_name}")

    print(f"STARTING EXPERIMENT: {exp_name}")
    model.learn(total_timesteps=total_timesteps, callback=ViolationTrackingCallback())
    model.save(f"models/{exp_name}")
    print(f"FINISHED: {exp_name}")


if __name__ == "__main__":
    run_experiment("neuro_symbolic_agent_v1", total_timesteps=50000)
