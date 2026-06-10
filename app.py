import streamlit as st
import pandas as pd

# ==========================================
# โหลดฐานข้อมูลสถานที่จาก CSV
# ==========================================
@st.cache_data # ใช้ Cache เพื่อไม่ให้โปรแกรมโหลดไฟล์ CSV ใหม่ทุกครั้งที่คลิก
def load_data():
    return pd.read_csv('seismic_data.csv')

df_location = load_data()

with st.sidebar:
    st.header("⚙️ ข้อมูลสำหรับการออกแบบ")
    st.subheader("1. ตำแหน่งที่ตั้ง")
    
    # ดึงรายชื่อจังหวัดทั้งหมดแบบไม่ซ้ำ
    province_list = df_location['Province'].unique()
    selected_province = st.selectbox("เลือกจังหวัด", province_list)
    
    # กรองรายชื่ออำเภอตามจังหวัดที่เลือก
    district_list = df_location[df_location['Province'] == selected_province]['District']
    selected_district = st.selectbox("เลือกอำเภอ", district_list)

# ==========================================
# ดึงค่า Ss และ S1 ไปคำนวณ
# ==========================================
# ค้นหาข้อมูลแถวที่ตรงกับจังหวัดและอำเภอที่เลือก
location_row = df_location[(df_location['Province'] == selected_province) & 
                           (df_location['District'] == selected_district)].iloc[0]

Ss = float(location_row['Ss'])
S1 = float(location_row['S1'])

# แสดงผลเพื่อตรวจสอบ
st.info(f"📍 **พื้นที่ออกแบบ:** อ.{selected_district} จ.{selected_province} | **Ss** = {Ss} g, **S1** = {S1} g")
