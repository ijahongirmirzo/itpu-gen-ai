import json
import logging
from typing import Generator, Optional
from openai import OpenAI

from src.tools import TOOL_DEFINITIONS, execute_tool, get_schema

# Logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(message)s')
log = logging.getLogger("Agent")

SYSTEM_PROMPT = """You are a helpful 3D printing analytics assistant. You help makers and engineers understand their print history, filament usage, and printer performance.

## Data Context
You have access to a database table 'print_jobs' with:
- date, model_name, printer_name (e.g. Ender 3, Bambu X1C)
- material_type (PLA, PETG, etc) & filament_brand
- weight_used_grams, print_time_hours, cost_usd
- success_status (1=success, 0=fail), failure_reason (if failed)
- settings: layer_height, infill, nozzle_temp, bed_temp
- project_category (Miniatures, Functional, etc)

## Your Goal
Help the user optimize their printing workflow.
- Analyze failure rates ("Why is my PETG failing?")
- Track costs ("How much did I spend on filament?")
- Compare printers ("Is the Bambu worth it?")

## Rules
1. Use `query_database` to get real data. Don't guess.
2. If the user asks for "success rate", calculate it: SUM(success_status) / COUNT(*) * 100.
3. Be practical. If a user has many failures, suggest checking common issues like bed adhesion or nozzle clogs based on the data.
4. Only read data. You cannot print files or modifying settings remotely.

Keep answers concise and friendly, like a fellow maker."""

class DataAgent:
    def __init__(self, api_key: str, model="gpt-4o-mini", config=None):
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.config = config or {}
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        log.info(f"Agent loaded: {model}")

    def reset(self):
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]
        log.info("History cleared")

    def chat_sync(self, msg: str) -> str:
        log.info(f"User: {msg}")
        self.history.append({"role": "user", "content": msg})

        # First calling
        completion = self.client.chat.completions.create(
            model=self.model,
            messages=self.history,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto"
        )
        
        resp_msg = completion.choices[0].message
        tool_calls = resp_msg.tool_calls
        
        if tool_calls:
            log.info(f"Tools called: {len(tool_calls)}")
            self.history.append(resp_msg)
            
            for tc in tool_calls:
                fn_name = tc.function.name
                args = json.loads(tc.function.arguments)
                
                log.info(f"Exec {fn_name} {args}")
                result = execute_tool(fn_name, args, self.config)
                
                self.history.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result)
                })
                
            # Follow up response
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=self.history
            )
            resp_msg = completion.choices[0].message
            
        final_text = resp_msg.content or ""
        self.history.append({"role": "assistant", "content": final_text})
        log.info(f"Response: {final_text[:50]}...")
        
        return final_text
