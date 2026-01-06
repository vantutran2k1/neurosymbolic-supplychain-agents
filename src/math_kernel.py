import math

from src.entities import AgentState, FactoryProfile, Contract


class MathKernel:
    @staticmethod
    def calculate_production_limit(
        state: AgentState, profile: FactoryProfile, input_contracts: list[Contract]
    ) -> int:
        """
        Calculates Q_a^p (Total Producible Quantity) based on Eq (2).
        Q_a^p = min(inventory + input_contracts, balance / production_cost)
        """
        # Quantity from contracts
        q_in = sum(c.quantity for c in input_contracts)

        # Total available inputs
        total_inputs = state.inventory + q_in

        # Financial constraint: How many units can we afford to manufacture?
        # Constraint: q <= balance / m_a
        financial_cap = (
            math.floor(state.balance / profile.production_cost)
            if profile.production_cost > 0
            else float("inf")
        )

        # The physical limit is the minimum of material availability and financial ability
        return min(total_inputs, financial_cap)

    @staticmethod
    def calculate_actual_production(
        profile: FactoryProfile,
        producible_quantity: int,
        output_contracts: list[Contract],
    ) -> int:
        """
        Calculates Q*out (Actual Produced/Sold) based on Eq (3) [cite: 411-412].
        Must satisfy:
        1. <= Total contracted output (Demand)
        2. <= Production lines (lambda_a)
        3. <= Producible quantity (Q_a^p from inputs)
        """
        q_contracted_out = sum(c.quantity for c in output_contracts)

        # Physical constraints
        limit_lines = profile.lines
        limit_inputs = producible_quantity

        # We produce as much as we can to satisfy contracts, limited by constraints
        return min(q_contracted_out, limit_lines, limit_inputs)

    @staticmethod
    def calculate_daily_profit(
        state: AgentState,
        profile: FactoryProfile,
        actual_production: int,  # Q*out
        input_contracts: list[Contract],
        output_contracts: list[Contract],
        trading_price_in: float,
        trading_price_out: float,
    ) -> float:
        """
        Implements SCML Equation (6) strictly.
        Profit = Revenue - InputCosts - ProdCosts - StoragePenalty - ShortfallPenalty
        """
        # 1. Revenue: sum(p_c * q*_c) for satisfied outputs
        # Simplified: In SCML Std, if we produce Q*out, we fulfill highest value contracts first.
        # For simulation accuracy, we assume proportional fulfillment or greedy by price.
        # Here we calculate exact revenue based on the specific contracts filled.
        # (Logic for sorting contracts by price would happen before this call [cite: 410])

        # Placeholder for sorted execution (Greedy approach per [cite: 420])
        sorted_sales = sorted(
            output_contracts, key=lambda x: x.unit_price, reverse=True
        )
        revenue = 0
        remaining_prod = actual_production
        q_contracted_out = 0

        for contract in sorted_sales:
            filled = min(remaining_prod, contract.quantity)
            revenue += filled * contract.unit_price
            remaining_prod -= filled
            q_contracted_out += contract.quantity

        # 2. Input Costs: sum(p_c * q_c) - You pay for EVERYTHING you contracted to buy [cite: 433]
        input_costs = sum(c.unit_price * c.quantity for c in input_contracts)
        q_contracted_in = sum(c.quantity for c in input_contracts)

        # 3. Production Costs: m_a * Q*out [cite: 434]
        prod_costs = profile.production_cost * actual_production

        # 4. Penalties
        # Excess (Storage): Inventory + Bought - Produced [cite: 426]
        # Note: In SCML 2024, inventory does not carry over easily, you pay storage on excess.
        q_excess = max(0, state.inventory + q_contracted_in - actual_production)
        storage_penalty = state.current_storage_cost * trading_price_in * q_excess

        # Shortfall: Contracted_Out - Produced [cite: 426]
        q_shortfall = max(0, q_contracted_out - actual_production)
        shortfall_penalty = (
            state.current_shortfall_penalty * trading_price_out * q_shortfall
        )

        # Total Equation (6)
        profit = (
            revenue - input_costs - prod_costs - storage_penalty - shortfall_penalty
        )
        return profit
