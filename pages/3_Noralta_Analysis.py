import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import locale
import seaborn as sns
from pymongo import MongoClient
import numpy as np
from utils.data_utils import get_mongodb_data, filter_data

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
    st.title("Noralta Analysis")
    st.write("Detailed analysis specific to Noralta.")

    # MongoDB connection
    mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name = "real_estate"
    collection_name = "listings"

    # Fetch data
    data = get_mongodb_data(mongodb_uri, database_name, collection_name)
    if data.empty:
        st.error("No data available!")
        return

    # Data preprocessing
    data['Sold Date'] = pd.to_datetime(data['Sold Date'])
    data['Sold Price'] = data['Sold Price'].str.replace('$', '').str.replace(',', '').astype(float)
    data['List Price'] = data['List Price'].str.replace('$', '').str.replace(',', '').astype(float)
    data['Total Flr Area (SF)'] = data['Total Flr Area (SF)'].str.replace(',', '').astype(float)

    # Sidebar Filters
    st.sidebar.header("Filters")

    # Date Range
    min_date = data['Sold Date'].min()
    max_date = data['Sold Date'].max()
    default_start = datetime(2024, 1, 1)
    default_end = datetime(2024, 12, 31)
    start_date = st.sidebar.date_input("Start Date", value=default_start, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", value=default_end, min_value=min_date, max_value=max_date)

    # Agent-Specific
    all_agents = sorted(set(data['Listing Agent 1 - Agent Name'].dropna().unique()) | set(data['Buyer Agent 1 - Agent Name'].dropna().unique()))
    selected_agents = st.sidebar.multiselect("Select Agents", all_agents)

    # Community
    communities = sorted(data['Community'].dropna().unique())
    selected_communities = st.sidebar.multiselect("Select Communities", communities)

    # Property Type
    property_types = sorted(data['Property Class'].dropna().unique())
    selected_property_types = st.sidebar.multiselect("Select Property Types", property_types)

    # Building Type
    building_types = sorted(data['Building Type'].dropna().unique())
    selected_building_types = st.sidebar.multiselect("Select Building Types", building_types)

    # Transaction Type
    transaction_types = ['Listing Firm', 'Buyer Firm', 'Dual Representation']
    selected_transaction_type = st.sidebar.selectbox("Select Transaction Type", transaction_types)

    # Price Range
    max_price = int(data['Sold Price'].max())
    price_range = st.sidebar.text_input("Price Range (format: min-max)", f"0-{max_price}")
    try:
        min_price, max_price = map(int, price_range.split('-'))
    except:
        min_price, max_price = 0, data['Sold Price'].max()

    # Year Built
    years = sorted(data['Year Built'].dropna().unique())
    selected_years = st.sidebar.multiselect("Select Years Built", years)

    # Days on Market (DOM)
    max_dom = int(data['Days On Market'].max())
    dom_range = st.sidebar.slider("Days on Market", 0, max_dom, (0, max_dom))

    # Apply filters
    mask = (
        (data['Sold Date'].dt.date >= start_date) &
        (data['Sold Date'].dt.date <= end_date) &
        (data['Sold Price'].between(min_price, max_price)) &
        (data['Days On Market'].between(dom_range[0], dom_range[1])) &
        (data['Year Built'].isin(selected_years) if selected_years else True) &
        (data['Property Class'].isin(selected_property_types) if selected_property_types else True) &
        (data['Building Type'].isin(selected_building_types) if selected_building_types else True) &
        (data['Community'].isin(selected_communities) if selected_communities else True)
    )

    if selected_agents:
        mask &= (
            (data['Listing Agent 1 - Agent Name'].isin(selected_agents)) |
            (data['Buyer Agent 1 - Agent Name'].isin(selected_agents))
        )

    if selected_transaction_type == 'Listing Firm':
        mask &= data['Listing Firm 1 - Office Name'].notna()
    elif selected_transaction_type == 'Buyer Firm':
        mask &= data['Buyer Firm 1 - Office Name'].notna()
    elif selected_transaction_type == 'Dual Representation':
        mask &= (data['Listing Firm 1 - Office Name'] == data['Buyer Firm 1 - Office Name'])

    filtered_data = data[mask]

    # KPI Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total Listings Sold", len(filtered_data))

    with col2:
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

if __name__ == "__main__":
    main()