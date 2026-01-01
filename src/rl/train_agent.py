import os

from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env

from src.rl.negotiation_env import SupplyChainNegotiationEnv


def train_rl_agent():
    env = SupplyChainNegotiationEnv()

    print("Checking environment compatibility...")
    check_env(env)
    print("Environment is valid.")

    model = PPO("MlpPolicy", env, verbose=1, learning_rate=0.0003)

    print("Starting training...")
    model.learn(total_timesteps=10000)

    save_path = "models/rl/negotiation_ppo"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    model.save(save_path)
    print(f"Model saved to {save_path}")


if __name__ == "__main__":
    train_rl_agent()
