import streamlit as st
import pandas as pd
import sqlite3
import datetime
import hashlib
import io
import base64
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet

# ----------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------
st.set_page_config(page_title="Accountant Excel Advanced AI", layout="wide")

# ----------------------------------------------------------------------
# Authentication
# ----------------------------------------------------------------------
def check_password():
    def password_entered():
        if st.session_state["password"] == "20082010":
            st.session_state["authenticated"] = True
            del st.session_state["password"]
        else:
            st.session_state["authenticated"] = False

    if "authenticated" not in st.session_state:
        st.text_input("🔐 Enter password to unlock", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["authenticated"]:
        st.text_input("🔐 Enter password to unlock", type="password", on_change=password_entered, key="password")
        st.error("Wrong password. Access denied.")
        return False
    else:
        return True

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
    conn.commit()
    conn.close()

init_db()

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

def add_cash_transaction(date, trans_type, category, description, amount):
    conn = sqlite3.connect("accounting.db")
    c = conn.cursor()
    c.execute("INSERT INTO cash_transactions (date, type, category, description, amount) VALUES (?,?,?,?,?)",
              (date, trans_type, category, description, amount))
    conn.commit()
    conn.close()

def get_cash_balance():
    conn = sqlite3.connect("accounting.db")
    df = pd.read_sql_query("SELECT type, amount FROM cash_transactions", conn)
    conn.close()
    if df.empty:
        return 0
    income = df[df['type'] == 'Income']['amount'].sum()
    expense = df[df['type'] == 'Expense']['amount'].sum()
    return income - expense

def get_cash_flow(start_date, end_date):
    conn = sqlite3.connect("accounting.db")
    df = pd.read_sql_query("SELECT * FROM cash_transactions WHERE date BETWEEN ? AND ?", conn, params=(start_date, end_date))
    conn.close()
    return df

def add_loan(borrower, amount, start_date, interest_rate, payment_frequency, payment_amount, total_payments):
    conn = sqlite3.connect("accounting.db")
    c = conn.cursor()
    c.execute("""INSERT INTO loans (borrower, amount, start_date, interest_rate, payment_frequency, payment_amount, total_payments)
                 VALUES (?,?,?,?,?,?,?)""",
              (borrower, amount, start_date, interest_rate, payment_frequency, payment_amount, total_payments))
    conn.commit()
    conn.close()

def record_loan_payment(loan_id, payment_date, amount):
    conn = sqlite3.connect("accounting.db")
    c = conn.cursor()
    c.execute("INSERT INTO loan_payments (loan_id, payment_date, amount) VALUES (?,?,?)", (loan_id, payment_date, amount))
    c.execute("UPDATE loans SET payments_made = payments_made + 1 WHERE id = ?", (loan_id,))
    # Check if fully paid
    c.execute("SELECT payments_made, total_payments FROM loans WHERE id = ?", (loan_id,))
    made, total = c.fetchone()
    if made >= total:
        c.execute("UPDATE loans SET status = 'completed' WHERE id = ?", (loan_id,))
    conn.commit()
    conn.close()

def get_loans(status=None):
    conn = sqlite3.connect("accounting.db")
    query = "SELECT * FROM loans"
    if status:
        query += " WHERE status = ?"
        df = pd.read_sql_query(query, conn, params=(status,))
    else:
        df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def get_loan_payments(loan_id):
    conn = sqlite3.connect("accounting.db")
    df = pd.read_sql_query("SELECT * FROM loan_payments WHERE loan_id = ? ORDER BY payment_date", conn, params=(loan_id,))
    conn.close()
    return df

def generate_pdf_report(title, data, columns):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph(title, styles['Title']))
    story.append(Spacer(1, 12))
    if not data.empty:
        table_data = [columns] + data.values.tolist()
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.grey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('BACKGROUND', (0,1), (-1,-1), colors.beige),
            ('GRID', (0,0), (-1,-1), 1, colors.black)
        ]))
        story.append(table)
    else:
        story.append(Paragraph("No data available.", styles['Normal']))
    doc.build(story)
    buffer.seek(0)
    return buffer

# ----------------------------------------------------------------------
# Main UI
# ----------------------------------------------------------------------
if not check_password():
    st.stop()

