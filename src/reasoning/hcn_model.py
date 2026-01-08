import torch
import torch.nn as nn
import torch.nn.functional as F


class HcnAgent(nn.Module):
    """
    Research-Grade Hierarchical Consensus Network.
    Structure:
    1. Manager Head: Context + Private State -> High-level Strategy (Latent)
    2. Worker Head: Strategy + Time -> Low-level Action (Price, Qty)
    """

    def __init__(self, input_dim_ctx=4, input_dim_priv=4, input_dim_neg=1, hidden_dim=64):
        super(HcnAgent, self).__init__()

        # --- Encoders ---
        # Context Vector from RAG4DyG [Success_Rate, Price_Norm, Flexibility, Duration]
        self.ctx_encoder = nn.Linear(input_dim_ctx, hidden_dim)

        # Private State [Balance_Norm, Lines_Norm, Inventory_Norm, Cost_Norm]
        self.priv_encoder = nn.Linear(input_dim_priv, hidden_dim)

        # Negotiation State [Time_Remaining_Ratio]
        self.neg_encoder = nn.Linear(input_dim_neg, hidden_dim)

        # --- Hierarchy ---

        # 1. The Manager (Strategic Layer)
        # Decides the 'Goal' based on who we are fighting (Context) and what we have (Private)
        self.manager = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, 3),  # Latent Strategies (e.g., Aggressive, Neutral, Yielding)
            nn.Softmax(dim=-1),
        )

        # 2. The Worker (Tactical Layer)
        # Executes the strategy given the current deadline constraints
        self.worker = nn.Sequential(
            nn.Linear(3 + hidden_dim, hidden_dim),  # 3 strategy probs + neg encoding
            nn.ReLU(),
            nn.Linear(hidden_dim, 2),  # [Price_Factor, Quantity_Factor]
        )

    def forward(self, ctx, priv, neg):
        # 1. Encode Features
        h_ctx = F.relu(self.ctx_encoder(ctx))
        h_priv = F.relu(self.priv_encoder(priv))
        h_neg = F.relu(self.neg_encoder(neg))

        # 2. Manager Decision
        combined_strategic = torch.cat([h_ctx, h_priv], dim=-1)
        strategy_dist = self.manager(combined_strategic)

        # 3. Worker Action
        combined_tactical = torch.cat([strategy_dist, h_neg], dim=-1)
        action_raw = self.worker(combined_tactical)

        # 4. Bounded Output (Sigmoid scaling)
        # Price Factor: 0.8x to 1.5x of reference
        p_factor = torch.sigmoid(action_raw[:, 0]) * 0.7 + 0.8
        # Quantity Factor: 0.1x to 1.0x of capacity
        q_factor = torch.sigmoid(action_raw[:, 1]) * 0.9 + 0.1

        return p_factor, q_factor

    def get_action(self, ctx_vec, priv_state, neg_state):
        """
        Inference helper for the LangGraph node.
        """
        self.eval()
        with torch.no_grad():
            # Convert dict/lists to Tensors
            t_ctx = torch.tensor(ctx_vec, dtype=torch.float32).unsqueeze(0)

            # Normalize Private State (Estimated max values for SCML 2024)
            priv_norm = [
                min(1.0, priv_state["balance"] / 5000.0),
                min(1.0, priv_state["num_lines"] / 20.0),
                min(1.0, priv_state["inventory"] / 200.0),
                min(1.0, priv_state["cost"] / 10.0),
            ]
            t_priv = torch.tensor(priv_norm, dtype=torch.float32).unsqueeze(0)

            # Normalize Time
            t_neg = torch.tensor([neg_state["time_remaining"]], dtype=torch.float32).unsqueeze(0)

            p, q = self.forward(t_ctx, t_priv, t_neg)
            return p.item(), q.item()
