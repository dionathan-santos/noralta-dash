import streamlit as st  
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import locale
import seaborn as sns
from pymongo import MongoClient


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
    mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name = "real_estate"

    # Load data
    listings_data = get_mongodb_data(mongodb_uri, database_name, "listings")

    # Data preprocessing
    listings_data['Sold Date'] = pd.to_datetime(listings_data['Sold Date'])
    listings_data['Sold Price'] = listings_data['Sold Price'].str.replace('$', '').str.replace(',', '').astype(float)
    listings_data['List Price'] = listings_data['List Price'].str.replace('$', '').str.replace(',', '').astype(float)
    listings_data['Total Flr Area (SF)'] = listings_data['Total Flr Area (SF)'].str.replace(',', '').astype(float)

    # Sidebar Filters
    st.sidebar.header("Filters")

    # Date Range
    min_date = listings_data['Sold Date'].min()
    max_date = listings_data['Sold Date'].max()
    # Set default dates to 2024, but allow selection from full date range
    default_start = datetime(2024, 1, 1)
    default_end = datetime(2024, 12, 31)

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
    bath_range = st.sidebar.slider("Number of Bathrooms", 1, max_baths, (1, max_baths))

    # Bedrooms Slider
    max_beds = int(listings_data['Total Bedrooms'].max())
    bed_range = st.sidebar.slider("Number of Bedrooms", 1, max_beds, (1, max_beds))

    # Price Range
    max_price = int(listings_data['Sold Price'].max())
    price_range = st.sidebar.text_input("Price Range (format: min-max)", f"0-{max_price}")
    try:
        min_price, max_price = map(int, price_range.split('-'))
    except:
        min_price, max_price = 0, listings_data['Sold Price'].max()

    # Days on Market Slider
    dom_range = st.sidebar.slider("Days on Market", 0, 200, (0, 200))

    # Year Built
    years = sorted(listings_data['Year Built'].dropna().unique())
    selected_years = st.sidebar.multiselect("Select Years Built", years)

    # Apply filters
    mask = (
        (listings_data['Sold Date'].dt.date >= start_date) &
        (listings_data['Sold Date'].dt.date <= end_date) &
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

    # Group by property type and month
    monthly_sales_by_type = filtered_data.groupby([filtered_data['Sold Date'].dt.to_period('M'), 'Property Class']).agg({
        'Sold Price': ['sum', 'count', 'mean']
    }).reset_index()

    # Flatten the multi-level columns
    monthly_sales_by_type.columns = ['Sold Date', 'Property Class', 'Total Gross Sales', 'Total Sales #', 'Avg Sales Price']
    monthly_sales_by_type['Sold Date'] = monthly_sales_by_type['Sold Date'].dt.to_timestamp()

    # Calculate total sales for all property types
    total_sales = monthly_sales_by_type.groupby('Sold Date').agg({
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
            'Avg Sales Price: $%{customdata[1]:,.2f}'
        ),
        customdata=total_sales[['Total Gross Sales', 'Avg Sales Price']]
    ))

    # Add lines for each property type
    property_types = ['Detached Single Family', 'Lowrise Apartment', 'Apartment High Rise', 'Condo', 'Townhouse', 'Residential Attached']
    colors = ['blue', 'green', 'orange', 'purple', 'yellow', 'white']

    for i, property_type in enumerate(property_types):
        property_sales = monthly_sales_by_type[monthly_sales_by_type['Property Class'] == property_type]
        fig_sales.add_trace(go.Scatter(
            x=property_sales['Sold Date'],
            y=property_sales['Total Sales #'],
            name=property_type,
            line=dict(color=colors[i], width=2),
            hovertemplate=(
                'Date: %{x}<br>' +
                'Property Type: %{text}<br>' +
                'Total Gross Sales: $%{customdata[0]:,.2f}<br>' +
                'Total Sales #: %{y}<br>' +
                'Avg Sales Price: $%{customdata[1]:,.2f}'
            ),
            customdata=property_sales[['Total Gross Sales', 'Avg Sales Price']],
            text=property_type
        ))

    # Update layout
    fig_sales.update_layout(
        title='Number of Properties Sold per Month by Property Type',
        xaxis_title='Date',
        yaxis_title='Number of Sales',
        legend_title='Property Type'
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







    # Filter to the top 20 communities by number of sales
    top_20_communities = community_metrics.nlargest(20, 'Number_of_Sales')

    # Create a heatmap using go.Figure instead of px.density_heatmap
    fig_heatmap = go.Figure(data=go.Heatmap(
        x=top_20_communities['Community'],
        y=top_20_communities['Average_DOM'],
        z=top_20_communities['Number_of_Sales'].values.reshape(-1, 1),
        colorscale='Viridis',
        hoverongaps=False,
        hovertemplate=(
            "<b>Community: %{x}</b>
    " +
            "Average Days on Market: %{y:.1f} days
    " +
            "Number of Sales: %{z}
    " +
            "Average Sales Price: $%{customdata[0]:,.2f}
    " +
            "Total Volume: $%{customdata[1]:,.2f}
    " +
            "Top Selling Firm: %{customdata[2]}<extra></extra>"
        ),
        customdata=np.dstack((
            top_20_communities['Average_Price'],
            top_20_communities['Total_Volume'],
            top_20_communities['Top_Selling_Firm']
        ))[0]
    ))

    # Update layout
    fig_heatmap.update_layout(
        title='Heatmap of Sold Properties by Top 20 Communities',
        xaxis_title='Community',
        yaxis_title='Average Days on Market',
        xaxis={'tickangle': -45},
        coloraxis_colorbar_title='Number of Sales'
    )

    # Display the heatmap
    st.plotly_chart(fig_heatmap)


if __name__ == "__main__":
    main()