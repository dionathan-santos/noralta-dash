import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime

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
        st.write("This section will display monthly performance metrics for agents.")
        # Add your monthly report content here (e.g., charts, tables, etc.)

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

    # Content for the "Forecasting" tab
    with tab3:
        st.header("Forecasting")
        st.write("This section will provide forecasts for future agent performance and market trends.")
        # Add your forecasting content here (e.g., predictive models, trends, etc.)

if __name__ == "__main__":
    main()