import streamlit as st
import io
import re
import base64
import requests
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import pdfplumber

# ==========================================
# PAUTAN SISTEM
# ==========================================
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwtls5utGSr6pjeaQ0526WN5GOZMTzTRdmYEATnT8nXRQIX78Fali31efPbXGfAlcgQ/exec"
SHEET_URL = "https://docs.google.com/spreadsheets/d/1a5Uc5H7IYYtK8ry6dlZQCvkRg63YgNldF8Qinp0TUH0/edit?usp=sharing"

# ==========================================
# KONFIGURASI UI & CSS
# ==========================================
st.set_page_config(page_title="Auto Urusan Dokumen", layout="wide")

page_bg_color = """
<style>
/* Latar belakang utama aplikasi */
[data-testid="stAppViewContainer"] {
    background-color: #0B192C;
    color: white;
}
[data-testid="stSidebar"] {
    background-color: #1A365D;
}

/* Penyesuaian warna teks dan tajuk */
h1, h2, h3, h4, label, [data-testid="stMarkdownContainer"] p {
    color: #FFFFFF !important;
}

/* Kotak Dropdown (Selectbox) */
div[data-baseweb="select"] * {
    color: #111827 !important;
}
div[data-baseweb="popover"] * {
    color: #111827 !important;
}

/* Kotak Upload Dokumen */
[data-testid="stFileUploaderDropzone"] {
    background-color: #132742 !important;
    border: 2px dashed #3B82F6 !important;
    border-radius: 8px !important;
}
[data-testid="stFileUploaderDropzone"] * {
    color: #FFFFFF !important;
}
[data-testid="stFileUploaderDropzone"] button {
    background-color: #3B82F6 !important;
    color: #FFFFFF !important;
    border: none !important;
    font-weight: bold !important;
}

/* Butang Utama */
.stButton>button {
    background-color: #4CAF50 !important;
    color: white !important;
    font-weight: bold !important;
    border: none !important;
    border-radius: 6px !important;
    padding: 10px 0px !important;
}
.stButton>button:hover {
    background-color: #45a049 !important;
    color: white !important;
}
</style>
"""
st.markdown(page_bg_color, unsafe_allow_html=True)

# ==========================================
# FUNGSI COP & IMBASAN PDF
# ==========================================
def create_stamp():
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    c.setFont("Helvetica-Bold", 60)
    c.setFillColorRGB(1, 0, 0, alpha=0.3)
    c.translate(200, 400)
    c.rotate(45)
    c.drawString(0, 0, "BANTU")
    c.save()
    packet.seek(0)
    return packet

def stamp_pdf(uploaded_file):
    stamp_packet = create_stamp()
    stamp_pdf = PdfReader(stamp_packet)
    stamp_page = stamp_pdf.pages[0]
    
    pdf = PdfReader(uploaded_file)
    pdf_writer = PdfWriter()
    
    for page in pdf.pages:
        page.merge_page(stamp_page)
        pdf_writer.add_page(page)
        
    output = io.BytesIO()
    pdf_writer.write(output)
    return output.getvalue()

def extract_data_from_borang(pdf_file):
    """Mengekstrak data Nama, No IC, dan Tarikh terus daripada dokumen Borang Permohonan."""
    data = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                data += text + "\n"
                
    result = {}

    # 1. Mengesan Nama
    nama_match = re.search(r'nama\s*:\s*\n?\s*([^\r\n]+)', data, re.IGNORECASE)
    if nama_match:
        nama_val = nama_match.group(1).strip()
        if not any(nama_val.lower().startswith(x) for x in ["no", "tarikh", "ic"]):
            result['nama'] = nama_val
        else:
            result['nama'] = "Klien_Tanpa_Nama"
    else:
        result['nama'] = "Klien_Tanpa_Nama"

    # 2. Mengesan No IC
    ic_match = re.search(r'no\.?\s*ic\s*:\s*([^\r\n]+)', data, re.IGNORECASE)
    if ic_match:
        result['ic'] = ic_match.group(1).strip()
    else:
        result['ic'] = "Tiada_IC"

    # 3. Mengesan Tarikh Permohonan
    tarikh_match = re.search(r'tarikh(?:\s*permohonan)?\s*:\s*([^\r\n]+)', data, re.IGNORECASE)
    result['tarikh'] = tarikh_match.group(1).strip() if tarikh_match else datetime.now().strftime("%d/%m/%y")
        
    return result

