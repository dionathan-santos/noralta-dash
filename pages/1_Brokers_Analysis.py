"""dashboard.py


Git commands used:
    git add .
    git commit -m "aws update"
    git push origin main
"""

import streamlit as st
import plotly.express as px
import pandas as pd
import locale
import boto3
from boto3.dynamodb.conditions import Key

# =============================================================================
# AWS Credentials and Data Retrieval Functions
# =============================================================================

def get_dynamodb_client():
    """
    Creates and returns a DynamoDB client using AWS credentials.
    
    Returns:
        boto3.client: DynamoDB client object
    """
    try:
        aws_secrets = st.secrets["aws"]
        client = boto3.client(
            'dynamodb',
            aws_access_key_id=aws_secrets["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=aws_secrets["AWS_SECRET_ACCESS_KEY"],
            region_name=aws_secrets.get("AWS_REGION", "us-east-2")
        )
        return client
    except Exception as e:
        st.error(f"Failed to create DynamoDB client: {str(e)}")
        return None

@st.cache_data
def get_dynamodb_data(table_name):
    """
    Retrieves data from DynamoDB table.
    
    Args:
        table_name (str): Name of DynamoDB table
        
    Returns:
        pd.DataFrame: Data from table as DataFrame
    """
    client = get_dynamodb_client()
    if not client:
        return pd.DataFrame()
        
    try:
        paginator = client.get_paginator('scan')
        items = []
        for page in paginator.paginate(TableName=table_name):
            items.extend(page['Items'])
            
        df = pd.DataFrame([{k: v.get('S', v.get('N', '')) for k,v in item.items()} for item in items])
        
        # Convert date columns
        if 'Sold Date' in df.columns:
            df['Sold Date'] = pd.to_datetime(df['Sold Date'])
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
            
        return df
    except Exception as e:
        st.error(f"Failed to fetch data from {table_name}: {str(e)}")
        return pd.DataFrame()

def load_and_normalize_data():
    """
    Loads and normalizes data from DynamoDB tables.
    
    Returns:
        tuple: (listings_df, brokerage_df)
    """
    listings_df = get_dynamodb_data('listings')
    brokerage_df = get_dynamodb_data('brokerage')
    
    # Normalize office names
    if not listings_df.empty:
        for col in ['Listing Firm 1 - Office Name', 'Buyer Firm 1 - Office Name']:
            if col in listings_df.columns:
                listings_df[col] = listings_df[col].str.lower().str.strip()
                
    if not brokerage_df.empty and 'Broker' in brokerage_df.columns:
        brokerage_df['Broker'] = brokerage_df['Broker'].str.lower().str.strip()
        
    return listings_df, brokerage_df
    """
    Fetches data from a DynamoDB table and converts the result into a Pandas DataFrame.

    Depending on the table_name, certain date columns are also parsed and normalized.

    Args:
        table_name (str): Name of the DynamoDB table.

    Returns:
        DataFrame: Loaded data from DynamoDB.
    """
    aws_access_key, aws_secret_key, aws_region = get_aws_credentials()
    if not aws_access_key or not aws_secret_key:
        return pd.DataFrame()
    try:
        dynamodb = boto3.resource(
            "dynamodb",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        table = dynamodb.Table(table_name)
        items = []
        last_evaluated_key = None
        while True:
            if last_evaluated_key:
                response = table.scan(ExclusiveStartKey=last_evaluated_key)
            else:
                response = table.scan()
            items.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break
        df = pd.DataFrame(items)
        # Convert date columns based on the table
        if table_name == "real_estate_listings" and "Sold Date" in df.columns:
            df["Sold Date"] = pd.to_datetime(df["Sold Date"],
                                             format='%m/%d/%Y',
                                             errors='coerce').dt.normalize()
        if table_name == "brokerage" and "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"],
                                        format='%m/%d/%Y',
                                        errors='coerce').dt.normalize()
        return df
    except Exception as e:
        st.error(f"Failed to fetch data from DynamoDB for {table_name}: {str(e)}")
        return pd.DataFrame()

