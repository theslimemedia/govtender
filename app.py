
import streamlit as st
import pandas as pd

st.title('GovTender Autopilot')

@st.cache_data
def load_data():
    url = "https://open.canada.ca/data/dataset/6abd20d4-7a1c-4b38-baa2-9525d0bb2fd2/resource/05b804dd-11ec-4271-8d69-d6044e1a5481/download/f-new_tender_notices.csv"
    storage_options = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    df = pd.read_csv(url, storage_options=storage_options)
    return df

df = load_data()

search_term = st.text_input('🔍 Search Contracts')

if search_term:
    # A simple search across all columns for the search term
    # The `na=False` argument ensures that rows with NaN values in any column are not returned as True.
    # The `.astype(str)` is to make sure all columns are strings before applying `.contains()`.
    filtered_df = df[df.apply(lambda row: row.astype(str).str.contains(search_term, case=False, na=False).any(), axis=1)]
    st.write(f"Found {len(filtered_df)} results.")
    st.dataframe(filtered_df)
else:
    st.write("Displaying first 10 rows.")
    st.dataframe(df.head(10))
