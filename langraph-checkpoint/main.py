from graph import  create_chat_graph
from dotenv import load_dotenv
from langgraph.checkpoint.mongodb import MongoDBSaver

load_dotenv()

# DB_URI = "mongodb+srv://usha:usha@lang-graph.ltols9b.mongodb.net/"
DB_URI = "mongodb://localhost:27017"
config = {"configurable" : {"thread_id": "57"}}

def init():
   
    
    # every graph invocation is a thread
    
    with MongoDBSaver.from_conn_string(DB_URI) as checkpointer:
        graph_with_mongo = create_chat_graph(checkpointer=checkpointer)
    
    # Initial state
      #   state = {"messages": []}

      #   while True:
      #      user_input = input(">> ")

      #      if user_input.lower() in {"exit", "quit"}:
      #         print("👋 Goodbye!")
      #         break

      #   # Add user input to state
      #      state["messages"].append({"role": "user", "content": user_input})

      #   # Invoke graph
      #   #    state = graph.invoke(state)
      #      state = graph_with_mongo.invoke(state , config=config)
      #         # Get the last message from the state

      #   # Get assistant response (AIMessage object)
      #      last_message = state["messages"][-1]
      #      print("🤖", last_message.content)
      
        while True:
           user_input = input("> ")
           for event in graph_with_mongo.stream(
             {"messages": [{"role": "user", "content": user_input}]},
            config,
             stream_mode="values"
             ):
            if "messages" in event:
               last_msg = event["messages"][-1]
               if isinstance(last_msg, dict):
                 print("🤖", last_msg.get("content"))
               else:
                 print("🤖", last_msg.content)




init()
