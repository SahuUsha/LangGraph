import os
import json
import requests
import google.generativeai as genai
from dotenv import load_dotenv
from langsmith import traceable
from langsmith import Client

load_dotenv()

os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGSMITH_TRACING", "true")
os.environ["LANGCHAIN_ENDPOINT"] = os.getenv("LANGSMITH_ENDPOINT")
os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT")

client = Client()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

model = genai.GenerativeModel(model_name="gemini-2.0-flash")

SYSTEM_PROMPT = """You are a helpful AI Assistant who is specialized in resolving user query.
    You work on start, plan, action, observe mode.

    For the given user query and available tools, plan the step by step execution, based on the planning,
    select the relevant tool from the available tool. And based on the tool selected you perform an action to call the tool.

    Wait for the observation and based on the observation from the tool call resolve the user query.

    Rules:
    - Follow the Output JSON Format.
    - Always perform one step at a time and wait for the next input.
    - Carefully analyse the user query.

    Output JSON Format:
    {{
        "step": "string",
        "content": "string",
        "function": "The name of function if the step is action",
        "input": "The input parameter for the function",
        "output": "The output of the function"
    }}

    Available Tools:
    - "get_weather": Takes a city name as input and returns the weather of the city.
    - "run_command": Takes linux command as string and executes the command and returns the output after executing it.

    Example:
    Input: What is the weather in Hyderabad?
    Output: {{ "step": "plan", "content": "The user is interested in weather data of Hyderabad. So I will use the get_weather tool to get the weather data of Hyderabad." }}
    Output: {{ "step": "plan", "content": "From the available tools, I should call get_weather" }}
    Output: {{ "step": "action", "function": "get_weather", "input": "Hyderabad" }}
    Output: {{ "step": "observe", "content": "24 degrees C" }}
    Output: {{ "step": "output", "content": "The weather for Hyderabad seems to be 24 degrees C" }}
"""
 # keep your prompt as is
@traceable
def get_weather(city: str) -> str:
    url = f"https://wttr.in/{city}?format=%C+%t"
    response = requests.get(url)

    if response.status_code == 200:
        return f"The weather in {city} is {response.text}."
    else:
        return "Sorry, I couldn't get the weather data for the city"
@traceable
def run_command(cmd: str):
    result = os.system(cmd)
    return result

available_tools = {
    "get_weather": get_weather,
    "run_command": run_command,
}

messages = [
    {"role": "user", "parts": [SYSTEM_PROMPT]}
]

while True:
    query = input("> ")
    messages.append({"role": "user", "parts": [query]})
    while True:
        response = model.generate_content(messages, generation_config={"response_mime_type": "application/json"})

        parsed_response = json.loads(response.text)
        # print(parsed_response)

        if parsed_response.get("step") == "plan":
           print("🧠:", parsed_response["content"])
           messages.append({"role": "model", "parts": [response.text]})
           continue

        elif parsed_response.get("step") == "action":
          fn = parsed_response["function"]
          inp = parsed_response["input"]

          print(f"🔨 Calling Tool: {fn} with input: {inp}")
          result = available_tools[fn](inp)
          obs_msg = {"step": "observe", "output": result}
          print("👀 Observation:", result)

          messages.append({"role": "user", "parts": [json.dumps(obs_msg)]})
          continue

        elif parsed_response.get("step") == "output":
          print("🤖:", parsed_response["content"])
          messages.append({"role": "model", "parts": [response.text]})
          break