# Sidebar branding
st.sidebar.image("https://flagcdn.com/w320/ht.png", width=100)
st.sidebar.title("Accountant Excel Advanced AI")
st.sidebar.markdown("**GlobalInternet.py**")
st.sidebar.markdown("Owner: Gesner Deslandes")
st.sidebar.markdown("📧 deslndes78@gmail.com | 📞 (509) 4738-5663")
st.sidebar.markdown("---")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "💰 Cash In/Out", "🏦 Loans", "📄 Reports"])

# ----------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------
with tab1:
    st.header("Financial Dashboard")
    balance = get_cash_balance()
    st.metric("Current Cash Balance", f"${balance:,.2f}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Recent Cash Transactions")
        conn = sqlite3.connect("accounting.db")
        recent_cash = pd.read_sql_query("SELECT date, type, category, description, amount FROM cash_transactions ORDER BY date DESC LIMIT 10", conn)
        conn.close()
        st.dataframe(recent_cash, use_container_width=True)
    with col2:
        st.subheader("Active Loans")
        active_loans = get_loans(status='active')
        if not active_loans.empty:
            st.dataframe(active_loans[['borrower', 'amount', 'payments_made', 'total_payments', 'status']], use_container_width=True)
        else:
            st.info("No active loans.")

# ----------------------------------------------------------------------
# Cash In/Out
# ----------------------------------------------------------------------
with tab2:
    st.header("Cash In / Cash Out")
    with st.form("cash_form"):
        date = st.date_input("Date", value=datetime.date.today())
        trans_type = st.selectbox("Type", ["Income", "Expense"])
        category = st.text_input("Category (e.g., Sales, Rent, Salary)")
        description = st.text_area("Description")
        amount = st.number_input("Amount ($)", min_value=0.01, step=0.01)
        submitted = st.form_submit_button("Add Transaction")
        if submitted:
            add_cash_transaction(str(date), trans_type, category, description, amount)
            st.success("Transaction added!")
            st.rerun()
    
    st.subheader("Transaction History")
    conn = sqlite3.connect("accounting.db")
    cash_df = pd.read_sql_query("SELECT * FROM cash_transactions ORDER BY date DESC", conn)
    conn.close()
    st.dataframe(cash_df, use_container_width=True)
    
    # Export to Excel
    if not cash_df.empty:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            cash_df.to_excel(writer, sheet_name="Cash Transactions", index=False)
        st.download_button("📥 Download Excel", data=output.getvalue(), file_name="cash_transactions.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

# ----------------------------------------------------------------------
# Loans
# ----------------------------------------------------------------------
with tab3:
    st.header("Loan Management")
    with st.expander("➕ Add New Loan"):
        with st.form("loan_form"):
            borrower = st.text_input("Borrower Name")
            amount = st.number_input("Loan Amount ($)", min_value=0.01, step=0.01)
            start_date = st.date_input("Start Date", value=datetime.date.today())
            interest_rate = st.number_input("Interest Rate (%)", min_value=0.0, step=0.1, value=0.0)
            payment_frequency = st.selectbox("Payment Frequency", ["Weekly", "Monthly"])
            payment_amount = st.number_input("Payment Amount ($)", min_value=0.01, step=0.01)
            total_payments = st.number_input("Total Number of Payments", min_value=1, step=1, value=12)
            submitted = st.form_submit_button("Create Loan")
            if submitted:
                add_loan(borrower, amount, str(start_date), interest_rate, payment_frequency, payment_amount, total_payments)
                st.success("Loan created!")
                st.rerun()
    
    st.subheader("All Loans")
    loans_df = get_loans()
    if not loans_df.empty:
        st.dataframe(loans_df[['id', 'borrower', 'amount', 'start_date', 'payment_frequency', 'payment_amount', 'payments_made', 'total_payments', 'status']], use_container_width=True)
        loan_id = st.selectbox("Select Loan ID to record payment or view details", loans_df['id'].tolist())
        loan_data = loans_df[loans_df['id'] == loan_id].iloc[0]
        st.write(f"**Borrower:** {loan_data['borrower']}")
        st.write(f"**Remaining payments:** {loan_data['total_payments'] - loan_data['payments_made']}")
        st.write(f"**Status:** {loan_data['status']}")
        
        if loan_data['status'] == 'active':
            with st.form("payment_form"):
                payment_date = st.date_input("Payment Date", value=datetime.date.today())
                payment_amount = st.number_input("Payment Amount ($)", value=float(loan_data['payment_amount']), step=0.01)
                if st.form_submit_button("Record Payment"):
                    record_loan_payment(loan_id, str(payment_date), payment_amount)
                    st.success("Payment recorded!")
                    st.rerun()
        
        # Payment history
        payments_df = get_loan_payments(loan_id)
        if not payments_df.empty:
            st.subheader("Payment History")
            st.dataframe(payments_df, use_container_width=True)
    else:
        st.info("No loans yet. Add a loan above.")

# ----------------------------------------------------------------------
# Reports
# ----------------------------------------------------------------------
with tab4:
    st.header("Generate Professional Reports")
    report_type = st.selectbox("Report Type", ["Cash Flow Statement", "Loan Status Report", "Payment History Report"])
    
    if report_type == "Cash Flow Statement":
        start_date = st.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=30))
        end_date = st.date_input("End Date", value=datetime.date.today())
        if st.button("Generate Cash Flow Report"):
            df = get_cash_flow(str(start_date), str(end_date))
            st.subheader(f"Cash Flow from {start_date} to {end_date}")
            st.dataframe(df, use_container_width=True)
            total_income = df[df['type'] == 'Income']['amount'].sum()
            total_expense = df[df['type'] == 'Expense']['amount'].sum()
            st.metric("Total Income", f"${total_income:,.2f}")
            st.metric("Total Expense", f"${total_expense:,.2f}")
            st.metric("Net Cash Flow", f"${total_income - total_expense:,.2f}")
            # Export options
            if not df.empty:
                # Excel
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name="Cash Flow", index=False)
                st.download_button("📥 Download Excel", data=output_excel.getvalue(), file_name=f"cash_flow_{start_date}_to_{end_date}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                # PDF
                pdf_buffer = generate_pdf_report(f"Cash Flow Statement {start_date} to {end_date}", df, list(df.columns))
                st.download_button("📄 Download PDF", data=pdf_buffer, file_name=f"cash_flow_{start_date}_to_{end_date}.pdf", mime="application/pdf")
    
    elif report_type == "Loan Status Report":
        status_filter = st.selectbox("Filter by status", ["All", "active", "completed"])
        df = get_loans() if status_filter == "All" else get_loans(status=status_filter)
        if st.button("Generate Loan Report"):
            st.dataframe(df, use_container_width=True)
            if not df.empty:
                output_excel = io.BytesIO()
                with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name="Loans", index=False)
                st.download_button("📥 Download Excel", data=output_excel.getvalue(), file_name="loan_report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                pdf_buffer = generate_pdf_report("Loan Status Report", df, list(df.columns))
                st.download_button("📄 Download PDF", data=pdf_buffer, file_name="loan_report.pdf", mime="application/pdf")
    
    else:  # Payment History Report
        all_loans = get_loans()
        if not all_loans.empty:
            selected_loan = st.selectbox("Select Loan", all_loans['id'].tolist(), format_func=lambda x: f"Loan #{x} - {all_loans[all_loans['id']==x]['borrower'].values[0]}")
            if st.button("Generate Payment History"):
                payments = get_loan_payments(selected_loan)
                st.dataframe(payments, use_container_width=True)
                if not payments.empty:
                    output_excel = io.BytesIO()
                    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                        payments.to_excel(writer, sheet_name="Payments", index=False)
                    st.download_button("📥 Download Excel", data=output_excel.getvalue(), file_name=f"loan_{selected_loan}_payments.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    pdf_buffer = generate_pdf_report(f"Payment History for Loan #{selected_loan}", payments, list(payments.columns))
                    st.download_button("📄 Download PDF", data=pdf_buffer, file_name=f"loan_{selected_loan}_payments.pdf", mime="application/pdf")
        else:
            st.info("No loans available to generate payment history.")

st.sidebar.markdown("---")
st.sidebar.markdown("© 2026 GlobalInternet.py – All rights reserved")
