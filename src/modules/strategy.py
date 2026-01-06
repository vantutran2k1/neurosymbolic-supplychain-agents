import json
import os
import re
from typing import TypedDict, Any

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda  # <--- KEY IMPORT
from langgraph.graph import StateGraph, END


# ==========================================
# 1. THE STATE
# ==========================================
class AgentState(TypedDict):
    # Context (Inputs)
    step: int
    cash: float
    product_id: int

    # Layer 1: Perception
    context_data: dict

    # Layer 2: Strategy
    decision: str

    # Layer 3: Tactics
    min_price: float
    max_price: float


# ==========================================
# 2. THE STRATEGIC BRAIN (HCN)
# ==========================================
class StrategicBrain:
    def __init__(self, knowledge_graph):
        self.kg = knowledge_graph

        # SWITCH: Use Real or Mock LLM
        if os.environ.get("OPENAI_API_KEY"):
            from langchain_openai import ChatOpenAI

            self.llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
            print("🧠 Brain: Powered by OpenAI GPT-3.5")
        else:
            # FIX: Wrap the function in RunnableLambda to make it pipe-able (|)
            self.llm = RunnableLambda(self._mock_logic)
            print("🧠 Brain: Powered by Mock Logic (Simulation)")

        self.workflow = self._build_hcn()

    def _mock_logic(self, prompt_input: Any) -> AIMessage:
        """
        The Logic for the Mock LLM.
        Reads the prompt string, performs regex "reasoning", and returns JSON.
        """
        # 1. Convert input (PromptValue or Message) to string
        text = str(prompt_input)

        # 2. Extract context using Regex (The "Neuro" simulation)
        # We look for "Wealth Ratio: 0.4" inside the prompt text
        wealth_match = re.search(r"Wealth Ratio:\s*([\d\.]+)", text)
        wealth_ratio = float(wealth_match.group(1)) if wealth_match else 1.0

        # 3. Apply Decision Logic (HCN Policy)
        if wealth_ratio < 0.5:
            decision = "SURVIVAL"
            min_pct = 0.80
            max_pct = 1.00
        elif wealth_ratio > 1.5:
            decision = "DOMINANCE"
            min_pct = 1.10
            max_pct = 1.30
        else:
            decision = "GROWTH"
            min_pct = 0.95
            max_pct = 1.05

        # 4. Generate JSON Response
        response_json = json.dumps(
            {
                "decision": decision,
                "min_pct": min_pct,
                "max_pct": max_pct,
                "reasoning": f"MockLLM saw wealth ratio {wealth_ratio}",
            }
        )

        return AIMessage(content=response_json)

    def _build_hcn(self):
        """Constructs the Hierarchical Consensus Network."""

        # NODE A: ANALYST (Perception Layer)
        def analyst(state: AgentState):
            # Uses RAG4DyG + DySK-Attn logic
            data = self.kg.retrieve_context(state["product_id"], state["step"])
            return {"context_data": data}

        # NODE B: STRATEGIST (Strategic Layer - LLM)
        def strategist(state: AgentState):
            data = state["context_data"]

            # Avoid division by zero
            comp_cash = data["competitor_cash"]
            wealth_ratio = state["cash"] / comp_cash if comp_cash > 0 else 1.0
            avg_price = data["avg_price"]

            # 1. Create Prompt
            # The prompt includes the data we extracted in the Analyst step
            prompt = ChatPromptTemplate.from_template(
                """
                You are a strategic factory manager.
                Context:
                - Wealth Ratio: {ratio} (My Cash / Avg Competitor Cash)
                - Market Trend: {trend}

                Decide a strategy:
                - SURVIVAL (If poor): Sell low.
                - GROWTH (If avg): Follow market.
                - DOMINANCE (If rich): Sell high.

                Return JSON: {{ "decision": "...", "min_pct": float, "max_pct": float }}
                """
            )

            # 2. Build Chain (Now works because self.llm is a Runnable)
            chain = prompt | self.llm | JsonOutputParser()

            try:
                # 3. Invoke
                res = chain.invoke(
                    {"ratio": round(wealth_ratio, 2), "trend": data["market_trend"]}
                )

                # 4. Calculate final prices
                return {
                    "decision": res["decision"],
                    "min_price": avg_price * res["min_pct"],
                    "max_price": avg_price * res["max_pct"],
                }
            except Exception as e:
                print(f"Brain Error: {e}")
                # Fallback
                return {
                    "decision": "FALLBACK",
                    "min_price": avg_price,
                    "max_price": avg_price,
                }

        # Build Graph
        workflow = StateGraph(AgentState)
        workflow.add_node("analyst", analyst)
        workflow.add_node("strategist", strategist)

        workflow.set_entry_point("analyst")
        workflow.add_edge("analyst", "strategist")
        workflow.add_edge("strategist", END)

        return workflow.compile()

    def think(self, step, cash, product_id):
        """Runs the HCN."""
        inputs = {
            "step": step,
            "cash": cash,
            "product_id": product_id,
            "context_data": {},
            "decision": "WAIT",
            "min_price": 0.0,
            "max_price": 0.0,
        }
        return self.workflow.invoke(inputs)
