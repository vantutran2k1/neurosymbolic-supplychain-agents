import json

import numpy as np
from stable_baselines3 import PPO

from src.guardian.validator import SymbolicGuardian
from src.llm.client import LLMClient
from src.rag.retriever import HybridRetriever


class StrategicAnalyst:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.llm = LLMClient()
        self.guardian = SymbolicGuardian()

        # TODO: read from DB
        self.business_constraints = {
            "budget": 5000.0,
            "max_warehouse_capacity": 1000,
            "current_stock": 800,
            "min_lead_time": 3,
        }

        self.rl_model_path = "models/rl/negotiation_ppo.zip"
        self.rl_agent = None
        try:
            self.rl_agent = PPO.load(self.rl_model_path)
            print("RL Strategic Model loaded successfully.")
        except:
            print("RL Model not found. Using heuristic fallback.")

    def analyze_market(self, user_query: str) -> str:
        context = self.retriever.search(user_query, top_k=3)

        system_prompt = """
        You are a Senior Supply Chain Analyst AI. Your goal is to optimize procurement strategies.

        INSTRUCTIONS:
        1. Base your answer STRICTLY on the provided 'Market Context'. Do not invent numbers.
        2. Analyze the price trends (Is it increasing/decreasing?).
        3. Evaluate supplier reliability.
        4. Give a concrete recommendation: BUY NOW, WAIT, or NEGOTIATE.
        5. Keep the tone professional, concise, and data-driven.
        """

        user_prompt_template = f"""
        USER QUESTION: "{user_query}"

        MARKET CONTEXT (Real-time data from Knowledge Graph):
        --------------------
        {context}
        --------------------

        Your Analysis and Recommendation:
        """

        response = self.llm.generate_response(system_prompt, user_prompt_template)
        return response

    def propose_action(self, user_query: str, max_retries=3) -> dict:
        context_text = self.retriever.search(user_query)

        market_price = 100.0
        cost = 80.0
        inventory = self.business_constraints["current_stock"]

        target_factor = self._get_optimal_price_factor(market_price, cost, inventory)
        target_price = market_price * target_factor

        system_prompt = f"""
        You are a Procurement Agent. 
        Your goal is to create a valid JSON procurement proposal based on constraints.

        CONSTRAINTS:
        - Budget: ${self.business_constraints['budget']}
        - Remaining Warehouse Space: {self.business_constraints['max_warehouse_capacity'] - self.business_constraints['current_stock']} units
        - Min Lead Time: {self.business_constraints['min_lead_time']} days
        - Recommended Target Price: ${target_price:.2f} (Based on inventory optimization).
        - Try to negotiate close to this price.

        OUTPUT FORMAT (Strict JSON):
        {{
            "reasoning": "brief explanation",
            "action": {{ "quantity": <int>, "unit_price": <float>, "delivery_days": <int> }}
        }}
        """

        conversation_history = f"QUERY: {user_query}\nCONTEXT: {context_text}"

        attempt_trace = []
        for attempt in range(max_retries):
            print(f"--- Attempt {attempt + 1} ---")

            raw_response = self.llm.generate_response(
                system_prompt, conversation_history
            )

            try:
                proposal_data = self._extract_json(raw_response)
                action = proposal_data["action"]

                is_valid, message = self.guardian.validate_proposal(
                    action, self.business_constraints
                )

                attempt_trace.append(
                    {
                        "attempt": attempt + 1,
                        "proposal": action,
                        "valid": is_valid,
                        "error": message if not is_valid else None,
                    }
                )

                if is_valid:
                    return {
                        "status": "success",
                        "final_proposal": proposal_data,
                        "trace": attempt_trace,
                    }
                else:
                    print(f"Guardian rejected: {message}")
                    feedback = f"\nSYSTEM FEEDBACK: Your previous proposal was REJECTED because: {message}. \nPlease propose a new valid action that fixes this specific error."

                    conversation_history += (
                        f"\nASSISTANT: {raw_response}\nUSER: {feedback}"
                    )

            except Exception as e:
                print(f"Parsing Error: {e}")
                conversation_history += (
                    f"\nSYSTEM: JSON Parsing Error. Please output valid JSON only."
                )

        return {
            "status": "failed",
            "error": "Max retries reached. Agent could not satisfy constraints.",
            "trace": attempt_trace,
        }

    def _get_optimal_price_factor(self, current_price, cost, inventory):
        if not self.rl_agent:
            return 1.1

        obs = np.array([current_price, cost, inventory, 0, 0], dtype=np.float32)

        action, _states = self.rl_agent.predict(obs, deterministic=True)
        price_factor = float(action[0])
        return price_factor

    @staticmethod
    def _extract_json(text):
        try:
            start = text.find("{")
            end = text.rfind("}") + 1
            return json.loads(text[start:end])
        except:
            raise ValueError("No JSON found")
