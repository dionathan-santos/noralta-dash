import streamlit as st

# Load Streamlit secrets
secret_key = st.secrets.get("TEST_PAGE_ACCESS_KEY")

# Ask for user input to match the secret key
access_key = st.text_input("Enter the access key to view this page:", type="password")

if access_key == secret_key:
    # Title for the test page
    st.title("Test Page")
    st.write("Welcome! This page is only visible to you.")

    # Sidebar content
    st.sidebar.title("Navigation")
    st.sidebar.write("This is the test page's sidebar.")

    # Main content for the page
    st.subheader("Testing Features")
    st.write("You can use this page to test new features without affecting other users.")
else:
    st.write("Access denied. This page is under development and not available to others.")
