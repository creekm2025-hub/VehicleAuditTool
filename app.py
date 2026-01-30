import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pdfplumber  # <--- New library for reading PDFs

# --- 1. BRANDING & THEME CONFIGURATION ---
company_name = "FLEETGUARD AUDIT SYSTEMS"
st.set_page_config(
    page_title=f"{company_name} | Compliance Audit",
    page_icon="🚛", 
    layout="wide"
)

# --- CUSTOM CSS ---
brand_color = "#004481"
bg_color = "#F5F7FA"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; }}
    h1, h2, h3 {{ color: {brand_color} !important; font-family: 'Arial', sans-serif; }}
    [data-testid="stSidebar"] {{ background-color: {brand_color}; }}
    [data-testid="stSidebar"] > div:first-child {{ background-color: {brand_color}; }}
    [data-testid="stSidebar"] .css-17lntkn, [data-testid="stSidebar"] .css-1d391kg {{ color: white; }}
    div[data-testid="stMetricValue"] {{ color: {brand_color}; }}
    </style>
""", unsafe_allow_html=True)

# --- HEADER WITH LOGO ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        st.image("logo.png", width=120)
    except:
        st.write("")

with col_title:
    st.markdown(f"<h1 style='margin-top: 10px;'>{company_name}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color: #666; margin-top: -20px;'>Vehicle Compliance Audit (PDF Support)</h3>", unsafe_allow_html=True)

st.markdown("---")

# --- SIDEBAR INPUTS ---
with st.sidebar:
    st.header("🚧 Control Panel")
    st.subheader("1. Current Status")
    current_km = st.number_input("Current Odometer (KM)", min_value=0, value=10000)
    current_hrs = st.number_input("Current Engine Hours", min_value=0, value=500)
    st.subheader("2. Vehicle Details")
    vin_input = st.text_input("VIN", "TEST-VIN-123")
    model_input = st.text_input("Model No (e.g., 3723R)", "3723R").upper()
    sale_date = st.date_input("Date of Sale", datetime(2023, 1, 1))

# --- NEW: FILE READING FUNCTION ---
def read_input_file(uploaded_file):
    """Reads Excel, CSV, or PDF and returns a DataFrame"""
    try:
        if uploaded_file.name.endswith('.pdf'):
            # Logic to read PDF
            all_tables = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        all_tables.extend(table)
            
            # Convert list of lists to DataFrame
            if all_tables:
                df = pd.DataFrame(all_tables[1:], columns=all_tables[0]) # Assume first row is header
                # Clean up empty rows
                df = df.dropna(how='all')
                return df
            else:
                return pd.DataFrame()
                
        elif uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            return pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        else:
            return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame()

# --- FILE UPLOADERS (Now accepts PDF) ---
col1, col2 = st.columns(2)
with col1:
    sap_file = st.file_uploader("📂 Upload SAP History (PDF/Excel)", type=['pdf', 'xlsx', 'csv'])
with col2:
    chart_file = st.file_uploader("📂 Upload Lubrication Schedule (PDF/Excel)", type=['pdf', 'xlsx', 'csv'])

# --- SPECIAL GREASING RULES LOGIC ---
def get_special_greasing_requirements(model, item_name):
    if not (model.endswith('R') or model.endswith('T')): return None, None
    item_name = str(item_name).upper().strip()
    
    if model in ['1617R', '1917R', '1917RD', '1917RT']:
        if 'FRONT HUB' in item_name: return 'A4009974046', 2
        elif 'REAR HUB' in item_name: return 'A4003571051', 2
        elif 'REAR AXLE II' in item_name or 'TAG AXLE' in item_name: return 'A4003570951', 2
        return None, None

    if 'FRONT HUB' in item_name: return 'A4009974046', 2
    elif 'STEER HUB' in item_name:
        if model in ['3723R', '4228R', '4828R']: return 'A4009973946', 2
        else: return None, None
    elif 'PUSHER AXLE HUB' in item_name: return 'A4009973946', 2
    elif 'REAR AXLE HUB' in item_name: return 'A4009976546', 2
    elif 'REAR AXLE II' in item_name or 'TAG AXLE' in item_name: return 'A4009974146', 2
    return None, None

# --- MAIN PROCESSING ---
if sap_file and chart_file:
    try:
        # Use the new reading function
        df_sap = read_input_file(sap_file)
        df_chart = read_input_file(chart_file)

        if df_sap.empty or df_chart.empty:
            st.error("Could not extract data from the PDFs. Please ensure the tables are clearly formatted.")
        else:
            # Display raw data for verification (optional, helps debugging PDFs)
            with st.expander("View Extracted Data (Check if PDF read correctly)"):
                st.write("**SAP Data Preview:**")
                st.dataframe(df_sap.head())
                st.write("**Schedule Data Preview:**")
                st.dataframe(df_chart.head())

            # Normalize Dates
            # We look for common date column names in case PDF header differs slightly
            date_col = None
            for col in df_sap.columns:
                if 'date' in str(col).lower():
                    date_col = col
                    break
            
            if date_col:
                df_sap[date_col] = pd.to_datetime(df_sap[date_col], errors='coerce')
            
            results = []
            missing_records = []

            # Try to find the item column
            item_col = None
            for col in df_chart.columns:
                if 'lubrication' in str(col).lower() or 'name' in str(col).lower():
                    item_col = col
                    break
            
            if not item_col:
                st.error("Could not find 'Lubrication Name' column in Schedule PDF. Please check column headers.")
            else:
                for _, row in df_chart.iterrows():
                    item = row[item_col]
                    
                    # Get Intervals (Look for KM, Months columns)
                    int_km = row.get('Interval KM', 0) if 'Interval KM' in row else 0
                    int_hrs = row.get('Interval Hrs', 0) if 'Interval Hrs' in row else 0
                    int_months = row.get('Interval Months', 0) if 'Interval Months' in row else 0

                    # Special Rules
                    part_no, qty = get_special_greasing_requirements(model_input, item)

                    # Search SAP
                    sap_item_col = None
                    for col in df_sap.columns:
                        if 'description' in str(col).lower() or 'item' in str(col).lower():
                            sap_item_col = col
                            break
                    
                    if sap_item_col:
                        # Convert column to string to avoid errors during search
                        df_sap[sap_item_col] = df_sap[sap_item_col].astype(str)
                        item_history = df_sap[df_sap[sap_item_col].str.contains(str(item), case=False, na=False)]
                    else:
                        item_history = pd.DataFrame()

                    last_done_date = None
                    last_done_km = 0
                    last_done_hrs = 0
                    status = "OK"

                    if not item_history.empty:
                        last_record = item_history.sort_values(by=date_col, ascending=False).iloc[0]
                        last_done_date = last_record[date_col]
                        
                        # Try to find KM column
                        km_col = None
                        for col in df_sap.columns:
                            if 'km' in str(col).lower():
                                km_col = col
                                break
                        if km_col:
                            last_done_km = last_record[km_col]
                        
                        next_due_km = last_done_km + int_km
                        next_due_date = last_done_date + relativedelta(months=int_months)
                    else:
                        missing_records.append(item)
                        last_done_date = "Not Recorded"
                        next_due_km = int_km
                        next_due_date = sale_date + relativedelta(months=int_months)

                    # Status Logic
                    is_overdue_km = current_km > next_due_km
                    is_overdue_date = datetime.now() > next_due_date
                    due_soon_km = next_due_km * 0.90
                    due_soon_date = next_due_date - relativedelta(months=1)
                    is_due_soon_km = current_km >= due_soon_km
                    is_due_soon_date = datetime.now() >= due_soon_date

                    if is_overdue_km and is_overdue_date: status = "OVERDUE"
                    elif is_due_soon_km or is_due_soon_date: status = "DUE SOON"

                    results.append({
                        "Lubrication Name": item,
                        "Part No (Special)": part_no if part_no else "-",
                        "Last Done Date": last_done_date,
                        "Last Done KM": last_done_km,
                        "Interval KM": int_km,
                        "Next Due KM": next_due_km,
                        "Next Due Date": next_due_date,
                        "Current Status": status
                    })

                df_results = pd.DataFrame(results)

                # --- OUTPUT SECTION ---
                st.subheader("📊 1. Compliance Audit Table")
                def color_status(val):
                    if 'OVERDUE' in val: return 'background-color: #ffcccc; color: black'
                    if 'DUE SOON' in val: return 'background-color: #fff3cd; color: black'
                    return 'background-color: #d4edda; color: black'
                
                st.dataframe(df_results.style.applymap(color_status, subset=['Current Status']))

                st.subheader("⚠️ 2. SAP Data Errors & Observations")
                if missing_records:
                    st.error(f"Missing Records: {', '.join(missing_records)}")
                else:
                    st.success("All items found in history.")

                st.subheader("📝 3. Summary")
                c1, c2, c3 = st.columns(3)
                pending_count = len(df_results[df_results['Current Status'] != 'OK'])
                with c1: st.metric("Pending Actions", pending_count)
                with c2: st.metric("Next Major Service (KM)", int(df_results['Next Due KM'].max()))
                with c3: st.metric("Overall Compliance", "COMPLIANT" if pending_count == 0 else "NON-COMPLIANT")

    except Exception as e:
        st.error(f"An error occurred: {e}")
else:
    st.info("👈 Please upload both documents (PDF or Excel) to begin.")