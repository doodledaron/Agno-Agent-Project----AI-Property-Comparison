"""
Property Compare Agents Module - Enhanced with Image Support and Expert Recommendations
"""

import os
import json
import re
from typing import Dict, List, Any

from agno.agent import Agent
from agno.models.groq import Groq
from agno.tools.firecrawl import FirecrawlTools
from agno.tools.calculator import CalculatorTools
from agno.tools.googlesearch import GoogleSearchTools
from agno.models.openai import OpenAIChat
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API keys from environment variables
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

# Default model to use for agents
DEFAULT_MODEL = OpenAIChat(id="gpt-4o-mini")


def create_crawl_agent() -> Agent:
    """
    Creates an agent specialized in crawling property websites with image extraction.
    """
    return Agent(
        tools=[FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=True, crawl=True)],
        show_tool_calls=True,
        markdown=True,
    )


def create_format_agent() -> Agent:
    """
    Creates an agent specialized in formatting raw data into structured JSON.
    """
    return Agent(
        model=DEFAULT_MODEL,
        show_tool_calls=False,
        markdown=True,
    )


def create_property_comparison_agent() -> Agent:
    """
    Creates an agent specialized in finding similar Malaysian properties with images.
    """
    return Agent(
        model=DEFAULT_MODEL,
        tools=[
            GoogleSearchTools(),
            FirecrawlTools(api_key=FIRECRAWL_API_KEY, scrape=True, crawl=True),
            CalculatorTools()
        ],
        show_tool_calls=True,
        markdown=True,
    )


def create_main_agent() -> Agent:
    """
    Creates the main control agent.
    """
    return Agent(
        model=DEFAULT_MODEL,
        markdown=True,
        show_tool_calls=True,
    )


def process_property_url(url: str) -> Dict[str, Any]:
    """
    Extract information from a property listing URL with images.
    """
    try:
        # Create agents
        crawl_agent = create_crawl_agent()
        format_agent = create_format_agent()
        
        # Crawl the website focusing on images
        raw_response = crawl_agent.run(
            f"Scrape {url}. Extract all property details including title, location, price, beds, "
            "baths, size, property type, facilities, amenities, agent info. "
            "IMPORTANT: Extract the main property image URL and gallery image URLs."
        )
        
        # Format data
        format_prompt = f"""
        Extract structured JSON from this property listing. Return ONLY valid JSON.
        
        Required fields:
        - title, location, price (MYR)
        - details: beds, baths, sqft
        - property_type, facilities, amenities
        - agent: name, contact
        - images: main_image (REQUIRED), gallery (array)
        - listing_url
        
        Raw data:
        {raw_response.content}
        """
        
        formatted_response = format_agent.run(format_prompt)
        
        # Parse JSON response
        try:
            if hasattr(formatted_response, 'content'):
                if isinstance(formatted_response.content, dict):
                    return formatted_response.content
                elif isinstance(formatted_response.content, str):
                    try:
                        json_data = json.loads(formatted_response.content)
                        return json_data
                    except json.JSONDecodeError:
                        if "```json" in formatted_response.content:
                            json_text = formatted_response.content.split("```json")[1].split("```")[0].strip()
                            json_data = json.loads(json_text)
                            return json_data
        except Exception as e:
            print(f"Error extracting JSON: {e}")
        
        # Fallback: extract basic info with regex
        raw_text = str(raw_response.content)
        
        # Extract basic property details
        title_match = re.search(r'# ([^\n]+)', raw_text) or re.search(r'title["\']?:\s*["\']([^"\']+)', raw_text)
        title = title_match.group(1) if title_match else "Property Details"
        
        location_match = re.search(r'location["\']?:\s*["\']([^"\']+)', raw_text) or re.search(r'address["\']?:\s*["\']([^"\']+)', raw_text)
        location = location_match.group(1) if location_match else "Not specified"
        
        price_match = re.search(r'RM\s*[\d,]+(\s*/\s*mo)?', raw_text) or re.search(r'price["\']?:\s*["\']([^"\']+)', raw_text)
        price = price_match.group(0) if price_match else "Not available"
        
        beds_match = re.search(r'(\d+)\s*Beds', raw_text) or re.search(r'bed(?:room)?s?["\']?:\s*(\d+)', raw_text)
        beds = beds_match.group(1) if beds_match else "Not available"
        
        baths_match = re.search(r'(\d+)\s*Baths', raw_text) or re.search(r'bath(?:room)?s?["\']?:\s*(\d+)', raw_text)
        baths = baths_match.group(1) if baths_match else "Not available"
        
        size_match = re.search(r'(\d+)\s*sq(?:ft|\.ft\.)', raw_text) or re.search(r'size["\']?:\s*(\d+)', raw_text)
        size = size_match.group(1) if size_match else "Not available"
        
        # Extract image
        image_match = re.search(r'src=["\'](https?://[^"\']+\.(?:jpg|jpeg|png|gif|webp))["\']', raw_text, re.IGNORECASE)
        main_image = image_match.group(1) if image_match else None
        
        # Return basic property data
        return {
            "title": title,
            "location": location,
            "price": price,
            "details": {
                "beds": beds,
                "baths": baths,
                "sqft": size
            },
            "property_type": "Not specified",
            "facilities": [],
            "amenities": {},
            "images": {
                "main_image": main_image,
                "gallery": []
            },
            "listing_url": url
        }
            
    except Exception as e:
        print(f"Error in property extraction: {str(e)}")
        # Return minimal property data on error
        return {
            "title": "Property Details",
            "location": "Not available",
            "price": "Not available",
            "details": {"beds": "N/A", "baths": "N/A", "sqft": "N/A"},
            "property_type": "Not specified",
            "facilities": [],
            "amenities": {},
            "images": {"main_image": None, "gallery": []},
            "listing_url": url,
            "error": f"Error: {str(e)}"
        }


