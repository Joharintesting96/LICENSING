# ==========================================
# KONFIGURASI UI & CSS (DIKEMASKINI)
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

/* Tajuk, label teks, dan radio button kekal putih */
h1, h2, h3, h4, label, [data-testid="stMarkdownContainer"] p {
    color: #FFFFFF !important;
}
[data-testid="stRadio"] label p {
    color: #FFFFFF !important;
}

/* Kotak Dropdown (Selectbox) & Menu Pilihan - jadikan teks gelap/hitam pekat */
div[data-baseweb="select"] * {
    color: #111827 !important;
}
div[data-baseweb="popover"] * {
    color: #111827 !important;
}

/* Kotak Upload File - berlatar belakang biru gelap dengan teks putih & sempadan kemas */
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
    font-weight: 500 !important;
}

/* Butang RUN */
.stButton>button {
    background-color: #4CAF50 !important;
    color: white !important;
    font-weight: bold !important;
}
</style>
"""
st.markdown(page_bg_color, unsafe_allow_html=True)
