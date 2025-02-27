"""
Test script for the two-agent property extraction approach.
"""

import os
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import the function from the updated agents module
from agents import process_property_url

def test_two_agent_extraction(url):
    """Test the two-agent property extraction approach."""
    print(f"Testing two-agent property extraction for URL: {url}")
    
    try:
        # Process the URL using the two-agent approach
        property_data = process_property_url(url)
        
        # Print the extracted property data
        print("\nExtracted Property Data:")
        print(json.dumps(property_data, indent=2))
        
        return property_data
    except Exception as e:
        print(f"Error during extraction test: {str(e)}")
        return None

if __name__ == "__main__":
    # Test with the PropertyGuru URL
    test_url = "https://www.propertyguru.com.my/property-listing/residensi-brickfields-for-rent-by-loges-42669947"
    
    # Run the test
    test_two_agent_extraction(test_url)