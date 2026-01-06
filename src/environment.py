import random

from src.config import SimulationConfig
from src.entities import MarketState, Product, AgentState, FactoryProfile, Contract


class SCMLEnv:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.day = 0
        self.agents: dict[str, AgentState] = {}
        self.profiles: dict[str, FactoryProfile] = {}
        self.markets: dict[int, MarketState] = {}
        self.products: dict[int, Product] = {}

        self._initialize_world()

    def _initialize_world(self):
        # 1. Setup Products & Markets
        for pid in range(self.config.n_products):
            # Price increases by level to ensure profit margin exists
            base_price = 10 * (pid + 1) + (5 * pid)
            self.products[pid] = Product(pid, f"Prd_{pid}", base_price)
            self.markets[pid] = MarketState(pid, base_price, self.config.gamma)

        # 2. Setup Agents (Factories)
        for i in range(self.config.n_agents):
            aid = f"Agent_{i}"
            # Assign level: 0 (Supplier), 1 (Manufacturer), 2 (Retailer/Consumer)
            # Simple round-robin assignment for balance
            level = i % (self.config.n_products - 1)

            # Factory Config [cite: 591]
            profile = FactoryProfile(
                factory_id=aid,
                level=level,
                lines=10,
                production_cost=2.0 + level,  # Higher cost for higher complexity
                storage_cost_mean=0.1,
                storage_cost_std=0.01,
                shortfall_penalty_mean=0.5,
                shortfall_penalty_std=0.05,
            )
            self.profiles[aid] = profile

            # Initial Balance [cite: 598] - enough to run for a while
            self.agents[aid] = AgentState(balance=1000.0, inventory=5)

    def step(self, actions: list[Contract]) -> dict:
        """
        Advances the simulation by one day.
        actions: A list of NEGOTIATED contracts (signed by agents).
        """
        # --- 1. Daily Initialization [cite: 506] ---
        # Sample stochastic costs for the day
        for aid, agent in self.agents.items():
            prof = self.profiles[aid]
            agent.current_storage_cost = max(
                0, random.gauss(prof.storage_cost_mean, prof.storage_cost_std)
            )
            agent.current_shortfall_penalty = max(
                0, random.gauss(prof.shortfall_penalty_mean, prof.shortfall_penalty_std)
            )

        # --- 2. Generate Exogenous Contracts [cite: 503] ---
        # (World buys from L-last, World sells to L-0)
        exogenous_contracts = self._generate_exogenous_contracts()
        all_contracts = actions + exogenous_contracts

        # --- 3. Execution Phase [cite: 288] ---
        # Critical: Order matters! Raw(0) -> Final(N).
        # This allows intermediate factories to receive goods before producing.

        # Group contracts by product to calculate market updates
        daily_trades = {p: {"q": 0, "val": 0.0} for p in self.markets}

        # We process execution "simultaneously" for accounting,
        # but logically input arrives before production.

        # ... (Execution logic uses SCMLMathKernel from Step 1.2) ...
        # [Abridged for brevity: We iterate agents, call calculate_production_limit,
        #  calculate_actual_production, calculate_profit, update balances]

        # --- 4. Market Updates [cite: 502] ---
        for contract in all_contracts:
            pid = contract.product_id
            daily_trades[pid]["q"] += contract.quantity
            daily_trades[pid]["val"] += contract.quantity * contract.unit_price

        for pid, market in self.markets.items():
            q = daily_trades[pid]["q"]
            if q > 0:
                avg_p = daily_trades[pid]["val"] / q
                market.update(q, avg_p)

        self.day += 1

        # Return Snapshot for Knowledge Graph
        return self._capture_snapshot(all_contracts)

    def _capture_snapshot(self, contracts):
        """
        Returns data ready for Neo4j ingestion.
        """
        return {
            "day": self.day,
            "market_prices": {
                p: m.current_trading_price for p, m in self.markets.items()
            },
            "agents": {
                aid: {"bal": a.balance, "inv": a.inventory}
                for aid, a in self.agents.items()
            },
            "contracts": contracts,
        }

    def _generate_exogenous_contracts(self):
        # Implementation of randomized world supply/demand
        return []  # Placeholder
