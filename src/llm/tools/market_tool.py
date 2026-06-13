from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
from robo_market_search.unified.client import UnifiedSearchClient


class MarketSearchInput(BaseModel):
    query: str = Field(
        description="The name or part number of the electronic component to search for in the market."
    )
    limit_per_store: Optional[int] = Field(
        default=5, description="Maximum number of items to fetch per store."
    )


@tool("market_search_tool", args_schema=MarketSearchInput)
def unified_market_search_tool(query: str, limit_per_store: int = 5) -> str:
    """
    Search for electronic components across multiple Turkish electronics markets
    (Robolink, Robotistan, Robo90, Direncnet).
    Use this tool to find real-time prices and availability of parts to optimize a Bill of Materials.
    """
    client = UnifiedSearchClient()
    try:
        results = client.search(query=query, limit_per_store=limit_per_store)

        if not results:
            return f"No results found in any market for query: '{query}'."

        output = [f"Search Results for '{query}':"]
        for p in results:
            stock_status = "In Stock" if p.in_stock else "Out of Stock"
            output.append(
                f"- Store: {p.store} "
                f"| Name: {p.name} "
                f"| Price: {p.price} {p.currency} "
                f"| Status: {stock_status} "
                f"| URL: {p.url}"
            )
        return "\n".join(output)
    except Exception as e:
        return f"An error occurred while searching for '{query}': {str(e)}"
