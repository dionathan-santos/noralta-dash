import streamlit as st  
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import locale
import seaborn as sns
from pymongo import MongoClient
import numpy as np


def main():
    st.title("Real Estate Market Analysis Dashboard")

    
def get_mongodb_data(mongodb_uri, database_name, collection_name):
    """
    Retrieve data from MongoDB and return as a pandas DataFrame
    """
    try:
        # Create a MongoDB client
        client = MongoClient(mongodb_uri)
        
        # Get the database
        db = client[database_name]
        
        # Get the collection
        collection = db[collection_name]
        
        # Retrieve all documents from the collection
        data = list(collection.find({}, {'_id': 0}))  # Exclude MongoDB _id field
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Close the connection
        client.close()
        
        if df.empty:
            st.error("No data retrieved from MongoDB")
        
        return df
    
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {str(e)}")
        return pd.DataFrame()

def main():
    st.title("Real Estate Market Analysis Dashboard")

    # Your existing MongoDB connection details
    mongodb_uri = "mongodb+srv://dionathan:19910213200287@cluster1.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster1"
    database_name = "real_estate"

    # Load data
    listings_data = get_mongodb_data(mongodb_uri, database_name, "listings")

    # Data preprocessing
    listings_data['Sold Date'] = pd.to_datetime(listings_data['Sold Date'], format='%m/%d/%Y')
    listings_data['Sold Price'] = listings_data['Sold Price'].str.replace('$', '').str.replace(',', '').astype(float)
    listings_data['List Price'] = listings_data['List Price'].str.replace('$', '').str.replace(',', '').astype(float)
    listings_data['Total Flr Area (SF)'] = listings_data['Total Flr Area (SF)'].str.replace(',', '').astype(float)

    # Sidebar Filters
    st.sidebar.header("Filters")

    # Date Range
    min_date = listings_data['Sold Date'].min()
    max_date = listings_data['Sold Date'].max()
    # Set default dates to 2024, but allow selection from full date range
    default_start = datetime(2025, 1, 1)
    default_end = datetime(2025, 1, 31)

    start_date = st.sidebar.date_input("Start Date",
    value=default_start,
    min_value=min_date,
    max_value=max_date)
    end_date = st.sidebar.date_input("End Date",
    value=default_end,
    min_value=min_date,
    max_value=max_date)

    # Firm Selection
    all_firms = sorted(set(listings_data['Listing Firm 1 - Office Name'].dropna().unique()) |
    set(listings_data['Buyer Firm 1 - Office Name'].dropna().unique()))
    selected_firms = st.sidebar.multiselect("Select Firms", all_firms)

    # Area/City
    cities = sorted(listings_data['Area/City'].dropna().unique())
    selected_cities = st.sidebar.multiselect("Select Cities", cities)

    # Community
    communities = sorted(listings_data['Community'].dropna().unique())
    selected_communities = st.sidebar.multiselect("Select Communities", communities)

    # Property Type
    property_types = sorted(listings_data['Property Class'].dropna().unique())
    selected_property_types = st.sidebar.multiselect("Select Property Types", property_types)

    # Building Type
    building_types = sorted(listings_data['Building Type'].dropna().unique())
    selected_building_types = st.sidebar.multiselect("Select Building Types", building_types)

    # Bathrooms Slider
    max_baths = int(listings_data['Total Baths'].max())
    bath_range = st.sidebar.slider("Number of Bathrooms", 1, max_baths, (0, max_baths))

    # Bedrooms Slider
    max_beds = int(listings_data['Total Bedrooms'].max())
    bed_range = st.sidebar.slider("Number of Bedrooms", 1, max_beds, (0, max_beds))

    # Price Range
    max_price = int(listings_data['Sold Price'].max())
    price_range = st.sidebar.text_input("Price Range (format: min-max)", f"0-{max_price}")
    try:
        min_price, max_price = map(int, price_range.split('-'))
    except:
        min_price, max_price = 0, listings_data['Sold Price'].max()

    # Days on Market Slider
    dom_range = st.sidebar.slider("Days on Market", 0, 1001, (0, 1000))

    # Year Built
    years = sorted(listings_data['Year Built'].dropna().unique())
    selected_years = st.sidebar.multiselect("Select Years Built", years)

    # Apply filters
    mask = (
        (listings_data['Sold Date'].dt.normalize() >= pd.to_datetime(start_date)) &
        (listings_data['Sold Date'].dt.normalize() <= pd.to_datetime(end_date)) &
        (listings_data['Total Baths'].between(bath_range[0], bath_range[1])) &
        (listings_data['Total Bedrooms'].between(bed_range[0], bed_range[1])) &
        (listings_data['Sold Price'].between(min_price, max_price)) &
        (listings_data['Days On Market'].between(dom_range[0], dom_range[1]))
)

    if selected_firms:
        mask &= (
            (listings_data['Listing Firm 1 - Office Name'].isin(selected_firms)) |
            (listings_data['Buyer Firm 1 - Office Name'].isin(selected_firms))
        )

    if selected_cities:
        mask &= listings_data['Area/City'].isin(selected_cities)

    if selected_communities:
        mask &= listings_data['Community'].isin(selected_communities)

    if selected_property_types:
        mask &= listings_data['Property Class'].isin(selected_property_types)

    if selected_years:
        mask &= listings_data['Year Built'].isin(selected_years)

    if selected_building_types:
        mask &= listings_data['Building Type'].isin(selected_building_types)

    # Move this line outside of the if statements
    filtered_data = listings_data[mask] if 'mask' in locals() else listings_data

    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Listings Sold", len(filtered_data))

    with col2:
        st.metric("Total Sales Volume", f"${filtered_data['Sold Price'].sum():,.2f}")
        avg_dom = filtered_data['Days On Market'].mean()
        st.metric("Average DOM", f"{avg_dom:.1f} days")

    with col3:
        avg_price = filtered_data['Sold Price'].mean()
        st.metric("Average Sold Price", f"${avg_price:,.2f}")

    with col4:
        avg_price_sqft = (filtered_data['Sold Price'] / filtered_data['Total Flr Area (SF)']).mean()
        st.metric("Average Price/SqFt", f"${avg_price_sqft:.2f}")

    # Price Trends Chart
    st.subheader("Price Trends Over Time")
    monthly_avg = filtered_data.groupby(filtered_data['Sold Date'].dt.to_period('M')).agg({
        'List Price': 'mean',
        'Sold Price': 'mean'
    }).reset_index()
    monthly_avg['Sold Date'] = monthly_avg['Sold Date'].dt.to_timestamp()

    fig_price = go.Figure()
    fig_price.add_trace(go.Scatter(x=monthly_avg['Sold Date'], y=monthly_avg['List Price'],
                                   name='List Price', line=dict(color='blue')))
    fig_price.add_trace(go.Scatter(x=monthly_avg['Sold Date'], y=monthly_avg['Sold Price'],
                                   name='Sold Price', line=dict(color='green')))
    fig_price.update_layout(title='Average List vs Sold Prices',
                            xaxis_title='Date',
                            yaxis_title='Price ($)')
    st.plotly_chart(fig_price)






    # Sold Listings Over Time
    st.subheader("Sold Listings Over Time")

    # Group by style and month
    monthly_sales_by_style = filtered_data.groupby([filtered_data['Sold Date'].dt.to_period('M'), 'Style']).agg({
        'Sold Price': ['sum', 'count', 'mean']
    }).reset_index()

    # Flatten the multi-level columns
    monthly_sales_by_style.columns = ['Sold Date', 'Style', 'Total Gross Sales', 'Total Sales #', 'Avg Sales Price']
    monthly_sales_by_style['Sold Date'] = monthly_sales_by_style['Sold Date'].dt.to_timestamp()

    # Calculate total sales for all styles
    total_sales = monthly_sales_by_style.groupby('Sold Date').agg({
        'Total Gross Sales': 'sum',
        'Total Sales #': 'sum',
        'Avg Sales Price': 'mean'
    }).reset_index()

    # Create the figure
    fig_sales = go.Figure()

    # Add a thicker line for total sales
    fig_sales.add_trace(go.Scatter(
        x=total_sales['Sold Date'],
        y=total_sales['Total Sales #'],
        name='Total Sales',
        line=dict(color='red', width=6),
        hovertemplate=(
            'Date: %{x}<br>' +
            'Total Gross Sales: $%{customdata[0]:,.2f}<br>' +
            'Total Sales #: %{y}<br>' +
            'Avg Sales Price: $%{customdata[1]:,.2f}<br>'
        ),
        customdata=total_sales[['Total Gross Sales', 'Avg Sales Price']]
    ))

    # Add lines for each style
    styles = sorted(monthly_sales_by_style['Style'].unique())
    colors = ['blue', 'green', 'orange', 'purple', 'yellow', 'white', 'pink', 'gray', 'brown', 'cyan']

    for i, style in enumerate(styles):
        style_sales = monthly_sales_by_style[monthly_sales_by_style['Style'] == style]
        fig_sales.add_trace(go.Scatter(
            x=style_sales['Sold Date'],
            y=style_sales['Total Sales #'],
            name=style,
            line=dict(color=colors[i % len(colors)], width=2),
            hovertemplate=(
                'Date: %{x}<br>' +
                'Style: %{text}<br>' +
                'Total Gross Sales: $%{customdata[0]:,.2f}<br>' +
                'Total Sales #: %{y}<br>' +
                'Avg Sales Price: $%{customdata[1]:,.2f}<br>'
            ),
            customdata=style_sales[['Total Gross Sales', 'Avg Sales Price']],
            text=style
        ))

    # Update layout
    fig_sales.update_layout(
        title='Number of Properties Sold per Month by Style',
        xaxis_title='Date',
        yaxis_title='Number of Sales',
        legend_title='Style'
    )

    # Display the chart
    st.plotly_chart(fig_sales)



    # Days on Market Analysis
    st.subheader("Days on Market vs Sold Price Distribution")

    # Create a 2D histogram (heatmap)
    fig_dom_price = px.density_heatmap(
        filtered_data,
        x='Days On Market',
        y='Sold Price',
        nbinsx=50,
        nbinsy=50,
        title='Distribution of Days on Market vs Sold Price',
        color_continuous_scale='Viridis'
    )

    fig_dom_price.update_layout(
        xaxis_title='Days on Market',
        yaxis_title='Sold Price ($)',
        coloraxis_colorbar_title='Count'
    )

    st.plotly_chart(fig_dom_price)

    # Create community-based metrics
    community_metrics = filtered_data.groupby('Community').agg({
        'Sold Price': ['count', 'mean', 'sum'],
        'Days On Market': 'mean'
    }).reset_index()

    community_metrics.columns = ['Community', 'Number_of_Sales', 'Average_Price', 'Total_Volume', 'Average_DOM']

    # Calculate the top selling firm for each community
    top_selling_firms = filtered_data.groupby('Community').apply(
        lambda x: x['Listing Firm 1 - Office Name'].value_counts().idxmax()
    ).reset_index(name='Top_Selling_Firm')

    # Merge the top selling firm information into the community metrics
    community_metrics = community_metrics.merge(top_selling_firms, on='Community', how='left')

    # Add a detailed community metrics table
    st.subheader("Community Metrics Detail")
    # Format the metrics for better readability
    community_metrics['Average_Price'] = community_metrics['Average_Price'].map('${:,.2f}'.format)
    community_metrics['Total_Volume'] = community_metrics['Total_Volume'].map('${:,.2f}'.format)
    community_metrics['Average_DOM'] = community_metrics['Average_DOM'].map('{:.1f} days'.format)

    # Display the table
    st.dataframe(
        community_metrics.sort_values('Number_of_Sales', ascending=False),
        height=400
    )




    # Check if community_metrics is not empty before filtering
    if not community_metrics.empty:
        # Filter to the top 20 communities by number of sales
        top_20_communities = community_metrics.nlargest(20, 'Number_of_Sales')

        # Sort the top_20_communities by Average_DOM
        top_20_communities = top_20_communities.sort_values('Average_DOM')

        # Create a heatmap using go.Figure
        fig_heatmap = go.Figure(data=go.Heatmap(
            x=top_20_communities['Community'],  # x-axis: Communities
            y=top_20_communities['Average_DOM'],  # y-axis: Average Days on Market
            z=top_20_communities['Number_of_Sales'],  # z-axis: Number of Sales
            colorscale='Viridis',  # Color scale
            hoverongaps=False,
            hovertemplate=(
                "<b>Community: %{x}</b><br>" +

                "Number of Sales: %{z}<br>" +

                "Top Selling Firm: %{customdata[2]}<extra></extra>"
            ),
            customdata=np.array([
                top_20_communities['Average_Price'],
                top_20_communities['Total_Volume'],
                top_20_communities['Top_Selling_Firm']
            ]).T  # Transpose to match the shape
        ))

        # Update layout
        fig_heatmap.update_layout(
            title='Heatmap of Sold Properties by Top 20 Communities',
            xaxis_title='Community',
            yaxis_title='Average Days on Market',
            xaxis=dict(tickangle=-45),
            coloraxis_colorbar_title='Total Sales'
        )

        # Display the heatmap
        st.plotly_chart(fig_heatmap)
    else:
        st.warning("No data available for the selected filters.")






    # Add transaction table at the end of the page before main() closure
    # Section 6: Transaction Details
    st.subheader("Transaction Details")
    st.write(f"Showing all {len(filtered_data)} transactions closed by Noralta")
    
    # Display dataframe with all relevant transactions
    st.dataframe(
        filtered_data[[
            'Listing ID #',
            'Sold Date', 
            'Listing Agent 1 - Agent Name',
            'Buyer Agent 1 - Agent Name',
            'Sold Price',
            'Community',
            'Days On Market',
            'Property Class'
        ]].sort_values('Sold Date', ascending=False),
        height=600
    )
    
    # Add raw data expander
    with st.expander("View Raw Transaction Data"):
        st.write("Full transaction data including all fields:")
        st.dataframe(filtered_data)


if __name__ == "__main__":
    main()
