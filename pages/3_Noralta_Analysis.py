# import streamlit as st
# import plotly.express as px
# from utils.data_utils import get_mongodb_data, filter_data

# def main():
#     st.title("Noralta Analysis")
#     st.write("Detailed analysis specific to Noralta properties.")

#     # MongoDB connection
#     mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
#     database_name = "real_estate"
#     collection_name = "listings"

#     # Fetch data
#     data = get_mongodb_data(mongodb_uri, database_name, collection_name)
#     if data.empty:
#         st.error("No data available!")
#         return

#     # Filters
#     st.sidebar.header("Filters")
#     min_date = data['Sold Date'].min().date()
#     max_date = data['Sold Date'].max().date()
#     start_date = st.sidebar.date_input("Start Date", min_date, min_date, max_date)
#     end_date = st.sidebar.date_input("End Date", max_date, min_date, max_date)
#     area_city = st.sidebar.selectbox("Select Area/City", ["Noralta"] if "Noralta" in data['Area/City'].unique() else [""])
    
#     filtered_data = filter_data(data, start_date, end_date, area_city)

#     # Visualization: Distribution of Property Types in Noralta
#     property_type_counts = filtered_data['Property Class'].value_counts()
#     fig = px.pie(
#         values=property_type_counts.values,
#         names=property_type_counts.index,
#         title="Distribution of Property Class in Noralta",
#     )
#     st.plotly_chart(fig, use_container_width=True)

# if __name__ == "__main__":
#     main()
