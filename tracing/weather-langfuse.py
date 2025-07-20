from langfuse import Langfuse
from langfuse.decorators import observe
import os
from dotenv import load_dotenv
import google.generativeai as genai
import json
import requests

load_dotenv()

# ✅ Correct Langfuse instance (no get_client!)
langfuse = Langfuse(
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
)

from langfuse import get_observe_decorator

observe = get_observe_decorator()
# ✅ Gemini setup
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# Load Gemini Model
# model = genai.GenerativeModel(model_name="gemini-2.0-flash")

# === SYSTEM PROMPT ===
SYSTEM_PROMPT = """You are a helpful AI Assistant...
(keep your full prompt unchanged here)
"""

# === Tools ===
@observe()
def get_weather(city: str) -> str:
    url = f"https://wttr.in/{city}?format=%C+%t"
    response = requests.get(url)
    return f"The weather in {city} is {response.text}." if response.status_code == 200 else "Sorry, I couldn't get the weather data for the city."

@observe()
def run_command(cmd: str):
    return os.popen(cmd).read().strip()

available_tools = {
    "get_weather": get_weather,
    "run_command": run_command,
}

# === Chat loop ===
messages = [
    {"role": "user", "parts": [SYSTEM_PROMPT]}
]

while True:
    query = input("> ")

    # Langfuse Trace starts here
    trace = langfuse.trace(name="user-query", metadata={"user_query": query})
    span = trace.span(name="gemini-initial-reasoning")

    messages.append({"role": "user", "parts": [query]})

    while True:
        # Log Gemini response generation
        with span:
            response = model.generate_content(
                messages,
                generation_config={"response_mime_type": "application/json"}
            )

        parsed_response = json.loads(response.text)
        step = parsed_response.get("step")

        # === PLAN ===
        if step == "plan":
            print("🧠:", parsed_response["content"])
            messages.append({"role": "model", "parts": [response.text]})
            continue

        # === ACTION ===
        elif step == "action":
            fn = parsed_response["function"]
            inp = parsed_response["input"]

            print(f"🔨 Calling Tool: {fn} with input: {inp}")

            tool_span = trace.span(name=f"tool:{fn}", metadata={"input": inp})
            with tool_span:
                result = available_tools[fn](inp)

            print("👀 Observation:", result)
            obs_msg = {"step": "observe", "output": result}
            messages.append({"role": "user", "parts": [json.dumps(obs_msg)]})
            continue

        # === OUTPUT ===
        elif step == "output":
            print("🤖:", parsed_response["content"])
            messages.append({"role": "model", "parts": [response.text]})
            trace.update(name="user-query", metadata={"final_output": parsed_response["content"]})
            break
