from google.adk.models import BaseLlm
from google.adk.models.lite_llm import LiteLlm


def get_llm_model(model_name: str) -> BaseLlm:
    # TODO: Use Gemini directly instead of LiteLLM everywhere.
    return LiteLlm(model=model_name)
