class NegotiationStrategy:
    @staticmethod
    def calculate_prices(
        market_price: float, is_buying: bool, time_fraction: float, volatility: float
    ) -> tuple[float, float]:
        k = 0.2

        margin = 0.15 + (volatility * 0.5)

        if is_buying:
            base_reservation = market_price * 1.05
            ideal_price = market_price * (1 - margin)
        else:
            base_reservation = market_price * 0.95
            ideal_price = market_price * (1 + margin)

        concession = (base_reservation - ideal_price) * (time_fraction**k)
        current_target = ideal_price + concession

        return current_target, base_reservation
