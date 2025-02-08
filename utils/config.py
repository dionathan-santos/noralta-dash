import os
import streamlit as st

def get_aws_credentials():
    """
    Get AWS credentials from Streamlit secrets.
    Returns a tuple of (access_key, secret_key, region)
    """
    # Debugging: Print available secret keys and their contents
    st.write("Available Secrets Keys:", list(st.secrets.keys()))
    
    # Special handling for nested 'aws' dictionary
    if 'aws' in st.secrets:
        st.write("AWS Secrets Keys:", list(st.secrets.aws.keys()))

    # Credential retrieval methods
    credential_methods = [
        # 1. Nested AWS section access (most likely scenario)
        lambda: (
            st.secrets.get('aws', {}).get('AWS_ACCESS_KEY_ID'),
            st.secrets.get('aws', {}).get('AWS_SECRET_ACCESS_KEY')
        ),
        
        # 2. Direct root-level access
        lambda: (
            st.secrets.get("AWS_ACCESS_KEY_ID"),
            st.secrets.get("AWS_SECRET_ACCESS_KEY")
        ),
        
        # 3. Environment variables fallback
        lambda: (
            os.environ.get("AWS_ACCESS_KEY_ID"),
            os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
    ]

    # Try each credential retrieval method
    for method in credential_methods:
        try:
            aws_access_key, aws_secret_key = method()
            if aws_access_key and aws_secret_key:
                # Validate the credentials are not placeholders
                if "YOUR" in str(aws_access_key) or "KEY" in str(aws_access_key):
                    st.error("❌ Detected placeholder AWS credentials. Please replace with actual credentials.")
                    raise ValueError("Placeholder credentials detected")

                # Mask the keys for logging
                masked_access_key = f"{aws_access_key[:4]}...{aws_access_key[-4:]}"
                st.info(f"AWS Access Key found: {masked_access_key}")
                
                # Get region with fallback
                aws_region = (
                    st.secrets.get('aws', {}).get('AWS_REGION') or 
                    st.secrets.get('AWS_REGION') or 
                    os.environ.get('AWS_REGION', 'us-east-2')
                )
                
                return aws_access_key, aws_secret_key, aws_region
        except Exception as e:
            st.write(f"Credential method failed: {e}")

    # If no credentials found
    error_message = """
    ❌ AWS Credentials Configuration Error ❌

    Credentials could not be found. Please configure:

    Option 1: Streamlit Cloud Secrets (Recommended)
    In the Secrets section, add:
    [aws]
    AWS_ACCESS_KEY_ID = "your_actual_access_key"
    AWS_SECRET_ACCESS_KEY = "your_actual_secret_key"
    AWS_REGION = "us-east-2"  # Optional, defaults to us-east-2

    Option 2: Environment Variables
    - Set AWS_ACCESS_KEY_ID
    - Set AWS_SECRET_ACCESS_KEY

    Current available secret keys: {}
    """.format(list(st.secrets.keys()))
    
    st.error(error_message)
    raise ValueError(error_message)