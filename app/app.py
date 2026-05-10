import streamlit as st
import pandas as pd
from db import get_connection
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Sınav Takvim Sistemi", layout="wide")

st.title("🎓 Sınav Takvimi ve Gözetmen Dağıtım Sistemi")

conn = get_connection()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Yönetici Ayarları", 
    "Kapasite Planlama", 
    "Sınav ve Gözetmen Atama",
    "Değişim Logları",
    "Sınav Programı ve Raporlama"
])


with st.sidebar:
    st.title("⚙️ Sistem Araçları")
    st.write(f"Bağlı Kullanıcı: {os.getenv('DB_USER', 'sa')}")
    st.divider()
    
    if st.button("💾 Veritabanı Yedeği Al"):
        try:
            original_autocommit = conn.autocommit
            conn.autocommit = True 
            
            cursor = conn.cursor()
            
            backup_query = """
            BACKUP DATABASE examscheduler 
            TO DISK = '/var/opt/mssql/data/examscheduler.bak' 
            WITH FORMAT, NAME = 'Full Backup of examscheduler';
            """
            
            cursor.execute(backup_query)
            
            while cursor.nextset():
                pass
                
            st.sidebar.success("✅ Yedekleme başarıyla alındı!")
            
            conn.autocommit = original_autocommit
            
        except Exception as e:
            st.sidebar.error(f"Yedekleme hatası: {e}")


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

    # 1.2 Ders Yönetimi 
    with sub_tab2:
        st.subheader("Ders Bilgileri")
        if conn:
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
                    bolumler = pd.read_sql("SELECT * FROM Bolum", conn)
                    secilen_bolum = st.selectbox("Bölüm", bolumler['bolum_adi'])
                    b_id = int(bolumler[bolumler['bolum_adi'] == secilen_bolum]['bolum_id'].values[0])
                    
                    if st.form_submit_button("Dersi Kaydet"):
                        cursor = conn.cursor()
                        cursor.execute("INSERT INTO Ders (ders_adi, ogrenci_sayisi, yariyil, bolum_id) VALUES (?, ?, ?, ?)", (d_ad, kont, yariyil, b_id))
                        conn.commit()
                        st.success("Ders başarıyla eklendi!")
                        st.rerun()

    # 1.3 Personel Yönetimi
    with sub_tab3:
        st.subheader("Personel Listesi")
        if conn:
            try:
                query = """
                    SELECT p.personel_id, p.ad, p.soyad, p.unvan, b.bolum_adi 
                    FROM Personel p 
                    JOIN Bolum b ON p.bolum_id = b.bolum_id
                """
                df_personel = pd.read_sql(query, conn)
                
                df_personel['Ad Soyad'] = df_personel['ad'] + " " + df_personel['soyad']
                st.dataframe(df_personel[['personel_id', 'Ad Soyad', 'unvan', 'bolum_adi']], 
                             use_container_width=True, hide_index=True)
                
                with st.expander("➕ Yeni Personel Ekle"):
                    with st.form("personel_form_new"):
                        col1, col2 = st.columns(2)
                        p_ad = col1.text_input("Ad")
                        p_soyad = col2.text_input("Soyad")
                        
                        col3, col4 = st.columns(2)
                        p_unvan = col3.selectbox("Unvan", ["Prof. Dr.", "Doç. Dr.", "Dr. Öğr. Üyesi", "Arş. Gör.", "Öğr. Gör."])
                        
                        bolumler_df = pd.read_sql("SELECT * FROM Bolum", conn)
                        secilen_p_bolum = col4.selectbox("Bölüm", bolumler_df['bolum_adi'], key="p_bolum")
                        p_b_id = int(bolumler_df[bolumler_df['bolum_adi'] == secilen_p_bolum]['bolum_id'].values[0])
                        
                        if st.form_submit_button("Personeli Kaydet"):
                            if p_ad and p_soyad:
                                cursor = conn.cursor()
                                cursor.execute(
                                    "INSERT INTO Personel (ad, soyad, unvan, bolum_id) VALUES (?, ?, ?, ?)", 
                                    (p_ad, p_soyad, p_unvan, p_b_id)
                                )
                                conn.commit()
                                st.success(f"{p_ad} {p_soyad} başarıyla sisteme eklendi!")
                                st.rerun()
                            else:
                                st.warning("Lütfen Ad ve Soyad alanlarını doldurun.")
            except Exception as e:
                st.error(f"Personel verileri yüklenirken hata oluştu: {e}")

