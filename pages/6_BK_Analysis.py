import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from datetime import datetime

# Set page title and layout
st.set_page_config(page_title="Brokerage Performance Analysis", layout="wide")
st.title("Brokerage Performance Analysis")

# Function to retrieve AWS credentials from Streamlit secrets
def get_aws_credentials():
    """Retrieves AWS credentials from Streamlit secrets."""
    try:
        aws_secrets = st.secrets["aws"]  # Get the entire 'aws' dictionary
        return (
            aws_secrets["AWS_ACCESS_KEY_ID"],
            aws_secrets["AWS_SECRET_ACCESS_KEY"],
            aws_secrets.get("AWS_REGION", "us-east-2")  # Default to us-east-2 if not set
        )
    except KeyError:
        st.error("AWS credentials are missing. Check Streamlit secrets configuration.")
        return None, None, None

# Function to fetch data from DynamoDB
@st.cache_data
def get_dynamodb_data():
    """Fetch data from DynamoDB and convert it to a Pandas DataFrame."""
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
        table = dynamodb.Table("real_estate_listings")

        items, last_evaluated_key = [], None
        while True:
            response = table.scan(ExclusiveStartKey=last_evaluated_key) if last_evaluated_key else table.scan()
            items.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        return pd.DataFrame(items)

    except Exception as e:
        st.error(f"Failed to fetch data from DynamoDB: {str(e)}")
        return pd.DataFrame()

# Load data from AWS DynamoDB
listings_data = get_dynamodb_data()

# Ensure data is loaded
if listings_data.empty:
    st.error("No data available to display!")
    st.stop()

# Convert 'sold_date' to datetime format
listings_data["sold_date"] = pd.to_datetime(listings_data["sold_date"], errors="coerce").dt.normalize()

# Sidebar filters
st.sidebar.header("Filters")

