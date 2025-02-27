import os
import json
import streamlit as st
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load agents from our agents module
from agents import (
    create_crawl_agent,
    create_format_agent,
    process_property_url,
    find_comparable_properties,
    generate_final_recommendation,
    create_property_comparison_agent,
    create_main_agent
)

# Load environment variables
load_dotenv()

# Check for required API keys
if not os.getenv("GROQ_API_KEY"):
    st.error("⚠️ GROQ_API_KEY not found in environment variables. Please set it in the .env file.")
    st.stop()


def initialize_session_state():
    """Initialize session state variables if they don't exist."""
    if "step" not in st.session_state:
        st.session_state.step = 1  # Current step in the workflow

    if "property_url" not in st.session_state:
        st.session_state.property_url = ""
    
    if "reference_property" not in st.session_state:
        st.session_state.reference_property = None
    
    if "user_preferences" not in st.session_state:
        st.session_state.user_preferences = {}
    
    if "comparable_properties" not in st.session_state:
        st.session_state.comparable_properties = None
    
    if "recommendation" not in st.session_state:
        st.session_state.recommendation = None
        
    if "agents_initialized" not in st.session_state:
        st.session_state.crawl_agent = create_crawl_agent()
        st.session_state.format_agent = create_format_agent()
        st.session_state.comparison_agent = create_property_comparison_agent()
        st.session_state.main_agent = create_main_agent()
        st.session_state.agents_initialized = True


