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

# get default model based on provider and API key
def get_default_model(api_provider="openai", api_key=None, model_id=None):
    """Get the appropriate model based on provider and API key."""
    if api_provider == "openai":
        return OpenAIChat(api_key=api_key, id=model_id or "gpt-4o-mini")
    else:  # groq
        return Groq(api_key=api_key, id=model_id or "llama3-70b-8192")


def create_crawl_agent(firecrawl_api_key=None) -> Agent:
    """Creates an agent specialized in crawling property websites with image extraction."""
    return Agent(
        tools=[FirecrawlTools(api_key=firecrawl_api_key, scrape=True, crawl=True)],
        show_tool_calls=True,
        markdown=True,
    )

def create_format_agent(api_provider="openai", api_key=None, model_id=None) -> Agent:
    """Creates an agent specialized in formatting raw data into structured JSON."""
    model = get_default_model(api_provider, api_key, model_id)
    return Agent(
        model=model,
        show_tool_calls=False,
        markdown=True,
    )

def create_property_comparison_agent(api_provider="openai", api_key=None, model_id=None, firecrawl_api_key=None) -> Agent:
    """Creates an agent specialized in finding similar Malaysian properties with images."""
    model = get_default_model(api_provider, api_key, model_id)
    return Agent(
        model=model,
        tools=[
            GoogleSearchTools(),
            FirecrawlTools(api_key=firecrawl_api_key, scrape=True, crawl=True),
            CalculatorTools()
        ],
        show_tool_calls=True,
        markdown=True,
    )

def create_main_agent(api_provider="openai", api_key=None, model_id=None) -> Agent:
    """Creates the main control agent."""
    model = get_default_model(api_provider, api_key, model_id)
    return Agent(
        model=model,
        markdown=True,
        show_tool_calls=True,
    )

