import streamlit as st
import pandas as pd
import sqlite3
import datetime
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, numbers
from openpyxl.utils.dataframe import dataframe_to_rows

# ====== CHECK FOR EDGE TTS (REQUIRED FOR NATIVE VOICES) ======
EDGE_TTS_AVAILABLE = False
try:
    import edge_tts
    import asyncio
    import tempfile
    import os
    EDGE_TTS_AVAILABLE = True
except ImportError:
    pass

# ----------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------
st.set_page_config(page_title="Excel Advanced Accounting", layout="wide")

# ----------------------------------------------------------------------
# Custom CSS – Blue Theme + Full Table Styling
# ----------------------------------------------------------------------
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background-color: #e6f2ff !important;
    }
    .stApp [data-testid="stAppViewContainer"] {
        background-color: transparent !important;
    }
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #cce5ff !important;
        border-right: 1px solid #99ccff;
    }
    [data-testid="stSidebar"] * {
        color: #003366 !important;
    }
    h1, h2, h3 {
        color: #003366 !important;
    }
    .stTextInput > div > div > input,
    .stTextArea > div > textarea,
    .stSelectbox > div > div {
        background: #ffffff !important;
        color: #003366 !important;
        border: 1px solid #99ccff !important;
        border-radius: 8px !important;
    }
    .stButton > button {
        background: linear-gradient(105deg, #1e88e5 0%, #42a5f5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 40px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        width: 100% !important;
        transition: 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 4px 20px rgba(30, 136, 229, 0.4);
    }
    [data-testid="stMetricValue"] {
        color: #003366 !important;
    }
    .stTabs [data-baseweb="tab-list"] {
        background-color: #cce5ff !important;
        border-radius: 8px !important;
    }
    .stTabs [data-baseweb="tab"] {
        color: #003366 !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1e88e5 !important;
        color: white !important;
        border-radius: 8px !important;
    }

    /* ---- PROFESSIONAL TABLE STYLING (full coverage) ---- */
    div[data-testid="stDataFrame"] {
        border: 1px solid #b0c4de !important;
        border-radius: 4px !important;
        overflow: hidden !important;
    }
    div[data-testid="stDataFrame"] table {
        border-collapse: collapse !important;
        width: 100% !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        font-size: 14px !important;
        border: 1px solid #b0c4de !important;
        background-color: #ffffff !important;
    }
    /* Header row */
    div[data-testid="stDataFrame"] thead tr th {
        background-color: #1e88e5 !important;
        color: white !important;
        font-weight: bold !important;
        text-align: center !important;
        padding: 8px 6px !important;
        border: 1px solid #1565c0 !important;
    }
    /* Data rows – alternating colors */
    div[data-testid="stDataFrame"] tbody tr:nth-child(even) {
        background-color: #f0f8ff !important;
    }
    div[data-testid="stDataFrame"] tbody tr:nth-child(odd) {
        background-color: #ffffff !important;
    }
    div[data-testid="stDataFrame"] tbody tr:hover {
        background-color: #d9eaf7 !important;
    }
    /* Cells */
    div[data-testid="stDataFrame"] td {
        padding: 6px 8px !important;
        border: 1px solid #b0c4de !important;
        text-align: right !important;
        color: #1a2a3a !important;
    }
    div[data-testid="stDataFrame"] td:first-child {
        text-align: left !important;
    }
    div[data-testid="stDataFrame"] td:nth-child(3) {  /* Description column */
        text-align: left !important;
    }
    /* Remove any default yellow highlight */
    div[data-testid="stDataFrame"] tbody tr:focus,
    div[data-testid="stDataFrame"] tbody tr:active,
    div[data-testid="stDataFrame"] td:focus,
    div[data-testid="stDataFrame"] td:active {
        background-color: inherit !important;
    }
    .stDataFrameSelectedRow {
        background-color: #d9eaf7 !important;
    }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Full translations for UI and Voice explanation
# ----------------------------------------------------------------------
translations = {
    "en": {
        "app_title": "Excel Advanced Accounting",
        "subtitle": "Professional Accounting & Loan Management Suite",
        "login_title": "🔐 Login",
        "login_password": "Enter password to unlock",
        "wrong_password": "Wrong password. Access denied.",
        "logout": "🚪 Logout",
        "dashboard": "📊 Dashboard",
        "cash_tab": "💰 Cash In/Out",
        "loans_tab": "🏦 Loans",
        "reports_tab": "📄 Reports",
        "reconciliation_tab": "📋 Reconciliation Ledger",
        "current_balance": "Current Cash Balance",
        "current_balance_htg": "Current Cash Balance (HTG)",
        "recent_transactions": "Recent Cash Transactions",
        "active_loans": "Active Loans",
        "no_active_loans": "No active loans.",
        "add_transaction": "Add Transaction",
        "date": "Date",
        "type": "Type",
        "income": "Income",
        "expense": "Expense",
        "category": "Category (e.g., Sales, Rent, Salary)",
        "description": "Description",
        "amount": "Amount ($)",
        "amount_htg": "Amount (HTG)",
        "transaction_added": "Transaction added!",
        "transaction_history": "Transaction History",
        "download_excel": "📥 Download Excel",
        "loan_management": "Loan Management",
        "add_new_loan": "➕ Add New Loan",
        "borrower_name": "Borrower Name",
        "loan_amount": "Loan Amount ($)",
        "loan_amount_htg": "Loan Amount (HTG)",
        "start_date": "Start Date",
        "interest_rate": "Interest Rate (%)",
        "payment_frequency": "Payment Frequency",
        "weekly": "Weekly",
        "monthly": "Monthly",
        "payment_amount": "Payment Amount ($)",
        "payment_amount_htg": "Payment Amount (HTG)",
        "total_payments": "Total Number of Payments",
        "create_loan": "Create Loan",
        "loan_created": "Loan created!",
        "all_loans": "All Loans",
        "select_loan": "Select Loan ID to record payment or view details",
        "remaining_payments": "Remaining payments",
        "status": "Status",
        "record_payment": "Record Payment",
        "payment_date": "Payment Date",
        "payment_recorded": "Payment recorded!",
        "payment_history": "Payment History",
        "no_loans": "No loans yet. Add a loan above.",
        "generate_reports": "Generate Professional Reports",
        "report_type": "Report Type",
        "cash_flow_statement": "Cash Flow Statement",
        "loan_status_report": "Loan Status Report",
        "payment_history_report": "Payment History Report",
        "generate": "Generate",
        "from_date": "Start Date",
        "to_date": "End Date",
        "total_income": "Total Income",
        "total_expense": "Total Expense",
        "net_cash_flow": "Net Cash Flow",
        "filter_by_status": "Filter by status",
        "all": "All",
        "active": "active",
        "completed": "completed",
        "no_data": "No data available.",
        "select_loan_for_history": "Select Loan",
        "created_by": "Python Developer",
        "reconciliation_title": "Reconciliation July - 2026",
        "exchange_rate": "Exchange Rate: 1 USD = 100 HTG",
        "balance_usd": "Balance USD",
        "balance_htg": "Balance HTG",
        "credit_cash_in": "Credit (Cash In HTG)",
        "credit_cash_in_usd": "Credit (Cash In USD)",
        "description_item": "Description / Item Details",
        "qty": "qty",
        "currency_htg": "Currency Unit (HTG)",
        "unit_htg": "unit htg",
        "unit_usd": "unit usd",
        "total_htg": "total htg",
        "total_usd": "total usd",
        "add_entry": "Add Entry",
        "credit": "Credit (Cash In HTG)",
        "qty_input": "Quantity",
        "unit_htg_input": "Unit Price (HTG)",
        "description_input": "Description / Item Details",
        "entry_added": "Entry added!",
        "download_reconciliation": "📥 Download Excel",
        "starting_balance_usd": "Starting Balance (USD)",
        "starting_balance_htg": "Starting Balance (HTG)",
        "initial_balance_forwarded": "Balance Forwarded from February",
        "delete_entry": "Delete Entry",
        "cannot_delete_balance": "Cannot delete the initial balance row.",
        "net_balance_htg": "Net Balance (HTG)",
        "net_balance_usd": "Net Balance (USD)",
        # Voice
        "voice_welcome": "Welcome to Excel Advanced Accounting.",
        "voice_ledger": "Here is your Reconciliation Ledger summary.",
        "voice_entries": "Currently, you have {count} entries.",
        "voice_credit": "Total cash in is {credit_htg:,.2f} HTG, which is {credit_usd:,.2f} USD.",
        "voice_expenses": "Total expenses are {expense_htg:,.2f} HTG and {expense_usd:,.2f} USD.",
        "voice_balance": "Your current net balance is {balance_htg:,.2f} HTG and {balance_usd:,.2f} USD. This is calculated as total cash in minus total expenses.",
        "voice_how_it_works": "Remember: each cash‑in increases your net balance, and each purchase decreases it. The system automatically converts HTG to USD using the exchange rate of 1 USD = 100 HTG.",
        "voice_closing": "You can download a professionally formatted Excel report with one click. This application was built by Gesner Deslandes, Chief Engineer at GlobalInternet.py."
    },
    "fr": {
        "net_balance_htg": "Solde Net (HTG)",
        "net_balance_usd": "Solde Net (USD)",
        # ... (other translations omitted for brevity; keep your existing ones)
    },
    "es": {
        "net_balance_htg": "Saldo Neto (HTG)",
        "net_balance_usd": "Saldo Neto (USD)",
        # ... (other translations)
    }
}

def _(key):
    lang = st.session_state.get("language", "en")
    return translations[lang].get(key, key)

# ----------------------------------------------------------------------
# Authentication
# ----------------------------------------------------------------------
def get_expected_password():
    try:
        return st.secrets["password"]
    except KeyError:
        return "20082010"

def check_password():
    def password_entered():
        if st.session_state["password"] == get_expected_password():
            st.session_state["authenticated"] = True
            del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            st.image(
                "https://raw.githubusercontent.com/Deslandes1/Accountant-Excel-Advanced-AI-/main/Gemini_Generated_Image_8s108y8s108y8s10.png",
                width=100
            )
        with col2:
            st.markdown(f"<h1 style='text-align: center;'>{_('app_title')}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center;'><em>{_('subtitle')}</em></p>", unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div style='text-align: right;'>
                <b>GlobalInternet.py</b><br>
                Gesner Deslandes<br>
                Chief Engineer at GlobalInternet.py
            </div>
            """, unsafe_allow_html=True)
        st.divider()
        st.text_input(_("login_password"), type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["authenticated"]:
        st.text_input(_("login_password"), type="password", on_change=password_entered, key="password")
        st.error(_("wrong_password"))
        return False
    else:
        return True

def logout():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# ----------------------------------------------------------------------
# Database setup
# ----------------------------------------------------------------------
def init_db():
    conn = sqlite3.connect("accounting.db")
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS cash_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        type TEXT,
        category TEXT,
        description TEXT,
        amount REAL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        borrower TEXT,
        amount REAL,
        start_date TEXT,
        interest_rate REAL,
        payment_frequency TEXT,
        payment_amount REAL,
        total_payments INTEGER,
        payments_made INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active'
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS loan_payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        loan_id INTEGER,
        payment_date TEXT,
        amount REAL,
        FOREIGN KEY (loan_id) REFERENCES loans (id)
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS reconciliation_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        credit REAL DEFAULT 0,
        description TEXT,
        qty REAL DEFAULT 0,
        unit_htg REAL DEFAULT 0,
        unit_usd REAL DEFAULT 0,
        total_htg REAL DEFAULT 0,
        total_usd REAL DEFAULT 0
    )""")
    # Only insert demo data if table is empty
    c.execute("SELECT COUNT(*) FROM reconciliation_entries")
    if c.fetchone()[0] == 0:
        demo_entries = [
            ("2023-03-01", "Cash in from operation (HTG)", 300000.00, 0, 0, 0, 0, 0),
            ("2023-03-02", "Office supplies - paper & pens", 0, 20, 150.00, 1.50, 3000.00, 30.00),
            ("2023-03-03", "Equipment rental - projector", 0, 5, 500.00, 5.00, 2500.00, 25.00),
            ("2023-03-05", "Fuel for delivery vehicles", 0, 40, 125.00, 1.25, 5000.00, 50.00),
            ("2023-03-07", "Cash in from sales (HTG)", 120000.00, 0, 0, 0, 0, 0),
            ("2023-03-10", "Utility bills - electricity", 0, 0, 0, 0, 4000.00, 40.00),
            ("2023-03-12", "Transportation - maintenance", 0, 2, 800.00, 8.00, 1600.00, 16.00)
        ]
        for entry in demo_entries:
            c.execute("""INSERT INTO reconciliation_entries (date, description, credit, qty, unit_htg, unit_usd, total_htg, total_usd)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", entry)
        conn.commit()
    conn.commit()
    conn.close()

init_db()

# ====== Reset ledger function ======
def reset_ledger():
    conn = sqlite3.connect("accounting.db")
    c = conn.cursor()
    c.execute("DELETE FROM reconciliation_entries")
    conn.commit()
    conn.close()
    st.cache_data.clear()

# ----------------------------------------------------------------------
# Helper functions (keep all existing ones)
# ----------------------------------------------------------------------
# ... (all the helper functions: add_cash_transaction, get_cash_balance, get_cash_flow, add_loan, record_loan_payment, get_loans, get_loan_payments, get_reconciliation_entries, add_reconciliation_entry, delete_reconciliation_entry, generate_pdf_report, usd_to_htg, etc.) ...

# For brevity, I'll omit the full helpers here; they are identical to the previous version.
# Please use the same helper functions as before – they already compute net_htg and net_usd correctly.

# ====== Voice functions ======
def generate_voice_explanation(entries, net_htg, net_usd, lang='en'):
    # same as before
    pass

def text_to_speech(text, lang='en'):
    # same as before
    pass

def play_voice_explanation():
    # same as before
    pass

# ----------------------------------------------------------------------
# Main UI (only the Reconciliation tab is shown here; the rest is unchanged)
# ----------------------------------------------------------------------
if not check_password():
    st.stop()

# Language selector, sidebar, etc. (keep as is)

# Tabs
tab1, tab2, tab3, tab4, tab5 = st.tabs([_("dashboard"), _("cash_tab"), _("loans_tab"), _("reports_tab"), _("reconciliation_tab")])

# ---- Reconciliation Ledger ----
with tab5:
    st.header(_("reconciliation_title"))
    st.caption(_("exchange_rate"))
    st.info("💡 " + _("How it works:") + " " + _("Enter Credit (Cash In) in HTG. The system converts it to USD at 1 USD = 100 HTG. Expenses reduce the net balance."))

    # ---- RESET BUTTON ----
    col_reset, _ = st.columns([1, 3])
    with col_reset:
        if st.button("🗑️ Reset Ledger (Clear All Entries)", use_container_width=True):
            if st.checkbox("⚠️ Confirm: delete ALL entries?"):
                reset_ledger()
                st.success("Ledger reset! Start adding your own entries.")
                st.rerun()
            else:
                st.warning("Please confirm the deletion.")

    df_rec = get_reconciliation_entries()
    
    if not df_rec.empty:
        last_row = df_rec.iloc[-1]
        net_usd = last_row['net_usd']
        net_htg = last_row['net_htg']
        col1, col2 = st.columns(2)
        with col1:
            st.metric(_("net_balance_usd"), f"${net_usd:,.2f}")
        with col2:
            st.metric(_("net_balance_htg"), f"G {net_htg:,.2f}")

        # Summary
        st.subheader("📊 Cash In / Expenses Summary")
        credit_total_htg = df_rec['credit'].sum()
        expense_total_htg = df_rec['total_htg'].sum()
        net_htg_summary = credit_total_htg - expense_total_htg

        credit_total_usd = credit_total_htg / EXCHANGE_RATE
        expense_total_usd = expense_total_htg / EXCHANGE_RATE
        net_usd_summary = credit_total_usd - expense_total_usd

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Total Cash In (HTG)", f"G {credit_total_htg:,.2f}")
            st.metric("💰 Total Cash In (USD)", f"${credit_total_usd:,.2f}")
        with col2:
            st.metric("💸 Total Expenses (HTG)", f"G {expense_total_htg:,.2f}")
            st.metric("💸 Total Expenses (USD)", f"${expense_total_usd:,.2f}")
        with col3:
            st.metric("📊 Net Balance (HTG)", f"G {net_htg_summary:,.2f}", delta=f"{net_htg_summary:,.2f}")
            st.metric("📊 Net Balance (USD)", f"${net_usd_summary:,.2f}", delta=f"{net_usd_summary:,.2f}")

        # Manual calculator
        st.markdown("---")
        st.subheader("🧮 Quick Cash Calculator (Manual Entry)")
        # ... (calculator code as before)

    # Table and add entry form (same as before, with net_htg/net_usd columns)

    # Delete entry (same)

    # Download Excel (same)
