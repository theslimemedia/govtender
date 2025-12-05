
import streamlit as st
import pandas as pd
import openai

# Set page config
st.set_page_config(layout="wide")

# --- Design System ---
def inject_custom_css():
    st.markdown(
        """
        <style>
            /* Hide Streamlit's default header and footer */
            .st-emotion-cache-18ni7ap, .st-emotion-cache-h5rgaw {
                display: none;
            }
            /* Use system fonts */
            body {
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
            /* Style text inputs */
            .stTextInput > div > div > input {
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border: 1px solid #e6e6e6;
                padding: 10px;
            }
            /* Style buttons */
            .stButton > button {
                border-radius: 12px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                border: none;
                padding: 10px 20px;
                background-color: #007aff;
                color: white;
            }
            /* Card styles */
            .contract-card {
                background-color: white;
                border-radius: 12px;
                padding: 20px;
                margin-bottom: 15px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                border: 1px solid #e6e6e6;
            }
            .contract-title {
                font-weight: bold;
                font-size: 1.2em;
                margin-bottom: 5px;
            }
            .closing-date {
                color: #8e8e93;
                font-size: 0.9em;
                margin-bottom: 15px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_custom_css()

# --- Data Loading ---
@st.cache_data
def load_data():
    url = "https://open.canada.ca/data/dataset/6abd20d4-7a1c-4b38-baa2-9525d0bb2fd2/resource/05b804dd-11ec-4271-8d69-d6044e1a5481/download/f-new_tender_notices.csv"
    storage_options = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        df = pd.read_csv(url, storage_options=storage_options, encoding='utf-8')
        return df
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

# --- Main Layout ---
st.title("GovTender Autopilot")

# --- Sidebar Filters ---
st.sidebar.header("Filters")
if not df.empty:
    # Using 'gsin' for category as it seems to be a good categorical identifier.
    # We will handle potential missing values.
    df['gsin'] = df['gsin'].fillna('Not Specified')
    categories = ['All'] + sorted(df['gsin'].unique().tolist())
    selected_category = st.sidebar.selectbox("Category (GSIN)", categories)

    # Filtering logic
    if selected_category != 'All':
        filtered_df = df[df['gsin'] == selected_category]
    else:
        filtered_df = df
else:
    filtered_df = pd.DataFrame()
    st.sidebar.write("No data to filter.")


# --- Main Area: Contract Cards ---
if not filtered_df.empty:
    st.write(f"Displaying top 10 of {len(filtered_df)} contracts.")
    for index, row in filtered_df.head(10).iterrows():
        title = row.get('title_en', 'No Title Available')
        closing_date = row.get('closing_date', 'N/A')
        description = row.get('description_en', 'No Description')

        card_html = f"""
        <div class="contract-card">
            <div class="contract-title">{title}</div>
            <div class="closing-date">Closes: {closing_date}</div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        with st.expander("Details"):
            st.write(description)
            if st.button('✨ Analyze Opportunity', key=f"analyze_{index}"):
                try:
                    # Check for OpenAI API key in secrets
                    if 'OPENAI_API_KEY' in st.secrets:
                        openai.api_key = st.secrets["OPENAI_API_KEY"]
                        prompt = f"Analyze the following government contract and provide a brief 'Winning Strategy' for a company specializing in digital marketing and web development. Contract Title: '{title}', Description: '{description}'"
                        
                        with st.spinner("🤖 AI is analyzing..."):
                            response = openai.ChatCompletion.create(
                                model="gpt-3.5-turbo",
                                messages=[
                                    {"role": "system", "content": "You are a helpful assistant that provides concise winning strategies for government contracts."},
                                    {"role": "user", "content": prompt}
                                ]
                            )
                            strategy = response.choices[0].message['content']
                            st.success("**Winning Strategy:**")
                            st.write(strategy)
                    else:
                        st.warning('⚠️ AI Brain Missing. Please add OpenAI Key to Secrets.')
                except Exception as e:
                    st.error(f"An error occurred with the AI analysis: {e}")

else:
    st.write("No contracts to display based on the current filters.")