def display_header():
    """Display the application header with Malaysian context."""
    st.title("PropertyCompare Malaysia")
    st.subheader("AI-Powered Malaysian Property Comparison Assistant")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        Make data-driven property investment decisions by comparing Malaysian properties 
        from iProperty and PropertyGuru with similar alternatives in the market.
        
        Designed specifically for the Malaysian property market, considering local factors
        like tenure type, maintenance fees, and nearby amenities.
        """)
    
    with col2:
        st.markdown("""
        **Supported Malaysian Property Sites:**
        - iProperty.com.my
        - PropertyGuru.com.my
        """)
    
    st.markdown("---")


def url_input_step():
    """Handle the property URL input step with expanded examples."""
    st.header("Step 1: Property Details")
    st.markdown("Enter the URL of a Malaysian property listing you're interested in purchasing.")
    
    # Add website selection with logos
    website_col1, website_col2 = st.columns(2)
    
    with website_col1:
        st.markdown("**Supported websites:**")
    
    with website_col2:
        st.markdown("iProperty.com.my | PropertyGuru.com.my")
    
    # URL input with example
    example_url = "https://www.iproperty.com.my/property/..." if st.session_state.get("example_site") != "propertyguru" else "https://www.propertyguru.com.my/property/..."
    
    property_url = st.text_input(
        "Property Listing URL",
        value=st.session_state.property_url,
        placeholder=example_url
    )
    
    # Quick examples to help users - expanded with more options
    st.markdown("#### Quick Examples")
    
    # Create a 2x2 grid for examples
    example_row1_col1, example_row1_col2 = st.columns(2)
    example_row2_col1, example_row2_col2 = st.columns(2)
    
    with example_row1_col1:
        if st.button("iProperty House (Sale)", key="iproperty_house", use_container_width=True):
            st.session_state.property_url = "https://www.iproperty.com.my/property/bangsar/sale-104072500/"
            st.session_state.example_site = "iproperty"
            st.rerun()
    
    with example_row1_col2:
        if st.button("iProperty Condo (Rent)", key="iproperty_condo", use_container_width=True):
            st.session_state.property_url = "https://www.iproperty.com.my/property/kampung-kerinchi-bangsar-south/secoya-residence/rent-108241524/"
            st.session_state.example_site = "iproperty"
            st.rerun()
    
    with example_row2_col1:
        if st.button("PropertyGuru House (Sale)", key="pg_house", use_container_width=True):
            st.session_state.property_url = "https://www.propertyguru.com.my/property-listing/petaling-jaya-for-sale-by-wes-chang-41137999"
            st.session_state.example_site = "propertyguru"
            st.rerun()
    
    with example_row2_col2:
        if st.button("PropertyGuru Condo (Rent)", key="pg_condo", use_container_width=True):
            st.session_state.property_url = "https://www.propertyguru.com.my/property-listing/sunsuria-forum-serviced-apartment-for-rent-by-ken-tan-42881000"
            st.session_state.example_site = "propertyguru"
            st.rerun()
    
    # Add helpful caption
    st.caption("Click any example to load a sample property listing URL")
    
    # Validation warning
    if property_url and not ("iproperty.com.my" in property_url or "propertyguru.com.my" in property_url):
        st.warning("⚠️ This application works best with iProperty and PropertyGuru listings. Other websites may not be analyzed correctly.")
    
    # Create space before the analyze button
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Analyze button - centered with increased width
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Analyze Property", type="primary", use_container_width=True):
            if not property_url:
                st.error("Please enter a property URL")
                return
            
            st.session_state.property_url = property_url
            
            with st.spinner("Extracting property details from Malaysian property website..."):
                try:
                    # Progress indicator
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    # Step 1: Extract property details
                    status_text.text("Crawling property website...")
                    progress_bar.progress(25)
                    
                    reference_property = process_property_url(property_url)
                    
                    # Update progress
                    status_text.text("Processing property data...")
                    progress_bar.progress(75)
                    
                    if reference_property and "title" in reference_property:
                        st.session_state.reference_property = reference_property
                        status_text.text("Property details extracted successfully!")
                        progress_bar.progress(100)
                        
                        st.session_state.step = 2
                        st.rerun()
                    else:
                        st.error("Could not extract property details. Please try another URL or use the manual entry option.")
                    
                except Exception as e:
                    st.error(f"Error extracting property details: {str(e)}")


def preferences_input_step():
    """Handle the user preferences input step with improved sliders."""
    st.header("Step 2: Your Requirements")
    
    if st.session_state.reference_property:
        property_data = st.session_state.reference_property
        
        st.subheader("Reference Property Summary")
        col1, col2, col3 = st.columns(3)
        with col1:
            title = property_data.get("title", "Property")
            property_type = property_data.get("property_type", "Not specified")
            st.markdown(f"**{title}**")
            st.markdown(f"*{property_type}*")
        with col2:
            try:
                price = property_data.get("price", "N/A")
                if isinstance(price, dict):
                    price_amount = price.get("amount", "N/A")
                    price_currency = price.get("currency", "RM")
                    st.markdown(f"**Price:** {price_currency} {price_amount:,}")
                else:
                    st.markdown(f"**Price:** {price}")
            except:
                st.markdown("**Price:** Not available")
        with col3:
            try:
                details = property_data.get("details", {})
                beds = details.get("beds", property_data.get("rooms", {}).get("bedrooms", "N/A"))
                baths = details.get("baths", property_data.get("rooms", {}).get("bathrooms", "N/A"))
                st.markdown(f"**Rooms:** {beds} bed, {baths} bath")
            except:
                st.markdown("**Rooms:** Not available")
        
        with st.expander("View Complete Property Details", expanded=False):
            st.json(property_data)
    
    st.markdown("---")
    st.markdown("Please tell us about your requirements to find better matching properties in Malaysia.")
    
    # Create columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        purpose = st.selectbox(
            "Purpose of buying",
            options=["Investment for Rental Income", "Own Stay (Primary Home)", "Own Stay (Vacation Home)", "Both Investment & Own Stay"],
            index=0,
            help="This helps us prioritize rental yield or living comfort metrics"
        )
    
    with col2:
        occupants = st.number_input(
            "Number of people who will stay in the property",
            min_value=1,
            max_value=20,
            value=1,
            help="Helps determine suitable property size and layout"
        )
    
    st.markdown("#### Property Preferences")
    col1, col2 = st.columns(2)
    
    with col1:
        preferred_tenure = st.selectbox(
            "Preferred Tenure",
            options=["No Preference", "Freehold Only", "Leasehold Acceptable"],
            index=0,
            help="Freehold properties generally maintain better value in Malaysia"
        )
    
    with col2:
        preferred_furnishing = st.selectbox(
            "Preferred Furnishing",
            options=["No Preference", "Fully Furnished", "Partially Furnished", "Unfurnished"],
            index=0,
            help="Furnishing status affects move-in readiness and rental potential"
        )
    
    # Fix for location flexibility slider - use session state to persist value
    if "location_flexibility" not in st.session_state:
        st.session_state.location_flexibility = 5
        
    location_flexibility = st.slider(
        "Location flexibility (Willing to consider nearby areas?)",
        min_value=0,
        max_value=10,
        value=st.session_state.location_flexibility,
        step=1,
        help="0 = Only this exact location, 10 = Open to any nearby area in Malaysia"
    )
    st.session_state.location_flexibility = location_flexibility
    
    # Fix for budget range slider - use session state to persist values
    if "budget_min" not in st.session_state:
        st.session_state.budget_min = 100000
    if "budget_max" not in st.session_state:
        st.session_state.budget_max = 500000
    
    # Use a container for the budget slider to ensure proper rendering
    with st.container():
        budget_range = st.slider(
            "Your budget range (RM)",
            min_value=50000,
            max_value=5000000,
            value=(st.session_state.budget_min, st.session_state.budget_max),
            step=10000,
            format="%d",
            help="Typical condo prices in KL range from RM400K-1.5M"
        )
        st.session_state.budget_min = budget_range[0]
        st.session_state.budget_max = budget_range[1]
    
    st.markdown("#### Additional Preferences")
    col1, col2 = st.columns(2)
    
    with col1:
        # Use session state for checkboxes too
        if "public_transport" not in st.session_state:
            st.session_state.public_transport = False
            
        public_transport = st.checkbox(
            "Near public transport (MRT/LRT)",
            value=st.session_state.public_transport,
            help="Properties near MRT/LRT stations often command premium prices but offer convenience"
        )
        st.session_state.public_transport = public_transport
    
    with col2:
        if "international_schools" not in st.session_state:
            st.session_state.international_schools = False
            
        international_schools = st.checkbox(
            "Near international schools",
            value=st.session_state.international_schools,
            help="Important consideration for expats or families considering international education"
        )
        st.session_state.international_schools = international_schools
    
    with st.expander("Malaysia Property Market Context (Optional)", expanded=False):
        st.markdown("#### Additional Malaysian Market Context")
        col1, col2 = st.columns(2)
        with col1:
            if "buying_motivation" not in st.session_state:
                st.session_state.buying_motivation = "First-time buyer"
                
            buying_motivation = st.radio(
                "Your buying motivation",
                options=["First-time buyer", "Upgrading from current property", "Downsizing", "Pure investment"],
                index=["First-time buyer", "Upgrading from current property", "Downsizing", "Pure investment"].index(st.session_state.buying_motivation),
                help="Helps contextualize your property needs"
            )
            st.session_state.buying_motivation = buying_motivation
        with col2:
            if "foreign_buyer" not in st.session_state:
                st.session_state.foreign_buyer = "Malaysian citizen"
                
            foreign_buyer = st.radio(
                "Buyer status",
                options=["Malaysian citizen", "Malaysian PR", "Foreigner"],
                index=["Malaysian citizen", "Malaysian PR", "Foreigner"].index(st.session_state.foreign_buyer),
                help="Foreign buyers face different regulations and minimum purchase thresholds in Malaysia"
            )
            st.session_state.foreign_buyer = foreign_buyer
    
    # Create a spacer before the button for better UI
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Centered button with increased width
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Find Comparable Properties in Malaysia", type="primary", use_container_width=True):
            user_preferences = {
                "purpose": purpose,
                "occupants": occupants,
                "location_flexibility": location_flexibility,
                "budget_range": {
                    "min": st.session_state.budget_min,
                    "max": st.session_state.budget_max
                },
                "malaysian_preferences": {
                    "preferred_tenure": preferred_tenure,
                    "preferred_furnishing": preferred_furnishing,
                    "public_transport_proximity": public_transport,
                    "international_schools_proximity": international_schools,
                    "buying_motivation": buying_motivation,
                    "buyer_status": foreign_buyer
                }
            }
            st.session_state.user_preferences = user_preferences
            
            with st.spinner("Finding and comparing Malaysian properties... (This may take a moment)"):
                try:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    status_text.text("Searching for comparable properties on Malaysian property websites...")
                    progress_bar.progress(25)
                    
                    comparable_properties = find_comparable_properties(
                        st.session_state.reference_property,
                        user_preferences,
                        st.session_state.comparison_agent
                    )
                    st.session_state.comparable_properties = comparable_properties
                    
                    status_text.text("Analyzing property features and investment metrics...")
                    progress_bar.progress(50)
                    
                    status_text.text("Preparing personalized recommendations...")
                    progress_bar.progress(75)
                    
                    recommendation = generate_final_recommendation(
                        st.session_state.reference_property,
                        comparable_properties,
                        user_preferences,
                        st.session_state.main_agent
                    )
                    st.session_state.recommendation = recommendation
                    
                    status_text.text("Analysis complete!")
                    progress_bar.progress(100)
                    
                    st.session_state.step = 3
                    st.rerun()
                except Exception as e:
                    st.error(f"Error comparing Malaysian properties: {str(e)}")
def display_results_step():
    """
    Display the comparison results and recommendations for Malaysian properties.
    Enhanced with better UI spacing and containers for a minimalistic design.
    """
    st.header("Property Comparison Results")
    
    if st.session_state.recommendation:
        try:
            # Display the recommendation in a well-formatted way
            recommendation_text = st.session_state.recommendation
            
            # Check if the recommendation is properly structured with markdown
            if "# Property Comparison Analysis" in recommendation_text or "## 1. Market Value Analysis" in recommendation_text:
                # The recommendation is already well-formatted, so we can split it into sections
                
                # Extract main sections using regex or string splitting
                import re
                
                # Function to extract sections
                def extract_section(text, section_title, next_section_titles=None):
                    pattern = f"{section_title}(.*?)"
                    if next_section_titles:
                        pattern += f"(?:{'|'.join(next_section_titles)})"
                    else:
                        pattern += "$"
                    match = re.search(pattern, text, re.DOTALL)
                    if match:
                        return match.group(1).strip()
                    return ""
                
                # Extract main sections
                market_value_section = extract_section(
                    recommendation_text, 
                    "## 1. Market Value Analysis", 
                    ["## 2. Property Comparison"]
                )
                
                property_comparison_section = extract_section(
                    recommendation_text, 
                    "## 2. Property Comparison", 
                    ["## 3. Investment Potential"]
                )
                
                investment_potential_section = extract_section(
                    recommendation_text, 
                    "## 3. Investment Potential", 
                    ["## 4. Expert Recommendation"]
                )
                
                expert_recommendation_section = extract_section(
                    recommendation_text, 
                    "## 4. Expert Recommendation"
                )
                
                # Create expandable sections with clean styling
                with st.container():
                    # Extract the best value property (if available)
                    best_property_match = re.search(r"### Best Value: (.*?)[\n\*]", expert_recommendation_section)
                    best_property = best_property_match.group(1).strip() if best_property_match else "Recommended Property"
                    
                    # Top summary container with key recommendation
                    st.subheader("💎 Our Recommendation")
                    
                    recommendation_col1, recommendation_col2 = st.columns([3, 1])
                    
                    with recommendation_col1:
                        st.markdown(f"### {best_property}")
                        
                        # Extract final verdict
                        final_verdict_match = re.search(r"### Final Verdict\s*(.*?)(?=$|\n\n)", expert_recommendation_section, re.DOTALL)
                        if final_verdict_match:
                            st.markdown(f"*{final_verdict_match.group(1).strip()}*")
                    
                    with recommendation_col2:
                        # Extract pros count to show as a metric
                        pros_count = len(re.findall(r"\* \[PRO \d+\]", expert_recommendation_section))
                        if pros_count == 0:  # If we couldn't find the template format, try counting actual bullet points
                            pros_section = re.search(r"### Pros\s*(.*?)(?=###)", expert_recommendation_section, re.DOTALL)
                            if pros_section:
                                pros_count = len(re.findall(r"\* ", pros_section.group(1)))
                        
                        st.metric("Pros", f"{pros_count}")
                    
                st.markdown("---")
                
                # Tabbed interface for detailed analysis
                tab1, tab2, tab3, tab4 = st.tabs(["📊 Market Value", "🏙️ Property Comparison", "📈 Investment Potential", "🔍 Expert Analysis"])
                
                with tab1:
                    st.markdown(market_value_section)
                    
                    # Extract property details for a visual comparison
                    try:
                        # Simple regex pattern to extract price values from the recommendation
                        reference_price_match = re.search(r"Reference.*?RM\s*([\d,]+)", market_value_section)
                        alt1_price_match = re.search(r"Alternative 1.*?RM\s*([\d,]+)", market_value_section)
                        alt2_price_match = re.search(r"Alternative 2.*?RM\s*([\d,]+)", market_value_section)
                        
                        if reference_price_match and alt1_price_match and alt2_price_match:
                            reference_price = float(reference_price_match.group(1).replace(',', ''))
                            alt1_price = float(alt1_price_match.group(1).replace(',', ''))
                            alt2_price = float(alt2_price_match.group(1).replace(',', ''))
                            
                            # Create a simple bar chart for price comparison
                            import altair as alt
                            import pandas as pd
                            
                            price_data = pd.DataFrame({
                                'Property': ['Reference', 'Alternative 1', 'Alternative 2'],
                                'Price (RM)': [reference_price, alt1_price, alt2_price]
                            })
                            
                            price_chart = alt.Chart(price_data).mark_bar().encode(
                                x=alt.X('Property', sort=None),
                                y='Price (RM):Q',
                                color=alt.Color('Property', legend=None)
                            ).properties(
                                title='Price Comparison'
                            )
                            
                            st.altair_chart(price_chart, use_container_width=True)
                    except Exception as chart_error:
                        # If chart creation fails, just skip it
                        pass
                
                with tab2:
                    st.markdown(property_comparison_section)
                
                with tab3:
                    st.markdown(investment_potential_section)
                
                with tab4:
                    st.markdown(expert_recommendation_section)
                
                # Bottom action buttons in a clean layout
                st.markdown("---")
                st.subheader("Next Steps")
                
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if st.button("📋 Start Over", type="primary", use_container_width=True):
                        for key in list(st.session_state.keys()):
                            if key != "agents_initialized":
                                del st.session_state[key]
                        initialize_session_state()
                        st.rerun()
                
                with col2:
                    if st.button("🔄 Refine Criteria", use_container_width=True):
                        st.session_state.step = 2
                        st.rerun()
                
                with col3:
                    if st.button("📱 Contact Agent", use_container_width=True):
                        st.info("This feature would connect you with the property agent (not implemented in demo).")
                
            else:
                # Fallback if the recommendation is not in the expected format
                st.markdown(recommendation_text)
                
                # Simple buttons at the bottom
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Start Over", type="primary"):
                        for key in list(st.session_state.keys()):
                            if key != "agents_initialized":
                                del st.session_state[key]
                        initialize_session_state()
                        st.rerun()
                
                with col2:
                    if st.button("Refine Search Criteria"):
                        st.session_state.step = 2
                        st.rerun()
                
        except Exception as e:
            # In case of errors, show the raw recommendation
            st.markdown(st.session_state.recommendation)
            st.error(f"Error displaying formatted results: {str(e)}")
    else:
        # Handle the case when no recommendation is available
        st.error("No recommendation generated. Please try again.")
        
        if st.button("Start Over", type="primary"):
            for key in list(st.session_state.keys()):
                if key != "agents_initialized":
                    del st.session_state[key]
            initialize_session_state()
            st.rerun()
    
    # Property terms section with cleaner formatting
    with st.expander("Understanding Malaysian Property Terms", expanded=False):
        term_col1, term_col2 = st.columns(2)
        
        with term_col1:
            st.markdown("""
            ### Key Malaysian Property Terms
            
            - **Freehold**: Property ownership without time limit
            - **Leasehold**: Property ownership for a fixed term (typically 99 years)
            - **Bumi Lot**: Properties reserved for Bumiputera buyers
            - **Strata Title**: Ownership of apartment/condo unit with shared common areas
            - **Individual Title**: Ownership of land and building
            """)
        
        with term_col2:
            st.markdown("""
            ### Common Abbreviations
            
            - **PSF**: Price Per Square Foot
            - **KLCC**: Kuala Lumpur City Centre
            - **PJ**: Petaling Jaya
            - **MRT**: Mass Rapid Transit
            - **LRT**: Light Rail Transit
            """)


def main():
    """Main application function with minimalistic UI design."""
    st.set_page_config(
        page_title="PropertyCompare Malaysia", 
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Add custom CSS for a minimalistic design
    st.markdown("""
        <style>
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        h1, h2, h3 {
            font-weight: 400;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2rem;
        }
        .stTabs [data-baseweb="tab"] {
            height: 4rem;
            white-space: pre-wrap;
            background-color: transparent;
            border-radius: 4px 4px 0px 0px;
            gap: 1rem;
            padding-top: 0.5rem;
            padding-bottom: 0.5rem;
        }
        .css-1544g2n {padding: 2rem 1rem;}
        </style>
    """, unsafe_allow_html=True)
    
    initialize_session_state()
    
    # Sidebar with minimalistic design
    with st.sidebar:
        st.image("https://assets.grok.com/users/82ed4b11-0e6f-43c1-8956-7418be7acfec/1vx7l9bGla7ACFZz-generated_image.jpg", width=100) 
        st.title("PropertyCompare")
        
        # Step indicator
        st.caption("NAVIGATION")
        step_options = ["Property Details", "Your Requirements", "Results"]
        current_step_idx = st.session_state.step - 1
        
        for i, step in enumerate(step_options):
            if i == current_step_idx:
                st.markdown(f"**→ {step}**")
            else:
                if st.button(step, key=f"nav_{step}", use_container_width=True):
                    st.session_state.step = i + 1
                    st.rerun()
        
        st.markdown("---")
        st.caption("ABOUT")
        st.info("AI-powered Malaysian property comparison tool to help you make data-driven investment decisions.")
    
    # Header container - simplified for minimalistic design
    with st.container():
        if st.session_state.step == 1:
            st.title("PropertyCompare Malaysia")
            st.caption("AI-Powered Malaysian Property Comparison")
        elif st.session_state.step == 2:
            st.title("Your Requirements")
            st.caption("Help us find the perfect property match")
        elif st.session_state.step == 3:
            st.title("Property Analysis")
            st.caption("Expert comparison of your selected properties")
    
    # Main content container
    with st.container():
        if st.session_state.step == 1:
            url_input_step()
        elif st.session_state.step == 2:
            preferences_input_step()
        elif st.session_state.step == 3:
            display_results_step()
    
    # Footer container - minimalist version
    with st.container():
        st.markdown("---")
        st.caption("PropertyCompare Malaysia © 2025 | AI-Powered Property Insights")


if __name__ == "__main__":
    main()
