import streamlit as st
import pandas as pd
from db import get_connection

st.set_page_config(page_title="Sınav Takvim Sistemi", layout="wide")

st.title("🎓 Sınav Takvimi ve Gözetmen Dağıtım Sistemi")

conn = get_connection()

tab1, tab2, tab3, tab4 = st.tabs([
    "⚙️ Yönetici Ayarları", 
    "📐 Kapasite Planlama", 
    "📅 Sınav ve Gözetmen Atama",
    "📜 Değişim Logları"
])

# --- MODÜL 1: YÖNETİCİ AYARLARI ---
with tab1:
    st.header("Sistem Sabitlerini Tanımla")
    
    sub_tab1, sub_tab2, sub_tab3 = st.tabs(["Derslikler", "Dersler", "Personel"])

    # 1.1 Derslik Yönetimi
    with sub_tab1:
        st.subheader("Derslik Listesi")
        if conn:
            df_derslik = pd.read_sql("SELECT * FROM Derslik", conn)
            st.dataframe(df_derslik, use_container_width=True)
            
            with st.expander("➕ Yeni Derslik Ekle"):
                with st.form("derslik_form"):
                    col1, col2, col3 = st.columns(3)
                    ad = col1.text_input("Derslik Adı")
                    kap = col2.number_input("Kapasite", min_value=1)
                    tip = col3.selectbox("Tip", ["Sınıf", "Amfi", "Lab"])
                    if st.form_submit_button("Dersliği Kaydet"):
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO Derslik (ad, kapasite, tip, aktif_mi) VALUES (?, ?, ?, 1)", (ad, kap, tip))
                        conn.commit()
                        st.success("Derslik başarıyla eklendi!")
                        st.rerun()

    # 1.2 Ders Yönetimi (Yarıyıl Kontrolü İçin Kritik)
    with sub_tab2:
        st.subheader("Ders Bilgileri")
        if conn:
            # Bolum isimlerini çekmek için JOIN kullanıyoruz
            df_ders = pd.read_sql("""
                SELECT d.ders_id, d.ders_adi, d.ogrenci_sayisi, d.yariyil, b.bolum_adi 
                FROM Ders d JOIN Bolum b ON d.bolum_id = b.bolum_id
            """, conn)
            st.dataframe(df_ders, use_container_width=True)
            
            with st.expander("➕ Yeni Ders Ekle"):
                with st.form("ders_form"):
                    d_ad = st.text_input("Ders Adı")
                    col1, col2 = st.columns(2)
                    kont = col1.number_input("Öğrenci Sayısı (Kontenjan)", min_value=1)
                    yariyil = col2.selectbox("Yarıyıl", [1, 2, 3, 4, 5, 6, 7, 8])
                    # Bölümleri dinamik çekelim
                    bolumler = pd.read_sql("SELECT * FROM Bolum", conn)
                    secilen_bolum = st.selectbox("Bölüm", bolumler['bolum_adi'])
                    b_id = int(bolumler[bolumler['bolum_adi'] == secilen_bolum]['bolum_id'].values[0])
                    
                    if st.form_submit_button("Dersi Kaydet"):
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO Ders (ders_adi, ogrenci_sayisi, yariyil, bolum_id) VALUES (?, ?, ?, ?)", (d_ad, kont, yariyil, b_id))
                        conn.commit()
                        st.success("Ders başarıyla eklendi!")
                        st.rerun()

# --- MODÜL 2: KAPASİTE PLANLAMA ---
with tab2:
    st.header("Modül 2: Akıllı Salon Hesaplama")
    st.info("Bu modül, ders kontenjanına göre en uygun salonları önerir.")

    if conn:
        # Sınavı planlanacak dersi seç
        ders_listesi = pd.read_sql("SELECT ders_id, ders_adi, ogrenci_sayisi FROM Ders", conn)
        if not ders_listesi.empty:
            secilen_ders_ad = st.selectbox("Sınavı Planlanacak Ders:", ders_listesi['ders_adi'])
            
            ders_info = ders_listesi[ders_listesi['ders_adi'] == secilen_ders_ad].iloc[0]
            kontenjan = int(ders_info['ogrenci_sayisi'])
            
            st.write(f"**Toplam Kontenjan:** {kontenjan}")
            
            if st.button("En Verimli Salon Kombinasyonunu Hesapla"):
                # Boş ve aktif salonları kapasiteye göre büyükten küçüğe çek[cite: 1]
                salonlar = pd.read_sql("SELECT ad, kapasite FROM Derslik WHERE aktif_mi = 1 ORDER BY kapasite DESC", conn)
                
                kalan_ogrenci = kontenjan
                secilen_salonlar = []
                
                for index, row in salonlar.iterrows():
                    if kalan_ogrenci <= 0:
                        break
                    secilen_salonlar.append(row)
                    kalan_ogrenci -= row['kapasite']
                
                if secilen_salonlar:
                    st.success(f"Önerilen Salon Kombinasyonu:")
                    öneri_df = pd.DataFrame(secilen_salonlar)
                    st.table(öneri_df)
                    st.write(f"**Toplam Kapasite:** {sum(s['kapasite'] for s in secilen_salonlar)}")
                    st.write(f"**Gerekli Gözetmen Sayısı:** {len(secilen_salonlar)}") 
                else:
                    st.error("Uygun salon bulunamadı!")
        else:
            st.warning("Önce 'Yönetici Ayarları' kısmından ders eklemelisiniz.")
# --- MODÜL 4: LOGLAR (Trigger Testi) ---
with tab4:
    st.header("Sistem Hareket Kayıtları (Loglar)")
    st.write("Sınav saati veya tarihi değiştiğinde trigger üzerinden kaydedilen veriler:")
    if conn:
        df_logs = pd.read_sql("SELECT * FROM Log_Kayitlari ORDER BY degisim_tarihi DESC", conn)
        if not df_logs.empty:
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.write("Henüz bir değişiklik kaydı bulunmuyor.")

if conn:
    conn.close()