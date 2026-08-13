from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import create_agent
from dotenv import load_dotenv
from ml_model import Logistic

load_dotenv()

logistic_model = Logistic()

def get_diabetes_prediction():
    """
    Reads the diabetes CSV file, trains a Logistic Regression model,
    and returns the classification report showing model performance.
    Use this tool when the user asks to read the CSV, train the model,
    or get diabetes prediction results.
    """
    report = logistic_model.get_results()
    return f"Logistic Regression Classification Report:\n\n{report}"

def get_weather(city: str):
    """Get weather for a given city."""
    return f"It is always sunny in {city}!"

def add(a: int, b: int):
    """Add two numbers."""
    return a + b

def muiltply(a: int, b: int):
    """Multiply two numbers."""
    return a * b


class Ai:
    def __init__(self):
        self.gemini_model = ChatGoogleGenerativeAI(
            model="gemini-3.6-flash"
        )
        self.create_agent()

    def create_agent(self):
        self.agent = create_agent(
            model=self.gemini_model,
            tools=[add, muiltply, get_weather, get_diabetes_prediction]
        )

    def invoke(self, query):
        response = self.agent.invoke(
            {
                "messages": [{"role": "user", "content": query}]
            }
        )
        return response["messages"][-1].content[0]["text"]