import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Thai Seismic Calculator", layout="wide")

st.title("🏗️ โปรแกรมคำนวณแรงแผ่นดินไหว (มยผ. 1301/1302)")
st.markdown("คำนวณพารามิเตอร์และแรงเฉือนที่ฐานอาคารตามมาตรฐานกรมโยธาธิการและผังเมือง")

# --- ข้อมูลจำลองตาม มยผ. (ควรเพิ่มให้ครบทุกจังหวัด/อำเภอ ในการใช้งานจริง) ---
# รูปแบบ: 'จังหวัด': [Ss, S1]
location_data = {
    'เชียงใหม่ (เมือง)': [0.85, 0.25],
    'เชียงราย (แม่สาย)': [1.20, 0.35],
    'กรุงเทพมหานคร (ชั้นดินเหนียวอ่อน)': [0.10, 0.08], # กทม. จะมีวิธีการคิดเฉพาะ แต่เราใช้ค่าสมมติเพื่อสาธิต
    'ภูเก็ต (เมือง)': [0.15, 0.05]
}

# --- Sidebar สำหรับรับค่า Inputs ---
st.sidebar.header("📝 กรอกข้อมูลอาคาร")

location = st.sidebar.selectbox("เลือกสถานที่ก่อสร้าง", list(location_data.keys()))
site_class = st.sidebar.selectbox("ประเภทชั้นดิน (Site Class)", ['A', 'B', 'C', 'D', 'E'])
importance_factor = st.sidebar.number_input("ตัวคูณความสำคัญของอาคาร (I)", min_value=1.0, max_value=1.5, value=1.0, step=0.25)
r_factor = st.sidebar.number_input("ตัวคูณปรับลดผลตอบสนอง (R)", min_value=1.0, max_value=8.0, value=5.0, step=0.5)
building_weight = st.sidebar.number_input("น้ำหนักรวมของอาคาร W (ตัน)", min_value=0.0, value=1000.0, step=100.0)

# --- คำนวณพารามิเตอร์ ---
Ss, S1 = location_data[location]

# ฟังก์ชันจำลองการหา Fa, Fv (ของจริงต้องเปิดตาราง interpolate ตามค่า Ss, S1 และ Site Class)
def get_fa_fv(site_class, Ss, S1):
    # นี่คือค่าสมมติอย่างง่ายสำหรับการสาธิต
    fa_dict = {'A': 0.8, 'B': 1.0, 'C': 1.2, 'D': 1.4, 'E': 2.5}
    fv_dict = {'A': 0.8, 'B': 1.0, 'C': 1.5, 'D': 2.0, 'E': 3.5}
    return fa_dict[site_class], fv_dict[site_class]

Fa, Fv = get_fa_fv(site_class, Ss, S1)

# คำนวณ Spectral Acceleration
SMS = Fa * Ss
SM1 = Fv * S1
SDS = (2/3) * SMS
SD1 = (2/3) * SM1

# คาบเวลา
T0 = 0.2 * (SD1 / SDS) if SDS > 0 else 0
TS = SD1 / SDS if SDS > 0 else 0

# --- แสดงผลการคำนวณพารามิเตอร์ ---
st.header("📊 ผลการคำนวณพารามิเตอร์")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Ss (g)", f"{Ss:.3f}")
col2.metric("S1 (g)", f"{S1:.3f}")
col3.metric("SDS (g)", f"{SDS:.3f}")
col4.metric("SD1 (g)", f"{SD1:.3f}")

# --- สร้างกราฟ Design Response Spectrum ---
st.subheader("📈 Design Response Spectrum")
T_values = np.linspace(0.0, 4.0, 100)
Sa_values = []

for T in T_values:
    if T < T0:
        Sa = SDS * (0.4 + 0.6 * (T / T0))
    elif T0 <= T <= TS:
        Sa = SDS
    else:
        Sa = SD1 / T
    Sa_values.append(Sa)

chart_data = pd.DataFrame({
    'Period T (sec)': T_values,
    'Spectral Acceleration Sa (g)': Sa_values
})

st.line_chart(chart_data.set_index('Period T (sec)'))

# --- คำนวณ Base Shear ---
st.header("🏢 การคำนวณแรงเฉือนที่ฐาน (Base Shear)")

# คำนวณ Cs
Cs_calculated = SDS / (r_factor / importance_factor)
# เงื่อนไขขั้นต่ำ-สูงสุดของ Cs (ฉบับย่อ)
Cs_max = SD1 / (T_values[20] * (r_factor / importance_factor)) # สมมติใช้ T ที่ 0.8 sec เป็นตัวอย่าง
Cs = min(Cs_calculated, Cs_max) 
Cs = max(Cs, 0.01) # ค่าต่ำสุดตาม มยผ.

V = Cs * building_weight

st.info(f"**สัมประสิทธิ์ผลตอบสนองแผ่นดินไหว (Cs):** {Cs:.4f}")
st.success(f"**แรงเฉือนที่ฐานอาคาร (Base Shear, V):** {V:.2f} ตัน")

st.markdown("---")
st.caption("หมายเหตุ: โปรแกรมนี้เป็นเพียงฉบับร่าง (Draft) เพื่อการสาธิตการทำงานของ Streamlit ตัวเลข Fa, Fv และเงื่อนไข กทม. จำเป็นต้องเขียนโค้ดผูกตารางตาม มยผ. ฉบับเต็มเพิ่มเติม")
