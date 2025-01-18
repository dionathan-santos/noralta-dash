import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.express as px

# MongoDB connection
def get_mongodb_data(mongodb_uri, database_name, collection_name):
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

# Main function
def main():
    st.title("Under Construction")
    st.write("This page is under construction.")

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Monthly Report", "2024 Market Performance", "Forecasting"])

    # Content for the "Monthly Report" tab

    with tab1:
        st.header("Monthly Report")
        st.write("This section compares performance metrics for November 2024 and December 2024.")

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

        # Filter data for November and December 2024
        monthly_data = data[(data['Sold Date'].dt.year == 2024) & (data['Sold Date'].dt.month.isin([11, 12]))]
        monthly_data['Month'] = monthly_data['Sold Date'].dt.month_name()

        #### Market Trends
        st.header("Market Trends (November vs December 2024)")

        # Volume of Transactions by Property Class - Bar Chart
        st.subheader("Volume of Transactions by Property Class")
        volume_data = monthly_data.groupby(['Month', 'Property Class']).size().reset_index(name='Count')
        volume_data = volume_data[volume_data['Property Class'].isin(['Condo', 'Single Family'])]
        fig1 = px.bar(
            volume_data,
            x='Month',
            y='Count',
            color='Property Class',
            title="Volume of Transactions by Property Class (November vs December 2024)",
            barmode='group'
        )
        st.plotly_chart(fig1)
        st.write("**Analysis:** Add your analysis here.")

        # Volume of Transactions by Total Sqft (Single-Family Only) - Bar Chart
        st.subheader("Volume of Transactions by Total Sqft (Single-Family Only)")
        single_family_data = monthly_data[monthly_data['Property Class'] == 'Single Family']
        single_family_data['Sqft Range'] = pd.cut(single_family_data['Total Flr Area (SF)'], bins=range(0, 5001, 500))
        sqft_data = single_family_data.groupby(['Month', 'Sqft Range']).size().reset_index(name='Count')
        fig2 = px.bar(
            sqft_data,
            x='Month',
            y='Count',
            color='Sqft Range',
            title="Volume of Transactions by Total Sqft (Single-Family Only)",
            barmode='group'
        )
        st.plotly_chart(fig2)
        st.write("**Analysis:** Add your analysis here.")

        # Volume of Transactions by Total Bedrooms (Single-Family Only) - Bar Chart
        st.subheader("Volume of Transactions by Total Bedrooms (Single-Family Only)")
        bedroom_data = single_family_data.groupby(['Month', 'Total Bedrooms']).size().reset_index(name='Count')
        fig3 = px.bar(
            bedroom_data,
            x='Month',
            y='Count',
            color='Total Bedrooms',
            title="Volume of Transactions by Total Bedrooms (Single-Family Only)",
            barmode='group'
        )
        st.plotly_chart(fig3)
        st.write("**Analysis:** Add your analysis here.")

        # Average Sold Prices vs. List Prices - Line Chart
        st.subheader("Average Sold Prices vs. List Prices")
        price_data = monthly_data.groupby('Month').agg({'Sold Price': 'mean', 'List Price': 'mean'}).reset_index()
        fig4 = px.line(
            price_data,
            x='Month',
            y=['Sold Price', 'List Price'],
            title="Average Sold vs List Prices (November vs December 2024)",
            color_discrete_map={'Sold Price': 'red', 'List Price': 'blue'}
        )
        st.plotly_chart(fig4)
        st.write("**Analysis:** Add your analysis here.")

        # Days on Market (DOM) Analysis - Bar Chart
        st.subheader("Days on Market (DOM) Analysis")
        dom_data = monthly_data.groupby(['Month', 'Property Class'])['Days On Market'].mean().reset_index()
        dom_data = dom_data[dom_data['Property Class'].isin(['Condo', 'Single Family'])]
        fig5 = px.bar(
            dom_data,
            x='Month',
            y='Days On Market',
            color='Property Class',
            title="Average DOM by Property Class (November vs December 2024)",
            barmode='group'
        )
        st.plotly_chart(fig5)
        st.write("**Analysis:** Add your analysis here.")

        #### Geographical Insights
        st.header("Geographical Insights (November vs December 2024)")

        # Performance by Area/Community
        st.subheader("Performance by Area/Community")
        col1, col2 = st.columns(2)

        with col1:
            cities = sorted(monthly_data['Area/City'].dropna().unique())
            # Default to Edmonton
            selected_cities = st.multiselect("Select Cities", cities, default=['Edmonton'])

        with col2:
            communities = sorted(monthly_data[monthly_data['Area/City'].isin(selected_cities)]['Community'].dropna().unique())
            selected_communities = st.multiselect("Select Communities", communities, default=communities[:2])

        if selected_cities:
            area_data = monthly_data[monthly_data['Area/City'].isin(selected_cities)]
            if selected_communities:
                area_data = area_data[area_data['Community'].isin(selected_communities)]
            monthly_deals = area_data.groupby(['Area/City', 'Community', 'Month']).size().reset_index(name='Deals')

            if selected_communities:
                fig6 = px.bar(
                    monthly_deals,
                    x='Month',
                    y='Deals',
                    color='Community',
                    title=f"Monthly Deals by Community in {', '.join(selected_cities)}",
                    barmode='group'
                )
            else:
                monthly_deals = area_data.groupby(['Area/City', 'Month']).size().reset_index(name='Deals')
                fig6 = px.bar(
                    monthly_deals,
                    x='Month',
                    y='Deals',
                    color='Area/City',
                    title=f"Monthly Deals by City in {', '.join(selected_cities)}",
                    barmode='group'
                )
            st.plotly_chart(fig6)
            st.write("**Analysis:** Add your analysis here.")

        # Top 10 Neighbourhoods in Edmonton - Include DOM
        st.subheader("Top 10 Neighbourhoods in Edmonton")
        edmonton_neighbourhoods = monthly_data[(monthly_data['Area/City'] == 'Edmonton')]
        top_neighbourhoods = edmonton_neighbourhoods.groupby('Community').agg(
            Avg_Price=('Sold Price', 'mean'),
            Demand=('Sold Date', 'count'),
            Avg_DOM=('Days On Market', 'mean')
        ).reset_index().sort_values(by='Demand', ascending=False).head(10)

        fig7 = px.scatter(
            top_neighbourhoods,
            x='Avg_Price',
            y='Demand',
            size='Avg_DOM',
            text='Community',
            title="Top 10 Neighbourhoods by Average Price, Demand, and DOM (November vs December 2024)",
            labels={'Avg_Price': 'Average Price', 'Demand': 'Number of Deals', 'Avg_DOM': 'Average DOM'}
        )
        st.plotly_chart(fig7)
        st.write("**Analysis:** Add your analysis here.")

    # Content for the "2024 Market Performance" tab
    with tab2:
        st.header("2024 Market Performance")
        st.write("This section will analyze market trends and performance for 2024.")

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

        # Filter data for the last 3 years
        current_year = datetime.now().year
        data['Year'] = data['Sold Date'].dt.year
        last_3_years_data = data[data['Year'] >= (current_year - 2)]
        last_3_years_data['Month'] = last_3_years_data['Sold Date'].dt.to_period('M').astype(str)

        #### Market Trends
        st.header("Market Trends")

        # Volume of Transactions by Property Class (Last 3 Years) - Line Chart (Monthly)
        st.subheader("Volume of Transactions by Property Class (Last 3 Years)")
        volume_data = last_3_years_data.groupby(['Month', 'Property Class']).size().reset_index(name='Count')
        volume_data = volume_data[volume_data['Property Class'].isin(['Condo', 'Single Family'])]
        fig1 = px.line(
            volume_data,
            x='Month',
            y='Count',
            color='Property Class',
            title="Volume of Transactions by Property Class (Last 3 Years)"
        )
        st.plotly_chart(fig1)
        st.write("**Analysis:** Add your analysis here.")

        # Volume of Transactions by Total Sqft (Single-Family Only) - Line Chart (Monthly)
        st.subheader("Volume of Transactions by Total Sqft (Single-Family Only)")
        single_family_data = last_3_years_data[last_3_years_data['Property Class'] == 'Single Family']
        single_family_data['Sqft Range'] = pd.cut(single_family_data['Total Flr Area (SF)'], bins=range(0, 5001, 500))
        sqft_data = single_family_data.groupby(['Month', 'Sqft Range']).size().reset_index(name='Count')
        fig2 = px.line(
            sqft_data,
            x='Month',
            y='Count',
            color='Sqft Range',
            title="Volume of Transactions by Total Sqft (Single-Family Only)"
        )
        st.plotly_chart(fig2)
        st.write("**Analysis:** Add your analysis here.")

        # Volume of Transactions by Total Bedrooms (Single-Family Only) - Line Chart (Monthly)
        st.subheader("Volume of Transactions by Total Bedrooms (Single-Family Only)")
        bedroom_data = single_family_data.groupby(['Month', 'Total Bedrooms']).size().reset_index(name='Count')
        fig3 = px.line(
            bedroom_data,
            x='Month',
            y='Count',
            color='Total Bedrooms',
            title="Volume of Transactions by Total Bedrooms (Single-Family Only)"
        )
        st.plotly_chart(fig3)
        st.write("**Analysis:** Add your analysis here.")

        # Average Sold Prices vs. List Prices (2024 Only) - Red and White Lines
        st.subheader("Average Sold Prices vs. List Prices (2024 Only)")
        data_2024 = data[data['Year'] == 2024]
        fig4 = px.line(
            data_2024.groupby('Sold Date').agg({'Sold Price': 'mean', 'List Price': 'mean'}).reset_index(),
            x='Sold Date',
            y=['Sold Price', 'List Price'],
            title="Average Sold vs List Prices (2024)",
            color_discrete_map={'Sold Price': 'red', 'List Price': 'white'}
        )
        st.plotly_chart(fig4)
        st.write("**Analysis:** Add your analysis here.")

        # Days on Market (DOM) Analysis (Last 3 Years) - Line Chart with Tooltip (Monthly)
        st.subheader("Days on Market (DOM) Analysis (Last 3 Years)")
        dom_data = last_3_years_data.groupby(['Month', 'Property Class'])['Days On Market'].mean().reset_index()
        dom_data = dom_data[dom_data['Property Class'].isin(['Condo', 'Single Family'])]
        fig5 = px.line(
            dom_data,
            x='Month',
            y='Days On Market',
            color='Property Class',
            title="Average DOM by Property Class (Last 3 Years)",
            labels={'Days On Market': 'Average DOM'},
            hover_data={'Days On Market': ':.1f'}
        )
        st.plotly_chart(fig5)
        st.write("**Analysis:** Add your analysis here.")

        #### Geographical Insights
        st.header("Geographical Insights")

        # Performance by Area/Community
        st.subheader("Performance by Area/Community")
        col1, col2 = st.columns(2)

        with col1:
            cities = sorted(data['Area/City'].dropna().unique())
            # Default to Edmonton
            selected_cities = st.multiselect("Select Cities", cities, default=['Edmonton'])

        with col2:
            communities = sorted(data[data['Area/City'].isin(selected_cities)]['Community'].dropna().unique())
            selected_communities = st.multiselect("Select Communities", communities, default=communities[:2])

        if selected_cities:
            area_data = data[data['Area/City'].isin(selected_cities)]
            if selected_communities:
                area_data = area_data[area_data['Community'].isin(selected_communities)]
            area_data['Month'] = area_data['Sold Date'].dt.to_period('M').astype(str)
            monthly_deals = area_data.groupby(['Area/City', 'Community', 'Month']).size().reset_index(name='Deals')

            if selected_communities:
                fig6 = px.line(
                    monthly_deals,
                    x='Month',
                    y='Deals',
                    color='Community',
                    title=f"Monthly Deals by Community in {', '.join(selected_cities)}"
                )
            else:
                monthly_deals = area_data.groupby(['Area/City', 'Month']).size().reset_index(name='Deals')
                fig6 = px.line(
                    monthly_deals,
                    x='Month',
                    y='Deals',
                    color='Area/City',
                    title=f"Monthly Deals by City in {', '.join(selected_cities)}"
                )
            st.plotly_chart(fig6)
            st.write("**Analysis:** Add your analysis here.")

        # Top 10 Neighbourhoods in Edmonton (2024 Only) - Include DOM
        st.subheader("Top 10 Neighbourhoods in Edmonton (2024 Only)")
        edmonton_neighbourhoods = data[(data['Area/City'] == 'Edmonton') & (data['Year'] == 2024)]
        top_neighbourhoods = edmonton_neighbourhoods.groupby('Community').agg(
            Avg_Price=('Sold Price', 'mean'),
            Demand=('Sold Date', 'count'),
            Avg_DOM=('Days On Market', 'mean')
        ).reset_index().sort_values(by='Demand', ascending=False).head(10)

        fig7 = px.scatter(
            top_neighbourhoods,
            x='Avg_Price',
            y='Demand',
            size='Avg_DOM',
            text='Community',
            title="Top 10 Neighbourhoods by Average Price, Demand, and DOM (2024)",
            labels={'Avg_Price': 'Average Price', 'Demand': 'Number of Deals', 'Avg_DOM': 'Average DOM'}
        )
        st.plotly_chart(fig7)
        st.write("**Analysis:** Add your analysis here.")




        # Extract unique agent names from "Listing Agent 1 - Agent Name" and "Buyer Agent 1 - Agent Name"
        listing_agents = data['Listing Agent 1 - Agent Name'].dropna().unique()
        buyer_agents = data['Buyer Agent 1 - Agent Name'].dropna().unique()

        # Merge and deduplicate agent names
        all_agents = pd.Series(list(listing_agents) + list(buyer_agents)).drop_duplicates().tolist()

        # Create a DataFrame to track agent performance
        agent_performance_data = data[
            (data['Listing Agent 1 - Agent Name'].isin(all_agents)) |
            (data['Buyer Agent 1 - Agent Name'].isin(all_agents))
        ]

        # Add a multi-select year filter for first appearance
        st.subheader("Filter by First Appearance Year")
        selected_years = st.multiselect(
            "Select Year(s) for First Appearance",
            options=[2021, 2022, 2023, 2024],  # Adjust based on your data
            default=[2021, 2022, 2023, 2024]   # Default to all years
        )

        # Filter agents who made their first appearance in the selected years
        agent_performance_data['Year'] = agent_performance_data['Sold Date'].dt.year
        first_appearance_data = agent_performance_data[agent_performance_data['Year'].isin(selected_years)]

        # Get the first appearance date for each agent
        first_appearance_listing = first_appearance_data.groupby('Listing Agent 1 - Agent Name')['Sold Date'].min().reset_index().rename(columns={'Listing Agent 1 - Agent Name': 'Agent Name', 'Sold Date': 'First Appearance Date'})
        first_appearance_buyer = first_appearance_data.groupby('Buyer Agent 1 - Agent Name')['Sold Date'].min().reset_index().rename(columns={'Buyer Agent 1 - Agent Name': 'Agent Name', 'Sold Date': 'First Appearance Date'})

        # Combine first appearance dates for listing and buyer agents
        first_appearance_agents = pd.concat([first_appearance_listing, first_appearance_buyer]).drop_duplicates(subset=['Agent Name'])

        # Merge with the main data to get all deals by these agents
        agent_performance = pd.merge(
            agent_performance_data,
            first_appearance_agents,
            left_on=['Listing Agent 1 - Agent Name', 'Buyer Agent 1 - Agent Name'],
            right_on=['Agent Name', 'Agent Name'],
            how='inner'
        )

        # Filter deals after the agent's first appearance
        agent_performance = agent_performance[
            (agent_performance['Sold Date'] >= agent_performance['First Appearance Date'])
        ]

        # New Graph 1: Top 10 Regions Where Agents Performed Better (First Appearance: Selected Years)
        st.subheader(f"Top 10 Regions Where Agents Performed Better (First Appearance: {', '.join(map(str, selected_years))})")

        # Group by region and count deals
        top_regions = agent_performance.groupby('Area/City').size().reset_index(name='Deals').sort_values(by='Deals', ascending=False).head(10)

        # Plot the top 10 regions
        fig8 = px.bar(
            top_regions,
            x='Area/City',
            y='Deals',
            title=f"Top 10 Regions Where Agents Performed Better (First Appearance: {', '.join(map(str, selected_years))})",
            labels={'Area/City': 'Region', 'Deals': 'Number of Deals'}
        )
        st.plotly_chart(fig8)
        st.write("**Analysis:** Add your analysis here.")

        # List of cities to analyze
        cities = ["Edmonton", "St. Albert", "Fort Saskatchewan", "Sherwood Park", "Spruce Grove"]

        # Loop through each city and create a graph for its communities
        for city in cities:
            st.subheader(f"Top Communities in {city} Where Agents Performed Better (First Appearance: {', '.join(map(str, selected_years))})")

            # Filter data for the current city
            city_data = agent_performance[agent_performance['Area/City'] == city]

            # Group by community and count deals
            top_communities = city_data.groupby('Community').size().reset_index(name='Deals').sort_values(by='Deals', ascending=False).head(10)

            # Plot the top communities
            fig = px.bar(
                top_communities,
                x='Community',
                y='Deals',
                title=f"Top Communities in {city} Where Agents Performed Better (First Appearance: {', '.join(map(str, selected_years))})",
                labels={'Community': 'Community', 'Deals': 'Number of Deals'}
            )
            st.plotly_chart(fig)
            st.write(f"**Analysis for {city}:** Add your analysis here.")

        # New Graph 2: Top Property Types Where Agents Performed Better (First Appearance: Selected Years)
        st.subheader(f"Top Property Types Where Agents Performed Better (First Appearance: {', '.join(map(str, selected_years))})")

        # Group by property type and count deals
        top_property_types = agent_performance.groupby('Property Class').size().reset_index(name='Deals').sort_values(by='Deals', ascending=False)

        # Plot the top property types
        fig9 = px.bar(
            top_property_types,
            x='Property Class',
            y='Deals',
            title=f"Top Property Types Where Agents Performed Better (First Appearance: {', '.join(map(str, selected_years))})",
            labels={'Property Class': 'Property Type', 'Deals': 'Number of Deals'}
        )
        st.plotly_chart(fig9)
        st.write("**Analysis:** Add your analysis here.")

        with tab3:
            st.header("Forecasting")
            st.write("This section will show Machine Learning Forecasting for Trends and Predictions.")
            st.write("All the Models will be made focusing on Noralta's needs.")

if __name__ == "__main__":
    main()