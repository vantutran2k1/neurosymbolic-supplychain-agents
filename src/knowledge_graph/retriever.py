from typing import LiteralString

import numpy as np
from pydantic import BaseModel

from src.knowledge_graph.neo4j_client import Neo4jClient, neo4j_client


class RetrieverConfig(BaseModel):
    lookback_window: int = 30
    max_volatility: float = 5.0
    max_duration: float = 20.0
    market_scaling_factor: float = 2.0


class ContextTensor(BaseModel):
    vector: np.ndarray
    metadata: dict[str, float | str]
    trajectory: list[tuple[int, float]]


class KnowledgeGraphRetriever:
    def __init__(self, client: Neo4jClient = neo4j_client, config: RetrieverConfig = None):
        self._client = client
        self._cfg = config or RetrieverConfig()

    def retrieve_context(self, opponent_id: str, current_day: int) -> ContextTensor:
        query: LiteralString = """
        MATCH (me:Agent)-[:PARTICIPATED_IN]->(s:Session)<-[:PARTICIPATED_IN]-(opp:Agent {id: $opp_id})
        WHERE s.day >= $start_day AND s.day < $curr_day

        WITH s, opp, s.market_price as mkt_p
        OPTIONAL MATCH (s)<-[:BELONGS_TO]-(o:Offer)
        WHERE (opp)-[:MADE_OFFER]->(o)

        WITH s, mkt_p, o ORDER BY o.step ASC
        WITH s, mkt_p, collect(o.price) as prices, collect(o.step) as steps
        WITH s, mkt_p, prices,
             head(prices) as p_open,
             last(prices) as p_final,
             size(prices) as duration,
             stDev(o.price) as volatility,
             abs(last(prices) - prices[size(prices)-2]) as terminal_movement

        RETURN 
            count(s) as total_sessions,
            sum(CASE WHEN s.status = 'SUCCESS' THEN 1 ELSE 0 END) as wins,
            avg(CASE WHEN s.status = 'SUCCESS' THEN (s.final_price - mkt_p)/mkt_p ELSE 0 END) as avg_premium,
            avg((p_open - mkt_p)/mkt_p) as avg_opening_aggression,
            avg((p_open - p_final) / (duration + 1)) as avg_concession_slope,
            avg(terminal_movement) as avg_terminal_stiffness,
            sum(CASE WHEN s.fail_reason = 'walkaway' THEN 1 ELSE 0 END) as walkaways,
            sum(CASE WHEN s.fail_reason = 'timeout' THEN 1 ELSE 0 END) as timeouts,
            avg(s.final_price / mkt_p) as price_market_ratio
        """

        start_day = max(0, current_day - self._cfg.lookback_window)
        rec = self._client.execute_read(
            lambda tx: tx.run(query, opp_id=opponent_id, start_day=start_day, curr_day=current_day).single()
        )
        if not rec or rec["total_sessions"] == 0:
            return ContextTensor(vector=np.zeros(8, dtype=np.float32), metadata={"status": "COLD_START"}, trajectory=[])

        trajectory = self._retrieve_trajectory(opponent_id, current_day)
        total = rec["total_sessions"]

        # [0] Win Rate (0-1)
        f0 = rec["wins"] / total
        # [1] Premium (-1 to 1) -> Clamped
        f1 = np.clip(rec["avg_premium"] or 0, -1.0, 1.0)
        # [2] Aggression (0 to 2)
        f2 = np.clip(rec["avg_opening_aggression"] or 0, -1.0, 2.0)
        # [3] Concession Rate (Norm by max_price/max_steps ~ 1.0)
        # Higher = Faster Concession (Conceder), Lower = Slower (Boulware)
        f3 = np.clip(rec["avg_concession_slope"] or 0, 0.0, 2.0)
        # [4] Terminal Stiffness (0-1)
        # 0 = Completely frozen at deadline. >0 = Still moving.
        f4 = np.clip(rec["avg_terminal_stiffness"] or 0, 0.0, 1.0)
        # [5] Walkaway Risk (0-1)
        f5 = rec["walkaways"] / total
        # [6] Timeout Risk (0-1)
        f6 = rec["timeouts"] / total
        # [7] Market Ratio Consistency (Variance from 1.0)
        # If they are perfectly rational, ratio ~ 1.0 constant.
        # If erratic, this fluctuates.
        ratio = rec["price_market_ratio"] or 1.0
        f7 = np.clip(ratio - 1.0, -0.5, 0.5)

        vector = np.array([f0, f1, f2, f3, f4, f5, f6, f7], dtype=np.float32)

        return ContextTensor(
            vector=vector,
            metadata={"total_sessions": total, "avg_premium": rec["avg_premium"], "walkaway_rate": f5},
            trajectory=trajectory,
        )

    def _retrieve_trajectory(self, opponent_id: str, current_day: int) -> list[tuple[int, float]]:
        query: LiteralString = """
        MATCH (s:Session)<-[:PARTICIPATED_IN]-(opp:Agent {id: $opp_id})
        WHERE s.day < $curr_day 
            AND s.status IS NOT NULL
        WITH s ORDER BY s.day DESC LIMIT 1
        MATCH (o:Offer)-[:BELONGS_TO]->(s)
        WHERE (opp)-[:MADE_OFFER]->(o)
        
        RETURN o.step as step, o.price as price ORDER BY o.step ASC
        """

        result = self._client.execute_read(lambda tx: tx.run(query, opp_id=opponent_id, curr_day=current_day))
        return [(r["step"], r["price"]) for r in result]
