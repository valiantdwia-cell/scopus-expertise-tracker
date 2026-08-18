import streamlit as st
import pandas as pd
from collections import Counter
import pybliometrics
from pybliometrics.scopus import AuthorRetrieval
import time
import io

# 1. Page Configuration
st.set_page_config(page_title="Scopus Expertise Tracker", layout="wide")

st.title("Scopus Researcher Expertise Tracker")
st.write("An application to map overall expertise areas and specific research topics of authors using Scopus Author IDs.")

# 2. Initialize Scopus API Key
pybliometrics.scopus.init(keys=['ede6474ccb592558f068c82c9145cd65'])

# Helper function to extract data for a single author
def get_author_data(author_id):
    au = AuthorRetrieval(author_id)
    full_name = f"{au.given_name or ''} {au.surname or ''}".strip()
    affiliation = au.affiliation_current[0].preferred_name if au.affiliation_current else "Unknown"
    total_docs = getattr(au, 'document_count', getattr(au, 'doc_count', 0))
    h_index = getattr(au, 'hindex', getattr(au, 'h_index', 0))
    
    # Subject Areas (Top 3)
    areas = getattr(au, 'subject_areas', None) or getattr(au, 'classification', None)
    subject_list = []
    if areas:
        for area in areas:
            area_name = getattr(area, 'area', area[2] if isinstance(area, (list, tuple)) else 'N/A')
            subject_list.append(area_name)
    str_subject = ", ".join(subject_list[:3]) if subject_list else "Not Found"
    
    # Top Keywords (Top 5)
    docs = au.get_documents()
    list_keywords = []
    if docs:
        for doc in docs:
            if hasattr(doc, 'authkeywords') and doc.authkeywords:
                keywords = [k.strip().title() for k in doc.authkeywords.split('|')]
                list_keywords.extend(keywords)
        top_keywords = [item[0] for item in Counter(list_keywords).most_common(5)]
        str_keywords = ", ".join(top_keywords) if top_keywords else "No Keywords Found"
    else:
        str_keywords = "No Documents Found"
        
    return {
        'Author_ID': author_id,
        'Full Name': full_name,
        'Affiliation': affiliation,
        'Total Documents': total_docs,
        'h-Index': h_index,
        'Main Subject Areas': str_subject,
        'Dominant Research Topics': str_keywords,
        'Status': 'Success'
    }

# 3. Navigation Tabs
tab1, tab2 = st.tabs(["Single Author Search", "Bulk Author Search"])

# ==========================================
# TAB 1: SINGLE SEARCH
# ==========================================
with tab1:
    st.subheader("Single Author Lookup")
    author_id_input = st.text_input("Enter Scopus Author ID:", placeholder="e.g., 57196230000")
    
    if st.button("Search Author Data", type="primary"):
        if not author_id_input.strip():
            st.warning("Please enter a valid Scopus Author ID.")
        else:
            author_id = author_id_input.strip()
            with st.spinner("Fetching data from Scopus..."):
                try:
                    data = get_author_data(author_id)
                    st.success("Data Retrieved Successfully.")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Full Name:** {data['Full Name']}")
                        st.write(f"**Primary Affiliation:** {data['Affiliation']}")
                    with col2:
                        st.write(f"**Total Documents:** {data['Total Documents']}")
                        st.write(f"**h-Index:** {data['h-Index']}")
                    
                    st.divider()
                    st.write(f"**Main Subject Areas:** {data['Main Subject Areas']}")
                    st.write(f"**Dominant Research Topics:** {data['Dominant Research Topics']}")
                    
                except pybliometrics.exception.Scopus404Error:
                    st.error(f"Scopus Author ID '{author_id}' was not found.")
                except Exception as e:
                    st.error(f"An error occurred: {e}")

# ==========================================
# TAB 2: BULK SEARCH (EXCEL UPLOAD)
# ==========================================
with tab2:
    st.subheader("Bulk Search via Excel File")
    st.info("Make sure your Excel file contains a column header named Author_ID.")
    
    uploaded_file = st.file_uploader("Upload Excel File (.xlsx)", type=["xlsx"])
    
    if uploaded_file is not None:
        try:
            df_input = pd.read_excel(uploaded_file, dtype={'Author_ID': str})
            st.write("Input File Preview:")
            st.dataframe(df_input.head(), use_container_width=True)
            
            if 'Author_ID' not in df_input.columns:
                st.error("The Excel file must contain an 'Author_ID' column header.")
            else:
                if st.button("Start Bulk Extraction", type="primary"):
                    list_author_ids = df_input['Author_ID'].dropna().tolist()
                    total_data = len(list_author_ids)
                    
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    
                    hasil_pencarian = []
                    
                    for idx, aid in enumerate(list_author_ids, start=1):
                        aid = str(aid).strip()
                        status_text.text(f"Processing {idx}/{total_data} ID: {aid}...")
                        
                        try:
                            res = get_author_data(aid)
                            hasil_pencarian.append(res)
                        except Exception as e:
                            hasil_pencarian.append({
                                'Author_ID': aid,
                                'Full Name': '-',
                                'Affiliation': '-',
                                'Total Documents': 0,
                                'h-Index': 0,
                                'Main Subject Areas': '-',
                                'Dominant Research Topics': '-',
                                'Status': f'Failed ({type(e).__name__})'
                            })
                        
                        progress_bar.progress(idx / total_data)
                        time.sleep(0.5)
                        
                    status_text.success("All Data Processed Successfully.")
                    
                    # Display results table
                    df_hasil = pd.DataFrame(hasil_pencarian)
                    st.subheader("Extracted Expertise Results")
                    st.dataframe(df_hasil, use_container_width=True)
                    
                    # Download button for Excel output
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        df_hasil.to_excel(writer, index=False, sheet_name='Scopus_Results')
                    excel_bytes = output.getvalue()
                    
                    st.download_button(
                        label="Download Results as Excel (.xlsx)",
                        data=excel_bytes,
                        file_name="Scopus_Expertise_Results.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        type="primary"
                    )
        except Exception as e:
            st.error(f"Error reading Excel file: {e}")
