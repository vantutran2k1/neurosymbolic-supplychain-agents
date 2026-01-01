from langgraph.graph import StateGraph, END

from src.agents.analyst import StrategicAnalyst
from src.arena.seller import SellerAgent
from src.arena.state import NegotiationState

buyer_brain = StrategicAnalyst()
seller_brain = SellerAgent()


def buyer_node(state: NegotiationState):
    print(f"--- Buyer Turn (Round {state['round_count']}) ---")

    last_msg = state["messages"][-1]["content"] if state["messages"] else "Start"
    query = f"Opponent says: '{last_msg}'. Product Base Price is around {state['base_price']}. Negotiate for best price."

    result = buyer_brain.propose_action(query)

    if result["status"] == "success":
        action = result["final_proposal"]["action"]
        offer_price = action["unit_price"]
        reasoning = result["final_proposal"]["reasoning"]

        message = f"I offer ${offer_price} for {action['quantity']} units. {reasoning}"

        return {
            "messages": [{"role": "buyer", "content": message}],
            "current_proposer": "buyer",
            "current_price": offer_price,
            "current_quantity": action["quantity"],
            "round_count": state["round_count"] + 1,
        }
    else:
        return {
            "status": "failed",
            "messages": [{"role": "buyer", "content": "Internal Error"}],
        }


def seller_node(state: NegotiationState):
    print(f"--- Seller Turn ---")

    decision = seller_brain.respond(state)

    if decision["decision"] == "ACCEPT":
        return {
            "messages": [{"role": "seller", "content": "Deal! " + decision["reason"]}],
            "status": "deal_reached",
            "final_deal_price": state["current_price"],
        }
    else:
        counter_price = decision.get("price", state["base_price"] * 1.2)
        return {
            "messages": [
                {
                    "role": "seller",
                    "content": f"I cannot accept that. How about ${counter_price}? {decision['reason']}",
                }
            ],
            "current_proposer": "seller",
            "current_price": counter_price,
        }


def router(state: NegotiationState):
    if state.get("status") == "deal_reached":
        return END
    if state.get("status") == "failed":
        return END
    if state["round_count"] > 10:  # Giới hạn 10 vòng
        return END

    if state["current_proposer"] == "buyer":
        return "seller"
    else:
        return "buyer"


workflow = StateGraph(NegotiationState)

workflow.add_node("buyer", buyer_node)
workflow.add_node("seller", seller_node)

workflow.set_entry_point("buyer")

workflow.add_conditional_edges("buyer", router, {"seller": "seller", END: END})
workflow.add_conditional_edges("seller", router, {"buyer": "buyer", END: END})

app = workflow.compile()
