
import streamlit as st
import pandas as pd
import google.generativeai as genai
from datetime import datetime

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
                color: #1d1d1f !important; /* CRITICAL FIX: Force dark text */
            }
            .contract-title {
                font-weight: bold;
                font-size: 1.2em;
                margin-bottom: 5px;
            }
            .closing-date {
                color: #86868b; /* Lighter gray for this specific text */
                font-size: 0.9em;
                margin-bottom: 15px;
            }
            .urgent-label {
                color: #ff3b30;
                font-weight: bold;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

inject_custom_css()

# --- Data Loading & Cleaning ---
@st.cache_data
def load_data():
    url = "https://open.canada.ca/data/dataset/6abd20d4-7a1c-4b38-baa2-9525d0bb2fd2/resource/05b804dd-11ec-4271-8d69-d6044e1a5481/download/f-new_tender_notices.csv"
    storage_options = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
    try:
        df = pd.read_csv(url, storage_options=storage_options, encoding='utf-8')

        # Robustly rename columns
        df.rename(columns={
            'procurementCategory-categorieApprovisionnement': 'Category',
            'tenderStatus-tenderStatut-eng': 'Status',
            'dateClosing-dateCloture': 'Closing Date',
            'title-titre-eng': 'Title',
            'title-titre': 'Title',
            'title_en': 'Title',
            'description_en': 'Description',
            'description-eng': 'Description',
            'description-description-eng': 'Description',
            'procurementOrganization-organisationApprovisionnement-eng': 'Authority'
        }, inplace=True)

        # Handle the GSIN column
        if 'gsin-nins' in df.columns:
            df.rename(columns={'gsin-nins': 'GSIN'}, inplace=True)
        else:
            df['GSIN'] = 'General'

        # Ensure essential columns exist after renaming
        essential_columns = ['Title', 'Closing Date', 'Description', 'GSIN', 'Category', 'Status', 'Authority']
        for col in essential_columns:
            if col not in df.columns:
                df[col] = pd.NA # Use pandas NA for consistency

        # Smart Fallbacks
        df['Closing Date'] = df['Closing Date'].fillna('Open Continuous')
        if 'Title' in df.columns:
             df['Description'] = df['Description'].fillna(df['Title'])
        df['Description'] = df['Description'].fillna('No Description Available') # Final fallback
        df['Category'] = df['Category'].fillna('N/A').astype(str) # Ensure category is searchable
        df['Authority'] = df['Authority'].fillna('N/A')

        # Data Cleaning & Sorting
        df['Closing Date'] = pd.to_datetime(df['Closing Date'], errors='coerce')
        df.dropna(subset=['Closing Date'], inplace=True) # Remove rows where date conversion failed
        df = df[df['Closing Date'] >= datetime.now()]
        df = df.sort_values(by='Closing Date', ascending=True)


        return df
    except Exception as e:
        st.error(f"Error loading and processing data: {e}")
        return pd.DataFrame()

df = load_data()

# --- Main Layout ---
st.title("GovTender Autopilot")

# --- Feature A (CFO Metrics) ---
if not df.empty:
    total_active_leads = len(df)
    top_category = df['Category'].mode()[0] if not df['Category'].mode().empty else "N/A"
    next_deadline = df['Closing Date'].min().strftime('%Y-%m-%d') if not df.empty else "N/A"

    st.subheader("CFO Metrics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Active Leads", total_active_leads)
    col2.metric("Top Category", top_category)
    col3.metric("Next Deadline", next_deadline)

    st.subheader("Contracts by Category")
    category_counts = df['Category'].value_counts().nlargest(7)
    st.bar_chart(category_counts)


search_term = st.text_input("🔍 Search Contracts")


# --- Sidebar Filters ---
st.sidebar.header("Filters")
if not df.empty:
    df['GSIN'] = df['GSIN'].fillna('Not Specified')
    categories = ['All'] + sorted(df['GSIN'].unique().tolist())
    selected_category = st.sidebar.selectbox("Category (GSIN)", categories)
    
    df['Status'] = df['Status'].fillna('Unknown')
    statuses = ['All'] + sorted(df['Status'].unique().tolist())
    selected_status = st.sidebar.selectbox("Status", statuses)

    # Filtering logic
    filtered_df = df.copy()
    if selected_category != 'All':
        filtered_df = filtered_df[filtered_df['GSIN'] == selected_category]
    if selected_status != 'All':
        filtered_df = filtered_df[filtered_df['Status'] == selected_status]

    # Search filtering
    if search_term:
        search_term_lower = search_term.lower()
        filtered_df = filtered_df[
            filtered_df['Title'].str.lower().str.contains(search_term_lower, na=False) |
            filtered_df['Description'].str.lower().str.contains(search_term_lower, na=False) |
            filtered_df['Category'].str.lower().str.contains(search_term_lower, na=False)
        ]


else:
    filtered_df = pd.DataFrame()
    st.sidebar.write("No data to filter.")


# --- Main Area: Contract Cards ---
st.write(f"Found {len(filtered_df)} contracts.")

if not filtered_df.empty:
    st.write(f"Displaying top 10.")
    for index, row in filtered_df.head(10).iterrows():
        title = row.get('Title', 'No Title Available')
        closing_date = row.get('Closing Date')
        description = row.get('Description', 'No Description Available')
        authority = row.get('Authority', 'N/A')


        # Feature B (Smart Cards)
        urgent_label = ""
        if closing_date and (closing_date - datetime.now()).days <= 7:
            urgent_label = "<span class='urgent-label'>🔥 Urgent</span>"


        card_html = f'''
        <div class="contract-card">
            <div class="contract-title">{title}</div>
            <div class="closing-date">Closes: {closing_date.strftime('%Y-%m-%d')} {urgent_label}</div>
        </div>
        '''
        st.markdown(card_html, unsafe_allow_html=True)

        with st.expander("Details"):
            st.write(description)
            # Feature C (The Closer)
            strategy_tab, email_tab = st.tabs(["📊 Strategy", "✉️ Draft Email"])

            with strategy_tab:
                if st.button('✨ Analyze Opportunity', key=f"analyze_{index}"):
                    try:
                        if 'GEMINI_API_KEY' in st.secrets:
                            genai.configure(api_key=st.secrets['GEMINI_API_KEY'])
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            prompt = f"Analyze the following government contract and provide a brief 'Winning Strategy' for a company specializing in digital marketing and web development. Contract Title: '{title}', Description: '{description}'"
                            
                            with st.spinner("🤖 AI is analyzing..."):
                                response = model.generate_content(prompt)
                                strategy = response.text
                                st.success("**Winning Strategy:**")
                                st.write(strategy)
                        else:
                            st.warning('⚠️ AI Brain Missing. Please add Gemini API Key to Secrets.')
                    except Exception as e:
                        st.error(f"An error occurred with the AI analysis: {e}")
            
            with email_tab:
                if st.button('✍️ Generate Draft', key=f"draft_{index}"):
                    try:
                        if 'GEMINI_API_KEY' in st.secrets:
                            genai.configure(api_key=st.secrets['GEMINI_API_KEY'])
                            model = genai.GenerativeModel('gemini-1.5-flash')
                            prompt = f"Please draft a professional and formal inquiry email to the Contracting Authority, {authority}, regarding the tender titled '{title}'. The email should express interest and ask for any available clarification documents."

                            with st.spinner("🤖 AI is drafting..."):
                                response = model.generate_content(prompt)
                                email_draft = response.text
                                st.success("**Draft Email:**")
                                st.text_area("Email Body",email_draft, height=300)
                        else:
                            st.warning('⚠️ AI Brain Missing. Please add Gemini API Key to Secrets.')
                    except Exception as e:
                        st.error(f"An error occurred with the AI email generation: {e}")


else:
    st.write("No contracts to display based on the current filters.")
