import streamlit as st
import plotly.express as px
import pandas as pd
from utils.data_utils import get_mongodb_data


def normalize_office_names(data, column_name):
    """
    Normalize office names by converting to lowercase and stripping whitespace.
    """
    data[column_name] = data[column_name].str.lower().str.strip()
    return data


def filter_data(data, start_date, end_date, selected_cities=None, selected_communities=None, selected_building_types=None, selected_firms=None):
    # Ensure "Sold Date" is converted to datetime for filtering
    data['Sold Date'] = pd.to_datetime(data['Sold Date'], errors='coerce')

    # Filter by date range
    filtered_data = data[(data['Sold Date'] >= pd.Timestamp(start_date)) & (data['Sold Date'] <= pd.Timestamp(end_date))]

    # Filter by selected cities, if any
    if selected_cities and len(selected_cities) > 0:
        filtered_data = filtered_data[filtered_data['Area/City'].isin(selected_cities)]

    # Filter by selected communities, if any
    if selected_communities and len(selected_communities) > 0:
        filtered_data = filtered_data[filtered_data['Community'].isin(selected_communities)]

    # Filter by Building Type, if any
    if selected_building_types and len(selected_building_types) > 0:
        filtered_data = filtered_data[filtered_data['Building Type'].isin(selected_building_types)]

    # Filter by Firm - Office, if any
    if selected_firms and len(selected_firms) > 0:
        filtered_data = filtered_data[
            (filtered_data['Listing Firm 1 - Office Name'].isin(selected_firms)) |
            (filtered_data['Buyer Firm 1 - Office Name'].isin(selected_firms))
        ]

    return filtered_data


def color_offices(index_values):
    # Custom color-mapping function for offices
    return [
        "red" if office == "royal lepage noralta real estate" else "blue"
        for office in index_values
    ]


def main():
    st.title("Brokers Analysis")
    st.write("Analyze broker performance and activity.")

    # MongoDB connection
    mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name = "real_estate"

    # Fetch data from both collections
    listings_data = get_mongodb_data(mongodb_uri, database_name, "listings")
    brokerage_data = get_mongodb_data(mongodb_uri, database_name, "brokerage")

    if listings_data.empty or brokerage_data.empty:
        st.error("No data available!")
        return

    # Normalize office names in both collections
    listings_data = normalize_office_names(listings_data, 'Listing Firm 1 - Office Name')
    listings_data = normalize_office_names(listings_data, 'Buyer Firm 1 - Office Name')
    brokerage_data = normalize_office_names(brokerage_data, 'Broker')

    # Convert dates to datetime
    listings_data['Sold Date'] = pd.to_datetime(listings_data['Sold Date'], errors='coerce')
    brokerage_data['Date'] = pd.to_datetime(brokerage_data['Date'], errors='coerce')

    # Get actual min/max dates from the data
    actual_min_date = min(listings_data['Sold Date'].min(), brokerage_data['Date'].min())
    actual_max_date = max(listings_data['Sold Date'].max(), brokerage_data['Date'].max())

    # Set default filter dates (01-Jan-2023 to 31-Dec-2024)
    default_start = pd.Timestamp("2023-01-01")
    default_end = pd.Timestamp("2024-12-31")

    # Filters
    st.sidebar.header("Filters")
    start_date = st.sidebar.date_input("Start Date", default_start, actual_min_date, actual_max_date)
    end_date = st.sidebar.date_input("End Date", default_end, actual_min_date, actual_max_date)
    selected_cities = st.sidebar.multiselect("Select Area/City", sorted(listings_data['Area/City'].dropna().unique()))
    selected_communities = st.sidebar.multiselect("Select Community", sorted(listings_data['Community'].dropna().unique()))
    selected_building_types = st.sidebar.multiselect("Select Building Type", sorted(listings_data['Building Type'].dropna().unique()))

    # Combine unique offices from Listing and Buyer firms
    all_firms = sorted(set(listings_data['Listing Firm 1 - Office Name'].dropna().unique()) |
                      set(listings_data['Buyer Firm 1 - Office Name'].dropna().unique()))
    selected_firms = st.sidebar.multiselect("Select Firm - Office", all_firms)

    # Apply filters
    filtered_listings = filter_data(listings_data, start_date, end_date, selected_cities, selected_communities, selected_building_types, selected_firms)

    # Visualization: Top 10 Listing Office Firms
    listing_counts = filtered_listings['Listing Firm 1 - Office Name'].value_counts().head(10)
    fig1 = px.bar(
        x=listing_counts.index.str.title(),
        y=listing_counts.values,
        text=listing_counts.values,
        title="Top 10 Buyer Office Firms",
        labels={"x": "Office", "y": "Buyers Count"},
        height=600  # Increase chart height
    )

    fig1.update_traces(
        textposition="outside",
        marker_color=color_offices(listing_counts.index)
    )

    fig1.update_layout(
        margin=dict(b=120),  # Add extra space at the bottom
        xaxis=dict(tickangle=-45)  # Rotate the labels for better fit
    )

    st.plotly_chart(fig1, use_container_width=True)

    # Visualization: Top 10 Buyer Office Firms
    buyer_counts = filtered_listings['Buyer Firm 1 - Office Name'].value_counts().head(10)
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
        marker_color=color_offices(buyer_counts.index)
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
        marker_color=color_offices(combined_counts.index)
    )

    fig3.update_layout(
        margin=dict(b=120),  # Add extra space at the bottom
        xaxis=dict(tickangle=-45)  # Rotate the labels for better fit
    )
    

    st.plotly_chart(fig3, use_container_width=True)

    # Visualization: Deals Per Agent by Brokers
    st.header("Deals Per Agent by Brokers")

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

        # Count both listing and buyer deals
        month_deals = (
            month_data['Listing Firm 1 - Office Name'].value_counts() +
            month_data['Buyer Firm 1 - Office Name'].value_counts()
        ).reset_index()
        month_deals.columns = ['Broker', 'Deals']
        month_deals['Month'] = month.to_timestamp()
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

    # Make Royal LePage line thicker
    fig_line.update_traces(
        selector=dict(name="royal lepage noralta real estate"),
        line=dict(width=4),
    )

    # Add last value labels
    for broker in filtered_monthly_top['Broker'].unique():
        broker_data = filtered_monthly_top[filtered_monthly_top['Broker'] == broker]
        last_row = broker_data.iloc[-1]
        fig_line.add_annotation(
            x=last_row['Month'],
            y=last_row['Deals Per Agent'],
            text=f"{last_row['Deals Per Agent']:.2f}",
            showarrow=False,
            font=dict(size=12),
            align="right",
        )

    st.plotly_chart(fig_line, use_container_width=True)

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
        textposition="outside",
        marker_color="blue"
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
        textposition="outside",
        marker_color="green"
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
        textposition="outside",
        marker_color="purple"
    )
    st.plotly_chart(fig_combined_agents, use_container_width=True)


if __name__ == "__main__":
    main()