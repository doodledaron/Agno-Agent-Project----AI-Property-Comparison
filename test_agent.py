# Just a file to test out the agent with the Firecrawl API key. The agent is used to scrape the URL provided in the test. The agent is created with the FirecrawlTools tool, which is used to scrape the URL. The agent is then run with the URL and the instructions to return the data in JSON format. The response is then printed to the console.
# from agno.agent import Agent
from agno.tools.firecrawl import FirecrawlTools
import os
from dotenv import load_dotenv
load_dotenv()
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
# os.environ["FIRECRAWL_API_KEY"] = FIRECRAWL_API_KEY

agent = Agent(
    tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=False, crawl=True)],
    show_tool_calls=True,
    markdown=True,
    
    
)
response = agent.run("Scrape this https://www.propertyguru.com.my/property-listing/residensi-brickfields-for-rent-by-loges-42669947. Instructions: Return me in JSON format")
print(response)