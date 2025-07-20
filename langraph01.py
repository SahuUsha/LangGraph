from typing_extensions import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
import google.generativeai as genai
from langsmith import traceable
from langsmith import Client
from dotenv import load_dotenv
import os
import json

load_dotenv()

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# shema

class DetectCallResponse(BaseModel):
   is_question_ai: bool
   
class CodingAiResponse(BaseModel):
    answer: str



class State(TypedDict):
    user_message: str
    ai_message: str
    is_coding_question: bool
    

def detect_query(state: State):
    user_message = state.get("user_message")
    
    SYSTEM_PROMPT = """"
    
    You are an AI assisstant. Your job is to detect if the user's query is related to coding question or not.
    
    Return the response in specified JSON boolean only.
    
    
    {
        "is_question_ai": true
    }
    """
    messages = [
    {"role": "user", "parts": [SYSTEM_PROMPT]},
    {"role": "user", "parts": [user_message]}
    ]
    
    response = model.generate_content(
        messages,
        generation_config={"response_mime_type": "application/json"})
    
    
    try:
        parsed_json = json.loads(response.text)
        parsed_response = DetectCallResponse(**parsed_json)
        print(parsed_response.is_question_ai)
        state["is_coding_question"] = parsed_response.is_question_ai
    except Exception as e:
        print("Failed to parse response:", e)
        print("Raw response:", response.text)
        state["is_coding_question"] = False
    
    return state


def route_edge(state : State) -> Literal["solve_coding_question" , "solve_simple_question"]:
   is_coding_question = state.get("is_coding_question")
   
   if is_coding_question:
       return "solve_coding_question"
   else:
       return "solve_simple_question"
    
    
def solve_coding_question(state:State):
    user_message = state.get("user_message")
    
    SYSTEM_PROMPT= """"
    You are an AI assistent. Your job is to resolve the user query based on coding
    problem he is facing
    
    {
         "answer": "<code or detailed solution>"
    }
    
    """
    messages = [
        {"role": "user", "parts": [SYSTEM_PROMPT]},
        {"role": "user", "parts": [user_message]}
    ]
    response = model.generate_content(
        messages,
        generation_config={"response_mime_type": "application/json"}
    )
    
    try:
        parsed_json = json.loads(response.text)
        parsed_response = CodingAiResponse(**parsed_json)
        state["ai_message"] = parsed_response.answer
    except (json.JSONDecodeError) as e:
        print("Failed to parse coding response:", e)
        print("Raw response:", response.text)
        state["ai_message"] = "Sorry, I couldn't understand the coding answer format."
    
    
    return state


def solve_simple_question(state:State):
    user_message = state.get("user_message")
    
    SYSTEM_PROMPT = """
    You are an AI assistant. Your job is to chat with user
    
    {
         "answer": "<detailed answer>"
    }
    """
    
    messages =[
        {"role": "user", "parts": [SYSTEM_PROMPT]},
        {"role": "user", "parts": [user_message]}
    ]
    
    response = model.generate_content(
        messages,
        generation_config={"response_mime_type": "application/json"}
    )
    try:
        parsed_json = json.loads(response.text)
        parsed_response = CodingAiResponse(**parsed_json)
        state["ai_message"] = parsed_response.answer
    except (json.JSONDecodeError) as e:
        print("Failed to parse coding response:", e)
        print("Raw response:", response.text)
        state["ai_message"] = "Sorry, I couldn't understand the coding answer format."
    
    return state

graph_builder = StateGraph(State)


graph_builder.add_node("detect_query",detect_query)
graph_builder.add_node("solve_coding_question",solve_coding_question)
graph_builder.add_node("solve_simple_question", solve_simple_question)

graph_builder.add_node("route_edge", route_edge)

graph_builder.add_edge(START,"detect_query")
graph_builder.add_conditional_edges("detect_query", route_edge)

graph_builder.add_edge("solve_coding_question", END)
graph_builder.add_edge("solve_simple_question", END)

graph = graph_builder.compile()

def call_graph():
    user_query = input("Ask>> ")
    state= {
        "user_message" : user_query,
        "ai_message" : "",
        "is_coding_question" : False
        
        
    }
    
    result = graph.invoke(state)
    
    print("Final Result : ", result)
    
    
call_graph()

