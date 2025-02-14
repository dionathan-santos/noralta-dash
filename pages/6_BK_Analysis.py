import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from datetime import datetime

###    git add . ; git commit -m "new dash3" ; git push origin main  


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

# Convert 'sold_date' to datetime format and remove time part
listings_data["sold_date"] = pd.to_datetime(listings_data["sold_date"], errors="coerce").dt.normalize()

# Drop rows with invalid 'sold_date' values to prevent issues in filtering/grouping
listings_data = listings_data.dropna(subset=["sold_date"])

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






# ---------------------------------------------
# Visualization: Monthly Market Share by Firm (%) - Whole Market
# ---------------------------------------------
st.header("Monthly Market Share by Firm (%) - Top 10 + Noralta")

# Create a copy of filtered_data and add a Month column
market_data = filtered_data.copy()
market_data['Month'] = market_data['sold_date'].dt.to_period('M').dt.to_timestamp()

# Calculate monthly deals per firm for the listing side
monthly_deals_listing = (
    market_data.groupby(['listing_firm', 'Month']).size().reset_index(name='Deals')
)
# Calculate monthly deals per firm for the buyer side
monthly_deals_buyer = (
    market_data.groupby(['buyer_firm', 'Month']).size().reset_index(name='Deals')
)

# Standardize the firm column names for merging
monthly_deals_listing = monthly_deals_listing.rename(columns={'listing_firm': 'Firm'})
monthly_deals_buyer = monthly_deals_buyer.rename(columns={'buyer_firm': 'Firm'})

# Combine the two dataframes (all deals, across the whole market)
all_monthly_deals = pd.concat([monthly_deals_listing, monthly_deals_buyer], axis=0)
all_monthly_deals = all_monthly_deals.groupby(['Firm', 'Month'])['Deals'].sum().reset_index()

# Calculate total deals for each month across the whole market
total_monthly_deals = market_data.groupby('Month').size().reset_index(name='Total Deals')

# Merge firm-level deals with total monthly deals so that each firm's market share is relative to the entire market
market_share = pd.merge(all_monthly_deals, total_monthly_deals, on='Month')
market_share['Market Share (%)'] = (market_share['Deals'] / market_share['Total Deals']) * 100

# Determine the top 10 firms by overall market share (summing market share across months)
overall_market_share = market_share.groupby('Firm')['Market Share (%)'].sum().reset_index()
top_firms = overall_market_share.sort_values('Market Share (%)', ascending=False).head(10)['Firm'].tolist()

# Ensure the highlighted firm is included
highlight_firm = "Royal LePage Noralta Real Estate"
if highlight_firm not in top_firms:
    top_firms.append(highlight_firm)

# Filter the market share data to only include the top firms (from the whole market)
market_share_top = market_share[market_share['Firm'].isin(top_firms)].drop_duplicates(subset=['Firm', 'Month'])

# Create a line chart showing monthly market share for the selected firms
fig_market_share = px.line(
    market_share_top,
    x='Month',
    y='Market Share (%)',
    color='Firm',
    markers=True,
    title="Monthly Market Share by Firm (%) - Top 10 + Noralta"
)
fig_market_share.update_layout(
    xaxis_title="Month",
    yaxis_title="Market Share (%)",
    legend_title="Firm",
    margin=dict(b=120)
)
fig_market_share.update_xaxes(tickformat="%Y-%m-%d")
st.plotly_chart(fig_market_share, use_container_width=True)



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



########################################### TABLE DEALS PER AGENT


# ----- NEW CODE: Add brokerage data function and table for Avg Deals per Agent -----

# Function to load brokerage data from DynamoDB
@st.cache_data
def get_brokerage_data():
    """Fetch brokerage data from DynamoDB and convert it to a Pandas DataFrame."""
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
        table = dynamodb.Table("brokerage")

        items, last_evaluated_key = [], None
        while True:
            response = table.scan(ExclusiveStartKey=last_evaluated_key) if last_evaluated_key else table.scan()
            items.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        brokerage_df = pd.DataFrame(items)
        
        # Rename columns to match expected format
        brokerage_df = brokerage_df.rename(columns={
            "brokerage_name": "firm",
            "agent_count": "Active Agents",
            "report_date": "Month"
        })
        
        # Convert Month to datetime and Active Agents to numeric
        brokerage_df["Month"] = pd.to_datetime(brokerage_df["Month"]).dt.to_period("M").dt.to_timestamp()
        brokerage_df["Active Agents"] = pd.to_numeric(brokerage_df["Active Agents"])
        
        return brokerage_df

    except Exception as e:
        st.error(f"Failed to fetch brokerage data from DynamoDB: {str(e)}")
        return pd.DataFrame()

# ----- Calculate Monthly Deals for Top 10 Firms and Merge with Brokerage Data -----

# Create a copy of the filtered data and add a Month column.
# (Note: filtered_data is already loaded and processed earlier in the code.)
market_data = filtered_data.copy()
# Convert sold_date to the first day of the month (to align with brokerage data).
market_data["Month"] = pd.to_datetime(market_data["sold_date"]).dt.to_period("M").dt.to_timestamp()

# Calculate monthly deals from the listing side.
monthly_deals_listing = (
    market_data.groupby(["listing_firm", "Month"]).size().reset_index(name="Deals")
)
# Rename the column for consistency.
monthly_deals_listing = monthly_deals_listing.rename(columns={"listing_firm": "Firm"})

# Calculate monthly deals from the buyer side.
monthly_deals_buyer = (
    market_data.groupby(["buyer_firm", "Month"]).size().reset_index(name="Deals")
)
monthly_deals_buyer = monthly_deals_buyer.rename(columns={"buyer_firm": "Firm"})

# Combine both listing and buyer deals.
all_monthly_deals = pd.concat([monthly_deals_listing, monthly_deals_buyer], axis=0)
all_monthly_deals = all_monthly_deals.groupby(["Firm", "Month"])["Deals"].sum().reset_index()

# Determine the top 10 firms overall (by total deals over the period)
overall_deals = all_monthly_deals.groupby("Firm")["Deals"].sum().reset_index()
top_firms = overall_deals.sort_values("Deals", ascending=False).head(10)["Firm"].tolist()

# Filter the monthly deals data to only include rows for the top 10 firms.
top_monthly_deals = all_monthly_deals[all_monthly_deals["Firm"].isin(top_firms)]

# Load the brokerage data (which contains the number of active agents per firm and month)
brokerage_data = get_brokerage_data()
top_brokerage_data = brokerage_data[brokerage_data["firm"].isin(top_firms)]

# Merge the monthly deals with the brokerage data on both Firm and Month.
merged_data = pd.merge(top_monthly_deals, top_brokerage_data, on=["Firm", "Month"], how="left")

# Compute the average deals per agent.
# Use a lambda function that divides the total deals by the active agents (if active agents > 0).
merged_data["Avg Deals per Agent"] = merged_data.apply(
    lambda row: round(row["Deals"] / row["Active Agents"], 2) if row["Active Agents"] and row["Active Agents"] > 0 else 0,
    axis=1
)

# Prepare the final table with only the desired columns and sort by Firm and Month.
final_table = merged_data[["Firm", "Month", "Avg Deals per Agent", "Active Agents"]].sort_values(["Firm", "Month"])

# Display the final table in the Streamlit app.
st.subheader("Monthly Average Deals Per Agent & Active Agents for Top 10 Firms")
st.dataframe(final_table)
