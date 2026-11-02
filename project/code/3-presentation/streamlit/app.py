"""Dashboard Streamlit (3 halaman): Ringkasan, Kualitas Data, Dampak. Semua data adalah simulasi.
Jalankan dari folder project/:  streamlit run code/3-presentation/streamlit/app.py
Membaca CSV ringkas yang sudah di-commit di results/3-presentation/ (tidak perlu database)."""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

RES = Path(__file__).resolve().parents[3] / "results" / "3-presentation"
st.set_page_config(page_title="Project 33: Automated Excel-to-SQL ETL", layout="wide")


@st.cache_data
def load(name):
    return pd.read_csv(RES / name)


prod, dqs, dqm, iss, steps, imp, runs = (load(f"dash_{n}.csv") for n in ("prod", "dq_station", "dq_month", "issues", "impact_steps", "impact", "runs"))
BLUE, ORANGE = "#1A73E8", "#E8710A"
prod = prod.merge(dqs[["station", "ord"]], on="station")
st.sidebar.header("Filter")
stations = st.sidebar.multiselect("Stasiun", list(dict.fromkeys(prod.sort_values("ord").station)), default=list(dict.fromkeys(prod.sort_values("ord").station)))
models = st.sidebar.multiselect("Model", ["Basic", "Plus", "Pro"], default=["Basic", "Plus", "Pro"])
page = st.sidebar.radio("Halaman", ["1. Ringkasan produksi", "2. Kualitas data dan karantina", "3. Dampak waktu"])
st.sidebar.caption("Data simulasi buatan sendiri. Angka dampak berlabel estimated.")
d = prod[prod.station.isin(stations) & prod.model.isin(models)]
if d.empty:
    st.warning("Pilih minimal satu stasiun dan satu model."); st.stop()
st.title("Project 33: Automated Excel-to-SQL ETL")
st.caption("60 file Excel log operator (3 versi template, Mar–Agu 2026) dimuat ke DuckDB dengan validasi. Data simulasi.")

if page.startswith("1"):
    t = d[["input_qty", "ok_qty", "ng_qty"]].sum()
    c = st.columns(3)
    c[0].metric("Output (input_qty)", f"{int(t.input_qty):,}".replace(",", ".")); c[1].metric("Yield", f"{t.ok_qty / t.input_qty:.2%}"); c[2].metric("NG", f"{int(t.ng_qty):,}".replace(",", "."))
    m = d.groupby("month")[["input_qty", "ok_qty"]].sum().reset_index(); m["yield"] = m.ok_qty / m.input_qty
    st.plotly_chart(px.bar(m, x="month", y="input_qty", title="Output per bulan", color_discrete_sequence=[BLUE]), width="stretch")
    s = d.groupby(["station", "ord"])[["input_qty", "ng_qty"]].sum().reset_index().sort_values("ord"); s["ng_rate"] = s.ng_qty / s.input_qty
    st.plotly_chart(px.bar(s, x="station", y="ng_rate", title="NG rate per stasiun", color_discrete_sequence=[ORANGE]).update_yaxes(tickformat=".1%"), width="stretch")
elif page.startswith("2"):
    r = runs.iloc[0]
    c = st.columns(4)
    c[0].metric("Baris dibaca", f"{int(r.rows_read):,}".replace(",", ".")); c[1].metric("Dimuat", f"{int(r.rows_inserted):,}".replace(",", ".")); c[2].metric("Dikarantina", f"{int(r.rows_rejected)}"); c[3].metric("Reject rate", f"{r.reject_rate:.1%}")
    st.caption("Run kedua tidak memasukkan baris baru: " + f"{int(runs.iloc[1].rows_inserted)} baris." if len(runs) > 1 else "")
    st.subheader("Baris dikarantina per aturan")
    st.dataframe(iss, hide_index=True, width="stretch")
    st.plotly_chart(px.bar(dqm, x="month", y="rows_rejected", color="template_version", title="Baris dikarantina per bulan dan versi template"), width="stretch")
    st.plotly_chart(px.bar(dqs.sort_values("ord"), x="station", y="dq_score", title="Data quality score per stasiun (%)", color_discrete_sequence=[BLUE]).update_yaxes(range=[90, 100]), width="stretch")
else:
    a, b = st.columns(2)
    n_rep = a.slider("Laporan per bulan", 1, 20, 8)
    man = b.slider("Menit manual per laporan", 60, 300, int(steps.menit_manual.sum()), 5)
    etl = float(steps.menit_setelah_etl.sum())
    saved = (man - etl) * n_rep * 12 / 60
    k = st.columns(3)
    k[0].metric("Menit manual", man); k[1].metric("Menit setelah ETL (asumsi)", f"{etl:.0f}"); k[2].metric("Jam dihemat / tahun", f"{saved:,.0f}".replace(",", "."))
    st.plotly_chart(px.bar(steps.melt("langkah", ["menit_manual", "menit_setelah_etl"]), x="langkah", y="value", color="variable", barmode="group", title="Menit per langkah penyusunan laporan"), width="stretch")
    st.dataframe(imp, hide_index=True, width="stretch")
    st.caption("Estimated / simulated. Waktu manual adalah asumsi; waktu run ETL terukur dari run di mesin ini.")