def process_property_url(url: str, api_provider="openai", api_key=None, model_id=None, firecrawl_api_key=None) -> Dict[str, Any]:
    """Extract essential information from a property listing URL."""
    try:
        # Create agents
        crawl_agent = create_crawl_agent(firecrawl_api_key=firecrawl_api_key)
        format_agent = create_format_agent(api_provider=api_provider, api_key=api_key, model_id=model_id)
        
        # Focused crawl instruction - significantly reduced token usage
        raw_response = crawl_agent.run(
            f"Extract ONLY key property data from {url}: title, location, price, beds, baths, size, type, facilities."
        )

        # Truncate to 100K characters max
        if hasattr(raw_response, 'content') and isinstance(raw_response.content, str):
            raw_response.content = raw_response.content[:100000]
        
        # Streamlined formatting prompt
        format_prompt = f"""
        Create JSON with ONLY these fields:
        title, location, price, details(beds/baths/sqft), property_type, facilities, listing_url
        
        Raw data (first 100K chars):
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
            "listing_url": url,
            "error": f"Error: {str(e)}"
        }


def find_comparable_properties(
    reference_property: Dict[str, Any],
    user_preferences: Dict[str, Any],
    comparison_agent: Any
) -> List[Dict[str, Any]]:
    """Find properties similar to reference, with optimized token usage."""
    # Extract minimal necessary details
    location = reference_property.get("location", "Kuala Lumpur")
    price = reference_property.get("price", "")
    if isinstance(price, str):
        price = price.replace("RM", "").replace("/mo", "").strip()
    beds = reference_property.get("details", {}).get("beds", "")
    reference_url = reference_property.get("listing_url", "")
    reference_title = reference_property.get("title", "Unknown Property")

    # Extremely focused initial search - minimal tokens
    search_prompt = f"""
    Find 2 property listings in {location} different from "{reference_title}".
    Budget: RM{user_preferences.get('budget_range', {}).get('min', 0)}-{user_preferences.get('budget_range', {}).get('max', 0)}
    Return ONLY: JSON array with title, location, price, link
    """

    initial_response = comparison_agent.run(search_prompt)
    
    # Parse the response
    properties_list = []
    
    try:
        if hasattr(initial_response, 'content'):
            if isinstance(initial_response.content, list):
                properties_list = initial_response.content
            elif isinstance(initial_response.content, dict) and "properties" in initial_response.content:
                properties_list = initial_response.content["properties"]
            elif isinstance(initial_response.content, str):
                # Try extracting JSON
                if "```json" in initial_response.content:
                    json_text = initial_response.content.split("```json")[1].split("```")[0].strip()
                    result = json.loads(json_text)
                    if isinstance(result, list):
                        properties_list = result
                    elif isinstance(result, dict) and "properties" in result:
                        properties_list = result["properties"]
        
        # Process and enhance each property entry
        processed_properties = []
        
        for property_item in properties_list:
            # Skip if this matches the reference URL or title
            if property_item.get("link") == reference_url or property_item.get("title") == reference_title:
                continue
                
            # Ensure URL is complete
            if property_item.get("link") and not property_item["link"].startswith("http"):
                if "iproperty" in property_item["link"]:
                    property_item["link"] = f"https://www.iproperty.com.my{property_item['link']}"
                elif "propertyguru" in property_item["link"]:
                    property_item["link"] = f"https://www.propertyguru.com.my{property_item['link']}"
        
            # Fetch details in stages to control token usage
            if property_item.get("link"):
                # Stage 1: Core property stats (smallest token count)
                basic_prompt = f"""
                From {property_item['link']} extract ONLY:
                - Size in sqft (number only)
                - Bedrooms (number)
                - Price in RM (number)
                Return as JSON only.
                """
                basic_response = comparison_agent.run(basic_prompt)
                
                try:
                    basic_details = {}
                    if hasattr(basic_response, 'content'):
                        if isinstance(basic_response.content, dict):
                            basic_details = basic_response.content
                        elif isinstance(basic_response.content, str):
                            if "```json" in basic_response.content:
                                json_text = basic_response.content.split("```json")[1].split("```")[0].strip()
                                basic_details = json.loads(json_text)
                            else:
                                try:
                                    basic_details = json.loads(basic_response.content)
                                except:
                                    pass
                    
                    # Update property with basic details
                    if basic_details.get("size"):
                        try:
                            property_item["size"] = int(basic_details["size"])
                        except:
                            size_str = str(basic_details["size"])
                            size_match = re.search(r'(\d+)', size_str)
                            if size_match:
                                property_item["size"] = int(size_match.group(1))
                    
                    if basic_details.get("price"):
                        try:
                            price_val = basic_details["price"]
                            if isinstance(price_val, str):
                                price_val = price_val.replace("RM", "").replace(",", "").strip()
                            property_item["price_numeric"] = int(float(price_val))
                        except:
                            pass
                    
                    if basic_details.get("bedrooms"):
                        property_item["bedrooms"] = basic_details["bedrooms"]
                    
                except Exception as basic_error:
                    print(f"Error processing basic details: {basic_error}")
                
                # Stage 2: Additional details only if needed
                if not property_item.get("tenure") or not property_item.get("listing_type"):
                    extra_prompt = f"""
                    From {property_item['link']} extract ONLY:
                    - Tenure (Freehold or Leasehold)
                    - Listing type (For Sale or For Rent)
                    Return as JSON only.
                    """
                    extra_response = comparison_agent.run(extra_prompt)
                    
                    try:
                        extra_details = {}
                        if hasattr(extra_response, 'content'):
                            if isinstance(extra_response.content, dict):
                                extra_details = extra_response.content
                            elif isinstance(extra_response.content, str):
                                if "```json" in extra_response.content:
                                    json_text = extra_response.content.split("```json")[1].split("```")[0].strip()
                                    extra_details = json.loads(json_text)
                                else:
                                    try:
                                        extra_details = json.loads(extra_response.content)
                                    except:
                                        pass
                        
                        # Update property with extra details
                        if extra_details.get("tenure"):
                            property_item["tenure"] = extra_details["tenure"]
                        if extra_details.get("listing_type"):
                            property_item["listing_type"] = extra_details["listing_type"]
                            
                    except Exception as extra_error:
                        print(f"Error processing extra details: {extra_error}")
                
                # Stage 3: Facilities (only if needed and first two stages succeeded)
                if not property_item.get("facilities") and property_item.get("price_numeric") and property_item.get("size"):
                    facility_prompt = f"""
                    List only 3-5 main facilities at {property_item['link']}.
                    Return as JSON array ["facility1", "facility2", ...]
                    """
                    facility_response = comparison_agent.run(facility_prompt)
                    
                    try:
                        if hasattr(facility_response, 'content'):
                            if isinstance(facility_response.content, list):
                                property_item["facilities"] = facility_response.content[:5]  # Limit to 5
                            elif isinstance(facility_response.content, str):
                                if "```json" in facility_response.content:
                                    json_text = facility_response.content.split("```json")[1].split("```")[0].strip()
                                    facilities = json.loads(json_text)
                                    if isinstance(facilities, list):
                                        property_item["facilities"] = facilities[:5]  # Limit to 5
                                else:
                                    try:
                                        facilities = json.loads(facility_response.content)
                                        if isinstance(facilities, list):
                                            property_item["facilities"] = facilities[:5]  # Limit to 5
                                    except:
                                        pass
                    except Exception as facility_error:
                        print(f"Error processing facilities: {facility_error}")
            
            # Calculate price per sqft if we have the necessary data
            if not property_item.get("price_per_sqft") and property_item.get("size") and property_item.get("price_numeric"):
                try:
                    size = float(property_item["size"])
                    if size > 0:
                        property_item["price_per_sqft"] = round(property_item["price_numeric"] / size)
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
            
            # Default tenure if not found
            if not property_item.get("tenure"):
                property_item["tenure"] = "Unknown"
            
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
    
    
def generate_final_recommendation(reference_property: Dict[str, Any], comparable_properties: List[Dict[str, Any]], user_preferences: Dict[str, Any], main_agent: Agent) -> str:
    """Generate optimized property recommendation."""
    # Strip down properties to essential fields only to reduce tokens
    stripped_reference = {
        "title": reference_property.get("title", ""),
        "location": reference_property.get("location", ""),
        "price": reference_property.get("price", ""),
        "size": reference_property.get("details", {}).get("sqft", ""),
        "beds": reference_property.get("details", {}).get("beds", ""),
        "baths": reference_property.get("details", {}).get("baths", ""),
        "facilities": reference_property.get("facilities", [])[:3],  # Limit to top 3
        "tenure": reference_property.get("tenure", "Unknown"),
        "listing_type": reference_property.get("listing_type", "Unknown"),
        "listing_url": reference_property.get("listing_url", "")
    }
    
    # Similarly strip comparable properties
    stripped_comparables = []
    for prop in comparable_properties:
        stripped_prop = {
            "title": prop.get("title", ""),
            "location": prop.get("location", ""),
            "price": prop.get("price", ""),
            "price_numeric": prop.get("price_numeric", 0),
            "size": prop.get("size", 0),
            "bedrooms": prop.get("bedrooms", ""),
            "tenure": prop.get("tenure", "Unknown"),
            "listing_type": prop.get("listing_type", "Unknown"),
            "facilities": prop.get("facilities", [])[:3],  # Limit to top 3
            "link": prop.get("link", "")
        }
        stripped_comparables.append(stripped_prop)
    
    # Simplified user preferences - only include what's needed
    minimal_preferences = {
        "purpose": user_preferences.get("purpose", ""),
        "budget_range": user_preferences.get("budget_range", {}),
    }
    
    # Focused, shorter prompt
    prompt = f"""
    As Malaysian property expert, compare:
    
    REF: {json.dumps(stripped_reference)}
    
    ALT: {json.dumps(stripped_comparables)}
    
    PREFS: {json.dumps(minimal_preferences)}
    
    Create markdown report with:
    1. Market Value Analysis (ref property, alternatives, price comparison)
    2. Property Comparison (location, facilities, size)
    3. Investment Potential
    4. Expert Recommendation (best value, pros/cons, negotiation tips)
    
    ONLY include essential data. Be concise.
    """
    
    # Get recommendation
    response = main_agent.run(prompt)
    
    # Return response
    if hasattr(response, 'content'):
        return response.content if isinstance(response.content, str) else str(response.content)
    
    return "Could not generate a recommendation."