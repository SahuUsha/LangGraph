# graph.py

from typing import Annotated
from typing_extensions import TypedDict

# from langraph.graph.message import add_message
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END, START
# from langgraph.checkpoint.base import BaseSaver
from langchain_core.tools import tool
from langgraph.types import interrupt
from langgraph.prebuilt import ToolNode, tools_condition


import os
from dotenv import load_dotenv
load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", 
   google_api_key=os.getenv("GEMINI_API_KEY"),  # ✅ This works for langchain_google_genai v1.0.3+
    convert_system_message_to_human=True
)

@tool()
def human_assistance_tool(query: str):
    """Request assistance from a human."""
    human_response = interrupt({ "query": query }) # Graph will exit out after saving data in DB
    return human_response["data"]

tools = [human_assistance_tool]
llm_with_tools = llm.bind_tools(tools=tools)



# Define state type
class State(TypedDict):
    messages: list

# Node function
def chatbot(state: State) -> State:
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": state["messages"] + [response]}

tool_node = ToolNode(tools=tools)

# Build the graph
graph_builder = StateGraph(State)
graph_builder.add_node("chatbot", chatbot)
graph_builder.add_node("tools", tool_node)
graph_builder.set_entry_point("chatbot")

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

graph_builder.add_edge("tools", "chatbot") 

graph_builder.set_finish_point("chatbot")

# Compile the graph
graph = graph_builder.compile()


def create_chat_graph(checkpointer):
    
    
    
    return graph_builder.compile(checkpointer=checkpointer)