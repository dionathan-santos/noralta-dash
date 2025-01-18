import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# Title and description
st.title("Notebook-based Page")
st.write("This page was created from a Jupyter Notebook.")

# Example DataFrame
data = {'Category': ['A', 'B', 'C'], 'Values': [10, 20, 15]}
df = pd.DataFrame(data)
st.write("Here’s an example DataFrame:")
st.dataframe(df)

# Example plot
fig, ax = plt.subplots()
ax.bar(df['Category'], df['Values'])
ax.set_ylabel('Values')
st.pyplot(fig)