# =============================================================================
# Data Normalization and Helper Functions
# =============================================================================

def normalize_office_names(data, column_name):
    """
    Normalizes office names in a specified column by converting them to lowercase and
    stripping whitespace.

    Args:
        data (DataFrame): The input DataFrame.
        column_name (str): The column to normalize.

    Returns:
        DataFrame: DataFrame with normalized office names.
    """
    if column_name in data.columns:
        data[column_name] = data[column_name].astype(str).str.lower().str.strip()
    return data

def create_sidebar_filters(listings_data):
    """
    Creates sidebar filters based on the listings DataFrame.

    Args:
        listings_data (DataFrame): Data used to extract filter options.

    Returns:
        tuple: (start_date, end_date, selected_cities, selected_communities,
                selected_building_types, selected_firms)
    """
    st.sidebar.header("Filters")
    start_date = st.sidebar.date_input("Start Date", pd.Timestamp("2024-01-01"))
    end_date = st.sidebar.date_input("End Date", pd.Timestamp("2024-12-31"))

    # Provide unique sorted options for cities, communities, and building types
    selected_cities = st.sidebar.multiselect(
        "Select Area/City",
        sorted(listings_data['Area/City'].dropna().unique())
    )
    selected_communities = st.sidebar.multiselect(
        "Select Community",
        sorted(listings_data['Community'].dropna().unique())
    )
    selected_building_types = st.sidebar.multiselect(
        "Select Building Type",
        sorted(listings_data['Building Type'].dropna().unique())
    )

    # Combine unique listings and buyer firms
    all_firms = sorted(
        set(listings_data['Listing Firm 1 - Office Name'].dropna().unique()).union(
            set(listings_data['Buyer Firm 1 - Office Name'].dropna().unique())
        )
    )
    selected_firms = st.sidebar.multiselect("Select Firm - Office", all_firms)
    return (start_date, end_date, selected_cities,
            selected_communities, selected_building_types, selected_firms)

def filter_data(data, start_date, end_date,
                selected_cities=None, selected_communities=None,
                selected_building_types=None, selected_firms=None):
    """
    Filters the listings DataFrame based on the given date range and sidebar selections.

    Args:
        data (DataFrame): The input listings DataFrame.
        start_date (datetime): The start date filter.
        end_date (datetime): The end date filter.
        selected_cities (list, optional): List of cities.
        selected_communities (list, optional): List of communities.
        selected_building_types (list, optional): List of building types.
        selected_firms (list, optional): List of selected office firms.

    Returns:
        DataFrame: The filtered data.
    """
    if "Sold Date" in data.columns:
        data['Sold Date'] = pd.to_datetime(data['Sold Date'], errors='coerce')
        data = data[data['Sold Date'].notna()]

    start_dt = pd.to_datetime(start_date).normalize()
    end_dt = pd.to_datetime(end_date).normalize()

    filtered_data = data[
        (data['Sold Date'].dt.normalize() >= start_dt) &
        (data['Sold Date'].dt.normalize() <= end_dt)
    ]

    if selected_cities:
        filtered_data = filtered_data[filtered_data['Area/City'].isin(selected_cities)]
    if selected_communities:
        filtered_data = filtered_data[filtered_data['Community'].isin(selected_communities)]
    if selected_building_types:
        filtered_data = filtered_data[filtered_data['Building Type'].isin(selected_building_types)]
    if selected_firms:
        filtered_data = filtered_data[
            (filtered_data['Listing Firm 1 - Office Name'].isin(selected_firms)) |
            (filtered_data['Buyer Firm 1 - Office Name'].isin(selected_firms))
        ]
    return filtered_data

def format_currency(value):
    """
    Formats a given number as currency.

    Args:
        value (numeric): The numeric value to format.

    Returns:
        str: Currency formatted string.
    """
    if pd.isna(value):
        return 'N/A'
    try:
        return f"${value:,.2f}"
    except (TypeError, ValueError):
        return 'N/A'

