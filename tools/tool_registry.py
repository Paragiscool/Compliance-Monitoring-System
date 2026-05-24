import json
import logging
import os
import random
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

# Import live tools
from tools.sec_edgar import SecEdgarTool
from tools.financial_api import FinancialDataTool
from tools.web_search import WebSearchTool
from tools.news_sentiment import NewsSentimentTool

# ---------------------------------------------------------
# Remaining Mock Tool Stubs
# ---------------------------------------------------------

def earnings_transcript(ticker: str, quarter: str, year: int) -> str:
    """Mock implementation of earnings_transcript."""
    return f"[MOCK EARNINGS TRANSCRIPT] {ticker} {quarter} {year}.\nCEO: We had a record breaking quarter.\nCFO: Operating expenses were kept under control."

def company_profile(ticker: str) -> str:
    """Mock implementation of company_profile."""
    profile = {
        "ticker": ticker,
        "name": f"{ticker} Inc.",
        "sector": "Technology",
        "market_cap": "2.5 Trillion USD",
        "description": "A leading technology company specializing in consumer electronics."
    }
    return f"[MOCK COMPANY PROFILE]\n{json.dumps(profile, indent=2)}"


# ---------------------------------------------------------
# Tool Registry Class
# ---------------------------------------------------------

class ToolRegistry:
    def __init__(self, schemas_dir: str = "tools/schemas", simulate_failures: bool = False):
        self.schemas_dir = schemas_dir
        self.schemas: Dict[str, dict] = {}
        self.simulate_failures = simulate_failures
        if simulate_failures:
            logger.warning("⚠️  CHAOS MODE ENABLED: 50% random failure rate injected into all tool calls.")
        
        # Initialize Live Tools
        self.sec_tool = SecEdgarTool()
        self.fin_tool = FinancialDataTool()
        self.web_tool = WebSearchTool()
        self.news_tool = NewsSentimentTool()
        
        self.tools: Dict[str, Callable] = {
            "sec_filing_search": self.sec_tool.fetch_filing,
            "web_search": self.web_tool.search,
            "financial_data_api": self.fin_tool.fetch_financials,
            "news_sentiment": self.news_tool.analyze_sentiment,
            "earnings_transcript": earnings_transcript,
            "company_profile": company_profile
        }
        self._load_schemas()

    def _load_schemas(self):
        """Loads all JSON schemas from the schemas directory."""
        if not os.path.exists(self.schemas_dir):
            logger.warning(f"Schema directory '{self.schemas_dir}' not found. Tool validation will be skipped.")
            return

        for filename in os.listdir(self.schemas_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.schemas_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        schema = json.load(f)
                        name = schema.get("function", {}).get("name")
                        if name:
                            self.schemas[name] = schema
                except Exception as e:
                    logger.error(f"Failed to load schema '{filename}': {e}")

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Validates the arguments against the schema (basic validation)
        and executes the corresponding live tool or stub.
        When simulate_failures=True, randomly injects a 50% failure rate
        to stress-test the agent's error-recovery logic.
        """
        # --- THE CHAOS INJECTOR ---
        if self.simulate_failures and random.random() < 0.50:
            error_msg = f"Simulated network timeout for '{tool_name}'. Please retry or use an alternative source."
            logger.warning(f"💥 CHAOS INJECTED: {error_msg}")
            return json.dumps({"error": error_msg, "chaos": True})
        # --------------------------

        if tool_name not in self.tools:
            return json.dumps({"error": f"Tool '{tool_name}' not found in registry."})

        # Schema Validation: Check required params and enum values
        schema = self.schemas.get(tool_name)
        if schema:
            params_schema = schema.get("function", {}).get("parameters", {})
            properties = params_schema.get("properties", {})
            required_params = params_schema.get("required", [])

            # Check for missing required params
            missing_params = [p for p in required_params if p not in arguments]
            if missing_params:
                return json.dumps({"error": f"Missing required parameters for '{tool_name}': {', '.join(missing_params)}"})

            # Check for invalid enum values
            for param, value in arguments.items():
                prop_def = properties.get(param, {})
                allowed_values = prop_def.get("enum")
                if allowed_values and value not in allowed_values:
                    return json.dumps({"error": f"Invalid value '{value}' for parameter '{param}' in '{tool_name}'. Allowed values: {allowed_values}"})

        # Live Execution with "Soft Catch"
        try:
            func = self.tools[tool_name]
            result = func(**arguments)
            return result
        except TypeError as e:
            return json.dumps({"error": f"Parameter mismatch for '{tool_name}'. {str(e)}"})
        except Exception as e:
            return json.dumps({"error": f"Failed to execute '{tool_name}': {str(e)}. Please retry or check inputs."})


# Quick test when running the file directly
if __name__ == "__main__":
    registry = ToolRegistry(schemas_dir=os.path.join(os.path.dirname(__file__), "tools", "schemas"))
    
    print("Testing Live Tool Execution:")
    print("-" * 40)
    
    # Test 1: Valid Execution (Web Search)
    print("Executing Web Search...")
    print(registry.execute_tool("web_search", {"query": "Microsoft latest news", "max_results": 2}))
    print("-" * 40)
