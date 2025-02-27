from typing import Dict, List, Any
import re

def extract_property_details(scraped_data: str) -> List[Dict[str, Any]]:
    """
    Parses scraped property data to extract key details.

    Args:
        scraped_data (str): Raw HTML or text data from Firecrawl.

    Returns:
        List[Dict[str, Any]]: Extracted property details.
    """
    properties = []
    matches = re.findall(r'(\d+)\s+bedroom.*?RM\s*([\d,]+)', scraped_data, re.IGNORECASE)
    for match in matches:
        properties.append({
            "bedrooms": int(match[0]),
            "price": f"RM {match[1]}",
        })
    return properties