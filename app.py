import streamlit as st
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pdfplumber

# ==============================================================================
# 1. CONFIGURATION & BRANDING
# ==============================================================================

company_name = "FLEETGUARD AUDIT SYSTEMS"  # CHANGE YOUR COMPANY NAME HERE
st.set_page_config(
    page_title=f"{company_name} | Compliance Audit",
    page_icon="🚛",
    layout="wide"
)

# --- CUSTOM CSS THEME ---
brand_color = "#004481"  # Your Brand Color (Blue)
bg_color = "#F5F7FA"     # Background Color

st.markdown(f"""
    <style>
    .stApp {{ background-color: {bg_color}; }}
    h1, h2, h3 {{ color: {brand_color} !important; font-family: 'Arial', sans-serif; font-weight: bold;}}
    [data-testid="stSidebar"] {{ background-color: {brand_color}; }}
    [data-testid="stSidebar"] > div:first-child {{ background-color: {brand_color}; }}
    [data-testid="stSidebar"] .css-17lntkn, [data-testid="stSidebar"] .css-1d391kg {{ color: white; }}
    div[data-testid="stMetricValue"] {{ color: {brand_color}; font-size: 24px;}}
    </style>
""", unsafe_allow_html=True)

# --- HEADER LOGO & TITLE ---
col_logo, col_title = st.columns([1, 5])
with col_logo:
    try:
        st.image("logo.png", width=120) # Ensure logo.png is in the same folder
    except:
        st.write("📂")

with col_title:
    st.markdown(f"<h1 style='margin-top: 10px;'>{company_name}</h1>", unsafe_allow_html=True)
    st.markdown(f"<h3 style='color: #666; margin-top: -20px;'>Vehicle Compliance Audit & Lubrication Scheduler</h3>", unsafe_allow_html=True)

st.markdown("---")


# ==============================================================================
# 2. HELPER FUNCTIONS
# ==============================================================================

def find_column_name(df, keywords):
    """Smart Search: Finds the column name in a DataFrame that contains one of the keywords."""
    if df is None or df.empty:
        return None
    for col in df.columns:
        col_lower = str(col).lower()
        for kw in keywords:
            if kw in col_lower:
                return col
    return None

def read_input_file(uploaded_file):
    """Reads PDF, Excel, or CSV and returns a clean DataFrame."""
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
                
                # Handle Duplicates
                if col_name in col_counts:
                    col_counts[col_name] += 1
                    col_name = f"{col_name}_{col_counts[col_name]}"
                else:
                    col_counts[col_name] = 0
                new_header.append(col_name)
            
            df = pd.DataFrame(all_tables[1:], columns=new_header)
            df = df.dropna(axis=1, how='all') # Drop empty columns
            df = df.dropna(how='all')         # Drop empty rows
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
    """Step 2: Special Greasing Rules for Models ending in R & T."""
    if not (model.endswith('R') or model.endswith('T')):
        return None, None

    item_name = str(item_name).upper().strip()
    
    # Specific Exceptions
    if model in ['1617R', '1917R', '1917RD', '1917RT']:
        if 'FRONT HUB' in item_name: return 'A4009974046', 2
        elif 'REAR HUB' in item_name: return 'A4003571051', 2
        elif 'REAR AXLE II' in item_name or 'TAG AXLE' in item_name: return 'A4003570951', 2
        return None, None

    # Standard R & T Rules
    if 'FRONT HUB' in item_name: return 'A4009974046', 2
    elif 'STEER HUB' in item_name:
        if model in ['3723R', '4228R', '4828R']: return 'A4009973946', 2
        else: return None, None
    elif 'PUSHER AXLE HUB' in item_name: return 'A4009973946', 2
    elif 'REAR AXLE HUB' in item_name: return 'A4009976546', 2
    elif 'REAR AXLE II' in item_name or 'TAG AXLE' in item_name: return 'A4009974146', 2
    
    return None, None


# ==============================================================================
# 3. SIDEBAR INPUTS
# ==============================================================================
with st.sidebar:
    st.header("🚧 Control Panel")
    st.subheader("1. Current Vehicle Status")
    current_km = st.number_input("Current Odometer (KM)", min_value=0, value=10000)
    current_hrs = st.number_input("Current Engine Hours", min_value=0, value=500)
    
    st.subheader("2. Vehicle Details")
    vin_input = st.text_input("VIN", "TEST-VIN-123")
    model_input = st.text_input("Model No (e.g., 3723R)", "3723R").upper()
    sale_date = st.date_input("Date of Sale", datetime(2023, 1, 1))


# ==============================================================================
# 4. FILE UPLOADERS
# ==============================================================================
col1, col2 = st.columns(2)
with col1:
    sap_file = st.file_uploader("📂 Upload SAP History (PDF/Excel)", type=['pdf', 'xlsx', 'csv'])
with col2:
    chart_file = st.file_uploader("📂 Upload Lubrication Schedule (PDF/Excel)", type=['pdf', 'xlsx', 'csv'])