# ==========================================
# ANTARAMUKA UTAMA (UI)
# ==========================================
if 'page' not in st.session_state:
    st.session_state.page = None

st.title("🛡️ AUTO URUSAN DOKUMEN LICENSING")
st.markdown("---")

st.write("Sila pilih paparan:")
col_nav1, col_nav2, col_spacer = st.columns([1, 1, 2])

with col_nav1:
    if st.button("📄 PERMOHONAN BARU", use_container_width=True):
        st.session_state.page = "PERMOHONAN BARU"
        st.rerun()

with col_nav2:
    if st.button("📊 MASTERLIST CLIENT", use_container_width=True):
        st.session_state.page = "MASTERLIST CLIENT"
        st.rerun()

st.markdown("---")

if st.session_state.page == "PERMOHONAN BARU":
    st.subheader("Borang Permohonan Baru")
    
    pakej_pilihan = st.selectbox("Sila Pilih Pakej:", ["PAKEJ NOMBOR 1", "PAKEJ NOMBOR 2", "PAKEJ NOMBOR 3"])
    
    st.write("### Muat Naik Dokumen")
    col1, col2 = st.columns(2)
    with col1:
        borang_file = st.file_uploader("Borang Permohonan", type=["pdf"])
    with col2:
        ic_file = st.file_uploader("Salinan IC", type=["pdf"])

    if borang_file and ic_file:
        if st.button("🚀 RUN", use_container_width=True):
            with st.spinner("Sedang memproses dokumen dan mengekstrak data dari borang..."):
                try:
                    # 1. Cop Dokumen "BANTU" untuk kedua-dua fail
                    stamped_borang = stamp_pdf(borang_file)
                    stamped_ic = stamp_pdf(ic_file)
                    
                    # 2. Imbas Semua Data Teks (Nama, No IC, Tarikh) dari Borang Permohonan
                    data_borang = extract_data_from_borang(borang_file)
                    
                    nama = data_borang.get('nama')
                    no_ic = data_borang.get('ic')
                    tarikh = data_borang.get('tarikh')
                    
                    # 3. Hantar data ke Google Apps Script Web App
                    payload = {
                        "nama": nama,
                        "no_ic": no_ic,
                        "tarikh": tarikh,
                        "pakej": pakej_pilihan,
                        "borang_name": f"Borang_{nama}_{no_ic}_BANTU.pdf",
                        "borang_base64": base64.b64encode(stamped_borang).decode("utf-8"),
                        "ic_name": f"SalinanIC_{nama}_{no_ic}_BANTU.pdf",
                        "ic_base64": base64.b64encode(stamped_ic).decode("utf-8")
                    }
                    
                    response = requests.post(WEB_APP_URL, json=payload)
                    res_json = response.json()
                    
                    if res_json.get("status") == "success":
                        st.success("✅ PROSES BERJAYA! Data dan dokumen telah direkodkan ke Google Drive & Masterlist.")
                        st.markdown(f"- **Nama Dikesan:** `{nama}`")
                        st.markdown(f"- **No IC Dikesan:** `{no_ic}`")
                        st.markdown(f"- **Tarikh Permohonan:** `{tarikh}`")
                        st.markdown(f"- 📄 **Borang Permohonan:** [Buka Fail PDF]({res_json.get('borang_url')})")
                        st.markdown(f"- 🪪 **Salinan IC:** [Buka Fail PDF]({res_json.get('ic_url')})")
                    else:
                        st.error(f"Ralat dari pelayan: {res_json.get('message')}")
                        
                except Exception as e:
                    st.error(f"Berlaku ralat semasa pemprosesan: {e}")

elif st.session_state.page == "MASTERLIST CLIENT":
    st.subheader("Pangkalan Data Pelanggan")
    st.info("Pangkalan data ini disambungkan terus ke Google Sheet utama anda.")
    st.markdown(
        f"""
        <a href="{SHEET_URL}" target="_blank">
            <button style="background-color:#3B82F6; color:white; padding:14px 20px; margin:8px 0; border:none; cursor:pointer; width:100%; border-radius:6px; font-size:16px; font-weight:bold;">
                📊 BUKA GOOGLE SHEET MASTERLIST
            </button>
        </a>
        """, unsafe_allow_html=True
    )

else:
    st.info("👆 Sila klik salah satu pilihan butang di atas untuk memulakan urusan.")