# --- MODÜL 2: KAPASİTE PLANLAMA ---
with tab2:
    st.header("Modül 2: Akıllı Salon Hesaplama")
    st.info("Bu modül, ders kontenjanına göre en uygun salonları önerir.")

    if conn:
        ders_listesi = pd.read_sql("SELECT ders_id, ders_adi, ogrenci_sayisi FROM Ders", conn)
        if not ders_listesi.empty:
            secilen_ders_ad = st.selectbox("Sınavı Planlanacak Ders:", ders_listesi['ders_adi'])
            
            ders_info = ders_listesi[ders_listesi['ders_adi'] == secilen_ders_ad].iloc[0]
            kontenjan = int(ders_info['ogrenci_sayisi'])
            
            st.write(f"**Toplam Kontenjan:** {kontenjan}")
            
            if st.button("En Verimli Salon Kombinasyonunu Hesapla"):
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


# --- MODÜL 3: SINAV VE GÖZETMEN ATAMA (GÜNCEL & HATASIZ) ---
with tab3:
    st.header("🗓️ Sınav ve Gözetmen Planlama")
    
    if conn:
        try:
            dersler_df = pd.read_sql("SELECT ders_id, ders_adi, yariyil, ogrenci_sayisi FROM Ders", conn)
            oturumlar_df = pd.read_sql("SELECT oturum_id, aciklama FROM Oturum", conn)
            salonlar_df = pd.read_sql("SELECT derslik_id, ad, kapasite FROM Derslik WHERE aktif_mi = 1", conn)
            personel_df = pd.read_sql("SELECT personel_id, ad + ' ' + soyad AS ad_soyad FROM Personel", conn)
        except Exception as e:
            st.error(f"Veri çekme hatası: {e}")
            st.stop()

        with st.form("sinav_atama_form"):
            col1, col2 = st.columns(2)
            
            secilen_ders = col1.selectbox("Ders Seçin:", dersler_df['ders_adi'])
            sinav_tarihi = col2.date_input("Sınav Tarihi")
            secilen_oturum = col1.selectbox("Oturum Seçin:", oturumlar_df['aciklama'])
            
            secilen_salon_adlari = st.multiselect("Salonlar (Derslik):", salonlar_df['ad'])
            secilen_gozetmenler = st.multiselect("Gözetmenler:", personel_df['ad_soyad'])
            
            submit_btn = st.form_submit_button("Sınavı Kaydet")

            if submit_btn:
                d_info = dersler_df[dersler_df['ders_adi'] == secilen_ders].iloc[0]
                o_id = oturumlar_df[oturumlar_df['aciklama'] == secilen_oturum]['oturum_id'].values[0]
                toplam_kapasite = salonlar_df[salonlar_df['ad'].isin(secilen_salon_adlari)]['kapasite'].sum()

                if not secilen_salon_adlari or not secilen_gozetmenler:
                    st.warning("Lütfen en az bir salon ve gözetmen seçin!")
                elif len(secilen_gozetmenler) < len(secilen_salon_adlari):
                    st.error(f"Kural Hatası: Her salon için en az bir gözetmen olmalı! (En az {len(secilen_salon_adlari)} gözetmen seçin.)")
                elif toplam_kapasite < d_info['ogrenci_sayisi']:
                    st.error(f"Kapasite Hatası: Salon kapasitesi ({toplam_kapasite}) öğrenci sayısından ({d_info['ogrenci_sayisi']}) az olamaz!")
                else:
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            "INSERT INTO Sinav (ders_id, tarih, oturum_id) OUTPUT INSERTED.sinav_id VALUES (?, ?, ?)",
                            (int(d_info['ders_id']), sinav_tarihi, int(o_id))
                        )
                        yeni_id = cursor.fetchone()[0]

                        for s_ad in secilen_salon_adlari:
                            s_id = int(salonlar_df[salonlar_df['ad'] == s_ad]['derslik_id'].values[0])
                            cursor.execute("INSERT INTO Sinav_Salon (sinav_id, derslik_id) VALUES (?, ?)", (yeni_id, s_id))

                        for g_ad in secilen_gozetmenler:
                            g_id = int(personel_df[personel_df['ad_soyad'] == g_ad]['personel_id'].values[0])
                            cursor.execute("INSERT INTO Sinav_Gozetmen (sinav_id, personel_id) VALUES (?, ?)", (yeni_id, g_id))

                        conn.commit() 
                        st.success("Sınav ve tüm atamalar başarıyla kaydedildi!")
                        st.balloons()
                    except Exception as e:
                        conn.rollback()
                        st.error(f"Kayıt sırasında teknik hata: {e}")

    # 3. LİSTELEME VE GÜNCELLEME 
    st.divider()
    st.subheader("📋 Planlanmış Sınavlar")
    try:
        program_df = pd.read_sql("SELECT * FROM vw_SinavProgrami", conn)
        st.dataframe(program_df)
    except:
        st.info("Henüz planlanmış bir sınav bulunmuyor.")
  

     