# ==============================================================================
# 5. MAIN LOGIC PROCESSING
# ==============================================================================
if sap_file and chart_file:
    try:
        # --- LOAD DATA ---
        df_sap = read_input_file(sap_file)
        df_chart = read_input_file(chart_file)

        if df_sap.empty or df_chart.empty:
            st.error("Could not extract data. Check file formats.")
        else:
            # --- DEBUG VIEW (Helpful for PDFs) ---
            with st.expander("🔍 View Extracted Data (Check if columns are correct)"):
                c1, c2 = st.columns(2)
                c1.write("**SAP History Columns:**")
                c1.write(list(df_sap.columns))
                c1.dataframe(df_sap.head())
                
                c2.write("**Schedule Columns:**")
                c2.write(list(df_chart.columns))
                c2.dataframe(df_chart.head())

            # --- SMART COLUMN MAPPING ---
            # 1. SAP Columns
            sap_date_col = find_column_name(df_sap, ['date', 'time'])
            sap_km_col = find_column_name(df_sap, ['km', 'kilo', 'odometer', 'reading'])
            sap_item_col = find_column_name(df_sap, ['description', 'item', 'part', 'activity'])
            
            # 2. Schedule Columns
            chart_item_col = find_column_name(df_chart, ['lubrication', 'name', 'item', 'description'])
            chart_int_km_col = find_column_name(df_chart, ['interval km', 'km interval', 'frequency km'])
            chart_int_mon_col = find_column_name(df_chart, ['interval months', 'month interval', 'months'])

            # --- PREPARE SAP DATA ---
            if sap_date_col:
                df_sap[sap_date_col] = pd.to_datetime(df_sap[sap_date_col], errors='coerce')
                df_sap = df_sap.dropna(subset=[sap_date_col]) # Remove rows with invalid dates
            if sap_item_col:
                df_sap[sap_item_col] = df_sap[sap_item_col].astype(str).str.upper()

            # --- AUDIT LOOP ---
            results = []
            missing_records = []

            for _, row in df_chart.iterrows():
                # Get Item Name
                if not chart_item_col: continue
                item = str(row[chart_item_col]).strip().upper()
                if not item or item == 'NAN': continue

                # Get Intervals
                int_km = int(row[chart_int_km_col]) if chart_int_km_col and pd.notna(row[chart_int_km_col]) else 0
                int_months = int(row[chart_int_mon_col]) if chart_int_mon_col and pd.notna(row[chart_int_mon_col]) else 0

                # Special Rules Check
                part_no, qty = get_special_greasing_requirements(model_input, item)

                # Search History
                last_done_date = "Not Recorded"
                last_done_km = 0
                status = "OK"

                if sap_item_col and sap_date_col:
                    # Find matches
                    matches = df_sap[df_sap[sap_item_col].str.contains(item, case=False, na=False)]
                    
                    if not matches.empty:
                        # Get most recent
                        last_record = matches.sort_values(by=sap_date_col, ascending=False).iloc[0]
                        last_done_date = last_record[sap_date_col]
                        
                        if sap_km_col:
                            try:
                                last_done_km = float(last_record[sap_km_col])
                            except:
                                last_done_km = 0

                        # Calculate Next Due
                        next_due_km = last_done_km + int_km
                        next_due_date = last_done_date + relativedelta(months=int_months)
                    else:
                        # Missing Data Logic
                        missing_records.append(item)
                        next_due_km = int_km
                        next_due_date = sale_date + relativedelta(months=int_months)
                else:
                     missing_records.append(item)
                     next_due_km = int_km
                     next_due_date = sale_date + relativedelta(months=int_months)

                # --- STATUS CALCULATION ---
                is_overdue_km = current_km > next_due_km
                is_overdue_date = datetime.now() > next_due_date
                
                due_soon_km = next_due_km * 0.90
                due_soon_date = next_due_date - relativedelta(months=1)
                
                is_due_soon_km = current_km >= due_soon_km
                is_due_soon_date = datetime.now() >= due_soon_date

                if is_overdue_km and is_overdue_date:
                    status = "OVERDUE"
                elif is_due_soon_km or is_due_soon_date:
                    status = "DUE SOON"
                else:
                    status = "OK"

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

            # --- DISPLAY RESULTS ---
            st.subheader("📊 Compliance Audit Table")
            
            def color_status(val):
                if 'OVERDUE' in str(val): return 'background-color: #ffcccc; color: black; font-weight: bold'
                if 'DUE SOON' in str(val): return 'background-color: #fff3cd; color: black; font-weight: bold'
                return 'background-color: #d4edda; color: black'

            st.dataframe(df_results.style.applymap(color_status, subset=['Current Status']))

            # --- SUMMARY ---
            st.subheader("📝 Summary & Errors")
            
            c1, c2, c3 = st.columns(3)
            pending = len(df_results[df_results['Current Status'] != 'OK'])
            
            with c1: st.metric("Pending Actions", pending)
            with c2: st.metric("Next Major Service", int(df_results['Next Due KM'].max()))
            with c3: st.metric("Compliance", "COMPLIANT" if pending == 0 else "NON-COMPLIANT")

            if missing_records:
                st.warning(f"⚠️ Items with no history in SAP: {', '.join(missing_records)}")
            else:
                st.success("✅ All items found in history.")

    except Exception as e:
        st.error(f"Critical Error: {e}")
        st.write("Please check the 'View Extracted Data' section above to see how the PDF was read.")

else:
    st.info("👈 Please upload both documents to begin the audit.")