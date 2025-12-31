from src.llm.client import LLMClient
from src.rag.retriever import HybridRetriever


class StrategicAnalyst:
    def __init__(self):
        self.retriever = HybridRetriever()
        self.llm = LLMClient()

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
