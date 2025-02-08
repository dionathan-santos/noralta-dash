import streamlit as st
import plotly.express as px
import pandas as pd
from utils.data_utils import get_mongodb_data
import locale


#### git add . ; git commit -m "aws update" ; git push origin main  

# Normalize office names
def normalize_office_names(data, column_name):
    if column_name in data.columns:
        data[column_name] = data[column_name].str.lower().str.strip()
    return data

# Filter data function
def filter_data(data, start_date, end_date, selected_cities=None, selected_communities=None, selected_building_types=None, selected_firms=None):
    # Add explicit date format and normalize dates
    data['Sold Date'] = pd.to_datetime(data['Sold Date'], format='%m/%d/%Y', errors='coerce')
    data = data[data['Sold Date'].notna()]

    # Convert input dates to pandas timestamps and normalize
    start_dt = pd.to_datetime(start_date).normalize()
    end_dt = pd.to_datetime(end_date).normalize()

    # Filter with normalized dates
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

# Helper function to format currency
def format_currency(value):
    """Format a number as currency without relying on locale settings."""
    if pd.isna(value):
        return 'N/A'
    try:
        return f"${value:,.2f}"
    except (TypeError, ValueError):
        return 'N/A'

# Helper function for plot customizations
def customize_plot(fig, title):
    fig.update_traces(textposition="outside", marker=dict(size=6))
    fig.update_layout(
        title=title,
        xaxis=dict(tickangle=-45),
        margin=dict(b=120)
    )
    return fig

# Custom color-mapping function for offices
def color_offices(index_values):
    return [
        "red" if office == "royal lepage noralta real estate" else "blue"
        for office in index_values
    ]

# Load and normalize data
def load_and_normalize_data(mongodb_uri, database_name):
    listings_data = get_mongodb_data(mongodb_uri, database_name, "listings")
    brokerage_data = get_mongodb_data(mongodb_uri, database_name, "brokerage")

    for col in ['Listing Firm 1 - Office Name', 'Buyer Firm 1 - Office Name']:
        listings_data = normalize_office_names(listings_data, col)
    brokerage_data = normalize_office_names(brokerage_data, 'Broker')

    # Add format to both date columns
    listings_data['Sold Date'] = pd.to_datetime(listings_data['Sold Date'], format='%m/%d/%Y', errors='coerce')
    brokerage_data['Date'] = pd.to_datetime(brokerage_data['Date'], format='%m/%d/%Y', errors='coerce')

    return listings_data, brokerage_data

# Sidebar filters
def create_sidebar_filters(listings_data):
    st.sidebar.header("Filters")
    start_date = st.sidebar.date_input("Start Date", pd.Timestamp("2024-01-01"))
    end_date = st.sidebar.date_input("End Date", pd.Timestamp("2024-12-31"))
    selected_cities = st.sidebar.multiselect("Select Area/City", sorted(listings_data['Area/City'].dropna().unique()))
    selected_communities = st.sidebar.multiselect("Select Community", sorted(listings_data['Community'].dropna().unique()))
    selected_building_types = st.sidebar.multiselect("Select Building Type", sorted(listings_data['Building Type'].dropna().unique()))

    all_firms = sorted(set(listings_data['Listing Firm 1 - Office Name'].dropna().unique()) |
                      set(listings_data['Buyer Firm 1 - Office Name'].dropna().unique()))
    selected_firms = st.sidebar.multiselect("Select Firm - Office", all_firms)

    return start_date, end_date, selected_cities, selected_communities, selected_building_types, selected_firms

