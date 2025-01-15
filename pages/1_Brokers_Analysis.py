import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import folium
from streamlit_folium import folium_static
from datetime import datetime
import numpy as np
from utils.data_utils import get_mongodb_data

# Set page config
st.set_page_config(
    page_title="Real Estate Market Analysis",
    layout="wide"
)

# Custom CSS for better spacing and layout
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    </style>
    """, unsafe_allow_html=True)

def load_data():
    # MongoDB connection
    mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name = "real_estate"

    # Fetch data from listings collection
    listings_data = get_mongodb_data(mongodb_uri, database_name, "listings")

    # Convert price columns to numeric
    price_columns = ['List Price', 'Sold Price', 'Price Per SQFT']
    for col in price_columns:
        listings_data[col] = listings_data[col].str.replace('[$,]', '', regex=True).astype(float)

    # Convert dates
    listings_data['Sold Date'] = pd.to_datetime(listings_data['Sold Date'])

    return listings_data

def filter_data(data, filters):
    mask = pd.Series(True, index=data.index)

    if filters.get('cities'):
        mask &= data['Area/City'].isin(filters['cities'])

    if filters.get('communities'):
        mask &= data['Community'].isin(filters['communities'])

    if filters.get('property_types'):
        mask &= data['Property Class'].isin(filters['property_types'])

    if filters.get('beds_range'):
        mask &= (data['Total Bedrooms'] >= filters['beds_range'][0]) & \
                (data['Total Bedrooms'] <= filters['beds_range'][1])

    if filters.get('baths_range'):
        mask &= (data['Total Baths'] >= filters['baths_range'][0]) & \
                (data['Total Baths'] <= filters['baths_range'][1])

    if filters.get('price_range'):
        mask &= (data['Sold Price'] >= filters['price_range'][0]) & \
                (data['Sold Price'] <= filters['price_range'][1])

    if filters.get('dom_range'):
        mask &= (data['Days On Market'] >= filters['dom_range'][0]) & \
                (data['Days On Market'] <= filters['dom_range'][1])

    if filters.get('year_built'):
        mask &= data['Year Built'].isin(filters['year_built'])

    return data[mask]

def create_sidebar_filters(data):
    st.sidebar.header("Filters")

    # Area/City Filter
    cities = sorted(data['Area/City'].unique())
    selected_cities = st.sidebar.multiselect(
        "Select Area/City",
        options=cities,
        default=[]
    )

    # Community Filter
    communities = sorted(data['Community'].unique())
    selected_communities = st.sidebar.multiselect(
        "Select Community",
        options=communities,
        default=[]
    )

    # Property Type Filter
    property_types = sorted(data['Property Class'].unique())
    selected_property_types = st.sidebar.multiselect(
        "Select Property Type",
        options=property_types,
        default=[]
    )

    # Beds & Baths Sliders
    max_beds = int(data['Total Bedrooms'].max())
    max_baths = int(data['Total Baths'].max())

    beds_range = st.sidebar.slider(
        "Number of Bedrooms",
        0, max_beds, (0, max_beds)
    )

    baths_range = st.sidebar.slider(
        "Number of Bathrooms",
        0, max_baths, (0, max_baths)
    )

    # Price Range Input
    min_price = int(data['Sold Price'].min())
    max_price = int(data['Sold Price'].max())
    price_range = st.sidebar.slider(
        "Price Range ($)",
        min_price, max_price, (min_price, max_price),
        step=10000,
        format="$%d"
    )

    # Days on Market Slider
    dom_range = st.sidebar.slider(
        "Days on Market",
        0, 200, (0, 200)
    )

    # Year Built Selection
    years = sorted(data['Year Built'].unique())
    selected_years = st.sidebar.multiselect(
        "Select Year Built",
        options=years,
        default=[]
    )

    return {
        'cities': selected_cities,
        'communities': selected_communities,
        'property_types': selected_property_types,
        'beds_range': beds_range,
        'baths_range': baths_range,
        'price_range': price_range,
        'dom_range': dom_range,
        'year_built': selected_years
    }

def display_kpis(filtered_data):
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Listings Sold",
            f"{len(filtered_data):,}"
        )

    with col2:
        avg_dom = filtered_data['Days On Market'].mean()
        st.metric(
            "Average Days on Market",
            f"{avg_dom:.1f} days"
        )

    with col3:
        avg_price = filtered_data['Sold Price'].mean()
        st.metric(
            "Average Sold Price",
            f"${avg_price:,.2f}"
        )

    with col4:
        avg_price_sqft = filtered_data['Price Per SQFT'].mean()
        st.metric(
            "Average Price/SqFt",
            f"${avg_price_sqft:.2f}"
        )

def main():
    st.title("Real Estate Market Analysis")
    st.write("Comprehensive market analysis and performance metrics")

    # Load data
    data = load_data()

    # Create and apply filters
    filters = create_sidebar_filters(data)
    filtered_data = filter_data(data, filters)

    # Display KPIs
    display_kpis(filtered_data)

    # Create two columns for the charts
    col1, col2 = st.columns(2)

    with col1:
        # Price Trends Chart
        st.subheader("Price Trends")
        price_trends = filtered_data.groupby(filtered_data['Sold Date'].dt.to_period('M')).agg({
            'List Price': 'mean',
            'Sold Price': 'mean'
        }).reset_index()

        fig_price = px.line(price_trends,
                          x='Sold Date',
                          y=['List Price', 'Sold Price'],
                          title="Average List vs Sold Price Trends")
        st.plotly_chart(fig_price, use_container_width=True)

    with col2:
        # Days on Market Analysis
        st.subheader("Days on Market Distribution")
        fig_dom = px.histogram(filtered_data,
                             x='Days On Market',
                             nbins=30,
                             title="Distribution of Days on Market")
        st.plotly_chart(fig_dom, use_container_width=True)

    # Map visualization
    st.subheader("Property Locations")
    # Note: You'll need to add latitude and longitude to your data for this to work
    # This is a placeholder for the map visualization

    # Add more visualizations as needed

if __name__ == "__main__":
    main()