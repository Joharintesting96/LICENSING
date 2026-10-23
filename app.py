import streamlit as st
import io
import re
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import pdfplumber

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

/* Tajuk, label, dan teks */
h1, h2, h3, h4, label, [data-testid="stMarkdownContainer"] p {
    color: #FFFFFF !important;
}

/* Kotak Dropdown (Selectbox) & Menu Pilihan (Font gelap agar mudah dibaca) */
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

/* Semua Butang Aplikasi */
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
# KONFIGURASI GOOGLE API (DRIVE & SHEETS)
# ==========================================
SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SHEET_URL = "https://docs.google.com/spreadsheets/d/1a5Uc5H7IYYtK8ry6dlZQCvkRg63YgNldF8Qinp0TUH0/edit?usp=sharing"

def get_google_services():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPE)
        gc = gspread.authorize(creds)
        drive_service = build('drive', 'v3', credentials=creds)
        return gc, drive_service
    except Exception as e:
        st.warning(f"Sila muat naik fail 'credentials.json' yang sah. Ralat: {e}")
        return None, None

def upload_file_to_drive(drive_service, file_name, file_bytes):
    """Memuat naik fail ke Google Drive dan menjana pautan paparan."""
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype='application/pdf', resumable=True)
    file_metadata = {'name': file_name}
    
    uploaded_file = drive_service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink'
    ).execute()
    
    file_id = uploaded_file.get('id')
    
    # Menetapkan akses bacaan awam pada fail tersebut
    try:
        drive_service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
    except Exception:
        pass
        
    return uploaded_file.get('webViewLink')

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

def extract_data_from_pdf(pdf_file, doc_type):
    data = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                data += text + "\n"
                
    result = {}
    if doc_type == "ic":
        nama_match = re.search(r'Nama\s*:\s*(.*)', data, re.IGNORECASE)
        ic_match = re.search(r'No\.?ic\s*:\s*([\d-]+)', data, re.IGNORECASE)
        result['nama'] = nama_match.group(1).strip() if nama_match else "Gagal dikesan"
        result['ic'] = ic_match.group(1).strip() if ic_match else "Gagal dikesan"
    elif doc_type == "borang":
        tarikh_match = re.search(r'Tarikh\s*Permohonan\s*:\s*(.*)', data, re.IGNORECASE)
        result['tarikh'] = tarikh_match.group(1).strip() if tarikh_match else datetime.now().strftime("%d-%m-%Y")
        
    return result

# ==========================================
# ANTARAMUKA UTAMA (UI)
# ==========================================
# 1. Inisialisasi Sistem Navigasi Page (Session State)
if 'page' not in st.session_state:
    st.session_state.page = "PERMOHONAN BARU"

st.title("🛡️ AUTO URUSAN DOKUMEN LICENSING")
st.markdown("---")

# 2. Butang Navigasi Bersebelahan
st.write("Sila pilih paparan:")
col_nav1, col_nav2, col_nav3, col_nav4 = st.columns(4)

with col_nav1:
    if st.button("📄 PERMOHONAN BARU", use_container_width=True):
        st.session_state.page = "PERMOHONAN BARU"
with col_nav2:
    if st.button("📊 MASTERLIST CLIENT", use_container_width=True):
        st.session_state.page = "MASTERLIST CLIENT"

st.markdown("---")

# 3. Logik Paparan Berdasarkan Butang Yang Ditekan
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
            with st.spinner("Sedang memproses dokumen, memuat naik ke Drive, dan mengemaskini masterlist..."):
                try:
                    # Cop Dokumen "BANTU"
                    stamped_borang = stamp_pdf(borang_file)
                    stamped_ic = stamp_pdf(ic_file)
                    
                    # Imbas Data Teks
                    data_ic = extract_data_from_pdf(ic_file, "ic")
                    data_borang = extract_data_from_pdf(borang_file, "borang")
                    
                    nama = data_ic.get('nama')
                    no_ic = data_ic.get('ic')
                    tarikh = data_borang.get('tarikh')
                    
                    if nama == "Gagal dikesan": nama = "Klien_Tanpa_Nama"
                    if no_ic == "Gagal dikesan": no_ic = "Tiada_IC"
                    
                    # Muat Naik Fail ke Drive
                    gc, drive_service = get_google_services()
                    if gc and drive_service:
                        nama_fail_borang = f"Borang_Permohonan_{nama}_{no_ic}_BANTU.pdf"
                        nama_fail_ic = f"Salinan_IC_{nama}_{no_ic}_BANTU.pdf"
                        
                        link_borang = upload_file_to_drive(drive_service, nama_fail_borang, stamped_borang)
                        link_ic = upload_file_to_drive(drive_service, nama_fail_ic, stamped_ic)
                        
                        # Masukkan Rekod ke Google Sheet Masterlist
                        sheet = gc.open_by_url(SHEET_URL).sheet1
                        row_data = [nama, no_ic, tarikh, pakej_pilihan, link_borang, link_ic]
                        sheet.append_row(row_data)
                        
                        st.success("✅ PROSES BERJAYA! Dokumen dan rekod telah disimpan.")
                        st.markdown(f"- 📄 **Borang Permohonan:** [Buka Fail PDF]({link_borang})")
                        st.markdown(f"- 🪪 **Salinan IC:** [Buka Fail PDF]({link_ic})")
                    else:
                        st.error("Gagal menyambung ke Google API. Pastikan fail 'credentials.json' wujud.")
                        
                except Exception as e:
                    st.error(f"Berlaku ralat: {e}")

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
