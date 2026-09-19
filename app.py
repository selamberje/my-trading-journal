from datetime import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# ---------------------------------------------------------
# 1. TETAPAN HALAMAN (RESPONSIF HP & LAPTOP)
# ---------------------------------------------------------
st.set_page_config(
    page_title="Pro Trading Journal",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.title("📊 PRO TRADING JOURNAL DASHBOARD")

# Sambungan ke Google Sheets (Ganti URL ini dengan URL Google Sheet anda)
GSHEET_URL = (
    "https://docs.google.com/spreadsheets/d/1DvB3Mo5WOi91VshDxOsAR08tTDbwaMkgDHx8CXrf2x4/edit#gid=0"
)

conn = st.connection("gsheets", type=GSheetsConnection)


# Fungsi membaca data
def load_data():
    try:
        df = conn.read(spreadsheet=GSHEET_URL, ttl="10s")
        # Pastikan jenis data betul
        df["Net Profit"] = pd.to_numeric(df["Net Profit"], errors="coerce").fillna(
            0.0
        )
        df["Lot"] = pd.to_numeric(df["Lot"], errors="coerce").fillna(0)
        df["Entry"] = pd.to_numeric(df["Entry"], errors="coerce").fillna(0.0)
        df["TP"] = pd.to_numeric(df["TP"], errors="coerce").fillna(0.0)
        return df
    except Exception as e:
        st.error(f"Gagal membaca data dari Google Sheets: {e}")
        return pd.DataFrame(
            columns=[
                "Date Buy",
                "Date Sell",
                "Stock",
                "Lot",
                "Entry",
                "TP",
                "Net Profit",
                "Remark",
            ]
        )


df = load_data()

# ---------------------------------------------------------
# 2. RINGKASAN KPI (CARDS)
# ---------------------------------------------------------
total_profit = df["Net Profit"].sum()
win_trades = len(df[df["Net Profit"] > 0])
loss_trades = len(df[df["Net Profit"] < 0])
total_trades = len(df)
win_rate = (win_trades / total_trades * 100) if total_trades > 0 else 0.0

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("NET PROFIT / LOSS", f"RM {total_profit:,.2f}")
c2.metric("WIN RATE", f"{win_rate:.1f}%")
c3.metric("WINNING TRADES", win_trades)
c4.metric("LOSING TRADES", loss_trades)
c5.metric("TOTAL TRADES", total_trades)

st.divider()

# ---------------------------------------------------------
# 3. JADUAL TRANSAKSI
# ---------------------------------------------------------
st.subheader("📋 Transaction History")
st.dataframe(
    df.style.map(
        lambda val: (
            "color: #34D399; font-weight: bold;"
            if isinstance(val, (int, float)) and val > 0
            else (
                "color: #F87171; font-weight: bold;"
                if isinstance(val, (int, float)) and val < 0
                else ""
            )
        ),
        subset=["Net Profit"],
    ),
    use_container_width=True,
    height=350,
)

# ---------------------------------------------------------
# 4. POP-UP / EXPANDER CARTA PERFORMANCE (LINE CHART)
# ---------------------------------------------------------
with st.expander("📈 View Analytics Chart (Line Chart)", expanded=False):
    if not df.empty:
        # Ekstrak Tahun
        df_chart = df.copy()
        df_chart["Date Sell Clean"] = pd.to_datetime(
            df_chart["Date Sell"], errors="coerce"
        )
        df_chart = df_chart.dropna(subset=["Date Sell Clean"])
        df_chart["Year"] = df_chart["Date Sell Clean"].dt.year.astype(str)
        df_chart["Month_Year"] = df_chart["Date Sell Clean"].dt.strftime(
            "%b %Y"
        )

        years = ["All Years"] + sorted(df_chart["Year"].unique().tolist())
        selected_year = st.selectbox("Tapis Mengikut Tahun:", years)

        if selected_year != "All Years":
            df_chart = df_chart[df_chart["Year"] == selected_year]

        # Kumpul keuntungan bulanan
        monthly_df = (
            df_chart.groupby("Month_Year", as_index=False)["Net Profit"]
            .sum()
            .reset_index()
        )

        # Plot Line Chart
        fig = px.line(
            monthly_df,
            x="Month_Year",
            y="Net Profit",
            markers=True,
            title=f"Monthly Profit / Loss Trend ({selected_year})",
            labels={"Net Profit": "Profit (RM)", "Month_Year": "Bulan"},
        )
        fig.update_traces(
            line_color="#38BDF8", marker=dict(size=8, color="#60A5FA")
        )
        fig.add_hline(y=0, line_dash="dash", line_color="#64748B")
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#12131C",
            plot_bgcolor="#181A26",
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Tiada data untuk dipaparkan pada carta.")

st.divider()

# ---------------------------------------------------------
# 5. BORANG TAMBAH TRADING (LENGKAP MULTI-ENTRY)
# ---------------------------------------------------------
st.subheader("➕ Add New Trade Log")

with st.form("trade_form", clear_on_submit=True):
    col_a, col_b, col_c = st.columns(3)

    date_buy = col_a.date_input("Date Buy", datetime.now()).strftime(
        "%d %b %Y"
    )
    date_sell = col_b.date_input("Date Sell", datetime.now()).strftime(
        "%d %b %Y"
    )
    stock = col_c.text_input("Stock Name", placeholder="contoh: Uzma")

    col_d, col_e, col_f = st.columns(3)
    lot = col_d.number_input("Total Lot", min_value=1, value=10, step=1)
    entry_price = col_e.number_input(
        "Entry Price (RM)", min_value=0.001, value=0.500, format="%.3f"
    )
    take_profit = col_f.number_input(
        "Take Profit / Sell Price (RM)",
        min_value=0.000,
        value=0.550,
        format="%.3f",
    )

    remark = st.text_input("Remark / Catatan", placeholder="follow plan / etc.")

    # Kira Net Profit Anggaran Ringkas (Boleh ditukar mengikut formula caj anda)
    sell_val = lot * 100 * take_profit
    buy_val = lot * 100 * entry_price
    est_net_profit = round(sell_val - buy_val, 2)

    st.caption(f"💰 **Anggaran Net Profit:** RM {est_net_profit:,.2f}")

    submitted = st.form_submit_button("💾 Save Trade to Cloud", use_container_width=True)

    if submitted:
        if stock.strip() == "":
            st.warning("Sila isi Nama Saham!")
        else:
            new_row = pd.DataFrame(
                [
                    {
                        "Date Buy": date_buy,
                        "Date Sell": date_sell,
                        "Stock": stock,
                        "Lot": lot,
                        "Entry": entry_price,
                        "TP": take_profit,
                        "Net Profit": est_net_profit,
                        "Remark": remark,
                    }
                ]
            )

            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(spreadsheet=GSHEET_URL, data=updated_df)
            st.success(
                f"Trade '{stock}' berjaya disimpan ke Google Sheet cloud!"
            )
            st.rerun()
