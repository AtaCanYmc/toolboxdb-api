from langchain_core.tools import tool
from sqlalchemy.orm import Session
from src.models import Component
from pydantic import BaseModel


class InventoryInput(BaseModel):
    # Tool requires no specific input to list all items, but a schema might still be needed.
    pass


def get_full_inventory_tool(db: Session, user_id: int):
    @tool("get_full_inventory_tool", args_schema=InventoryInput)
    def full_inventory_tool() -> str:
        """
        Retrieves the user's entire component inventory.
        Use this tool when you need to know ALL the parts the user has in stock to brainstorm project ideas.
        """
        components = (
            db.query(Component)
            .filter(Component.user_id == user_id, Component.quantity > 0)
            .all()
        )

        if not components:
            return "The user currently has no items in their inventory."

        output = ["User's Full Inventory:"]
        for c in components:
            output.append(f"- {c.name} (Qty: {c.quantity})")
        return "\n".join(output)

    return full_inventory_tool
