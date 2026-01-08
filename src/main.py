import json
import pandas as pd
import numpy as np
from typing import List, Dict
from lab_data_generator import LabSimulation
from factory_agent import FactoryAgent
from agent_workflow import build_research_agent, AgentState

# --- 1. The Wrapper Agent (Adapting LangGraph to Simulator) ---

class NeuroSymbolicPlayer(FactoryAgent):
    """
    Wraps the LangGraph workflow into the standard FactoryAgent interface
    expected by the simulator.
    """
    def __init__(self, agent_id, num_lines, balance, cost, config: Dict):
        super().__init__(agent_id, num_lines, balance, cost)
        self.config = config
        self.brain = build_research_agent()
        self.safety_violation_count = 0

    def create_negotiator(self, is_buyer, trading_price):
        # We override this to return a 'NeuroNegotiator' proxy
        return NeuroNegotiator(self, is_buyer, trading_price)

class NeuroNegotiator:
    """
    Proxy that delegates decision making to the LangGraph brain.
    """
    def __init__(self, parent, is_buyer, trading_price):
        self.parent = parent
        self.is_buyer = is_buyer
        self.trading_price = trading_price
        self.agent_id = parent.agent_id

    def propose(self, state: Dict):
        # 1. Construct State Object
        agent_state = {
            "negotiation_data": {
                "step": state['negotiation_step'],
                "max_steps": state['max_steps'],
                "current_day": state['current_day'],
                "opponent_id": "Unknown", # (Simulator needs to pass this ideally)
                "trading_price": self.trading_price,
                "is_buyer": self.is_buyer
            },
            "private_state": {
                "balance": self.parent.balance,
                "num_lines": self.parent.num_lines,
                "inventory": self.parent.inventory,
                "production_cost": self.parent.production_cost
            },
            "config": self.parent.config,
            # Init empty internal fields
            "context_vector": None, "verbal_strategy": None,
            "draft_proposal": None, "final_offer": None,
            "safety_violations": []
        }

        # 2. Invoke Brain
        result = self.parent.brain.invoke(agent_state)

        # 3. Record Metrics
        if result['safety_violations']:
            self.parent.safety_violation_count += len(result['safety_violations'])

        # 4. Convert to Offer Object
        from agent_zoo import Offer
        final = result['final_offer']
        return Offer(
            quantity=final['quantity'],
            delivery_day=state['current_day'],
            unit_price=final['price']
        )

    def respond(self, offer, state):
        # For simplicity in this experiment, we use a heuristic acceptance
        # based on the price our brain *would* have proposed.
        my_proposal = self.propose(state)

        from agent_zoo import ResponseType
        if self.is_buyer:
            if offer.unit_price <= my_proposal.unit_price:
                return ResponseType.ACCEPT
        else:
            if offer.unit_price >= my_proposal.unit_price:
                return ResponseType.ACCEPT
        return ResponseType.REJECT

# --- 2. The Experiment Controller ---

class ResearchExperiment:
    def __init__(self, num_days=10):
        self.num_days = num_days
        self.results = []

    def run_condition(self, condition_name: str, config: Dict):
        print(f"\n🧪 Running Condition: {condition_name} ...")

        # 1. Setup Simulation
        sim = LabSimulation(num_days=self.num_days, log_file=f"logs_{condition_name}.json")

        # 2. Inject OUR Agent (Replacing one of the default manufacturers)
        # We replace "Manufacturer_linear_0" with our Neuro-Symbolic Bot
        target_idx = 0
        our_agent = NeuroSymbolicPlayer(
            agent_id="Neuro_Research_Bot",
            num_lines=10,
            balance=1000,
            cost=3.0,
            config=config
        )
        sim.manufacturers[target_idx] = our_agent

        # 3. Run Sim
        sim.run()

        # 4. Collect Metrics
        # (Balance at end represents profit)
        profit = our_agent.balance - 1000
        violations = our_agent.safety_violation_count

        print(f"   -> Result: Profit=${profit:.2f}, Safety Violations={violations}")

        self.results.append({
            "Condition": condition_name,
            "Profit": profit,
            "Violations": violations,
            "Config": str(config)
        })

    def run_full_study(self):
        # A. Baseline 1: Unsafe & Blind (Pure Neural)
        self.run_condition("Baseline_Neural", {
            "use_rag": False, "use_llm": False, "use_smt": False, "agent_id": "Bot"
        })

        # B. Baseline 2: Symbolic Safe (Rules Only)
        self.run_condition("Baseline_Symbolic", {
            "use_rag": False, "use_llm": False, "use_smt": True, "agent_id": "Bot"
        })

        # C. Proposed: Full Neuro-Symbolic
        self.run_condition("Proposed_Full", {
            "use_rag": True, "use_llm": True, "use_smt": True, "agent_id": "Bot"
        })

        # Save Report
        df = pd.DataFrame(self.results)
        df.to_csv("experiment_results.csv", index=False)
        print("\n✅ Study Complete. Results saved to experiment_results.csv")
        print(df)

if __name__ == "__main__":
    study = ResearchExperiment(num_days=15) # Short run for testing
    study.run_full_study()