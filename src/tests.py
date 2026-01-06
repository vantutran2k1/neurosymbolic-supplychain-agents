from src.entities import MarketState, FactoryProfile, AgentState, Contract, Proposal
from src.guardian import SymbolicGuardian
from src.math_kernel import MathKernel


def verify_market_dynamics():
    print("--- Test 1: Market Dynamics (Price Inertia) ---")
    # Setup: Catalog Price = 10, Gamma = 0.9
    market = MarketState(product_id=1, catalog_price=10.0, gamma=0.9)

    print(f"Day 0 Price: {market.current_trading_price:.2f} (Expected: 10.00)")

    # Simulation: 10 days of trading at Price = 20.0, Quantity = 100
    for d in range(1, 11):
        market.update(daily_quantity=100, daily_avg_price=20.0)
        print(f"Day {d} Price: {market.current_trading_price:.2f}")

    # Validation Logic:
    # On Day 1, it should NOT be 20. It mixes history (Price 10) with new (Price 20).
    # Expected approx: (0.9*50*10 + 0.9*100*20) / (0.9*50 + 0.9*100) ≈ 16.66 (Rough estimate)
    assert 10.0 < market.current_trading_price < 20.0, "Price failed to update cleanly"
    print("✅ Market Price behavior confirmed: Smooth transition observed.")


verify_market_dynamics()


def verify_production_constraints():
    print("\n--- Test 2: Production Constraints (The Wallet Limit) ---")

    # Setup: Agent has $100. Production cost is $20/unit.
    profile = FactoryProfile(
        factory_id="TestFactory",
        level=1,
        lines=100,
        production_cost=20.0,
        storage_cost_mean=0,
        storage_cost_std=0,
        shortfall_penalty_mean=0,
        shortfall_penalty_std=0,
    )
    state = AgentState(balance=100.0, inventory=0)

    # Scenario: Agent signs a contract to sell 10 units (Requires $200 production cost)
    # The agent enters the day with 0 inventory, so they must produce everything.
    # Input contracts = 10 units (so material is available)
    input_c = [
        Contract("c1", "sup", "me", 0, 10, 5, 0, 0)
    ]  # Cost $50 (paid from balance?)
    # NOTE: Eq 2 constraint is q <= balance / m_a.
    # The balance check usually happens before paying input contracts in strict SCML,
    # or balance is "available funds". Let's assume balance pays for production.

    limit = MathKernel.calculate_production_limit(state, profile, input_c)

    # Calculation:
    # Financial Limit: Balance 100 / Cost 20 = 5 units max.
    # Physical Limit: Input 10 units.
    # Result should be 5.

    print(f"Contracted Quantity: 10")
    print(f"Financial Capability: {state.balance} / {profile.production_cost} = 5")
    print(f"Kernel Limit Output: {limit}")

    assert limit == 5, f"Constraint Error: Kernel allowed {limit}, expected 5"
    print("✅ Financial constraint strictly enforced.")


verify_production_constraints()


def verify_utility_math():
    print("\n--- Test 3: Utility & Penalties (Equation 6) ---")

    # Setup:
    # Produced & Sold: 5 units @ $30 (Revenue = 150)
    # Bought Inputs: 5 units @ $10 (Input Cost = 50)
    # Production Cost: 5 units @ $5 (Prod Cost = 25)
    # Operational Profit = 150 - 50 - 25 = 75

    # Penalty Scenario:
    # We Contracted to Sell 8, but only Produced 5. Shortfall = 3.
    # Shortfall Penalty Rate = 0.5 * Trading Price ($30) = $15/unit.
    # Total Penalty = 3 * 15 = 45.

    # Expected Final Utility = 75 - 45 = 30.

    profile = FactoryProfile("F1", 1, 10, 5.0, 0, 0, 0, 0)
    state = AgentState(1000, 0)
    state.current_shortfall_penalty = 0.5  # beta_a

    # Mock Contracts
    in_c = [Contract("in1", "s", "me", 0, 5, 10, 0, 0)]
    out_c = [
        Contract("out1", "me", "b", 1, 8, 30, 0, 0)
    ]  # High quantity (8) triggers shortfall

    profit = MathKernel.calculate_daily_profit(
        state=state,
        profile=profile,
        actual_production=5,
        input_contracts=in_c,
        output_contracts=out_c,
        trading_price_in=10,
        trading_price_out=30,
    )

    print(f"Calculated Profit: {profit}")
    print(f"Expected Profit: 30.0")

    assert abs(profit - 30.0) < 0.01, f"Math Error: Got {profit}, expected 30.0"
    print("✅ Utility function matches SCML Eq 6 exactly.")


verify_utility_math()


def verify_guardian():
    print("\n--- Test 4: Symbolic Guardian (Safety Layer) ---")

    # Setup: Factory with 10 lines, $100 balance, $5 prod cost.
    # Inventory: 0.
    prof = FactoryProfile(
        "G1",
        1,
        lines=10,
        production_cost=5.0,
        storage_cost_mean=0,
        storage_cost_std=0,
        shortfall_penalty_mean=0,
        shortfall_penalty_std=0,
    )
    state = AgentState(balance=100.0, inventory=0)
    guardian = SymbolicGuardian(prof)

    # --- Scenario A: The "Greedy" Hallucination ---
    # LLM says: "Buy 50 units at $10!" (Cost $500) -> Impossible (Balance $100)
    bad_proposal_1 = Proposal("buy", q_buy=50, unit_price_buy=10.0)
    is_valid = guardian.verify_proposal(state, bad_proposal_1)

    print(f"Scenario A (Cost $500 vs Bal $100): {'Allowed' if is_valid else 'BLOCKED'}")
    assert is_valid is False, "Guardian failed to block insolvent trade!"

    # --- Scenario B: The "Impossible Production" ---
    # LLM says: "Sell 15 units!" (Lines = 10) -> Impossible
    bad_proposal_2 = Proposal("sell", q_sell=15, unit_price_sell=20.0)
    is_valid = guardian.verify_proposal(state, bad_proposal_2)

    print(f"Scenario B (Sell 15 vs Lines 10): {'Allowed' if is_valid else 'BLOCKED'}")
    assert is_valid is False, "Guardian failed to block capacity violation!"

    # --- Scenario C: The "Valid" Trade ---
    # LLM says: "Buy 5 at $10 ($50) and Sell 5 ($25 prod cost). Total $75." -> Possible ($100 Bal)
    good_proposal = Proposal("buy_and_sell", q_buy=5, unit_price_buy=10.0, q_sell=5)
    is_valid = guardian.verify_proposal(state, good_proposal)

    print(
        f"Scenario C (Valid Trade $75 vs Bal $100): {'Allowed' if is_valid else 'BLOCKED'}"
    )
    assert is_valid is True, "Guardian blocked a valid trade!"

    print("✅ Symbolic Guardian functioning correctly.")


verify_guardian()
