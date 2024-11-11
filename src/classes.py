from pydantic import BaseModel
from typing import Optional

class Agent(BaseModel):
    name: str = "Agent"
    model: str = "gpt-4o"
    instructions: str = "You are a helpful Agent"
    tools: list = []
    file_name: str = ""

class Response(BaseModel):
    agent: Optional[Agent]
    messages: list
