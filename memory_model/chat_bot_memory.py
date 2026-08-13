import json
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, messages_from_dict, messages_to_dict
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel
from typing import Union
from dotenv import load_dotenv
from PIL import Image
from io import BytesIO

load_dotenv()

MEMORY_FILE = "memory.json"

class AgentState(BaseModel):
    message: list[Union[HumanMessage, AIMessage]]

llm = ChatGroq(model="llama-3.1-8b-instant",temperature=0) # the higher the temp the more creative the models becomes and less accurate

def chat_bot(state: AgentState) -> AgentState:
    response = llm.invoke(state.message)
    state.message.append(AIMessage(content=response.content))
    print("\nAI:", response.content)
    return state

graph = StateGraph(AgentState)
graph.add_node("chatbot",chat_bot)
graph.add_edge(START,"chatbot")
graph.add_edge("chatbot",END)

agent = graph.compile()

pixel_val = agent.get_graph().draw_mermaid_png()
temp_img_path = Image.open(BytesIO(pixel_val))
# temp_img_path.show()

def load_memory():
    """Load previous conversation from memory.json"""
    try:
        with open(MEMORY_FILE, "r") as file:
            data = json.load(file)

        history = messages_from_dict(data)
        print(f"[Loaded {len(history)} messages from memory]")
        return history
    
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_memory(history):
    """Save conversation to memory.json"""
    with open(MEMORY_FILE, "w") as file:
        json.dump(
            messages_to_dict(history),
            file,indent=4
        )

conversation_history = load_memory()

while True:
    user_input = input("You: ")
    if user_input.lower() == "exit":
        print("Goodbye!")
        break

    conversation_history.append(HumanMessage(content=user_input))
    result = agent.invoke({"message": conversation_history})
    conversation_history = result["message"]
    save_memory(conversation_history)