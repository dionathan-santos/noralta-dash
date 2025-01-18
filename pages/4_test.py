import streamlit as st

# Get the logged-in user's information on Streamlit Cloud
user_info = st.experimental_user
email = user_info["email"] if user_info else None

# Debugging: Print user info to check your email (useful for the first time)
st.write("Logged-in user info:", user_info)

# Check if the logged-in user is you
if email == "dionathan.adiel@live.com":  # Replace with your GitHub email
    # Title for the test page
    st.title("Test Page")
    st.write("Welcome! This page is only visible to you.")

    # Sidebar content
    st.sidebar.title("Navigation")
    st.sidebar.write("This is the test page's sidebar.")
    
    # Main content for the page
    st.subheader("Testing Features")
    st.write("You can use this page to test new features without affecting other users.")
    
    # Example of some test widgets
    st.write("### Widgets for Testing")
    number = st.number_input("Enter a number for testing:", min_value=0, max_value=100, value=50)
    st.write(f"You entered: {number}")

    text = st.text_input("Enter some text for testing:")
    st.write(f"You entered: {text}")

    # Display a placeholder to simulate loading
    with st.spinner("Simulating a long-running process..."):
        import time
        time.sleep(2)  # Simulate a 2-second delay
    st.success("Process completed successfully!")

else:
    # If the user is not authorized, display a message and stop
    st.write("This page is under development and not available to others.")
    st.stop()