def color_offices(index_values):
    """
    Generates marker colors for office names. Offices equal to "royal lepage noralta real estate"
    are colored red; others blue.

    Args:
        index_values (iterable): List of office names.

    Returns:
        list: List of marker color strings.
    """
    return ["red" if office == "royal lepage noralta real estate" else "blue"
            for office in index_values]

def customize_plot(fig, title):
    """
    Applies some standard customizations to a Plotly figure.

    Args:
        fig (Figure): A Plotly figure.
        title (str): Title for the figure.

    Returns:
        Figure: The customized Plotly figure.
    """
    fig.update_traces(textposition="outside", marker=dict(size=6))
    fig.update_layout(
        title=title,
        xaxis=dict(tickangle=-45),
        margin=dict(b=120)
    )
    return fig

# =============================================================================
# Main Dashboard Function
# =============================================================================

def main():
    st.title("Brokers Analysis Dashboard")

    # ---------------------------------------------
    # Data Loading
    # ---------------------------------------------
    listings_data, brokerage_data = load_and_normalize_data()
    
    if listings_data.empty or brokerage_data.empty:
        st.error("Unable to load data. Please check your AWS credentials and try again.")
        return

    # ---------------------------------------------
    # Data Normalization
    # ---------------------------------------------
    for col in ['Listing Firm 1 - Office Name', 'Buyer Firm 1 - Office Name']:
        listings_data = normalize_office_names(listings_data, col)

    brokerage_data = normalize_office_names(brokerage_data, 'Broker')

    # ---------------------------------------------
    # Sidebar Filters & Data Filtering
    # ---------------------------------------------
    (start_date, end_date, selected_cities,
     selected_communities, selected_building_types, selected_firms) = create_sidebar_filters(listings_data)

    filtered_listings = filter_data(listings_data, start_date, end_date,
                                    selected_cities, selected_communities,
                                    selected_building_types, selected_firms)

    # Convert Sold Price to numeric (remove currency symbols)
    if 'Sold Price' in filtered_listings.columns:
        filtered_listings['Sold Price'] = (
            filtered_listings['Sold Price']
            .replace('[\$,]', '', regex=True)
            .astype(float)
        )

    # ---------------------------------------------
    # Visualization: Top 10 Listing Office Firms
    # ---------------------------------------------
    st.subheader("Top 10 Listing Office Firms")

    listing_counts = filtered_listings['Listing Firm 1 - Office Name'].value_counts().head(10)
    gross_sales_listing = (
        filtered_listings.groupby('Listing Firm 1 - Office Name')['Sold Price']
        .sum()
        .reindex(listing_counts.index)
        .fillna(0)
    )

    fig1 = px.bar(
        x=listing_counts.index.str.title(),
        y=listing_counts.values,
        text=listing_counts.values,
        title="Top 10 Listing Office Firms",
        labels={"x": "Office", "y": "Listings Count"},
        height=600
    )

    fig1.update_traces(
        textposition="outside",
        marker_color=color_offices(listing_counts.index),
        hovertemplate=("<b>Office: %{x}</b><br>"
                       "Total Deals: %{y}<br>"
                       "Total Gross Sales: %{customdata}<extra></extra>"),
        customdata=[format_currency(v) for v in gross_sales_listing.values]
    )

    fig1.update_layout(
        margin=dict(b=120),
        xaxis=dict(tickangle=-45)
    )
    st.plotly_chart(fig1, use_container_width=True)

    # ---------------------------------------------
    # Visualization: Top 10 Buyer Office Firms
    # ---------------------------------------------
    st.subheader("Top 10 Buyer Office Firms")

    buyer_counts = filtered_listings['Buyer Firm 1 - Office Name'].value_counts().head(10)
    gross_sales_buyer = (
        filtered_listings.groupby('Buyer Firm 1 - Office Name')['Sold Price']
        .sum()
        .reindex(buyer_counts.index)
        .fillna(0)
    )

    fig2 = px.bar(
        x=buyer_counts.index.str.title(),
        y=buyer_counts.values,
        text=buyer_counts.values,
        title="Top 10 Buyer Office Firms",
        labels={"x": "Office", "y": "Buyers Count"},
        height=600
    )

    fig2.update_traces(
        textposition="outside",
        marker_color=color_offices(buyer_counts.index),
        hovertemplate=("<b>Office: %{x}</b><br>"
                       "Total Deals: %{y}<br>"
                       "Total Gross Sales: %{customdata}<extra></extra>"),
        customdata=[format_currency(v) for v in gross_sales_buyer.values]
    )

    fig2.update_layout(
        margin=dict(b=120),
        xaxis=dict(tickangle=-45)
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ---------------------------------------------
    # Visualization: Top Combined Office Firms
    # ---------------------------------------------
    st.subheader("Top Combined Office Firms")

    # Combine counts from listing and buyer sides.
    combined_counts = (
        filtered_listings['Listing Firm 1 - Office Name'].value_counts() +
        filtered_listings['Buyer Firm 1 - Office Name'].value_counts()
    ).dropna().sort_values(ascending=False).head(10)

    # Compute gross sales with half‐count adjustment for overlapping deals.
    gross_sales_combined = filtered_listings.apply(
        lambda x: x['Sold Price'] if x['Listing Firm 1 - Office Name'] != x['Buyer Firm 1 - Office Name']
                  else x['Sold Price'] / 2,
        axis=1
    ).groupby(filtered_listings['Listing Firm 1 - Office Name']).sum()

    # Add buyer side gross sales for offices not already included
    additional_sales = filtered_listings.groupby('Buyer Firm 1 - Office Name').apply(
        lambda x: x['Sold Price'].where(
            x['Listing Firm 1 - Office Name'] != x['Buyer Firm 1 - Office Name']
        ).sum()
    )
    gross_sales_combined = gross_sales_combined.add(
        additional_sales, fill_value=0
    )
    gross_sales_combined = gross_sales_combined.reindex(combined_counts.index).fillna(0)

    fig3 = px.bar(
        x=combined_counts.index.str.title(),
        y=combined_counts.values,
        text=combined_counts.values,
        title="Top Combined Office Firms",
        labels={"x": "Office", "y": "Total Count"},
        height=600
    )

    fig3.update_traces(
        textposition="outside",
        marker_color=color_offices(combined_counts.index),
        hovertemplate=("<b>Office: %{x}</b><br>"
                       "Total Deals: %{y}<br>"
                       "Total Gross Sales: %{customdata}<extra></extra>"),
        customdata=[format_currency(v) for v in gross_sales_combined.values]
    )

    fig3.update_layout(
        margin=dict(b=120),
        xaxis=dict(tickangle=-45)
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ---------------------------------------------
    # Visualization: Deals Per Agent by Brokers
    # ---------------------------------------------
    st.header("Deals Per Agent by Brokers - Top 10 + Noralta")

    # Filter brokerage data within date range.
    filtered_brokerage = brokerage_data[
        (brokerage_data['Date'] >= pd.Timestamp(start_date)) &
        (brokerage_data['Date'] <= pd.Timestamp(end_date))
    ].copy()

    # Group brokerage data by Broker and Month.
    filtered_brokerage['Month'] = filtered_brokerage['Date'].dt.to_period('M').dt.to_timestamp()
    monthly_agents = (
        filtered_brokerage
        .groupby(['Broker', 'Month'])['Value']
        .mean()
        .reset_index()
        .rename(columns={'Value': 'Average Agents'})
    )

    # Calculate monthly combined deals (listing + buyer) for each month.
    monthly_combined_deals = pd.DataFrame()
    months = filtered_listings['Sold Date'].dt.to_period('M').unique()
    for month in months:
        month_data = filtered_listings[filtered_listings['Sold Date'].dt.to_period('M') == month]
        month_deals = (
            month_data['Listing Firm 1 - Office Name'].value_counts() +
            month_data['Buyer Firm 1 - Office Name'].value_counts()
        ).reset_index()
        month_deals.columns = ['Broker', 'Deals']
        month_deals['Month'] = month.to_timestamp()
        monthly_combined_deals = pd.concat([monthly_combined_deals, month_deals], ignore_index=True)

    # Merge deals with brokerage agents data.
    merged_monthly = pd.merge(monthly_combined_deals, monthly_agents, on=['Broker', 'Month'], how='inner')
    merged_monthly['Deals Per Agent'] = merged_monthly['Deals'] / merged_monthly['Average Agents']

    # Create a complete grid of Broker and Month.
    all_months = pd.date_range(start=start_date, end=end_date, freq='MS')
    all_brokers = merged_monthly['Broker'].unique()
    complete_index = pd.MultiIndex.from_product([all_brokers, all_months], names=['Broker', 'Month'])
    merged_monthly = merged_monthly.set_index(['Broker', 'Month']).reindex(complete_index).reset_index()

    merged_monthly['Deals'] = merged_monthly['Deals'].fillna(0)
    merged_monthly['Average Agents'] = merged_monthly['Average Agents'].fillna(0)
    merged_monthly['Deals Per Agent'] = (merged_monthly['Deals'] / merged_monthly['Average Agents']).fillna(0)

    # Get top 10 brokers by total deals
    top_brokers = merged_monthly.groupby('Broker')['Deals'].sum().nlargest(10).index
    filtered_monthly_top = merged_monthly[merged_monthly['Broker'].isin(top_brokers)]

    # Ensure that "royal lepage noralta real estate" is included.
    royal_data = merged_monthly[merged_monthly['Broker'] == "royal lepage noralta real estate"]
    if not royal_data.empty and "royal lepage noralta real estate" not in top_brokers:
        filtered_monthly_top = pd.concat([filtered_monthly_top, royal_data])

    fig_line = px.line(
        filtered_monthly_top,
        x='Month',
        y='Deals Per Agent',
        color='Broker',
        title="Monthly Deals Per Agent by Broker",
        labels={'Deals Per Agent': 'Deals Per Agent', 'Month': 'Month', 'Broker': 'Broker'}
    )
    fig_line.update_traces(mode="lines+markers",
                           hovertemplate=("<b>Broker: %{color}</b><br>"
                                          "Month: %{x}<br>"
                                          "Deals Per Agent: %{y:.2f}<extra></extra>"))
    st.plotly_chart(fig_line, use_container_width=True)

    # ---------------------------------------------
    # Visualization: Monthly Market Share by Firm (%)
    # ---------------------------------------------
    st.header("Monthly Market Share by Firm (%) - Top 10 + Noralta")

    # Add Month column to listings.
    filtered_listings['Month'] = filtered_listings['Sold Date'].dt.to_period('M').dt.to_timestamp()

    # Calculate monthly deals per firm from both listing and buyer sides.
    monthly_firm_deals_list = (
        filtered_listings.groupby(['Listing Firm 1 - Office Name', 'Month']).size()
    )
    monthly_firm_deals_buyer = (
        filtered_listings.groupby(['Buyer Firm 1 - Office Name', 'Month']).size()
    )
    monthly_firm_deals = monthly_firm_deals_list.add(monthly_firm_deals_buyer, fill_value=0).reset_index(name='Deals')

    # Calculate total monthly deals.
    monthly_total_deals = (
        filtered_listings.groupby('Month').size().reset_index(name='Total Deals')
    )

    # Merge and compute market share.
    market_share_monthly = pd.merge(monthly_firm_deals, monthly_total_deals, on='Month')
    market_share_monthly['Market Share (%)'] = (market_share_monthly['Deals'] / market_share_monthly['Total Deals']) * 100

    # Determine the top 10 firms by overall market share.
    top_firms = market_share_monthly.groupby('Listing Firm 1 - Office Name')['Market Share (%)'].sum().nlargest(10).index
    top_firms_market_share = market_share_monthly[market_share_monthly['Listing Firm 1 - Office Name'].isin(top_firms)]

    # Drop duplicate firm-month entries if any.
    top_firms_market_share = top_firms_market_share.drop_duplicates(subset=['Listing Firm 1 - Office Name', 'Month'])

    fig_market_share = px.line(
        top_firms_market_share,
        x='Month',
        y='Market Share (%)',
        color='Listing Firm 1 - Office Name',
        title="Monthly Market Share by Firm (%)",
        labels={'Month': 'Month', 'Market Share (%)': 'Market Share (%)', 'Listing Firm 1 - Office Name': 'Firm'},
        markers=True
    )
    fig_market_share.update_layout(
        xaxis=dict(title='Month'),
        yaxis=dict(title='Market Share (%)'),
        legend_title="Firm",
        margin=dict(b=120)
    )
    st.plotly_chart(fig_market_share, use_container_width=True)

    # ---------------------------------------------
    # Table: Active Agents Per Firm by Month
    # ---------------------------------------------
    st.header("Active Agents Per Firm by Month")

    # Prepare data for listing and buyer agents.
    listing_agents = filtered_listings[['Listing Firm 1 - Office Name', 'Month', 'Listing Agent 1 - Agent Name']].rename(
        columns={'Listing Firm 1 - Office Name': 'Firm', 'Listing Agent 1 - Agent Name': 'Agent'}
    )
    buyer_agents = filtered_listings[['Buyer Firm 1 - Office Name', 'Month', 'Buyer Agent 1 - Agent Name']].rename(
        columns={'Buyer Firm 1 - Office Name': 'Firm', 'Buyer Agent 1 - Agent Name': 'Agent'}
    )

    all_agents = pd.concat([listing_agents, buyer_agents])
    monthly_firm_data = all_agents.groupby(['Firm', 'Month'])['Agent'].nunique().reset_index()
    monthly_firm_data.rename(columns={'Agent': 'Total_Active_Agents'}, inplace=True)

    # Filter to only include firms that appear in the Deals Per Agent graph.
    top_broker_firms = merged_monthly['Broker'].unique()
    filtered_firm_data_top = monthly_firm_data[monthly_firm_data['Firm'].isin(top_broker_firms)]

    active_agents_table = filtered_firm_data_top.pivot_table(
        index='Firm',
        columns='Month',
        values='Total_Active_Agents',
        aggfunc='sum'
    ).fillna(0).astype(int)

    # Change month columns to Month-Year format.
    active_agents_table.columns = active_agents_table.columns.strftime('%b-%Y')

    st.dataframe(active_agents_table)
    st.download_button(
        label="Download Table as CSV",
        data=active_agents_table.to_csv(),
        file_name="active_agents_per_firm_by_month.csv",
        mime="text/csv"
    )

    # ---------------------------------------------
    # Mapping Agents to Their Firms
    # ---------------------------------------------
    agent_to_firm_mapping = {}
    if 'Listing Agent 1 - Agent Name' in filtered_listings.columns:
        agent_to_firm_mapping.update(
            filtered_listings.groupby('Listing Agent 1 - Agent Name')['Listing Firm 1 - Office Name'].first().to_dict()
        )
    if 'Buyer Agent 1 - Agent Name' in filtered_listings.columns:
        agent_to_firm_mapping.update(
            filtered_listings.groupby('Buyer Agent 1 - Agent Name')['Buyer Firm 1 - Office Name'].first().to_dict()
        )

    # ---------------------------------------------
    # Visualization: Top 10 Listing Agents
    # ---------------------------------------------
    st.header("Top 10 Listing Agents")
    listing_agents_counts = filtered_listings['Listing Agent 1 - Agent Name'].value_counts().head(10)

    fig_listing_agents = px.bar(
        x=listing_agents_counts.index.str.title(),
        y=listing_agents_counts.values,
        text=listing_agents_counts.values,
        title="Top 10 Listing Agents",
        labels={"x": "Agent", "y": "Listings Count"}
    )

    fig_listing_agents.update_traces(
        textposition="inside",
        marker_color="blue",
        textfont=dict(size=12, color="white"),
        hovertemplate=("<b>Agent: %{x}</b><br>"
                       "Firm: %{customdata}<br>"
                       "Total Listings: %{y}<extra></extra>"),
        customdata=[agent_to_firm_mapping.get(agent, "Unknown Firm")
                    for agent in listing_agents_counts.index]
    )

    fig_listing_agents.update_layout(
        margin=dict(b=120),
        xaxis=dict(tickangle=-45),
        yaxis=dict(title="Listings Count", automargin=True),
        title=dict(x=0.5)
    )
    st.plotly_chart(fig_listing_agents, use_container_width=True)

    # ---------------------------------------------
    # Visualization: Top 10 Buyer Agents
    # ---------------------------------------------
    st.header("Top 10 Buyer Agents")
    buyer_agents_counts = filtered_listings["Buyer Agent 1 - Agent Name"].value_counts().head(10)

    fig_buyer_agents = px.bar(
        x=buyer_agents_counts.index.str.title(),
        y=buyer_agents_counts.values,
        text=buyer_agents_counts.values,
        title="Top 10 Buyer Agents",
        labels={"x": "Agent", "y": "Buyers Count"}
    )

    fig_buyer_agents.update_traces(
        textposition="inside",
        marker_color="green",
        textfont=dict(size=12, color="white"),
        hovertemplate=("<b>Agent: %{x}</b><br>"
                       "Firm: %{customdata}<br>"
                       "Total Buyers: %{y}<extra></extra>"),
        customdata=[agent_to_firm_mapping.get(agent, "Unknown Firm")
                    for agent in buyer_agents_counts.index]
    )

    fig_buyer_agents.update_layout(
        margin=dict(b=120),
        xaxis=dict(tickangle=-45),
        yaxis=dict(title="Buyers Count", automargin=True),
        title=dict(x=0.5)
    )
    st.plotly_chart(fig_buyer_agents, use_container_width=True)

    # ---------------------------------------------
    # Visualization: Top 10 Combined Agents
    # ---------------------------------------------
    st.header("Top 10 Combined Agents")
    combined_agents_counts = (
        filtered_listings['Listing Agent 1 - Agent Name'].value_counts() +
        filtered_listings["Buyer Agent 1 - Agent Name"].value_counts()
    ).dropna().sort_values(ascending=False).head(10)

    fig_combined_agents = px.bar(
        x=combined_agents_counts.index.str.title(),
        y=combined_agents_counts.values,
        text=combined_agents_counts.values,
        title="Top 10 Combined Agents",
        labels={"x": "Agent", "y": "Total Count"}
    )

    fig_combined_agents.update_traces(
        textposition="inside",
        marker_color="purple",
        textfont=dict(size=12, color="white"),
        hovertemplate=("<b>Agent: %{x}</b><br>"
                       "Firm: %{customdata}<br>"
                       "Total Deals: %{y}<extra></extra>"),
        customdata=[agent_to_firm_mapping.get(agent, "Unknown Firm")
                    for agent in combined_agents_counts.index]
    )

    fig_combined_agents.update_layout(
        margin=dict(b=120),
        xaxis=dict(tickangle=-45),
        yaxis=dict(title="Total Count", automargin=True),
        title=dict(x=0.5)
    )
    st.plotly_chart(fig_combined_agents, use_container_width=True)

    # End of main()
    st.write("Dashboard update complete.")

# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    main()

# =============================================================================
# End of File: dashboard.py
# =============================================================================