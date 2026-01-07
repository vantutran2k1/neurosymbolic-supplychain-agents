from abc import ABC, abstractmethod

from src.entities import Proposal


class LLMInterface(ABC):
    @abstractmethod
    def generate(self, system_prompt: str, user_prompt: str) -> dict:
        pass


class OpenAILLM(LLMInterface):
    """
    Wrapper for OpenAI API (GPT-3.5/4).
    """

    def __init__(self, api_key: str, model="gpt-3.5-turbo"):
        # self.client = OpenAI(api_key=api_key) # Requires openai package
        self.model = model
        print(f"   [LLM] Initialized {model}")

    def generate(self, system_prompt: str, user_prompt: str) -> dict:
        # Mocking the actual API call for this implementation plan
        # In real research, uncomment the API call
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.7
        )
        content = response.choices[0].message.content
        """
        # Returning a dummy valid JSON for demonstration continuity
        return {"price": 12, "quantity": 5, "delivery_day": 1}


class LocalMockLLM(LLMInterface):
    """
    A deterministic 'LLM' for testing logic flows without API costs.
    It simulates 'correction' based on feedback.
    """

    def generate(self, system_prompt: str, user_prompt: str) -> dict:
        # Check if there is feedback in the prompt
        if "Guardian Violation" in user_prompt:
            # Simulate "Oh, I need to reduce quantity"
            return {"price": 12, "quantity": 2, "delivery_day": 0}  # Reduced quantity
        else:
            # Default aggressive move
            return {"price": 12, "quantity": 50, "delivery_day": 0}  # High quantity


class GenerativeModule:
    def __init__(self, llm: LLMInterface):
        self.llm = llm

    def draft_proposal(
        self,
        intent: str,
        graph_context_str: str,
        market_price: float,
        guardian_feedback: str = None,
    ) -> Proposal:

        # 1. Construct System Prompt (The Persona)
        system_prompt = """
        You are an autonomous Supply Chain Agent. 
        Your goal is to maximize profit while strictly adhering to business constraints.

        Output Format: JSON only.
        Example: {"price": 10.5, "quantity": 50, "delivery_day": 2}
        """

        # 2. Construct User Prompt (The Task)
        user_prompt = f"""
        [CONTEXT]
        Current Market Price: {market_price}
        History:
        {graph_context_str}

        [STRATEGY]
        Your Strategic Intent is: {intent.upper()}
        """

        if intent == "buy":
            user_prompt += "\nTask: Generate a BUY offer."
        elif intent == "sell":
            user_prompt += "\nTask: Generate a SELL offer."
        else:
            return Proposal("hold")

        # 3. Add Feedback (The Self-Correction Mechanism)
        if guardian_feedback:
            user_prompt += f"""

            [WARNING - PREVIOUS ATTEMPT REJECTED]
            Your last proposal was rejected by the Symbolic Guardian.
            Reason: {guardian_feedback}

            INSTRUCTION: Adjust your parameters (e.g., lower quantity, check price) to satisfy the constraint.
            """

        # 4. Invoke LLM
        try:
            response_json = self.llm.generate(system_prompt, user_prompt)

            # 5. Parse Output
            # Note: Real LLMs might wrap JSON in markdown blocks, parsing logic needed here
            price = float(response_json.get("price", market_price))
            qty = int(response_json.get("quantity", 1))

            # Return proper Proposal object
            if intent == "buy":
                return Proposal("buy", q_buy=qty, unit_price_buy=price)
            elif intent == "sell":
                return Proposal("sell", q_sell=qty, unit_price_sell=price)

        except Exception as e:
            print(f"LLM Generation Error: {e}")
            return Proposal("hold")  # Fail-safe

        return Proposal("hold")
