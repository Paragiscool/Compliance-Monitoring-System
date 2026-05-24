"""
agent/llm_wrapper.py

RobustLLM: Gemini 2.5 Flash wrapper with retry logic.

Optimization 3 — Deterministic Generation Constraints:
  - temperature=0.0 for structured-output roles (Planner, Verifier).
  - temperature=0.1 for generative roles (Executor, Synthesizer).
  - max_tokens hard-capped per role to prevent the model from spinning
    on confused prompts and generating runaway responses.

Role         | Temperature | Max Tokens  | Rationale
-------------|-------------|-------------|----------------------------------
planner      | 0.0         | 512         | Pure JSON list — needs no creativity
executor     | 0.1         | 256         | Short structured observation JSON
synthesizer  | 0.2         | 1500        | Markdown report — needs mild creativity
verifier     | 0.0         | 256         | Binary JSON verdict — zero creativity
default      | 0.1         | 1024        | Safe fallback
"""

import os
import logging
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Optimization 3: Per-role generation constraints.
# Financial research is deterministic — we want the most probable token, not a creative one.
_ROLE_CONFIGS = {
    "planner":     {"temperature": 0.0, "max_output_tokens": 512},
    "executor":    {"temperature": 0.1, "max_output_tokens": 256},
    "synthesizer": {"temperature": 0.2, "max_output_tokens": 1500},
    "verifier":    {"temperature": 0.0, "max_output_tokens": 256},
    "default":     {"temperature": 0.1, "max_output_tokens": 1024},
}


class RobustLLM:
    def __init__(self, temperature: float = 0.1, role: str = "default"):
        """
        Initialises the Gemini 2.5 Flash wrapper.

        Args:
            temperature: Fallback temperature if no role is specified.
            role:        One of 'planner', 'executor', 'synthesizer', 'verifier', 'default'.
                         When set, overrides temperature and enforces a max_tokens cap.
        """
        self.model_name = "gemini-2.5-flash"
        self.role = role

        # Pick config from role table, fall back to explicit temperature if role unknown
        cfg = _ROLE_CONFIGS.get(role, _ROLE_CONFIGS["default"])
        effective_temp = cfg["temperature"]
        effective_max_tokens = cfg["max_output_tokens"]

        logger.info(
            f"RobustLLM initialised | Role: {role} | "
            f"Temp: {effective_temp} | MaxTokens: {effective_max_tokens}"
        )

        self.llm = ChatGoogleGenerativeAI(
            model=self.model_name,
            api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=effective_temp,
            max_output_tokens=effective_max_tokens,
        )

    def count_tokens(self, text) -> int:
        """Returns a rough estimate of tokens in a text string without external downloads."""
        if isinstance(text, list):
            return sum(len(getattr(msg, 'content', str(msg))) for msg in text) // 4
        return len(str(text)) // 4

    @retry(
        stop=stop_after_attempt(5),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.warning(
            f"API Error. Retrying in {retry_state.next_action.sleep} seconds..."
        )
    )
    def generate(self, prompt: str) -> str:
        """Sends the prompt to the LLM with token tracking and retry protection."""
        token_count = self.count_tokens(prompt)
        logger.info(f"[{self.role}] → {self.model_name} (~{token_count} tokens)")

        response = self.llm.invoke(prompt)
        return response.content


# Quick test block
if __name__ == "__main__":
    print("Testing Planner role (temp=0.0, max_tokens=512)...")
    planner_llm = RobustLLM(role="planner")
    reply = planner_llm.generate("Explain the difference between a 10-K and a 10-Q in one sentence.")
    print(f"Planner response: {reply}\n")

    print("Testing Synthesizer role (temp=0.2, max_tokens=1500)...")
    synth_llm = RobustLLM(role="synthesizer")
    reply2 = synth_llm.generate("Summarize why investors watch revenue growth.")
    print(f"Synthesizer response: {reply2}")
