from langchain_core.tools import tool
from sqlalchemy.orm import Session
from src.models import Component
from pydantic import BaseModel, Field


class StockSearchInput(BaseModel):
    query: str = Field(
        description="The name or part number of the electronic component to search for in user's stock."
    )


def get_stock_search_tool(db: Session, user_id: int):
    @tool("stock_search_tool", args_schema=StockSearchInput)
    def stock_search_tool(query: str) -> str:
        """
        Search the user's personal inventory/stock database for electronic components.
        Use this tool to check if the user already has a required part in stock
        before deciding to buy it from the market.
        If the user has the required quantity in stock,
        you can subtract it from the market purchase list and save money.
        """
        components = (
            db.query(Component)
            .filter(
                Component.user_id == user_id,
                Component.name.ilike(f"%{query}%"),
                Component.quantity > 0,
            )
            .all()
        )

        if not components:
            return f"No stock found for '{query}' in user's inventory."

        output = [f"Stock Results for '{query}' in user's inventory:"]
        for c in components:
            output.append(f"- Name: {c.name} | Quantity in stock: {c.quantity}")
        return "\n".join(output)

    return stock_search_tool
