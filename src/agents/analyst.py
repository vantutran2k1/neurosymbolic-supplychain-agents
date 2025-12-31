import json

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

    def propose_action(self, user_query: str) -> dict:
        context_text = self.retriever.search(user_query)

        system_prompt = f"""
        You are a Procurement Agent. 
        Based on the User Query and Market Context, generate a procurement proposal JSON.

        CURRENT CONSTRAINTS (For your reference):
        - Budget: ${self.business_constraints['budget']}
        - Warehouse Free Space: {self.business_constraints['max_warehouse_capacity'] - self.business_constraints['current_stock']} units

        OUTPUT FORMAT (Strict JSON):
        {{
            "reasoning": "Explain why you chose these numbers...",
            "action": {{
                "quantity": <integer>,
                "unit_price": <float>,
                "delivery_days": <integer>
            }}
        }}
        """

        user_prompt = f"QUERY: {user_query}\nCONTEXT: {context_text}"

        raw_response = self.llm.generate_response(system_prompt, user_prompt)
        try:
            start = raw_response.find("{")
            end = raw_response.rfind("}") + 1
            json_str = raw_response[start:end]
            proposal_data = json.loads(json_str)

            action = proposal_data["action"]

            is_valid, message = self.guardian.validate_proposal(
                action, self.business_constraints
            )

            final_result = {
                "llm_proposal": proposal_data,
                "validation": {"is_valid": is_valid, "status": message},
            }
            return final_result

        except json.JSONDecodeError:
            return {
                "error": "Failed to parse LLM response to JSON",
                "raw": raw_response,
            }
        except Exception as e:
            return {"error": f"System error: {str(e)}"}