def find_comparable_properties(
    reference_property: Dict[str, Any],
    user_preferences: Dict[str, Any],
    comparison_agent: Any
) -> List[Dict[str, Any]]:
    """
    Find and compare properties similar to the reference property,
    ensuring proper extraction of size, price per square foot, tenure type,
    listing type, and common facilities.
    """
    # Extract key property details
    location = reference_property.get("location", "Kuala Lumpur")
    price = reference_property.get("price", "")
    if isinstance(price, str):
        price = price.replace("RM", "").replace("/mo", "").strip()
    beds = reference_property.get("details", {}).get("beds", "")
    reference_url = reference_property.get("listing_url", "")

    # Enhanced prompt to get detailed property info including tenure, listing type, and facilities
    prompt = f"""
    Find 2 similar property listings to this reference property, 
    ensuring they are DIFFERENT properties:
    
    - Location: {location}
    - Price: up to RM {price}
    - Bedrooms: {beds}
    
    User wants: {user_preferences.get('purpose', 'Not specified')}
    Budget: RM {user_preferences.get('budget_range', {}).get('min', 0)}-{user_preferences.get('budget_range', {}).get('max', 0)}
    
    CRITICAL REQUIREMENTS: 
    1. Do NOT include this reference property URL: {reference_url}
    2. Extract the property size in square feet 
    3. Calculate the price per square foot 
    4. Determine if it's FREEHOLD or LEASEHOLD
    5. Specify if it's FOR SALE or FOR RENT
    6. Extract at least 3-5 common facilities (pool, gym, security, parking, etc.)
    7. Include FULL direct URLs from iProperty.com.my or PropertyGuru.com.my
    8. Extract one main image URL for each property
    
    For each property, crawl the full property page to extract all required details.
    
    Return as JSON array with this exact structure:
    ```json
    [
      {{
        "title": "Property Name",
        "location": "Full Location",
        "price": "RM 500,000",
        "price_numeric": 500000,
        "size": 1000,
        "price_per_sqft": 500,
        "bedrooms": 3,
        "tenure": "Freehold/Leasehold",
        "listing_type": "For Sale/For Rent",
        "facilities": ["Swimming Pool", "Gym", "24-hour Security", "Covered Parking", "Playground"],
        "main_image": "https://example.com/image.jpg",
        "link": "https://www.iproperty.com.my/property/..."
      }},
      ...
    ]
    ```
    """

    # Fetch results
    response = comparison_agent.run(prompt)
    
    # Parse the response
    properties_list = []
    
    try:
        if hasattr(response, 'content'):
            if isinstance(response.content, list):
                properties_list = response.content
            elif isinstance(response.content, dict) and "properties" in response.content:
                properties_list = response.content["properties"]
            elif isinstance(response.content, str):
                # Try extracting JSON
                if "```json" in response.content:
                    json_text = response.content.split("```json")[1].split("```")[0].strip()
                    result = json.loads(json_text)
                    if isinstance(result, list):
                        properties_list = result
                    elif isinstance(result, dict) and "properties" in result:
                        properties_list = result["properties"]
        
        # Process and enhance each property entry
        processed_properties = []
        
        for property_item in properties_list:
            # Skip if this matches the reference URL
            if property_item.get("link") == reference_url:
                continue
                
            # Ensure URL is complete
            if property_item.get("link") and not property_item["link"].startswith("http"):
                if "iproperty" in property_item["link"]:
                    property_item["link"] = f"https://www.iproperty.com.my{property_item['link']}"
                elif "propertyguru" in property_item["link"]:
                    property_item["link"] = f"https://www.propertyguru.com.my{property_item['link']}"
            
            # If we don't have key data, fetch it directly
            missing_data = (
                not property_item.get("size") or 
                not property_item.get("price_per_sqft") or
                not property_item.get("tenure") or
                not property_item.get("listing_type") or
                not property_item.get("facilities")
            )
            
            if missing_data and property_item.get("link"):
                detail_prompt = f"""
                Extract ONLY the following details from this property listing: {property_item['link']}
                
                Return ONLY a JSON object with these fields:
                {{
                    "size": 1000,                                         // Size in square feet (number only)
                    "price": 500000,                                      // Price in RM (number only)
                    "tenure": "Freehold",                                 // Either "Freehold" or "Leasehold"
                    "listing_type": "For Sale",                           // Either "For Sale" or "For Rent"
                    "facilities": ["Swimming Pool", "Gym", "Security"]    // List of facilities
                }}
                """
                
                details_response = comparison_agent.run(detail_prompt)
                
                try:
                    if hasattr(details_response, 'content'):
                        if isinstance(details_response.content, dict):
                            details = details_response.content
                        elif isinstance(details_response.content, str):
                            if "```json" in details_response.content:
                                json_text = details_response.content.split("```json")[1].split("```")[0].strip()
                                details = json.loads(json_text)
                            else:
                                try:
                                    details = json.loads(details_response.content)
                                except:
                                    details = {}
                            
                        # Update property with extracted details
                        if details.get("size"):
                            try:
                                property_item["size"] = int(details["size"])
                            except:
                                # Try to extract numeric part from string
                                size_str = str(details["size"])
                                size_match = re.search(r'(\d+)', size_str)
                                if size_match:
                                    property_item["size"] = int(size_match.group(1))
                        
                        if details.get("price"):
                            try:
                                price_val = details["price"]
                                if isinstance(price_val, str):
                                    price_val = price_val.replace("RM", "").replace(",", "").strip()
                                property_item["price_numeric"] = int(float(price_val))
                            except:
                                pass
                        
                        # Tenure (Freehold/Leasehold)
                        if details.get("tenure"):
                            property_item["tenure"] = details["tenure"]
                        
                        # Listing Type (For Sale/For Rent)
                        if details.get("listing_type"):
                            property_item["listing_type"] = details["listing_type"]
                        
                        # Facilities
                        if details.get("facilities") and isinstance(details["facilities"], list):
                            property_item["facilities"] = details["facilities"]
                        
                        # If we have both size and price, calculate price per sqft
                        if property_item.get("size") and property_item.get("price_numeric"):
                            property_item["price_per_sqft"] = round(property_item["price_numeric"] / property_item["size"])
                except Exception as detail_error:
                    print(f"Error extracting details: {detail_error}")
            
            # Fetch missing images
            if not property_item.get("main_image") and property_item.get("link"):
                image_prompt = f"Extract ONLY the main property image URL from {property_item['link']}."
                image_response = comparison_agent.run(image_prompt)
                
                if hasattr(image_response, 'content') and isinstance(image_response.content, str):
                    url_match = re.search(r'(https?://[^\s"\']+\.(?:jpg|jpeg|png|gif|webp))', 
                                       image_response.content, 
                                       re.IGNORECASE)
                    if url_match:
                        property_item["main_image"] = url_match.group(1)
            
            # Calculate price per sqft if we don't have it already
            if not property_item.get("price_per_sqft") and property_item.get("size") and property_item.get("price"):
                try:
                    price_str = property_item["price"]
                    if isinstance(price_str, str):
                        price_str = price_str.replace("RM", "").replace(",", "").strip()
                        price_numeric = float(price_str)
                    else:
                        price_numeric = float(price_str)
                    
                    size = float(property_item["size"])
                    property_item["price_per_sqft"] = round(price_numeric / size)
                except:
                    pass
            
            # Determine listing type if not provided
            if not property_item.get("listing_type"):
                title = property_item.get("title", "").lower()
                price = property_item.get("price", "").lower()
                
                if "rent" in title or "per month" in price or "/mo" in price:
                    property_item["listing_type"] = "For Rent"
                else:
                    property_item["listing_type"] = "For Sale"
            
            # Ensure we have facilities
            if not property_item.get("facilities") or not property_item["facilities"]:
                property_item["facilities"] = ["Information not available"]
                
            # Add to processed list if it has the minimum required data
            if property_item.get("title") and property_item.get("link"):
                processed_properties.append(property_item)
        
        return processed_properties
    except Exception as e:
        print(f"Error processing comparable properties: {str(e)}")
        return []

