"""
ReAct Agent Executor
Thought → Action → Observation → ... → Final Answer
"""
 
import json
import re
import os
from openai import AsyncOpenAI
from tools import TOOLS, run_tool
 
client = AsyncOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
)
 
MODEL = "llama-3.3-70b-versatile"
MAX_ITERATIONS = 8
 
SYSTEM_PROMPT = """You are an autonomous AI agent. You solve problems step-by-step using the ReAct framework.
 
You have access to these tools:
{tool_descriptions}
 
STRICT OUTPUT FORMAT — follow this exactly for every step:
 
Thought: <your reasoning about what to do next>
Action: <tool_name>
Action Input: <JSON input for the tool>
 
When you have enough information to answer:
 
Thought: I now have enough information to answer.
Final Answer: <your complete answer to the user>
 
Rules:
- Always start with a Thought
- Use one tool per step
- After each Observation, continue with another Thought
- Never invent tool results
- Be concise in thoughts, detailed in Final Answer
- If a tool fails, try a different approach
"""
 
def build_tool_descriptions():
    lines = []
    for name, meta in TOOLS.items():
        lines.append(f"- **{name}**: {meta['description']}")
        lines.append(f"  Input schema: {json.dumps(meta['input_schema'])}")
    return "\n".join(lines)
 
 
def parse_agent_output(text: str):
    """Parse LLM output into structured action or final answer."""
    # Final answer
    if "Final Answer:" in text:
        answer = text.split("Final Answer:")[-1].strip()
        return {"type": "final", "answer": answer}
 
    # Action
    thought_match = re.search(r"Thought:(.*?)(?=Action:|$)", text, re.DOTALL)
    action_match = re.search(r"Action:\s*(\w+)", text)
    input_match = re.search(r"Action Input:\s*(\{.*?\})", text, re.DOTALL)
 
    if action_match:
        thought = thought_match.group(1).strip() if thought_match else ""
        tool_name = action_match.group(1).strip()
        tool_input = {}
        if input_match:
            try:
                tool_input = json.loads(input_match.group(1))
            except json.JSONDecodeError:
                tool_input = {"raw": input_match.group(1)}
 
        return {
            "type": "action",
            "thought": thought,
            "tool": tool_name,
            "tool_input": tool_input,
        }
 
    # Fallback — treat entire text as final answer
    return {"type": "final", "answer": text.strip()}
 
 
class AgentExecutor:
    async def run(self, user_input: str, chat_id: str, history: list) -> dict:
        steps = []
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT.format(
                    tool_descriptions=build_tool_descriptions()
                ),
            }
        ]
 
        # Inject short-term memory
        for h in history[-6:]:
            messages.append(h)
 
        messages.append({"role": "user", "content": user_input})
 
        for iteration in range(MAX_ITERATIONS):
            response = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=0.2,
                max_tokens=1024,
                stop=["Observation:"],  # Stop before writing its own observation
            )
 
            llm_output = response.choices[0].message.content.strip()
            parsed = parse_agent_output(llm_output)
 
            if parsed["type"] == "final":
                steps.append({
                    "iteration": iteration + 1,
                    "thought": llm_output,
                    "type": "final",
                })
                return {
                    "answer": parsed["answer"],
                    "steps": steps,
                }
 
            # It's an action
            thought = parsed.get("thought", "")
            tool_name = parsed.get("tool", "")
            tool_input = parsed.get("tool_input", {})
 
            step = {
                "iteration": iteration + 1,
                "type": "action",
                "thought": thought,
                "tool": tool_name,
                "tool_input": tool_input,
            }
 
            # Execute tool
            if tool_name in TOOLS:
                try:
                    observation = await run_tool(tool_name, tool_input)
                except Exception as e:
                    observation = f"Tool error: {str(e)}"
            else:
                observation = f"Unknown tool '{tool_name}'. Available: {list(TOOLS.keys())}"
 
            step["observation"] = observation
            steps.append(step)
 
            # Append to messages so LLM sees the full trajectory
            messages.append({
                "role": "assistant",
                "content": llm_output,
            })
            messages.append({
                "role": "user",
                "content": f"Observation: {observation}",
            })
 
        # Max iterations hit
        return {
            "answer": "I reached the maximum number of steps. Here is what I found so far:\n\n" +
                      "\n".join(s.get("observation", "") for s in steps if "observation" in s),
            "steps": steps,
        }
 