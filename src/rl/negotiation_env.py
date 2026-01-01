import gymnasium as gym
import numpy as np
from gymnasium import spaces

from src.arena.seller import SellerAgent
from src.database.connector import Neo4jConnector
from src.guardian.validator import SymbolicGuardian


class SupplyChainNegotiationEnv(gym.Env):
    def __init__(self):
        super(SupplyChainNegotiationEnv, self).__init__()

        self.MIN_VAL = 0.0
        self.MAX_VAL = 10000.0

        self.action_space = spaces.Box(low=0.5, high=2.0, shape=(1,), dtype=np.float32)

        self.observation_space = spaces.Box(
            low=self.MIN_VAL, high=self.MAX_VAL, shape=(5,), dtype=np.float32
        )

        self.db = Neo4jConnector()
        self.max_rounds = 10
        self.current_round = 0
        self.product_data = None

        self.market_price = 100.0
        self.cost = 80.0
        self.inventory = 100.0
        self.last_opponent_offer = 0.0

    def _get_obs(self):
        obs = np.array(
            [
                self.market_price,
                self.cost,
                self.inventory,
                self.current_round,
                self.last_opponent_offer,
            ],
            dtype=np.float32,
        )

        obs = np.clip(obs, self.MIN_VAL, self.MAX_VAL)

        return obs

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        query = """
        MATCH (p:Product) 
        WITH p, rand() AS r 
        ORDER BY r LIMIT 1 
        RETURN p.base_price as price, 
               COALESCE(p.production_cost, p.base_price * 0.8) as cost
        """
        data = self.db.run_query(query)

        if not data:
            self.product_data = {"price": 100.0, "cost": 80.0}
        else:
            self.product_data = data[0]

        self.market_price = float(self.product_data.get("price", 100.0))
        self.cost = float(self.product_data.get("cost", self.market_price * 0.8))

        self.inventory = float(np.random.randint(100, 1000))
        self.current_round = 0.0
        self.last_opponent_offer = 0.0

        return self._get_obs(), {}

    def step(self, action):
        price_factor = float(np.clip(action[0], 0.5, 2.0))

        my_offer_price = self.market_price * price_factor
        opponent_acceptance_threshold = self.market_price * 1.1

        terminated = False
        truncated = False

        if my_offer_price <= opponent_acceptance_threshold:
            terminated = True
            profit = my_offer_price - self.cost
            reward = profit if profit > 0 else -10.0
            reward += (self.max_rounds - self.current_round) * 2
        else:
            self.current_round += 1.0
            reward = -1.0

            self.last_opponent_offer = max(0.0, my_offer_price * 0.95)

            if self.current_round >= self.max_rounds:
                terminated = True
                reward = -50.0

        return self._get_obs(), reward, terminated, truncated, {"offer": my_offer_price}


class ConstraintAwareNegotiationEnv(gym.Env):
    def __init__(self):
        super(ConstraintAwareNegotiationEnv, self).__init__()

        self.action_space = spaces.Box(
            low=np.array([0.5, 0.1]), high=np.array([2.0, 1.0]), dtype=np.float32
        )

        self.observation_space = spaces.Box(
            low=0, high=10000, shape=(6,), dtype=np.float32
        )

        self.db = Neo4jConnector()
        self.guardian = SymbolicGuardian()
        self.seller = SellerAgent()

        self.constraints = {}

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.constraints = {
            "budget": np.random.uniform(2000, 5000),
            "max_warehouse_capacity": 1000,
            "current_stock": np.random.randint(100, 900),
            "min_lead_time": 3,
        }

        self.market_price = 100.0
        self.cost = 80.0

        self.current_round = 0.0
        self.last_opponent_offer = 0.0

        return self._get_obs(), {}

    def _get_obs(self):
        obs = np.array(
            [
                self.market_price,
                self.cost,
                self.constraints["current_stock"],
                self.constraints["budget"],
                self.current_round,
                self.last_opponent_offer,
            ],
            dtype=np.float32,
        )
        return np.clip(obs, 0, 10000)

    def step(self, action):
        # 1. Decode Action
        price_factor = float(action[0])
        qty_factor = float(action[1])

        # Tính toán đề xuất cụ thể
        remaining_space = (
            self.constraints["max_warehouse_capacity"]
            - self.constraints["current_stock"]
        )
        target_quantity = int(remaining_space * qty_factor)
        target_price = self.market_price * price_factor

        proposal = {
            "quantity": target_quantity,
            "unit_price": target_price,
            "delivery_days": 5,
        }

        is_valid, violation_reason = self.guardian.validate_proposal(
            proposal, self.constraints
        )

        terminated = False
        truncated = False

        if not is_valid:
            reward = -10.0
            info = {"violation": violation_reason}
        else:
            state_dict = {
                "base_price": self.market_price,
                "current_price": target_price,
                "messages": [{"content": f"Offer {target_price}"}],
            }

            seller_decision = self.seller.respond(state_dict)

            if seller_decision["decision"] == "ACCEPT":
                terminated = True
                profit = (self.market_price * 1.2 - target_price) * target_quantity
                reward = profit / 1000.0
                reward += (10 - self.current_round) * 0.1
            else:
                reward = -0.1
                self.current_round += 1
                if self.current_round >= 10:
                    terminated = True
                    reward = -5.0

            info = {"seller_msg": seller_decision.get("reason")}

        return self._get_obs(), reward, terminated, truncated, info
