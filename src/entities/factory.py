from dataclasses import dataclass


@dataclass
class Contract:
    id: str
    product_id: int
    quantity: int
    unit_price: int
    is_exogenous: bool = False


@dataclass
class ProductionResult:
    quantity_to_buy: int
    quantity_to_produce: int
    quantity_to_sell: int
    expected_profit: float
    input_contracts_fulfilled: list[tuple[str, int]]  # (contract_id, quantity)
    output_contracts_fulfilled: list[tuple[str, int]]  # (contract_id, quantity)


class FactoryAgent:
    def __init__(
        self,
        agent_id: str,
        num_lines: int,
        initial_balance: float,
        production_cost_per_unit: float,
        initial_inventory: int = 0,
    ):
        self.agent_id = agent_id
        self.num_lines = num_lines

        self._balance = initial_balance
        self._production_cost = production_cost_per_unit
        self._inventory_input = initial_inventory

        self._current_storage_cost_unit = 0.0
        self._current_shortfall_penalty_unit = 0.0

        self._buy_contracts: list[Contract] = []
        self._sell_contracts: list[Contract] = []

    def set_daily_costs(self, storage_cost: float, shortfall_penalty: float):
        self._current_storage_cost_unit = storage_cost
        self._current_shortfall_penalty_unit = shortfall_penalty

    def add_contract(self, contract: Contract, is_buy: bool):
        if is_buy:
            self._buy_contracts.append(contract)
        else:
            self._sell_contracts.append(contract)

    def get_public_state(self):
        return {
            "agent_id": self.agent_id,
            "lines": self.num_lines,
        }

    def resolve_day(self) -> ProductionResult:
        q_star_in, inputs_fulfilled, funds_after_buying = self._optimize_inputs()
        q_p = self._calculate_producible_quantity(q_star_in, funds_after_buying)
        q_star_out, outputs_fulfilled = self._optimize_outputs(q_p)

        revenue = sum(
            qty * next(c.unit_price for c in self._sell_contracts if c.id == cid)
            for cid, qty in outputs_fulfilled
        )

        cost_inputs = sum(
            qty * next(c.unit_price for c in self._buy_contracts if c.id == cid)
            for cid, qty in inputs_fulfilled
        )

        cost_production = q_star_out * self._production_cost

        total_input_available = self._inventory_input + q_star_in
        q_excess = max(0, total_input_available - q_star_out)
        penalty_storage = q_excess * self._current_storage_cost_unit

        total_contracted_out = sum(c.quantity for c in self._sell_contracts)
        q_shortfall = max(0, total_contracted_out - q_star_out)
        penalty_shortfall = q_shortfall * self._current_shortfall_penalty_unit

        profit = (
            revenue
            - cost_inputs
            - cost_production
            - penalty_storage
            - penalty_shortfall
        )

        return ProductionResult(
            quantity_to_buy=q_star_in,
            quantity_to_produce=q_p,
            quantity_to_sell=q_star_out,
            expected_profit=profit,
            input_contracts_fulfilled=inputs_fulfilled,
            output_contracts_fulfilled=outputs_fulfilled,
        )

    def _optimize_inputs(self) -> tuple[int, list[tuple[str, int]], float]:
        sorted_contracts = sorted(self._buy_contracts, key=lambda c: c.unit_price)

        total_qty = 0
        fulfilled = []
        temp_balance = self._balance

        for contract in sorted_contracts:
            if temp_balance <= 0:
                break

            cost_for_all = contract.quantity * contract.unit_price

            if cost_for_all <= temp_balance:
                qty = contract.quantity
                cost = cost_for_all
            else:
                qty = int(temp_balance // contract.unit_price)
                cost = qty * contract.unit_price

            if qty > 0:
                total_qty += qty
                temp_balance -= cost
                fulfilled.append((contract.id, qty))

        return total_qty, fulfilled, temp_balance

    def _calculate_producible_quantity(
        self, q_star_in: int, available_funds: float
    ) -> int:
        total_input = q_star_in + self._inventory_input

        if self._production_cost > 0:
            max_affordable_production = int(available_funds // self._production_cost)
        else:
            max_affordable_production = total_input

        return min(total_input, max_affordable_production)

    def _optimize_outputs(self, q_producible: int) -> tuple[int, list[tuple[str, int]]]:
        sorted_contracts = sorted(
            self._sell_contracts, key=lambda c: c.unit_price, reverse=True
        )

        total_qty_sold = 0
        fulfilled = []
        remaining_production_capacity = min(q_producible, self.num_lines)

        for contract in sorted_contracts:
            if remaining_production_capacity <= 0:
                break

            qty = min(contract.quantity, remaining_production_capacity)

            if qty > 0:
                total_qty_sold += qty
                remaining_production_capacity -= qty
                fulfilled.append((contract.id, qty))

        return total_qty_sold, fulfilled