start_date = st.sidebar.date_input("Start Date", pd.Timestamp("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.Timestamp("2024-12-31"))

selected_cities = st.sidebar.multiselect("Select Cities", sorted(listings_data["area_city"].dropna().unique()))
selected_communities = st.sidebar.multiselect("Select Communities", sorted(listings_data["community"].dropna().unique()))
selected_building_types = st.sidebar.multiselect("Select Building Types", sorted(listings_data["building_type"].dropna().unique()))
selected_firms = st.sidebar.multiselect("Select Brokerage Firms", sorted(listings_data["listing_firm"].dropna().unique()))

# **Optimized Filtering with Pandas Query**
query_str = f"(sold_date >= '{start_date}') & (sold_date <= '{end_date}')"

if selected_cities:
    query_str += f" & (area_city in {selected_cities})"
if selected_communities:
    query_str += f" & (community in {selected_communities})"
if selected_building_types:
    query_str += f" & (building_type in {selected_building_types})"
if selected_firms:
    query_str += f" & (listing_firm in {selected_firms})"

filtered_data = listings_data.query(query_str) if query_str else listings_data

# Check if data is empty after filtering
if filtered_data.empty:
    st.warning("No data found for the selected filters!")
    st.stop()

# Top 10 Brokerages with Most Deals
brokerage_deals = filtered_data["listing_firm"].value_counts().reset_index()
brokerage_deals.columns = ["Brokerage", "Number of Deals"]

# Display KPIs
st.subheader("Brokerage Performance Summary")

col1, col2 = st.columns(2)
col1.metric("Total Deals in Period", filtered_data.shape[0])
col2.metric("Total Brokerages Involved", brokerage_deals.shape[0])

########################## highlighted brokerage



import streamlit as st
import pandas as pd
import plotly.express as px

# Define the brokerage to highlight
highlight_brokerage = "Royal LePage Noralta Real Estate"

# Function to create a bar chart with highlighted brokerage
def create_highlighted_bar_chart(df, x_col, y_col, title):
    """Creates a bar chart where 'Royal LePage Noralta Real Estate' is highlighted in red."""
    df = df.copy()  # Avoid modifying the original DataFrame

    # Assign colors: "red" for the highlight, "royalblue" for others
    df["Color"] = df[x_col].apply(lambda x: "red" if x == highlight_brokerage else "royalblue")

    # Ensure the x-axis is ordered correctly (sorted by y_col values)
    df = df.sort_values(by=y_col, ascending=False)

    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        title=title,
        labels={x_col: "Brokerage", y_col: "Number of Deals"},
        text_auto=True,
        color=df["Color"],  # Assign colors dynamically
        category_orders={x_col: df[x_col].tolist()},  # Ensure correct order
        color_discrete_map={"red": "red", "royalblue": "royalblue"}  # Define color mapping
    )

    return fig

###################   TOP 10 COMBINED BUYER & LISTING FIRMS ####################

# Ensure 'listing_firm' and 'buyer_firm' columns exist before using them
listing_deals = filtered_data["listing_firm"].value_counts().rename("Listing Deals") if "listing_firm" in filtered_data.columns else pd.Series(dtype="int")
buyer_deals = filtered_data["buyer_firm"].value_counts().rename("Buyer Deals") if "buyer_firm" in filtered_data.columns else pd.Series(dtype="int")

# Merge listing and buyer firm counts into a single DataFrame
combined_deals = pd.DataFrame({"Brokerage": listing_deals.index}).merge(
    listing_deals, left_on="Brokerage", right_index=True, how="outer"
).merge(
    pd.DataFrame({"Brokerage": buyer_deals.index}).merge(
        buyer_deals, left_on="Brokerage", right_index=True, how="outer"
    ),
    on="Brokerage",
    how="outer"
).fillna(0)

# Calculate total deals (listing + buyer)
combined_deals["Total Deals"] = combined_deals["Listing Deals"] + combined_deals["Buyer Deals"]

# Sort by total deals in descending order
combined_deals = combined_deals.sort_values(by="Total Deals", ascending=False).head(10)

st.subheader("Top 10 Brokerages (Buyer & Listing Combined)")
if not combined_deals.empty:
    fig_combined = create_highlighted_bar_chart(
        combined_deals,
        x_col="Brokerage",
        y_col="Total Deals",
        title="(Buyer & Listing) Top 10 Brokerages by Total Deals "
    )
    st.plotly_chart(fig_combined)
else:
    st.warning("No data available for the selected filters.")

###################   TOP 10 LISTING FIRMS ####################

# Ensure 'listing_firm' column exists before using it
if "listing_firm" in filtered_data.columns:
    brokerage_deals = filtered_data["listing_firm"].value_counts().reset_index()
    brokerage_deals.columns = ["Brokerage", "Number of Deals"]
    brokerage_deals = brokerage_deals.sort_values(by="Number of Deals", ascending=False).head(10)  # Correct sorting
else:
    brokerage_deals = pd.DataFrame(columns=["Brokerage", "Number of Deals"])

st.subheader("Listing Side - Top 10 Brokerages with Most Deals")
if not brokerage_deals.empty:
    fig = create_highlighted_bar_chart(
        brokerage_deals,
        x_col="Brokerage",
        y_col="Number of Deals",
        title="Top 10 Brokerages by Deals (Listing Side)"
    )
    st.plotly_chart(fig)
else:
    st.warning("No data available for the selected filters.")


###################   TOP 10 BUYER FIRMS ####################

# Ensure 'buyer_firm' column exists before using it
if "buyer_firm" in filtered_data.columns:
    buyer_brokerage_deals = filtered_data["buyer_firm"].value_counts().reset_index()
    buyer_brokerage_deals.columns = ["Brokerage", "Number of Deals"]
    buyer_brokerage_deals = buyer_brokerage_deals.sort_values(by="Number of Deals", ascending=False).head(10)  # Correct sorting
else:
    buyer_brokerage_deals = pd.DataFrame(columns=["Brokerage", "Number of Deals"])

st.subheader("Buyers Side - Top 10 Brokerages with Most Deals")
if not buyer_brokerage_deals.empty:
    fig_buyer = create_highlighted_bar_chart(
        buyer_brokerage_deals,
        x_col="Brokerage",
        y_col="Number of Deals",
        title="Top 10 Buyer Brokerages by Deals"
    )
    st.plotly_chart(fig_buyer)
else:
    st.warning("No data available for the selected filters.")



############################################################## ---------------------------------------------
# Visualization: Deals Per Agent by Brokers (Top 10 + Noralta)
# ---------------------------------------------
st.header("Deals Per Agent by Brokers - Top 10 + Noralta")

# ---------------------------------------------
# Initialize DynamoDB Connection
# ---------------------------------------------
dynamodb = boto3.resource("dynamodb", region_name="us-east-2")  # Adjust region if needed

# List all tables to check existence
existing_tables = dynamodb.meta.client.list_tables()["TableNames"]

# ---------------------------------------------
# Load Brokerage Data
# ---------------------------------------------
if "brokerage" in existing_tables:
    table = dynamodb.Table("brokerage")
    response = table.scan()
    brokerage_data = pd.DataFrame(response.get("Items", []))
else:
    st.error("Brokerage table not found in DynamoDB!")
    st.stop()

# Ensure required columns exist before processing
if not set(brokerage_data.columns).intersection({"Broker", "id"}):
    st.error("Missing required columns ('Broker', 'id') in brokerage data!")
    st.stop()

# Convert date-based columns into long format
brokerage_data_melted = brokerage_data.melt(
    id_vars=['Broker'], var_name='Date', value_name='Average Agents'
)
brokerage_data_melted['Date'] = pd.to_datetime(brokerage_data_melted['Date'], errors='coerce')
brokerage_data_melted = brokerage_data_melted.dropna()

# Convert Date to month-based timestamps
brokerage_data_melted['Month'] = brokerage_data_melted['Date'].dt.to_period('M').dt.to_timestamp()

# ---------------------------------------------
# Load Real Estate Listings Data
# ---------------------------------------------
if "real_estate_listings" in existing_tables:
    table = dynamodb.Table("real_estate_listings")
    response = table.scan()
    listings_data = pd.DataFrame(response.get("Items", []))
else:
    st.error("Real Estate Listings table not found in DynamoDB!")
    st.stop()

# Ensure `filtered_listings` exists before using it
if "sold_date" in listings_data.columns:
    listings_data["sold_date"] = pd.to_datetime(listings_data["sold_date"], errors="coerce")
else:
    st.error("Missing 'sold_date' column in listings data!")
    st.stop()

# ---------------------------------------------
# Filter Listings Within the Date Range
# ---------------------------------------------
start_date = st.sidebar.date_input("Start Date", pd.Timestamp("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.Timestamp("2024-12-31"))

filtered_listings = listings_data[
    (listings_data['sold_date'] >= pd.Timestamp(start_date)) &
    (listings_data['sold_date'] <= pd.Timestamp(end_date))
].copy()

# Extract the month for each transaction
filtered_listings['Month'] = filtered_listings['sold_date'].dt.to_period('M').dt.to_timestamp()

# ---------------------------------------------
# Count Total Deals (Listing + Buyer) per Month per Broker
# ---------------------------------------------
monthly_combined_deals = pd.DataFrame()
months = filtered_listings['Month'].unique()

for month in months:
    month_data = filtered_listings[filtered_listings['Month'] == month]
    
    # Ensure no missing values before counting
    month_deals = (
        month_data['listing_firm'].dropna().value_counts() +
        month_data['buyer_firm'].dropna().value_counts()
    ).reset_index()
    
    month_deals.columns = ['Brokerage', 'Deals']
    month_deals['Month'] = month
    monthly_combined_deals = pd.concat([monthly_combined_deals, month_deals], ignore_index=True)

# ---------------------------------------------
# Merge Deals with Agent Counts by Brokerage & Month
# ---------------------------------------------
if monthly_combined_deals.empty or brokerage_data_melted.empty:
    st.warning("No data available for merging.")
    st.stop()

merged_monthly = pd.merge(
    monthly_combined_deals,
    brokerage_data_melted,
    left_on=['Brokerage', 'Month'],
    right_on=['Broker', 'Month'],
    how='inner'
)

# ---------------------------------------------
# Calculate "Deals Per Agent"
# ---------------------------------------------
merged_monthly['Deals Per Agent'] = merged_monthly['Deals'] / merged_monthly['Average Agents']
merged_monthly = merged_monthly.drop(columns=['Broker'])  # Remove duplicate broker column

# Ensure complete data grid (all brokers for all months)
all_months = pd.date_range(start=start_date, end=end_date, freq='MS')
all_brokers = merged_monthly['Brokerage'].unique()
complete_index = pd.MultiIndex.from_product([all_brokers, all_months], names=['Brokerage', 'Month'])
merged_monthly = merged_monthly.set_index(['Brokerage', 'Month']).reindex(complete_index).reset_index()

# Fill missing values with 0
merged_monthly['Deals'] = merged_monthly['Deals'].fillna(0)
merged_monthly['Average Agents'] = merged_monthly['Average Agents'].fillna(0)
merged_monthly['Deals Per Agent'] = (merged_monthly['Deals'] / merged_monthly['Average Agents']).fillna(0)

# ---------------------------------------------
# Select Top 10 Brokerages by Total Deals
# ---------------------------------------------
top_brokers = merged_monthly.groupby('Brokerage')['Deals'].sum().nlargest(10).index
filtered_monthly_top = merged_monthly[merged_monthly['Brokerage'].isin(top_brokers)]

# Ensure Royal LePage Noralta Real Estate is included
royal_data = merged_monthly[merged_monthly['Brokerage'] == "Royal LePage Noralta Real Estate"]
if not royal_data.empty and "Royal LePage Noralta Real Estate" not in top_brokers:
    filtered_monthly_top = pd.concat([filtered_monthly_top, royal_data])

# ---------------------------------------------
# Create Line Chart
# ---------------------------------------------
fig_line = px.line(
    filtered_monthly_top,
    x='Month',
    y='Deals Per Agent',
    color='Brokerage',
    title="Monthly Deals Per Agent by Broker",
    labels={'Deals Per Agent': 'Deals Per Agent', 'Month': 'Month', 'Brokerage': 'Brokerage'}
)

fig_line.update_traces(mode="lines+markers",
                       hovertemplate=("<b>Brokerage: %{color}</b><br>"
                                      "Month: %{x}<br>"
                                      "Deals Per Agent: %{y:.2f}<extra></extra>"))
st.plotly_chart(fig_line, use_container_width=True)
