import numpy as np

from src.knowledge_graph.neo4j_client import Neo4jClient


class KnowledgeGraphRetriever:
    def __init__(self, client: Neo4jClient):
        self._client = client

    def retrieve_dy_context(self, opponent_id: str, current_day: int, window: int = 10):
        def _query(tx):
            start_day = max(0, current_day - window)

            result = tx.run(
                """
                // 1. Sparse Selection: Find relevant sessions in the time window
                MATCH (me:Agent)-[:PARTICIPATED_IN]->(s:Session)<-[:PARTICIPATED_IN]-(opp:Agent {id: $opp_id})
                WHERE s.day >= $start_day AND s.day < $curr_day
        
                // 2. Trajectory Extraction (The 'Dynamic' part)
                // We look at the Offer chain to calculate 'Stubbornness' (Avg Concession)
                OPTIONAL MATCH (s)<-[:BELONGS_TO]-(o:Offer)
                WITH s, opp, count(o) as steps, 
                 max(o.price) as max_p, 
                 min(o.price) as min_p,
                 s.final_price as final_p,
                 s.status as status
    
                // 3. Attention/Aggregation (Summarizing the Subgraph)
                RETURN 
                count(s) as total_sessions,
    
                // Feature A: Success Rate (How cooperative are they?)
                sum(CASE WHEN status = 'SUCCESS' THEN 1 ELSE 0 END) as successful_deals,
    
                // Feature B: Average Deal Price (If successful)
                avg(final_p) as avg_price,
    
                // Feature C: Stubbornness Score
                // (High variance between max/min bid suggests flexibility. Low variance = stubborn.)
                avg(max_p - min_p) as avg_concession_range,
    
                // Feature D: Patience (Avg Negotiation Length)
                avg(steps) as avg_duration
                """,
                opp_id=opponent_id,
                start_day=start_day,
                curr_day=current_day,
            )

            return result.single()

        data = self._client.execute_read(_query)
        if not data or data["total_sessions"] == 0:
            return {
                "exists": False,
                "vector": np.zeros(4, dtype=np.float32),  # [Success, Price, Concession, Duration]
            }

        # Normalize Features
        # Assuming standard price ~10, standard duration ~20 steps
        vec = np.array(
            [
                data["successful_deals"] / data["total_sessions"],  # 0.0 - 1.0
                (data["avg_price"] or 0) / 10.0,  # Normalized Price
                (data["avg_concession_range"] or 0) / 5.0,  # Normalized Flexibility
                (data["avg_duration"] or 0) / 20.0,  # Normalized Patience
            ],
            dtype=np.float32,
        )

        return {"exists": True, "raw_stats": dict(data), "vector": vec}

    def retrieve_trajectory_fingerprint(self, opponent_id: str):
        def _query(tx):
            result = tx.run(
                """
                MATCH (s:Session)<-[:PARTICIPATED_IN]-(opp:Agent {id: $opp_id})
                WHERE s.status IS NOT NULL
                WITH s ORDER BY s.day DESC LIMIT 1
    
                MATCH (o:Offer)-[:BELONGS_TO]->(s)
                RETURN o.step as step, o.price as price
                ORDER BY o.step ASC
                """,
                opp_id=opponent_id,
            )
            return [(r["step"], r["price"]) for r in result]

        return self._client.execute_read(_query)
