import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pymongo import MongoClient
import numpy as np

def get_mongodb_data(mongodb_uri, database_name, collection_name):
    """
    Retrieve data from MongoDB and return as a pandas DataFrame
    """
    try:
        client = MongoClient(mongodb_uri)
        db = client[database_name]
        collection = db[collection_name]
        data = list(collection.find({}, {'_id': 0}))
        df = pd.DataFrame(data)
        client.close()
        return df
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {str(e)}")
        return pd.DataFrame()

def main():
    st.title("Noralta Analysis")
    st.write("Aimed at providing insights for Royal LePage Noralta Real Estate.")

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

    # Area/City
    cities = sorted(data['Area/City'].dropna().unique())
    selected_cities = st.sidebar.multiselect("Select Cities", cities)

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
        (data['Community'].isin(selected_communities) if selected_communities else True) &
        (data['Area/City'].isin(selected_cities) if selected_cities else True)
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

    # Filter data for Noralta
    noralta_data = filtered_data[
        ((filtered_data['Listing Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate') |
         (filtered_data['Buyer Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate'))
    ]

    # Tab 1: Noralta's Numbers
    st.header("Noralta's Numbers")

    # Section 1: Overview KPIs
    st.subheader("Overview KPIs")
    col1, col2, col3, col4 = st.columns([1, 1.5, 1.5, 1])  # Adjust column widths for better spacing
    with col1:
        st.metric("Total Listings Closed by Noralta", len(noralta_data))
    with col2:
        total_sales_volume = noralta_data['Sold Price'].sum()
        st.metric("Total Sales Volume", f"${total_sales_volume:,.2f}")
    with col3:
        noralta_dom = int(noralta_data['Days On Market'].mean())
        market_dom = int(filtered_data['Days On Market'].mean())
        st.metric("Average DOM", f"{noralta_dom} days", delta=f"{market_dom - noralta_dom} days vs market", delta_color="inverse")
    with col4:
        noralta_sold_ratio = round(noralta_data['Sold Pr / List Pr Ratio'].mean(), 1)
        market_sold_ratio = round(filtered_data['Sold Pr / List Pr Ratio'].mean(), 1)
        st.metric("Sold/List Price Ratio", f"{noralta_sold_ratio}%", delta=f"{noralta_sold_ratio - market_sold_ratio:.1f}% vs market", delta_color="normal")
        
# Section 2: Market Share Analysis
    
    # Section 2: Market Share Analysis
    st.subheader("Market Share Analysis")
    col1, col2 = st.columns(2)
    with col1:
        # Pie Chart: Noralta’s share of total transactions vs competitors
        total_transactions = len(filtered_data)
        noralta_transactions = len(noralta_data)
        other_transactions = total_transactions - noralta_transactions
        fig_pie = px.pie(
            values=[noralta_transactions, other_transactions],
            names=["Noralta", "Competitors"],
            title="Noralta's Share of Total Transactions"
        )
        st.plotly_chart(fig_pie)
    with col2:
        # Bar Chart: Market share breakdown by property type
        property_type_share = noralta_data.groupby('Property Class').size().reset_index(name='Count')
        fig_bar = px.bar(
            property_type_share,
            x='Property Class',
            y='Count',
            title="Market Share by Property Type"
        )
        st.plotly_chart(fig_bar)

    # Section 3: Community Performance
    st.subheader("Community Performance")
    col1, col2 = st.columns(2)
    with col1:
        # Top Communities by Sales Volume
        top_communities_volume = noralta_data.groupby('Community')['Sold Price'].sum().nlargest(10).reset_index()
        fig_volume = px.bar(
            top_communities_volume,
            x='Community',
            y='Sold Price',
            title="Top Communities by Sales Volume"
        )
        st.plotly_chart(fig_volume)
    with col2:
        # Top Communities by Number of Sales
        top_communities_sales = noralta_data.groupby('Community').size().nlargest(10).reset_index(name='Count')
        fig_sales = px.bar(
            top_communities_sales,
            x='Community',
            y='Count',
            title="Top Communities by Number of Sales"
        )
        st.plotly_chart(fig_sales)




    # Section 4: Trends Over Time
    st.subheader("Trends Over Time")
    monthly_sales = noralta_data.groupby(noralta_data['Sold Date'].dt.to_period('M')).agg({
        'Listing ID #': 'count',  # Count of transactions (Total Sales)
        'Days On Market': 'mean'  # Average DOM
    }).reset_index()
    monthly_sales['Sold Date'] = monthly_sales['Sold Date'].dt.to_timestamp()

    fig_trends = go.Figure()
    fig_trends.add_trace(go.Scatter(
        x=monthly_sales['Sold Date'],
        y=monthly_sales['Listing ID #'],  # Total Sales (count of transactions)
        name='Total Sales',
        line=dict(color='blue')
    ))
    fig_trends.add_trace(go.Scatter(
        x=monthly_sales['Sold Date'],
        y=monthly_sales['Days On Market'],
        name='Average DOM',
        line=dict(color='green'),
        yaxis='y2'
    ))
    fig_trends.update_layout(
        title='Monthly Total Sales and DOM Trends',
        xaxis_title='Date',
        yaxis_title='Total Sales (Transactions)',  # Updated y-axis title
        yaxis2=dict(title='Average DOM', overlaying='y', side='right'),
        legend_title='Metric'
    )
    st.plotly_chart(fig_trends)


    # Seasonal DOM Trends: Heatmap of Average DOM by Month
    st.subheader("Noralta Seasonal DOM Trends: Average DOM by Month")

    # Ensure required columns exist
    required_columns = ['Sold Date', 'Days On Market']
    missing_columns = [col for col in required_columns if col not in noralta_data.columns]

    if missing_columns:
        st.error(f"Missing required columns: {missing_columns}. Please check your dataset.")
    else:
        # Extract month and year from Sold Date
        noralta_data['Month'] = noralta_data['Sold Date'].dt.month_name()  # Full month name
        noralta_data['Year'] = noralta_data['Sold Date'].dt.year

        # Group data by Year and Month, calculate average DOM
        seasonal_dom = noralta_data.groupby(['Year', 'Month'])['Days On Market'].mean().reset_index()

        # Pivot the data for heatmap
        seasonal_dom_pivot = seasonal_dom.pivot(index='Month', columns='Year', values='Days On Market')

        # Reorder months for proper sorting
        month_order = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]
        seasonal_dom_pivot = seasonal_dom_pivot.reindex(month_order)

        # Create heatmap
        fig_heatmap = px.imshow(
            seasonal_dom_pivot,
            labels=dict(x="Year", y="Month", color="Average DOM"),
            title="Average Days on Market (DOM) by Month and Year",
            color_continuous_scale='Viridis',  # Use a color scale
            text_auto=True  # Display values on the heatmap
        )

        # Update layout for better readability
        fig_heatmap.update_layout(
            xaxis_title="Year",
            yaxis_title="Month",
            coloraxis_colorbar=dict(title="Average DOM")
        )

        # Display the heatmap
    st.plotly_chart(fig_heatmap, use_container_width=True)

    st.write("""
            **Note:** The heatmap shows the average DOM for properties that were sold in a specific month.
            For example, if a property was listed in January and sold in March, its DOM will be included in the March average.
        """)



    # Section 5: Efficiency Metrics
    st.subheader("Efficiency Metrics")

    # Identify top 10 competitors by transaction count
    top_competitors = filtered_data['Listing Firm 1 - Office Name'].value_counts().nlargest(10).index.tolist()
    top_competitors_data = filtered_data[filtered_data['Listing Firm 1 - Office Name'].isin(top_competitors)].copy()

    # Bar Chart: Listing Firm vs Buyer Firm contributions
    listing_firm = len(noralta_data[noralta_data['Listing Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate'])
    buyer_firm = len(noralta_data[noralta_data['Buyer Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate'])

    # Calculate percentages
    total_transactions = listing_firm + buyer_firm
    listing_percentage = (listing_firm / total_transactions) * 100
    buyer_percentage = (buyer_firm / total_transactions) * 100







    # Identify top 10 competitors by transaction count (excluding Noralta)
    top_competitors = filtered_data[filtered_data['Listing Firm 1 - Office Name'] != 'Royal LePage Noralta Real Estate']
    top_competitors = top_competitors['Listing Firm 1 - Office Name'].value_counts().nlargest(10).index.tolist()
    top_competitors_data = filtered_data[filtered_data['Listing Firm 1 - Office Name'].isin(top_competitors)].copy()

    # Bar Chart: Listing Firm vs Buyer Firm contributions (Noralta)
    listing_firm = len(noralta_data[noralta_data['Listing Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate'])
    buyer_firm = len(noralta_data[noralta_data['Buyer Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate'])

    # Calculate percentages for Noralta
    total_transactions = listing_firm + buyer_firm
    listing_percentage = (listing_firm / total_transactions) * 100
    buyer_percentage = (buyer_firm / total_transactions) * 100

    # Create pie chart for Noralta
    fig_noralta = px.pie(
        names=['Listing Firm', 'Buyer Firm'],
        values=[listing_firm, buyer_firm],
        title="Noralta: Listing Firm vs Buyer Firm Contributions",
        color=['Listing Firm', 'Buyer Firm'],
        color_discrete_map={'Listing Firm': 'blue', 'Buyer Firm': 'green'},
        labels={'names': 'Role', 'values': 'Number of Transactions'},
        hole=0.3  # Optional: Adds a hole in the middle for a donut chart effect
    )

    # Add percentage labels for Noralta
    fig_noralta.update_traces(
        textinfo='percent+label',  # Show percentage and label
        textposition='inside',     # Place text inside the pie slices
        pull=[0.1, 0]              # Optional: Pull out the first slice for emphasis
    )

    # Calculate average contributions for top 10 competitors
    avg_listing_firm = top_competitors_data[top_competitors_data['Listing Firm 1 - Office Name'].isin(top_competitors)].groupby('Listing Firm 1 - Office Name').size().mean()
    avg_buyer_firm = top_competitors_data[top_competitors_data['Buyer Firm 1 - Office Name'].isin(top_competitors)].groupby('Buyer Firm 1 - Office Name').size().mean()

    # Create pie chart for top 10 competitors
    fig_top_competitors = px.pie(
        names=['Listing Firm', 'Buyer Firm'],
        values=[avg_listing_firm, avg_buyer_firm],
        title="Top 10 Competitors: Average Listing vs Buyer Firm Contributions",
        color=['Listing Firm', 'Buyer Firm'],
        color_discrete_map={'Listing Firm': 'blue', 'Buyer Firm': 'green'},
        labels={'names': 'Role', 'values': 'Number of Transactions'},
        hole=0.3  # Optional: Adds a hole in the middle for a donut chart effect
    )

    # Add percentage labels for top 10 competitors
    fig_top_competitors.update_traces(
        textinfo='percent+label',  # Show percentage and label
        textposition='inside',     # Place text inside the pie slices
        pull=[0.1, 0]              # Optional: Pull out the first slice for emphasis
    )

    # Display both pie charts side by side
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_noralta, use_container_width=True)
    with col2:
        st.plotly_chart(fig_top_competitors, use_container_width=True)




#####################################################################################

    # Tab 2: Agent Performance
    st.header("Agent Performance")

    # Filter data for Noralta's agents only
    noralta_agents_data = noralta_data[
        (noralta_data['Listing Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate') |
        (noralta_data['Buyer Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate')
    ]

    # Step 1: Filter for Noralta agents on both listing and buyer sides
    noralta_listing_agents = noralta_agents_data[
        noralta_agents_data['Listing Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate'
    ]['Listing Agent 1 - Agent Name'].dropna().unique()

    noralta_buyer_agents = noralta_agents_data[
        noralta_agents_data['Buyer Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate'
    ]['Buyer Agent 1 - Agent Name'].dropna().unique()

    # Step 2: Combine and remove duplicates to get unique Noralta agents
    unique_active_agents = set(noralta_listing_agents) | set(noralta_buyer_agents)

    # Step 3: Calculate total active agents (only Noralta agents)
    total_active_agents = len(unique_active_agents)  # Total unique Noralta agents who performed deals

    # Step 4: Calculate deals per agent (only Noralta agents)
    total_closed_deals = len(noralta_agents_data)  # Total closed deals by Noralta agents
    avg_closed_deals_per_agent = total_closed_deals / total_active_agents  # Deals per agent

    # Step 5: Display KPIs
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Avg Closed Deals per #Active Agent (Noralta)", round(avg_closed_deals_per_agent, 1))
    with col2:
        st.metric("Date Range Total Active Agents (Noralta)", total_active_agents)




    # Section 2: Top Agents
    st.subheader("Top Agents")

    # Top 10 Performing Agents (Listings)
    top_listing_agents = noralta_agents_data.groupby('Listing Agent 1 - Agent Name').agg({
        'Listing ID #': 'count',  # Total deals
        'Sold Price': 'sum'       # Revenue contribution
    }).nlargest(10, 'Listing ID #').reset_index()
    top_listing_agents.columns = ['Agent Name', 'Total Deals', 'Revenue Contribution']

    # Top 10 Performing Agents (Buyers)
    top_buyer_agents = noralta_agents_data.groupby('Buyer Agent 1 - Agent Name').agg({
        'Listing ID #': 'count',  # Total deals
        'Sold Price': 'sum'       # Revenue contribution
    }).nlargest(10, 'Listing ID #').reset_index()
    top_buyer_agents.columns = ['Agent Name', 'Total Deals', 'Revenue Contribution']

    # Display tables
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Top 10 Performing Agents (Listings)**")
        st.dataframe(top_listing_agents)
    with col2:
        st.write("**Top 10 Performing Agents (Buyers)**")
        st.dataframe(top_buyer_agents)




    # Section 4: Performance by Property Type
    st.subheader("Performance by Property Type")

    # Group data by property type to calculate transactions and average DOM
    property_performance = noralta_agents_data.groupby('Property Class').agg({
        'Listing ID #': 'count',  # Number of transactions
        'Days On Market': 'mean'  # Average DOM
    }).reset_index()
    property_performance.columns = ['Property Type', 'Transactions', 'Average DOM']

    # Histogram: Distribution of Transactions by Property Type per DOM
    fig_histogram = px.histogram(
        property_performance,
        x='Average DOM',  # Use Average DOM as the x-axis
        y='Transactions',  # Use Transactions as the y-axis
        color='Property Type',  # Differentiate by property type
        title="Distribution of Transactions by Property Type per DOM (Noralta)",
        labels={'Average DOM': 'Average Days on Market', 'Transactions': 'Number of Transactions'},
        nbins=20,  # Adjust the number of bins as needed
        opacity=0.7  # Adjust opacity for better visibility
    )

    # Update layout for better readability
    fig_histogram.update_layout(
        xaxis_title="Average Days on Market (DOM)",
        yaxis_title="Number of Transactions",
        barmode='group'  # Group bars for better comparison
    )

    # Display the histogram
    st.plotly_chart(fig_histogram, use_container_width=True)

    # Table: Property type performance (Transactions and Average DOM)
    st.write("**Property Type Performance (Noralta)**")
    st.dataframe(property_performance)





    # Section 5: Training and Support Insights
    st.subheader("Training and Support Insights")

    # Group data by agent and property type to calculate transactions and average DOM
    agent_property_performance = noralta_agents_data.groupby(['Listing Agent 1 - Agent Name', 'Property Class']).agg({
        'Listing ID #': 'count',  # Number of transactions
        'Days On Market': 'mean'  # Average DOM
    }).reset_index()
    agent_property_performance.columns = ['Agent Name', 'Property Type', 'Transactions', 'Average DOM']

    # Identify underperforming agents
    underperforming_agents = agent_property_performance[
        (agent_property_performance['Transactions'] < avg_closed_deals_per_agent) |  # Low deals
        (agent_property_performance['Average DOM'] > noralta_agents_data['Days On Market'].mean())  # High DOM
    ]

    # Display underperforming agents
    st.write("**Underperforming Agents (Noralta)**")
    st.dataframe(underperforming_agents)

    # Recommendations
    st.write("**Recommendations**")
    st.write("1. Provide training for agents in specific communities or property types where Noralta lags.")
    st.write("2. Identify opportunities to replicate strategies from top-performing agents.")


if __name__ == "__main__":
    main()