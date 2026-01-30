import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pdfplumber
import re

# ==============================================================================
# 1. CONFIGURATION & BRANDING
# ==============================================================================

company_name = "FLEETGUARD AUDIT SYSTEMS"
st.set_page_config(
    page_title=f"{company_name} | Compliance Audit",
    page_icon="🚛",
    layout="wide"
)

# --- CSS THEME ---
brand_color = "#004481"
bg_color = "#F5F7FA"

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; }}
    h1, h2, h3 {{ color: {brand_color} !important; font-family: 'Arial', sans-serif; }}
    [data-testid="stSidebar"] {{ background-color: {brand_color}; }}
    [data-testid="stSidebar"] > div:first-child {{ background-color: {brand_color}; }}
    [data-testid="stSidebar"] .css-17lntkn {{ color: white; }}
    div[data-testid="stMetricValue"] {{ color: {brand_color}; }}
    .health-pass {{ color: green; font-weight: bold; }}
    .health-fail {{ color: red; font-weight: bold; }}
    </style>
""", unsafe_allow_html=True)

# --- HEADER ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        st.image("logo.png", width=120)
    except:
        st.write("📂")

with col_title:
    st.markdown(f"<h1 style='margin-top: 0px;'>{company_name}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='color: #666; margin-top: -15px;'>Vehicle Compliance Audit & Lubrication Scheduler</h4>", unsafe_allow_html=True)

st.markdown("---")


# ==============================================================================
# 2. SMART HELPER FUNCTIONS
# ==============================================================================

def clean_text(text):
    """Removes spaces, newlines, and special chars to match columns easily."""
    if not isinstance(text, str): return ""
    return re.sub(r'[\n\r\s]+', '', text).lower()

def find_column_name(df, keywords):
    """Finds the column in the DataFrame that matches any of the keywords."""
    if df is None or df.empty:
        return None
    for col in df.columns:
        clean_col = clean_text(col)
        for kw in keywords:
            if kw in clean_col:
                return col
    return None

def read_input_file(uploaded_file):
    """Reads PDF, Excel, or CSV. Handles duplicate headers automatically."""
    try:
        if uploaded_file.name.endswith('.pdf'):
            all_tables = []
            with pdfplumber.open(uploaded_file) as pdf:
                for page in pdf.pages:
                    table = page.extract_table()
                    if table:
                        all_tables.extend(table)
            
            if not all_tables:
                return pd.DataFrame()

            # --- FIX DUPLICATE HEADERS ---
            header = all_tables[0]
            new_header = []
            col_counts = {}
            
            for i, col in enumerate(header):
                col_name = str(col).strip() if col is not None else f"Col_{i}"
                if not col_name: col_name = f"Col_{i}"
                
                # Handle Duplicates by appending _1, _2
                if col_name in col_counts:
                    col_counts[col_name] += 1
                    col_name = f"{col_name}_{col_counts[col_name]}"
                else:
                    col_counts[col_name] = 0
                new_header.append(col_name)
            
            df = pd.DataFrame(all_tables[1:], columns=new_header)
            df = df.dropna(axis=1, how='all') # Drop completely empty columns
            df = df.dropna(how='all')         # Drop completely empty rows
            return df

        elif uploaded_file.name.endswith('.xlsx') or uploaded_file.name.endswith('.xls'):
            return pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        else:
            return None
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return pd.DataFrame()

def get_special_greasing_requirements(model, item_name):
    """Step 2: Special Greasing Rules."""
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


# ==============================================================================
# 3. SIDEBAR
# ==============================================================================
with st.sidebar:
    st.header("🚧 Control Panel")
    current_km = st.number_input("Current Odometer (KM)", min_value=0, value=10000)
    current_hrs = st.number_input("Current Engine Hours", min_value=0, value=500)
    vin_input = st.text_input("VIN", "TEST-VIN-123")
    model_input = st.text_input("Model No (e.g., 3723R)", "3723R").upper()
    sale_date = st.date_input("Date of Sale", datetime(2023, 1, 1))


# ==============================================================================
# 4. MAIN APP LOGIC
# ==============================================================================

col1, col2 = st.columns(2)
with col1: sap_file = st.file_uploader("📂 SAP History (PDF/Excel)", type=['pdf', 'xlsx', 'csv'])
with col2: chart_file = st.file_uploader("📂 Lubrication Schedule (PDF/Excel)", type=['pdf', 'xlsx', 'csv'])

if sap_file and chart_file:
    
    try:
        # --- STEP 1: READ DATA ---
        df_sap = read_input_file(sap_file)
        df_chart = read_input_file(chart_file)

        if df_sap.empty or df_chart.empty:
            st.error("⚠️ One of the files appears to be empty or could not be read.")
        else:
            # --- STEP 2: AUTO-DETECT COLUMNS ---
            # SAP Columns
            sap_date_col = find_column_name(df_sap, ['date', 'time'])
            sap_km_col = find_column_name(df_sap, ['km', 'kilo', 'odometer', 'reading'])
            sap_item_col = find_column_name(df_sap, ['description', 'item', 'part', 'activity', 'work'])

            # Chart Columns
            chart_item_col = find_column_name(df_chart, ['lubrication', 'name', 'item', 'description', 'point'])
            chart_int_km_col = find_column_name(df_chart, ['intervalkm', 'interval km', 'frequency', 'km'])
            chart_int_mon_col = find_column_name(df_chart, ['intervalmonths', 'interval months', 'month', 'months'])

            # --- STEP 3: SYSTEM HEALTH CHECK (Visual Feedback) ---
            st.subheader("🔍 System Health Check")
            c1, c2, c3 = st.columns(3)
            
            # SAP Health
            with c1:
                st.markdown("**SAP History Columns Found:**")
                st.markdown(f"- Date: <span class='{'health-pass' if sap_date_col else 'health-fail'}'>{sap_date_col if sap_date_col else 'NOT FOUND'}</span>", unsafe_allow_html=True)
                st.markdown(f"- KM: <span class='{'health-pass' if sap_km_col else 'health-fail'}'>{sap_km_col if sap_km_col else 'NOT FOUND'}</span>", unsafe_allow_html=True)
                st.markdown(f"- Item: <span class='{'health-pass' if sap_item_col else 'health-fail'}'>{sap_item_col if sap_item_col else 'NOT FOUND'}</span>", unsafe_allow_html=True)

            # Schedule Health
            with c2:
                st.markdown("**Schedule Columns Found:**")
                st.markdown(f"- Item Name: <span class='{'health-pass' if chart_item_col else 'health-fail'}'>{chart_item_col if chart_item_col else 'NOT FOUND'}</span>", unsafe_allow_html=True)
                st.markdown(f"- Int. KM: <span class='{'health-pass' if chart_int_km_col else 'health-fail'}'>{chart_int_km_col if chart_int_km_col else 'NOT FOUND'}</span>", unsafe_allow_html=True)
                st.markdown(f"- Int. Month: <span class='{'health-pass' if chart_int_mon_col else 'health-fail'}'>{chart_int_mon_col if chart_int_mon_col else 'NOT FOUND'}</span>", unsafe_allow_html=True)

            # Raw Data Preview (For debugging)
            with c3:
                with st.expander("View Raw PDF Data"):
                    st.write("Schedule Cols:", list(df_chart.columns))
                    st.dataframe(df_chart.head(2))

            # --- CRITICAL STOP ---
            if not all([sap_item_col, chart_item_col]):
                st.error("🛑 STOP: Critical columns are missing. Please check the 'System Health Check' above. The column names in your PDF might not match the expected keywords.")
                st.stop()

            # --- STEP 4: PREPARE DATA ---
            if sap_date_col:
                df_sap[sap_date_col] = pd.to_datetime(df_sap[sap_date_col], errors='coerce')
                df_sap = df_sap.dropna(subset=[sap_date_col])
            
            if sap_item_col:
                df_sap[sap_item_col] = df_sap[sap_item_col].astype(str).str.upper()

            # --- STEP 5: AUDIT LOOP ---
            results = []
            missing_records = []

            for _, row in df_chart.iterrows():
                # Get Item Name
                item = str(row[chart_item_col]).strip().upper()
                if not item or item == 'NAN': continue

                # Get Intervals
                int_km = int(row[chart_int_km_col]) if chart_int_km_col and pd.notna(row[chart_int_km_col]) else 0
                int_months = int(row[chart_int_mon_col]) if chart_int_mon_col and pd.notna(row[chart_int_mon_col]) else 0

                # Special Rules
                part_no, qty = get_special_greasing_requirements(model_input, item)

                # Search History
                last_done_date = "Not Recorded"
                last_done_km = 0
                status = "OK"

                if sap_item_col and sap_date_col:
                    matches = df_sap[df_sap[sap_item_col].str.contains(item, case=False, na=False)]
                    
                    if not matches.empty:
                        last_record = matches.sort_values(by=sap_date_col, ascending=False).iloc[0]
                        last_done_date = last_record[sap_date_col]
                        if sap_km_col:
                            try: last_done_km = float(last_record[sap_km_col])
                            except: last_done_km = 0
                        
                        next_due_km = last_done_km + int_km
                        next_due_date = last_done_date + relativedelta(months=int_months)
                    else:
                        missing_records.append(item)
                        next_due_km = int_km
                        next_due_date = sale_date + relativedelta(months=int_months)
                else:
                    missing_records.append(item)
                    next_due_km = int_km
                    next_due_date = sale_date + relativedelta(months=int_months)

                # --- STATUS LOGIC ---
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
                    "Last Done KM": int(last_done_km),
                    "Interval KM": int_km,
                    "Next Due KM": int(next_due_km),
                    "Next Due Date": next_due_date,
                    "Current Status": status
                })

            df_results = pd.DataFrame(results)

            # --- STEP 6: FINAL OUTPUT ---
            if not df_results.empty:
                st.subheader("📊 Compliance Audit Table")
                def color_status(val):
                    if 'OVERDUE' in str(val): return 'background-color: #ffcccc; color: black; font-weight: bold'
                    if 'DUE SOON' in str(val): return 'background-color: #fff3cd; color: black; font-weight: bold'
                    return 'background-color: #d4edda; color: black'
                
                st.dataframe(df_results.style.applymap(color_status, subset=['Current Status']))

                st.subheader("📝 Summary")
                c1, c2, c3 = st.columns(3)
                pending = len(df_results[df_results['Current Status'] != 'OK'])
                c1.metric("Pending", pending)
                c2.metric("Next Major", int(df_results['Next Due KM'].max()))
                c3.metric("Status", "COMPLIANT" if pending == 0 else "NON-COMPLIANT")

                if missing_records:
                    st.warning(f"⚠️ Missing History: {', '.join(missing_records)}")
            else:
                st.warning("No results generated. Check column matching.")

    except Exception as e:
        st.error(f"Unexpected Error: {e}")
        st.write("If this error persists, please check the 'System Health Check' section above.")

else:
    st.info("👈 Please upload both documents to begin.")