# Main function
def main():
    st.title("Brokers Analysis Dashboard")

    mongodb_uri = "mongodb+srv://dionathan:19910213200287@cluster1.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster1"
    database_name = "real_estate"

    listings_data, brokerage_data = load_and_normalize_data(mongodb_uri, database_name)

    if listings_data.empty or brokerage_data.empty:
        st.error("No data available to display!")
        return

    start_date, end_date, selected_cities, selected_communities, selected_building_types, selected_firms = create_sidebar_filters(listings_data)

    filtered_listings = filter_data(listings_data, start_date, end_date, selected_cities, selected_communities, selected_building_types, selected_firms)

    filtered_listings['Sold Price'] = (
        filtered_listings['Sold Price']
        .replace('[\$,]', '', regex=True)
        .astype(float)
    )
    # Visualization: Top 10 Listing Office Firms
    listing_counts = filtered_listings['Listing Firm 1 - Office Name'].value_counts().head(10)

    # Calculate Gross Sales for Listing Firms
    gross_sales_listing = (
        filtered_listings.groupby('Listing Firm 1 - Office Name')['Sold Price']
        .sum()
        .reindex(listing_counts.index)
        .fillna(0)
    )

    # Visualization: Top 10 Listing Office Firms
    fig1 = px.bar(
        x=listing_counts.index.str.title(),
        y=listing_counts.values,
        text=listing_counts.values,
        title="Top 10 Listing Office Firms",
        labels={"x": "Office", "y": "Listings Count"},
        height=600  # Increase chart height
    )

    fig1.update_traces(
        textposition="outside",
        marker_color=color_offices(listing_counts.index),
        hovertemplate=(
            "<b>Office: %{x}</b>"
            "Total Deals: %{y}"
            "Total Gross Sales: %{customdata}<extra></extra>"
        ),
        customdata=[format_currency(v) for v in gross_sales_listing.values]  # Format gross sales as currency
    )

    fig1.update_layout(
        margin=dict(b=120),  # Add extra space at the bottom
        xaxis=dict(tickangle=-45)  # Rotate the labels for better fit
    )

    st.plotly_chart(fig1, use_container_width=True)

    # Visualization: Top 10 Buyer Office Firms
    buyer_counts = filtered_listings['Buyer Firm 1 - Office Name'].value_counts().head(10)

    # Calculate Gross Sales for Buyer Firms
    gross_sales_buyer = (
        filtered_listings.groupby('Buyer Firm 1 - Office Name')['Sold Price']
        .sum()
        .reindex(buyer_counts.index)
        .fillna(0)
    )

    # Visualization: Top 10 Buyer Office Firms
    fig2 = px.bar(
        x=buyer_counts.index.str.title(),
        y=buyer_counts.values,
        text=buyer_counts.values,
        title="Top 10 Buyer Office Firms",
        labels={"x": "Office", "y": "Buyers Count"},
        height=600  # Increase chart height
    )

    fig2.update_traces(
        textposition="outside",
        marker_color=color_offices(buyer_counts.index),
        hovertemplate=(
            "<b>Office: %{x}</b><br>"
            "Total Deals: %{y}<br>"
            "Total Gross Sales: %{customdata}<extra></extra>"
        ),
        customdata=[format_currency(v) for v in gross_sales_buyer.values]  # Format gross sales as currency
    )

    fig2.update_layout(
        margin=dict(b=120),  # Add extra space at the bottom
        xaxis=dict(tickangle=-45)  # Rotate the labels for better fit
    )

    st.plotly_chart(fig2, use_container_width=True)


    # Visualization: Top Combined Office Firms
    combined_counts = (
        filtered_listings['Listing Firm 1 - Office Name'].value_counts() +
        filtered_listings['Buyer Firm 1 - Office Name'].value_counts()
    ).dropna().sort_values(ascending=False).head(10)

    # Calculate Gross Sales for Combined Firms (Listing + Buyer sides without duplication)
    gross_sales_combined = filtered_listings.apply(
        lambda x: x['Sold Price'] if x['Listing Firm 1 - Office Name'] != x['Buyer Firm 1 - Office Name'] else x['Sold Price'] / 2,
        axis=1
    ).groupby(filtered_listings['Listing Firm 1 - Office Name']).sum()

    # Add Buyer side gross sales for offices not already included
    gross_sales_combined += filtered_listings.groupby('Buyer Firm 1 - Office Name').apply(
        lambda x: x['Sold Price'].where(
            x['Listing Firm 1 - Office Name'] != x['Buyer Firm 1 - Office Name']
        ).sum()
    ).reindex(gross_sales_combined.index, fill_value=0)

    # Reindex to match Top Combined Offices
    gross_sales_combined = gross_sales_combined.reindex(combined_counts.index).fillna(0)

    # Visualization: Top Combined Office Firms
    fig3 = px.bar(
        x=combined_counts.index.str.title(),
        y=combined_counts.values,
        text=combined_counts.values,
        title="Top Combined Office Firms",
        labels={"x": "Office", "y": "Total Count"},
        height=600  # Increase chart height
    )

    fig3.update_traces(
        textposition="outside",
        marker_color=color_offices(combined_counts.index),
        hovertemplate=(
            "<b>Office: %{x}</b><br>"
            "Total Deals: %{y}<br>"
            "Total Gross Sales: %{customdata}<extra></extra>"
        ),
        customdata=[format_currency(v) for v in gross_sales_combined.values]  # Format gross sales as currency
    )
    fig3.update_layout(
        margin=dict(b=120),  # Add extra space at the bottom
        xaxis=dict(tickangle=-45)  # Rotate the labels for better fit
    )

    st.plotly_chart(fig3, use_container_width=True)

    ##########################################

    # Visualization: Deals Per Agent by Brokers
    st.header("Deals Per Agent by Brokers - Top 10 + Noralta")

    # Filter brokerage data for the selected date range
    filtered_brokerage = brokerage_data[(brokerage_data['Date'] >= pd.Timestamp(start_date)) & (brokerage_data['Date'] <= pd.Timestamp(end_date))]

    # Group brokerage data by Broker and Month
    filtered_brokerage['Month'] = filtered_brokerage['Date'].dt.to_period('M').dt.to_timestamp()
    monthly_agents = filtered_brokerage.groupby(['Broker', 'Month'])['Value'].mean().reset_index()
    monthly_agents.columns = ['Broker', 'Month', 'Average Agents']

    # Calculate monthly combined deals (listing + buyer)
    monthly_combined_deals = pd.DataFrame()
    for month in filtered_listings['Sold Date'].dt.to_period('M').unique():
        month_data = filtered_listings[filtered_listings['Sold Date'].dt.to_period('M') == month]

        # Combine counts for both listing and buyer deals
        month_deals = (
            month_data['Listing Firm 1 - Office Name'].value_counts() +
            month_data['Buyer Firm 1 - Office Name'].value_counts()
        ).reset_index()

        # Rename columns
        month_deals.columns = ['Broker', 'Deals']
        month_deals['Month'] = month.to_timestamp()

        # Append to the combined DataFrame
        monthly_combined_deals = pd.concat([monthly_combined_deals, month_deals])

    # Merge deals and agents data
    merged_monthly = pd.merge(monthly_combined_deals, monthly_agents, on=['Broker', 'Month'], how='inner')
    merged_monthly['Deals Per Agent'] = merged_monthly['Deals'] / merged_monthly['Average Agents']

    # Create a complete list of all brokers and months
    all_months = pd.date_range(start=start_date, end=end_date, freq='MS')  # Monthly start dates
    all_brokers = merged_monthly['Broker'].unique()
    complete_index = pd.MultiIndex.from_product([all_brokers, all_months], names=['Broker', 'Month'])

    # Reindex the merged_monthly DataFrame to include all brokers and months
    merged_monthly = merged_monthly.set_index(['Broker', 'Month']).reindex(complete_index).reset_index()

    # Fill missing values with 0
    merged_monthly['Deals'].fillna(0, inplace=True)
    merged_monthly['Average Agents'].fillna(0, inplace=True)
    merged_monthly['Deals Per Agent'] = merged_monthly['Deals'] / merged_monthly['Average Agents']
    merged_monthly['Deals Per Agent'].fillna(0, inplace=True)

    # Get top 10 brokers by total deals
    top_brokers = merged_monthly.groupby('Broker')['Deals'].sum().nlargest(10).index
    filtered_monthly_top = merged_monthly[merged_monthly['Broker'].isin(top_brokers)]

    # Ensure Royal LePage is included
    royal_data = merged_monthly[merged_monthly['Broker'] == "royal lepage noralta real estate"]
    if not royal_data.empty and "royal lepage noralta real estate" not in top_brokers:
        filtered_monthly_top = pd.concat([filtered_monthly_top, royal_data])

    # Create line graph
    fig_line = px.line(
        filtered_monthly_top,
        x='Month',
        y='Deals Per Agent',
        color='Broker',
        title="Monthly Deals Per Agent by Broker",
        labels={'Deals Per Agent': 'Deals Per Agent', 'Month': 'Month', 'Broker': 'Broker'}
    )

    # Update traces to add markers
    fig_line.update_traces(
        hovertemplate=(
            "<b>Broker: %{Broker}</b><br>"
            "Month: %{x}<br>"
            "Deals Per Agent: %{y:.2f}<extra></extra>"
        )
    )

    # Customize tooltip for hover
    fig_line.update_traces(
        hovertemplate=(
            "<b>Broker: %{Broker}</b>"
            "Month: %{x}"
            "Deals Per Agent: %{y:.2f}<extra></extra>"
        )
    )

    # Display the chart
    st.plotly_chart(fig_line, use_container_width=True)

    # Market Share Line Graph (Top 10 Firms)
    st.header("Monthly Market Share by Firm (%) - Top 10 + Noralta")

    # Extract Month and Firm details
    filtered_listings['Month'] = filtered_listings['Sold Date'].dt.to_period('M').dt.to_timestamp()

    # Calculate Monthly Deals for Each Firm
    monthly_firm_deals = (
        filtered_listings.groupby(['Listing Firm 1 - Office Name', 'Month']).size() +
        filtered_listings.groupby(['Buyer Firm 1 - Office Name', 'Month']).size()
    ).reset_index(name='Deals')

    # Calculate Total Monthly Deals
    monthly_total_deals = filtered_listings.groupby('Month').size().reset_index(name='Total Deals')

    # Merge Monthly Firm Deals with Total Deals to Calculate Market Share
    market_share_monthly = pd.merge(monthly_firm_deals, monthly_total_deals, on='Month')
    market_share_monthly['Market Share (%)'] = (market_share_monthly['Deals'] / market_share_monthly['Total Deals']) * 100

    # Get Top 10 Firms by Total Market Share
    top_firms = market_share_monthly.groupby('Listing Firm 1 - Office Name')['Market Share (%)'].sum().nlargest(10).index

    # Filter Data for Top 10 Firms
    top_firms_market_share = market_share_monthly[market_share_monthly['Listing Firm 1 - Office Name'].isin(top_firms)]

    # Drop duplicates to ensure only one record per firm per month
    top_firms_market_share = top_firms_market_share.drop_duplicates(subset=['Listing Firm 1 - Office Name', 'Month'])

    # Line Graph for Market Share
    fig_market_share = px.line(
        top_firms_market_share,
        x='Month',
        y='Market Share (%)',
        color='Listing Firm 1 - Office Name',
        title="Monthly Market Share by Firm (%)",
        labels={'Month': 'Month', 'Market Share (%)': 'Market Share (%)', 'Listing Firm 1 - Office Name': 'Firm'},
    )

    # Update Layout for Better Visualization
    fig_market_share.update_traces(mode="lines+markers")  # Add markers
    fig_market_share.update_layout(
        xaxis=dict(title='Month'),
        yaxis=dict(title='Market Share (%)'),
        legend_title="Firm",
        margin=dict(b=120),  # Extra space at the bottom
    )

    # Display the Graph
    st.plotly_chart(fig_market_share, use_container_width=True)

    # Table: Active Agents Per Month for Top Firms
    st.header("Active Agents Per Firm by Month")

    # Extract Month and Firm details
    filtered_listings['Month'] = filtered_listings['Sold Date'].dt.to_period('M').dt.to_timestamp()

    # Create a DataFrame for listing agents
    listing_agents = filtered_listings[['Listing Firm 1 - Office Name', 'Month', 'Listing Agent 1 - Agent Name']].rename(columns={
        'Listing Firm 1 - Office Name': 'Firm',
        'Listing Agent 1 - Agent Name': 'Agent'
    })

    # Create a DataFrame for buyer agents
    buyer_agents = filtered_listings[['Buyer Firm 1 - Office Name', 'Month', 'Buyer Agent 1 - Agent Name']].rename(columns={
        'Buyer Firm 1 - Office Name': 'Firm',
        'Buyer Agent 1 - Agent Name': 'Agent'
    })

    # Combine listing and buyer agents
    all_agents = pd.concat([listing_agents, buyer_agents])

    # Group by firm and month to calculate unique agents
    monthly_firm_data = all_agents.groupby(['Firm', 'Month'])['Agent'].nunique().reset_index()
    monthly_firm_data.columns = ['Firm', 'Month', 'Total_Active_Agents']

    # Filter the firms to match those included in the "Deals Per Agent by Brokers" graph
    top_firms = merged_monthly['Broker'].unique()  # Assuming top_firms is derived from the graph
    filtered_firm_data_top = monthly_firm_data[monthly_firm_data['Firm'].isin(top_firms)]

    # Pivot the data to create a table format with firms as rows and months as columns
    active_agents_table = filtered_firm_data_top.pivot_table(
        index='Firm',
        columns='Month',
        values='Total_Active_Agents',
        aggfunc='sum'
    ).fillna(0).astype(int)

    # Rename columns to "Month-Year" format
    active_agents_table.columns = active_agents_table.columns.strftime('%b-%Y')

    # Display the table
    st.dataframe(active_agents_table)

    # Optionally allow download of the table
    st.download_button(
        label="Download Table as CSV",
        data=active_agents_table.to_csv(),
        file_name="active_agents_per_firm_by_month.csv",
        mime="text/csv"
    )

    # Create a mapping of agents to their respective listing or buyer firms
    agent_to_firm_mapping = filtered_listings.groupby('Listing Agent 1 - Agent Name')['Listing Firm 1 - Office Name'].first().to_dict()
    agent_to_firm_mapping.update(
        filtered_listings.groupby('Buyer Agent 1 - Agent Name')['Buyer Firm 1 - Office Name'].first().to_dict()
    )

     # Add firm name to each graph's tooltip

    # Visualization: Top 10 Listing Agents
    st.header("Top 10 Listing Agents")
    listing_agents_counts = filtered_listings['Listing Agent 1 - Agent Name'].value_counts().head(10)
    fig_listing_agents = px.bar(
        x=listing_agents_counts.index.str.title(),
        y=listing_agents_counts.values,
        text=listing_agents_counts.values,
        title="Top 10 Listing Agents",
        labels={"x": "Agent", "y": "Listings Count"},
    )

    fig_listing_agents.update_traces(
        textposition="inside",  # Display text inside the bars
        marker_color="blue",
        textfont=dict(size=12, color="white"),  # Improve readability
        hovertemplate=(
            "<b>Agent: %{x}</b><br>"
            "Firm: %{customdata}<br>"
            "Total Listings: %{y}<extra></extra>"
        ),
        customdata=[agent_to_firm_mapping.get(agent, "Unknown Firm") for agent in listing_agents_counts.index]
    )

    fig_listing_agents.update_layout(
        margin=dict(b=120),  # Add extra space at the bottom
        xaxis=dict(tickangle=-45),  # Rotate the labels for better fit
        yaxis=dict(title="Listings Count", automargin=True),  # Adjust axis
        title=dict(x=0.5)  # Center the title
    )
    st.plotly_chart(fig_listing_agents, use_container_width=True)

    # Visualization: Top 10 Buyer Agents
    st.header("Top 10 Buyer Agents")
    buyer_agents_counts = filtered_listings["Buyer Agent 1 - Agent Name"].value_counts().head(10)
    fig_buyer_agents = px.bar(
        x=buyer_agents_counts.index.str.title(),
        y=buyer_agents_counts.values,
        text=buyer_agents_counts.values,
        title="Top 10 Buyer Agents",
        labels={"x": "Agent", "y": "Buyers Count"},
    )

    fig_buyer_agents.update_traces(
        textposition="inside",  # Display text inside the bars
        marker_color="green",
        textfont=dict(size=12, color="white"),  # Improve readability
        hovertemplate=(
            "<b>Agent: %{x}</b><br>"
            "Firm: %{customdata}<br>"
            "Total Buyers: %{y}<extra></extra>"
        ),
        customdata=[agent_to_firm_mapping.get(agent, "Unknown Firm") for agent in buyer_agents_counts.index]
    )

    fig_buyer_agents.update_layout(
        margin=dict(b=120),  # Add extra space at the bottom
        xaxis=dict(tickangle=-45),  # Rotate the labels for better fit
        yaxis=dict(title="Buyers Count", automargin=True),  # Adjust axis
        title=dict(x=0.5)  # Center the title
    )
    st.plotly_chart(fig_buyer_agents, use_container_width=True)

    # Visualization: Top Combined Agents
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
        labels={"x": "Agent", "y": "Total Count"},
    )

    fig_combined_agents.update_traces(
        textposition="inside",  # Display text inside the bars
        marker_color="purple",
        textfont=dict(size=12, color="white"),  # Improve readability
        hovertemplate=(
            "<b>Agent: %{x}</b><br>"
            "Firm: %{customdata}<br>"
            "Total Deals: %{y}<extra></extra>"
        ),
        customdata=[agent_to_firm_mapping.get(agent, "Unknown Firm") for agent in combined_agents_counts.index]
    )

    fig_combined_agents.update_layout(
        margin=dict(b=120),  # Add extra space at the bottom
        xaxis=dict(tickangle=-45),  # Rotate the labels for better fit
        yaxis=dict(title="Total Count", automargin=True),  # Adjust axis
        title=dict(x=0.5)  # Center the title
    )
    st.plotly_chart(fig_combined_agents, use_container_width=True)


if __name__ == "__main__":
    main()