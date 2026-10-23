import streamlit as st
import io
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import pdfplumber
from datetime import datetime

# ==========================================
# KONFIGURASI UI & CSS (Dark Blue Background)
# ==========================================
st.set_page_config(page_title="Auto Urusan Dokumen", layout="wide")

page_bg_color = """
<style>
[data-testid="stAppViewContainer"] {
    background-color: #0B192C;
    color: white;
}
[data-testid="stSidebar"] {
    background-color: #1A365D;
}
h1, h2, h3, p, label, div {
    color: white !important;
}
.stButton>button {
    background-color: #4CAF50;
    color: white;
    font-weight: bold;
}
</style>
"""
st.markdown(page_bg_color, unsafe_allow_html=True)

# ==========================================
# FUNGSI GOOGLE API (DRIVE & SHEETS)
# ==========================================
# NOTA: Anda perlu ada fail credentials.json di dalam folder yang sama
SCOPE = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]
SHEET_URL = "https://docs.google.com/spreadsheets/d/1-6TO29A1zxyvjIbsiKe49zR3D147rGeRDfJNjNye0Es/edit?usp=sharing"

def get_google_services():
    try:
        creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', SCOPE)
        # Google Sheets
        gc = gspread.authorize(creds)
        # Google Drive
        drive_service = build('drive', 'v3', credentials=creds)
        return gc, drive_service
    except Exception as e:
        st.warning(f"Sila muat naik 'credentials.json' untuk membolehkan fungsi Google. Ralat: {e}")
        return None, None

def create_drive_folder(drive_service, folder_name):
    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder'
    }
    folder = drive_service.files().create(body=file_metadata, fields='id, webViewLink').execute()
    return folder.get('id'), folder.get('webViewLink')

def upload_to_drive(drive_service, folder_id, file_name, file_bytes):
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype='application/pdf', resumable=True)
    file_metadata = {'name': file_name, 'parents': [folder_id]}
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    return uploaded_file.get('id')

# ==========================================
# FUNGSI PEMPROSESAN PDF & COP "BANTU"
# ==========================================
def create_stamp():
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=A4)
    c.setFont("Helvetica-Bold", 60)
    c.setFillColorRGB(1, 0, 0, alpha=0.3) # Merah yang transparent
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
        # Scan menggunakan regex berdasarkan format "Nama :" dan "No.ic :"
        nama_match = re.search(r'Nama\s*:\s*(.*)', data, re.IGNORECASE)
        ic_match = re.search(r'No\.?ic\s*:\s*([\d-]+)', data, re.IGNORECASE)
        result['nama'] = nama_match.group(1).strip() if nama_match else "Gagal dikesan"
        result['ic'] = ic_match.group(1).strip() if ic_match else "Gagal dikesan"
    elif doc_type == "borang":
        # Scan tarikh permohonan
        tarikh_match = re.search(r'Tarikh\s*Permohonan\s*:\s*(.*)', data, re.IGNORECASE)
        result['tarikh'] = tarikh_match.group(1).strip() if tarikh_match else datetime.now().strftime("%d-%m-%Y")
        
    return result

# ==========================================
# ANTARAMUKA UTAMA (UI)
# ==========================================
st.title("🛡️ AUTO URUSAN DOKUMEN LICENSING")
st.markdown("---")

# Menu Navigasi
menu = st.radio("Sila pilih paparan:", ["PERMOHONAN BARU", "MASTERLIST CLIENT"], horizontal=True)

if menu == "PERMOHONAN BARU":
    st.subheader("Borang Permohonan Baru")
    
    # Dropdown Pakej
    pakej_pilihan = st.selectbox("Sila Pilih Pakej:", ["PAKEJ NOMBOR 1", "PAKEJ NOMBOR 2", "PAKEJ NOMBOR 3"])
    
    st.write("### Muat Naik Dokumen")
    # Dua ruang upload bersebelahan
    col1, col2 = st.columns(2)
    with col1:
        borang_file = st.file_uploader("Upload Borang Permohonan (PDF)", type=["pdf"])
    with col2:
        ic_file = st.file_uploader("Upload Salinan IC (PDF)", type=["pdf"])

    if borang_file and ic_file:
        if st.button("🚀 RUN", use_container_width=True):
            with st.spinner("Sedang memproses dokumen, mencipta folder, dan mengemaskini sistem..."):
                try:
                    # 1. Cop Dokumen
                    stamped_borang = stamp_pdf(borang_file)
                    stamped_ic = stamp_pdf(ic_file)
                    
                    # 2. Extract Data
                    data_ic = extract_data_from_pdf(ic_file, "ic")
                    data_borang = extract_data_from_pdf(borang_file, "borang")
                    
                    nama = data_ic.get('nama')
                    no_ic = data_ic.get('ic')
                    tarikh = data_borang.get('tarikh')
                    folder_name = f"{nama} - {no_ic}"
                    
                    # 3. Google API Action
                    gc, drive_service = get_google_services()
                    if gc and drive_service:
                        # Buat folder Drive
                        folder_id, folder_link = create_drive_folder(drive_service, folder_name)
                        
                        # Upload file ke dalam folder tersebut
                        upload_to_drive(drive_service, folder_id, f"Borang_Permohonan_BANTU.pdf", stamped_borang)
                        upload_to_drive(drive_service, folder_id, f"Salinan_IC_BANTU.pdf", stamped_ic)
                        
                        # Update Google Sheet
                        sheet = gc.open_by_url(SHEET_URL).sheet1
                        row_data = [nama, no_ic, tarikh, pakej_pilihan, folder_link]
                        sheet.append_row(row_data)
                        
                        st.success("✅ PROSES BERJAYA!")
                        st.info(f"📁 [Klik Sini Untuk Buka Folder Google Drive Client]({folder_link})")
                    else:
                        st.error("Gagal menyambung ke Google API. Pastikan credentials.json wujud dan sah.")
                        
                except Exception as e:
                    st.error(f"Berlaku ralat: {e}")

elif menu == "MASTERLIST CLIENT":
    st.subheader("Pangkalan Data Pelanggan")
    st.markdown(
        f"""
        <a href="{SHEET_URL}" target="_blank">
            <button style="background-color:#4CAF50; color:white; padding:14px 20px; margin:8px 0; border:none; cursor:pointer; width:100%; border-radius:4px; font-size:16px; font-weight:bold;">
                📊 KLIK DI SINI UNTUK MEMBUKA GOOGLE SHEET MASTERLIST
            </button>
        </a>
        """, unsafe_allow_html=True
    )
