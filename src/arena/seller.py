import json

from src.llm.client import LLMClient


class SellerAgent:
    def __init__(self):
        self.llm = LLMClient()
        self.min_acceptable_price_factor = 1.1

    def respond(self, state: dict) -> dict:
        history = state.get("messages", [])
        last_message = history[-1]["content"] if history else "Start negotiation"
        base_price = state["base_price"]
        current_offer = state.get("current_price", 0)

        min_price = base_price * self.min_acceptable_price_factor

        system_prompt = f"""
        You are a tough Sales Representative.
        Product Base Cost: ${base_price}.
        Your Bottom Line (Min Price): ${min_price}.

        INSTRUCTIONS:
        1. If the buyer's offer is >= ${min_price}, reply with JSON: {{"decision": "ACCEPT", "reason": "..."}}
        2. If offer is too low, reject and propose a counter-offer slightly lower than your previous ask but higher than Min Price. 
           Reply JSON: {{"decision": "COUNTER", "price": <float>, "reason": "..."}}
        3. Be polite but firm.
        """

        user_prompt = f"Buyer says: {last_message}\nCurrent Offer: ${current_offer}"

        raw_response = self.llm.generate_response(system_prompt, user_prompt)

        try:
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            decision_data = json.loads(raw_response[start:end])
            return decision_data
        except:
            return {
                "decision": "COUNTER",
                "price": base_price * 1.5,
                "reason": "Parse Error, resetting price.",
            }
