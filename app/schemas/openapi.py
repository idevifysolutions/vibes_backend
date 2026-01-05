from pydantic import BaseModel

class OpenAIPromptRequest(BaseModel):
    prompt: str
