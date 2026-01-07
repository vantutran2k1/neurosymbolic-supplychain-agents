import torch
import torch.nn as nn
import torch.nn.functional as F

from src.entities import Proposal, AgentState


class HCNModule(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int):
        super(HCNModule, self).__init__()

        # --- 1. Perception Encoder (Graph/Time embedding) ---
        # Processes the sequence of graph snapshots (Day t, t-1, t-2...)
        # input_dim = 3 (Market Price, Balance, Inventory)
        self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True)

        # --- 2. High-Level Policy (Strategic Intent) ---
        # Decides: 0=Hold, 1=Buy, 2=Sell
        self.strategy_head = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 3),  # Logits for Hold, Buy, Sell
            nn.Softmax(dim=-1),
        )

        # --- 3. Low-Level Policy (Tactical Execution) ---
        # Decides: Price Aggressiveness (0.0-2.0) and Quantity Factor (0.0-1.0)
        # Conditioned on the Strategy output (concatenated)
        self.tactic_head = nn.Sequential(
            nn.Linear(hidden_dim + 3, 32),  # +3 for the strategy one-hot
            nn.ReLU(),
            nn.Linear(32, 2),  # [Price_Factor, Quantity_Factor]
            nn.Sigmoid(),  # Normalize to 0-1 range
        )

    def forward(self, x_sequence):
        """
        x_sequence: Tensor of shape (Batch, Seq_Len, Features)
        """
        # LSTM forward
        _, (h_n, _) = self.lstm(x_sequence)
        # h_n shape: (1, Batch, Hidden) -> Squeeze to (Batch, Hidden)
        context_vector = h_n[-1]

        # 1. Strategic Decision
        strategy_probs = self.strategy_head(context_vector)

        # Sample or take Argmax (for training vs inference)
        # Here we use argmax for deterministic "intent" in forward pass,
        # but in RL training you would sample.
        strategy_idx = torch.argmax(strategy_probs, dim=1)
        strategy_one_hot = F.one_hot(strategy_idx, num_classes=3).float()

        # 2. Tactical Decision (Conditioned on Strategy)
        # We fuse the context with the decided strategy
        fusion = torch.cat([context_vector, strategy_one_hot], dim=1)
        tactics = self.tactic_head(fusion)

        return strategy_idx, tactics


class Strategist:
    def __init__(self, model: HCNModule, device="cpu"):
        self.model = model
        self.device = device
        self.model.to(device)
        self.model.eval()  # Inference mode

    def preprocess_graph_context(self, graph_data: list) -> torch.Tensor:
        """
        Converts list of dicts from Knowledge Graph to PyTorch Tensor.
        Normalizes values to help the Neural Net (Standard Scaling roughly).
        """
        # Example graph_data: [{'market_price': 10, 'my_balance': 100, ...}, ...]
        features = []
        for snapshot in graph_data:
            # Simple normalization (in real research, use running stats)
            p_norm = snapshot["market_price"] / 20.0
            b_norm = snapshot["my_balance"] / 1000.0
            i_norm = snapshot["my_stock"] / 20.0
            features.append([p_norm, b_norm, i_norm])

        # Pad if sequence is too short (omitted for brevity)
        # Shape: (1, Seq_Len, 3) -> Batch size 1
        return torch.tensor([features], dtype=torch.float32).to(self.device)

    def generate_proposal(
        self, state: AgentState, graph_context: list, market_price: float
    ) -> Proposal:
        """
        End-to-end generation: Graph -> Tensor -> Model -> Proposal
        """
        # 1. Preprocess
        x_input = self.preprocess_graph_context(graph_context)

        # 2. Inference
        with torch.no_grad():
            strat_idx, tactics = self.model(x_input)

        intent_id = strat_idx.item()  # 0=Hold, 1=Buy, 2=Sell
        price_factor, qty_factor = tactics[0].tolist()

        # 3. Decode Strategy to Proposal
        # Mapping: 0->Hold, 1->Buy, 2->Sell
        if intent_id == 0:
            return Proposal("hold")

        elif intent_id == 1:  # BUY
            # Tactic 0 is price aggressiveness (0.8 to 1.2 around market)
            # Tactic 1 is quantity factor (portion of max capacity)
            target_price = market_price * (0.8 + (price_factor * 0.4))

            # Use a heuristic for quantity base (e.g., max 10 units)
            # In RL, this '10' would be learned or derived from Guardian limit
            target_qty = max(1, int(10 * qty_factor))

            return Proposal("buy", q_buy=target_qty, unit_price_buy=target_price)

        elif intent_id == 2:  # SELL
            target_price = market_price * (0.9 + (price_factor * 0.4))
            # Quantity limited by current inventory
            target_qty = max(1, int(state.inventory * qty_factor))

            return Proposal("sell", q_sell=target_qty, unit_price_sell=target_price)

        return Proposal("hold")
