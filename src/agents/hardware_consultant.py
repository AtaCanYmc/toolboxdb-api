from langchain.agents import create_tool_calling_agent, AgentExecutor
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.language_models.chat_models import BaseChatModel
from src.llm.tools.market_tool import unified_market_search_tool
from typing import List, Dict


class HardwareConsultantAgent:
    def __init__(self, llm: BaseChatModel, extra_tools: List = None):
        self.llm = llm
        self.tools = [unified_market_search_tool]
        if extra_tools:
            self.tools.extend(extra_tools)
        self.prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    """You are a Proactive Hardware Consultant.
You help makers ideate projects, extract Bill of Materials (BOM), and optimize their shopping carts.

Instructions:
1. **Brainstorming**: If the user asks for project ideas,
FIRST use the 'get_full_inventory_tool' to see what they already have.
Then suggest projects using those parts. State clearly which parts are in stock and which need to be bought.
2. **Circuit & Code**: If asked for project details, explain the circuit wiring and provide an Arduino/C++ code sketch.
3. **BOM & Shopping**: If the user wants a parts list and pricing:
   - Determine the required BOM.
   - Use 'stock_search_tool' to check if they already own some of the needed components.
   - For missing components, use 'market_search_tool' to fetch prices across Turkish electronics stores.
   - Optimize the cart by grouping items to minimize distinct store shipping costs (assume ~50 TRY per distinct store).
4. **Tone**: Be professional, conversational, and helpful.
Always format code, tables, and cart combinations in clean Markdown.
""",
                ),
                MessagesPlaceholder(variable_name="chat_history"),
                ("user", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad"),
            ]
        )

        self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent, tools=self.tools, verbose=True
        )

    def chat(self, user_input: str, history: List[Dict[str, str]]) -> str:
        from langchain_core.messages import HumanMessage, AIMessage

        formatted_history = []
        for msg in history:
            if msg["role"] == "user":
                formatted_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                formatted_history.append(AIMessage(content=msg["content"]))

        response = self.agent_executor.invoke(
            {"input": user_input, "chat_history": formatted_history}
        )
        return response.get("output", "I could not process your request.")