def generate_final_recommendation(
    reference_property: Dict[str, Any],
    comparable_properties: List[Dict[str, Any]],
    user_preferences: Dict[str, Any],
    main_agent: Agent
) -> str:
    """
    Generate comprehensive expert property recommendation with enhanced property details.
    Formatted for better readability in a minimalistic UI.
    """
    # Structured expert recommendation prompt with improved format and spacing
    prompt = f"""
    As a Malaysian property expert, analyze these properties:
    
    REFERENCE PROPERTY:
    {json.dumps(reference_property, indent=2)}
    
    ALTERNATIVES:
    {json.dumps(comparable_properties, indent=2)}
    
    USER PREFERENCES:
    {json.dumps(user_preferences, indent=2)}
    
    Your analysis should be formatted for a CLEAN, MINIMALISTIC UI with good spacing between sections.
    Use Markdown formatting with clean headers, bullet points, and concise text.
    
    Follow this EXACT structure for your analysis:
    
    # Property Comparison Analysis
    
    ## 1. Market Value Analysis
    
    ### Reference Property: [PROPERTY NAME]
    * **Price:** RM [PRICE]
    * **Size:** [SIZE] sqft
    * **Price per sqft:** RM [CALCULATED VALUE]
    * **Tenure:** [FREEHOLD/LEASEHOLD]
    * **Listing Type:** [FOR SALE/FOR RENT]
    * **Link:** [FULL PROPERTY URL]
    
    ### Alternatives
    
    **1. [PROPERTY NAME]**
    * **Price:** RM [PRICE]
    * **Size:** [SIZE] sqft
    * **Price per sqft:** RM [CALCULATED VALUE]
    * **Tenure:** [FREEHOLD/LEASEHOLD]
    * **Listing Type:** [FOR SALE/FOR RENT]
    * **Link:** [FULL PROPERTY URL]
    
    **2. [PROPERTY NAME]**
    * **Price:** RM [PRICE]
    * **Size:** [SIZE] sqft
    * **Price per sqft:** RM [CALCULATED VALUE]
    * **Tenure:** [FREEHOLD/LEASEHOLD]
    * **Listing Type:** [FOR SALE/FOR RENT]
    * **Link:** [FULL PROPERTY URL]
    
    ### Price Comparison
    
    | Property | Price | Size (sqft) | Price/sqft |
    |----------|-------|-------------|------------|
    | Reference | RM [PRICE] | [SIZE] | RM [VALUE] |
    | Alternative 1 | RM [PRICE] | [SIZE] | RM [VALUE] |
    | Alternative 2 | RM [PRICE] | [SIZE] | RM [VALUE] |
    
    ### Conclusion
    [CONCISE PRICE ANALYSIS - 2-3 SENTENCES MAX]
    
    ## 2. Property Comparison
    
    ### Location 
    * **Reference:** [LOCATION DETAILS]
    * **Alternatives:** [COMPARISON]
    
    ### Facilities
    * **Reference:** [LIST KEY FACILITIES]
    * **Alternative 1:** [LIST KEY FACILITIES]
    * **Alternative 2:** [LIST KEY FACILITIES]
    
    ### Size and Layout
    * **Reference:** [SIZE AND BEDROOMS]
    * **Alternatives:** [COMPARISON]
    
    ### Accessibility
    [BRIEF ANALYSIS BASED ON USER PREFERENCES]
    
    ### Property Condition
    [BRIEF ASSESSMENT]
    
    ## 3. Investment Potential
    
    ### Market Trends
    [CONCISE AREA SPECIFIC ANALYSIS - 2-3 SENTENCES]
    
    ### Value Appreciation 
    * [BRIEF GROWTH ASSESSMENT]
    * [IMPACT OF TENURE ON FUTURE VALUE]
    
    ### Rental Yield Estimates 
    | Property | Est. Monthly Rental | Annual Yield |
    |----------|---------------------|--------------|
    | Reference | RM [AMOUNT] | [PERCENTAGE]% |
    | Alternative 1 | RM [AMOUNT] | [PERCENTAGE]% |
    | Alternative 2 | RM [AMOUNT] | [PERCENTAGE]% |
    
    ## 4. Expert Recommendation
    
    ### Best Value: [RECOMMENDED PROPERTY NAME]
    * **Price:** RM [PRICE]
    * **Size:** [SIZE] sqft
    * **Tenure:** [FREEHOLD/LEASEHOLD]
    * **Key Facilities:** [TOP 3 FACILITIES]
    * **Property URL:** [FULL URL]
    
    ### Why This Property?
    [2-3 SENTENCES EXPLAINING THE CHOICE]
    
    ### Pros
    * [PRO 1]
    * [PRO 2]
    * [PRO 3]
    
    ### Cons
    * [CON 1]
    * [CON 2]
    
    ### Negotiation Tips
    * [TIP 1]
    * [TIP 2]
    
    ### Final Verdict
    [CONCISE FINAL RECOMMENDATION - 1-2 SENTENCES]
    """
    
    # Get recommendation
    response = main_agent.run(prompt)
    
    # Return response
    if hasattr(response, 'content'):
        return response.content if isinstance(response.content, str) else str(response.content)
    
    return "Could not generate a recommendation."

