import crewai
import langchain_core.tools
import langchain.tools

print("CrewAI version:", crewai.__version__)
try:
    from crewai.tools import BaseTool
    print("Found crewai.tools.BaseTool")
except ImportError:
    print("crewai.tools.BaseTool NOT found")

try:
    from crewai.tools import tool
    print("Found crewai.tools.tool")
except ImportError:
    print("crewai.tools.tool NOT found")

# Check Agent's expectation
from crewai import Agent
print("Agent tools type annotation:", Agent.__annotations__.get('tools'))