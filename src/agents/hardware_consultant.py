from langgraph.prebuilt import create_react_agent
from langchain_core.language_models.chat_models import BaseChatModel
from src.llm.tools.market_tool import unified_market_search_tool
from src.llm.prompt_provider import render_prompt
from typing import List, Dict


class HardwareConsultantAgent:
    def __init__(self, llm: BaseChatModel, extra_tools: List = None):
        self.llm = llm
        self.tools = [unified_market_search_tool]
        if extra_tools:
            self.tools.extend(extra_tools)

        self.system_prompt = render_prompt(
            template_name="hardware_consultant_system_prompt.jinja2", context={}
        )

        self.agent_executor = create_react_agent(
            model=self.llm,  # type: ignore
            tools=self.tools,
            state_modifier=self.system_prompt,
        )

    def chat(self, user_input: str, history: List[Dict[str, str]]) -> str:
        from langchain_core.messages import HumanMessage, AIMessage

        formatted_history = []
        for msg in history:
            if msg["role"] == "user":
                formatted_history.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                formatted_history.append(AIMessage(content=msg["content"]))

        formatted_history.append(HumanMessage(content=user_input))

        response = self.agent_executor.invoke(
            {"messages": formatted_history}  # type: ignore
        )

        # The last message is usually the AIMessage returned by the agent
        return response["messages"][-1].content
