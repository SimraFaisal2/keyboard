from typing import TypedDict, Annotated
import re
import os
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from sandbox import run_code_in_sandbox

# Fallback checking to ensure the environment has an active key
api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
if not api_key:
    raise ValueError("❌ Missing Google API Key. Please set GOOGLE_API_KEY or GEMINI_API_KEY.")

# Initialize Gemini 1.5 Flash (highly fast, stable, and completely free tier)
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2, google_api_key=api_key)

def extract_python_code(text: str) -> str:
    """Helper function to cleanly pull code blocks away from markdown text."""
    pattern = r"```python(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.replace("```", "").strip()

class AgentState(TypedDict):
    source_code: str
    test_code: str
    security_report: str
    sandbox_output: str
    iterations: int
    status: str

# Node: Security Auditor Agent
def security_auditor(state: AgentState):
    print("🤖 [Auditor Agent] Reviewing code for vulnerabilities...")
    prompt = f"""
    You are an expert Security Auditor. Analyze this code for security flaws, bugs, or architectural weaknesses:
    {state['source_code']}
    
    If modifications or fixes are required, provide the complete updated code wrapped inside a single ```python code block.
    """
    response = llm.invoke(prompt)
    
    if "```python" in response.content:
        fixed_code = extract_python_code(response.content)
        return {
            "security_report": response.content, 
            "source_code": fixed_code,
            "iterations": state.get("iterations", 0) + 1
        }
        
    return {"security_report": response.content, "iterations": state.get("iterations", 0) + 1}

# Node: QA Automator Agent
def qa_automator(state: AgentState):
    print("🤖 [QA Agent] Generating test suite...")
    prompt = f"""
    You are a professional QA Engineer. Write a comprehensive unit test suite using `pytest` for this specific code:
    {state['source_code']}
    
    CRITICAL: Only output valid python code inside a single ```python block. Do not write text explanations or descriptions.
    """
    response = llm.invoke(prompt)
    test_code = extract_python_code(response.content)
    return {"test_code": test_code}

# Node: Sandbox Execution Engine
def code_executor(state: AgentState):
    print(f"🔄 [Sandbox Execution] Running test suite inside isolated Docker container... (Attempt {state['iterations']})")
    result = run_code_in_sandbox(state["source_code"], state["test_code"])
    
    if result["success"]:
        print("✅ [Sandbox Execution] All tests passed cleanly!")
        return {"sandbox_output": result["output"], "status": "passed"}
    else:
        print("❌ [Sandbox Execution] Tests failed or system raised execution errors.")
        combined_logs = f"{result['output']}\n{result['error'] if result['error'] else ''}"
        return {"sandbox_output": combined_logs, "status": "failed"}

# Routing Logic (Conditional Edge Loop)
def route_after_test(state: AgentState):
    if state["status"] == "passed":
        return "success"
    elif state["iterations"] >= 3:
        print("⚠️ [Swarm Engine] Max retry attempts (3) hit. Halting loop to prevent infinite runs.")
        return "max_retries"
    else:
        print("🔄 [Swarm Engine] Code failed validation. Routing back to Auditor for structural correction...")
        return "retry"

# Construct the Graph
workflow = StateGraph(AgentState)

workflow.add_node("auditor", security_auditor)
workflow.add_node("qa", qa_automator)
workflow.add_node("sandbox", code_executor)

workflow.set_entry_point("auditor")
workflow.add_edge("auditor", "qa")
workflow.add_edge("qa", "sandbox")

workflow.add_conditional_edges(
    "sandbox",
    route_after_test,
    {
        "success": END,
        "max_retries": END,
        "retry": "auditor" 
    }
)

app = workflow.compile()