# --- MODÜL 4: LOGLAR (Trigger Testi) ---
with tab4:
    st.header("Sistem Hareket Kayıtları (Loglar)")
    st.write("Sınav saati veya tarihi değiştiğinde trigger üzerinden kaydedilen veriler:")
    if conn:
        df_logs = pd.read_sql("SELECT * FROM Log_Kayitlari ORDER BY degisim_tarihi DESC", conn)
        if not df_logs.empty:
            st.dataframe(df_logs)
        else:
            st.write("Henüz bir değişiklik kaydı bulunmuyor.")



# --- MODÜL 5: GELİŞMİŞ RAPORLAMA VE İSTATİSTİKLER ---
with tab5:
    st.header("📊 Sınav Programı ve Raporlama")
    
    if conn:
        try:
            df_rapor = pd.read_sql("SELECT * FROM vw_SinavProgrami", conn)
            
            if not df_rapor.empty:
                ders_sutun = next((c for c in df_rapor.columns if 'Ders' in c), None)
                tarih_sutun = next((c for c in df_rapor.columns if 'Tarih' in c), None)

                st.subheader("🔍 Filtreleme")
                f_col1, f_col2 = st.columns(2)

                secilen_dersler = []
                if ders_sutun:
                    secilen_dersler = f_col1.multiselect("Derslere Göre Filtrele:", sorted(df_rapor[ders_sutun].unique()))

                secilen_tarih = f_col2.date_input("Belirli Bir Tarih Seçin:", value=None)
                
                filtered_df = df_rapor.copy()
                
                if secilen_dersler and ders_sutun:
                    filtered_df = filtered_df[filtered_df[ders_sutun].isin(secilen_dersler)]
                
                if secilen_tarih and tarih_sutun:
                    filtered_df[tarih_sutun] = pd.to_datetime(filtered_df[tarih_sutun]).dt.date
                    filtered_df = filtered_df[filtered_df[tarih_sutun] == secilen_tarih]

                st.divider()
                st.dataframe(filtered_df, use_container_width=True, hide_index=True)

                # --- EXCEL / CSV ÇIKTISI ---
                if not filtered_df.empty:
                    csv = filtered_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="📥 Filtrelenmiş Listeyi CSV Olarak İndir",
                        data=csv,
                        file_name='sinav_programi.csv',
                        mime='text/csv',
                    )
            else:
                st.info("Henüz planlanmış bir sınav kaydı bulunmuyor.")

            # --- İSTATİSTİK PANELİ  ---
            st.divider()
            st.subheader("📈 Kullanım İstatistikleri")
            c1, c2 = st.columns(2)

            salon_data = pd.read_sql("""
                SELECT d.ad, COUNT(ss.sinav_id) as SinavSayisi 
                FROM Derslik d 
                LEFT JOIN Sinav_Salon ss ON d.derslik_id = ss.derslik_id 
                GROUP BY d.ad
            """, conn)
            if not salon_data.empty:
                c1.bar_chart(salon_data.set_index('ad'))
                c1.caption("Salonların Toplam Sınav Yükü")

            gozetmen_data = pd.read_sql("""
                SELECT (p.ad + ' ' + p.soyad) as Personel, COUNT(sg.sinav_id) as GorevSayisi 
                FROM Personel p 
                LEFT JOIN Sinav_Gozetmen sg ON p.personel_id = sg.personel_id 
                GROUP BY p.ad, p.soyad
            """, conn)
            if not gozetmen_data.empty:
                c2.line_chart(gozetmen_data.set_index('Personel'))
                c2.caption("Gözetmenlerin Görev Dağılımı")

        except Exception as e:
            st.error(f"Raporlama sekmesinde bir hata oluştu: {e}")