# PropertyCompare Malaysia

PropertyCompare Malaysia is an AI-powered application specifically designed for the Malaysian property market that helps users make informed property investment decisions by analyzing property listings from iProperty and PropertyGuru and comparing them with alternatives. It uses the Agno Agent framework with LLMs to provide data-driven recommendations tailored to Malaysian property seekers.

## Features

- Analyze Malaysian property listings from iProperty and PropertyGuru URLs
- Capture user requirements and preferences with Malaysia-specific options
- Find and compare similar properties within the Malaysian market
- Consider Malaysian property factors (freehold/leasehold, maintenance fees, etc.)
- Generate detailed property comparisons with Malaysian market context
- Provide actionable recommendations for Malaysian property buyers

## How It Works

PropertyCompare uses a multi-agent approach with specialized AI agents:

1. **Main Control Agent**: Orchestrates the overall workflow and integrates results
2. **Crawl Agent**: Extracts raw data from property listing URLs
3. **Format Agent**: Converts raw data into structured property information
4. **Comparison Agent**: Searches for and compares similar properties

The application follows a three-step process:
1. Property URL input and analysis (using the crawl and format agents)
2. User preferences collection
3. Comparison and recommendation

## Architecture Diagram

```
┌────────────────┐     ┌───────────────┐     ┌─────────────────┐
│ Property URL   │     │ User          │     │ Final           │
│ Input & Parse  │────►│ Preferences   │────►│ Comparison &    │
│                │     │               │     │ Recommendation  │
└────────────────┘     └───────────────┘     └─────────────────┘
        │                      │                      ▲
        ▼                      │                      │
┌─────────────────┐            │                      │
│ Two-Agent       │            ▼                      │
│ Extraction      │    ┌───────────────┐             │
│ ┌───────┐┌─────┐│    │ Comparison    │             │
│ │Crawl  ││Format││───►│ Agent         │─────────────┘
│ │Agent  ││Agent ││    │               │
│ └───────┘└─────┘│    └───────────────┘
└─────────────────┘
```

## Technical Details

### Property Extraction
The application uses a two-agent approach for reliable property extraction:
- **Crawl Agent**: Uses FirecrawlTools to extract raw data from property websites
- **Format Agent**: Processes raw data into clean, structured JSON
- Includes robust fallback mechanisms to extract basic information if JSON parsing fails

### Comparison Engine
The comparison engine:
- Finds similar properties based on location, price, and features
- Calculates Malaysia-specific metrics like price per square foot
- Evaluates properties based on user preferences (investment vs. own stay)

### Recommendation System
The recommendation system:
- Provides a value assessment for the reference property
- Ranks alternatives by suitability
- Highlights key Malaysian property factors (tenure, facilities, location)
- Offers a clear, actionable recommendation

## Installation

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API keys (see `.env.example`)
4. Run the application:
   ```
   streamlit run app.py
   ```

## Requirements

- Python 3.8+
- Streamlit
- Agno Agent framework
- Groq API key (for LLM access)
- FirecrawlTools API key (for property website extraction)
- Optional: Google Search API key for enhanced property search

## Troubleshooting

- **Website Extraction Issues**: If property data extraction fails, try:
  - Using a direct property listing URL rather than a search page
  - Checking that your FirecrawlTools API key is valid
  - Using manual entry if automatic extraction doesn't work

- **Connection Errors**: If you encounter connection issues:
  - Verify your internet connection
  - Check API key permissions
  - Try again after a few minutes (API rate limits may apply)

- **UI Issues**: If the UI doesn't update properly:
  - Use the "Start Over" button to reset the session
  - Restart the Streamlit application

## Development

This is an MVP (Minimum Viable Product) version. Future improvements could include:
- Support for more property listing websites
- Historical price trend analysis
- Neighborhood safety and quality-of-life metrics
- Integration with property valuation APIs
- User accounts to save and compare multiple properties
- Enhanced data visualization for property comparisons