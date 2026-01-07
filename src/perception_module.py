class AdvancedPerceptionModule:
    def __init__(self, kg_manager):
        self.kg = kg_manager

    def retrieve_dysk_subgraph(
        self,
        agent_id: str,
        product_id: int,
        current_day: int,
        decay_lambda: float = 0.5,
        top_k: int = 5,
    ):
        """
        Implements RAG4DyG (Time-Decay) and DySK-Attn (Top-K Sparsity).
        """
        # Cypher Query:
        # 1. Matches market and agent states within a lookback window.
        # 2. Calculates a 'recency_score' using exp() decay.
        # 3. Sorts by score and limits to 'top_k' (Sparsity).
        query = """
        MATCH (d:Day)
        WHERE d.index <= $current_day AND d.index >= ($current_day - 10) // Hard lookback cap

        WITH d, ($current_day - d.index) as days_ago

        // Calculate Time Decay Weight (RAG4DyG)
        // e^(-lambda * days_ago)
        WITH d, days_ago, exp(-$lamb * days_ago) as time_weight

        // --- Branch 1: Market Information ---
        OPTIONAL MATCH (p:Product {id: $pid})-[:HAS_PRICE]->(m:MarketState)-[:AT_TIME]->(d)
        WITH d, days_ago, time_weight, m, p
        WHERE m IS NOT NULL
        // Semantic Relevance: 1.0 (Direct product match)
        WITH collect({
            type: 'market_price',
            value: m.price,
            day: d.index,
            score: 1.0 * time_weight
        }) as market_data, d, days_ago, time_weight

        // --- Branch 2: Agent Status (Self) ---
        MATCH (me:Agent {id: $aid})-[:HAS_STATUS]->(s:AgentState)-[:AT_TIME]->(d)
        WITH market_data, collect({
            type: 'my_status',
            balance: s.balance,
            inventory: s.inventory,
            day: d.index,
            score: 1.0 * time_weight // Self-status is always highly relevant
        }) as agent_data

        // --- Branch 3: Competitor Moves (DySK-Attn Expansion) ---
        // Find contracts signed by others for THIS product recently
        // This is "Sparse Attention" - we only look at DIRECT competitors for THIS product
        MATCH (c:Contract)-[:FOR_PRODUCT]->(:Product {id: $pid})
        WHERE (c)-[:SIGNED_ON]->(d)
        MATCH (seller:Agent)-[:SOLD]->(c)
        WITH market_data, agent_data, collect({
            type: 'competitor_trade',
            price: c.unit_price,
            qty: c.quantity,
            day: d.index,
            score: 0.8 * time_weight // Slightly less relevant than direct market price
        }) as comp_data

        // Aggregate and Prune (DySK-Attn)
        WITH market_data + agent_data + comp_data as all_events
        UNWIND all_events as event
        RETURN event
        ORDER BY event.score DESC
        LIMIT $k
        """

        with self.kg.driver.session() as session:
            result = session.run(
                query,
                aid=agent_id,
                pid=product_id,
                current_day=current_day,
                lamb=decay_lambda,
                k=top_k,
            )
            return [record["event"] for record in result]

    def format_context_for_llm(self, dysk_events: list) -> str:
        """
        Converts the sparse subgraph into a narrative prompt for the LLM.
        """
        # Sort by day (chronological for narrative flow)
        dysk_events.sort(key=lambda x: x["day"])

        prompt_lines = ["Recent Market Context (Weighted by Relevance):"]
        for e in dysk_events:
            day_str = f"[Day {e['day']}]"
            if e["type"] == "market_price":
                prompt_lines.append(f"{day_str} Market Price: ${e['value']:.2f}")
            elif e["type"] == "my_status":
                prompt_lines.append(
                    f"{day_str} My Balance: ${e['balance']:.0f}, Stock: {e['inventory']}"
                )
            elif e["type"] == "competitor_trade":
                prompt_lines.append(
                    f"{day_str} Competitor Trade: {e['qty']} units @ ${e['price']:.2f}"
                )

        return "\n".join(prompt_lines)
