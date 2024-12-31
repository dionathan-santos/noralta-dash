import streamlit as st
import plotly.express as px
from utils.data_utils import get_mongodb_data, filter_data
import pandas as pd


def filter_data(data, start_date, end_date, selected_cities=None, selected_communities=None):
    # Convert "Sold Date" to datetime for filtering
    data['Sold Date'] = pd.to_datetime(data['Sold Date'])
    
    # Filter by date range
    filtered_data = data[(data['Sold Date'] >= pd.Timestamp(start_date)) & (data['Sold Date'] <= pd.Timestamp(end_date))]
    
    # Filter by selected cities, if any
    if selected_cities and len(selected_cities) > 0:
        filtered_data = filtered_data[filtered_data['Area/City'].isin(selected_cities)]
    
    # Filter by selected communities, if any
    if selected_communities and len(selected_communities) > 0:
        filtered_data = filtered_data[filtered_data['Community'].isin(selected_communities)]
    
    return filtered_data


def color_offices(index_values):
    # Custom color-mapping function for offices
    return [
        "red" if office == "Royal LePage Noralta Real Estate" else "blue" 
        for office in index_values
    ]


def main():
    st.title("Brokers Analysis")
    st.write("Analyze broker performance and activity.")

    # MongoDB connection
    mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name = "real_estate"
    collection_name = "listings"

    # Fetch data
    data = get_mongodb_data(mongodb_uri, database_name, collection_name)
    if data.empty:
        st.error("No data available!")
        return

    # Filters
    st.sidebar.header("Filters")
    min_date = data['Sold Date'].min().date()
    max_date = data['Sold Date'].max().date()
    start_date = st.sidebar.date_input("Start Date", min_date, min_date, max_date)
    end_date = st.sidebar.date_input("End Date", max_date, min_date, max_date)
    selected_cities = st.sidebar.multiselect("Select Area/City", sorted(data['Area/City'].dropna().unique()))
    selected_communities = st.sidebar.multiselect("Select Community", sorted(data['Community'].dropna().unique()))

    # Apply filters
    filtered_data = filter_data(data, start_date, end_date, selected_cities, selected_communities)

    # Visualization: Top 10 Listing Office Firms
    listing_counts = filtered_data['Listing Firm 1 - Office Name'].value_counts().head(10)
    fig1 = px.bar(
        x=listing_counts.index,
        y=listing_counts.values,
        text=listing_counts.values,
        title="Top 10 Listing Office Firms",
        labels={"x": "Office", "y": "Listings Count"},
    )
    fig1.update_traces(
        textposition="outside",
        marker_color=color_offices(listing_counts.index)
    )
    fig1.update_layout(height=600, width=900)  # Adjust graph size
    st.plotly_chart(fig1, use_container_width=True)

    # Visualization: Top 10 Buyer Office Firms
    buyer_counts = filtered_data['Buyer Firm 1 - Office Name'].value_counts().head(10)
    fig2 = px.bar(
        x=buyer_counts.index,
        y=buyer_counts.values,
        text=buyer_counts.values,
        title="Top 10 Buyer Office Firms",
        labels={"x": "Office", "y": "Buyers Count"},
    )
    fig2.update_traces(
        textposition="outside",
        marker_color=color_offices(buyer_counts.index)
    )
    fig2.update_layout(height=600, width=900)  # Adjust graph size
    st.plotly_chart(fig2, use_container_width=True)

    # Visualization: Top 10 Combined (Listing + Buyer) Office Firms
    combined_counts = (
        filtered_data['Listing Firm 1 - Office Name'].value_counts() +
        filtered_data['Buyer Firm 1 - Office Name'].value_counts()
    ).dropna().sort_values(ascending=False).head(10)
    fig3 = px.bar(
        x=combined_counts.index,
        y=combined_counts.values,
        text=combined_counts.values,
        title="Top 10 Combined Office Firms",
        labels={"x": "Office", "y": "Total Count"},
    )
    fig3.update_traces(
        textposition="outside",
        marker_color=color_offices(combined_counts.index)
    )
    fig3.update_layout(height=600, width=900)  # Adjust graph size
    st.plotly_chart(fig3, use_container_width=True)

    # Visualization: Top 10 Listing Agents
    agent_listing_counts = filtered_data['Listing Agent 1 - Agent Name'].value_counts().head(10)
    fig4 = px.bar(
        x=agent_listing_counts.index,
        y=agent_listing_counts.values,
        text=agent_listing_counts.values,
        title="Top 10 Listing Agents",
        labels={"x": "Agent", "y": "Listings Count"},
    )
    fig4.update_traces(textposition="outside")
    fig4.update_layout(height=600, width=900)  # Adjust graph size
    st.plotly_chart(fig4, use_container_width=True)

    # Visualization: Top 10 Buyer Agents
    agent_buyer_counts = filtered_data['Buyer Agent 1 - Agent Name'].value_counts().head(10)
    fig5 = px.bar(
        x=agent_buyer_counts.index,
        y=agent_buyer_counts.values,
        text=agent_buyer_counts.values,
        title="Top 10 Buyer Agents",
        labels={"x": "Agent", "y": "Buyers Count"},
    )
    fig5.update_traces(textposition="outside")
    fig5.update_layout(height=600, width=900)  # Adjust graph size
    st.plotly_chart(fig5, use_container_width=True)

    # Visualization: Combined (Listing + Buyer) Agents
    combined_agent_counts = (
        filtered_data['Listing Agent 1 - Agent Name'].value_counts() +
        filtered_data['Buyer Agent 1 - Agent Name'].value_counts()
    ).dropna().sort_values(ascending=False).head(10)
    fig6 = px.bar(
        x=combined_agent_counts.index,
        y=combined_agent_counts.values,
        text=combined_agent_counts.values,
        title="Top 10 Combined Agents",
        labels={"x": "Agent", "y": "Total Count"},
    )
    fig6.update_traces(textposition="outside")
    fig6.update_layout(height=600, width=900)  # Adjust graph size
    st.plotly_chart(fig6, use_container_width=True)


if __name__ == "__main__":
    main()
