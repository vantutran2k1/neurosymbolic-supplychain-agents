from src.guardian.schemas import ProductionRecipe


def calculate_potential_production(
    target_product_id: str,
    current_inventory: dict[str, int],
    recipes: list[ProductionRecipe],
) -> int:
    relevant_recipe = None
    output_yield = 0

    for recipe in recipes:
        if target_product_id in recipe.outputs:
            relevant_recipe = recipe
            output_yield = recipe.outputs[target_product_id]
            break

    if not relevant_recipe:
        return 0

    possible_batches = float("inf")

    for input_id, required_qty in relevant_recipe.inputs.items():
        available = current_inventory.get(input_id, 0)
        if required_qty > 0:
            batches = available // required_qty
            if batches < possible_batches:
                possible_batches = batches

    if possible_batches == float("inf"):
        return 0

    return int(possible_batches * output_yield)
