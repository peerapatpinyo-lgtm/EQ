import streamlit as st
import pandas as pd
import numpy as np
from scipy.interpolate import interp1d

# ==========================================
# 1. การตั้งค่าหน้าจอ (UI Configuration)
# ==========================================
st.set_page_config(page_title="DPT 1301/1302 Seismic Calculator", page_icon="🏢", layout="wide")

st.title("🏢 DPT Seismic Design Calculator")
st.markdown("**โปรแกรมคำนวณแรงเฉือนที่ฐานอาคารและสเปกตรัมตอบสนอง ตามมาตรฐาน มยผ. 1301/1302**")

# ==========================================
# 2. ฐานข้อมูลและค่าคงที่ (อ้างอิง มยผ.)
# ==========================================
# หมายเหตุ: ในการใช้งานจริง ควรแยกข้อมูลเหล่านี้เป็นไฟล์ .csv หรือ .json
LOCATION_DB = {
    'เชียงใหม่ (เมือง)': {'Ss': 0.85, 'S1': 0.25},
    'เชียงราย (แม่สาย)': {'Ss': 1.20, 'S1': 0.35},
    'กรุงเทพมหานคร (ชั้นดินเหนียวอ่อน)': {'Ss': 0.10, 'S1': 0.08}, # ต้องใช้ค่าตามสเปกตรัมเฉพาะของ กทม.
    'ภูเก็ต (เมือง)': {'Ss': 0.15, 'S1': 0.05}
}

# ตาราง Fa (Site Coefficient) แบบย่อ เพื่อการ Interpolation
FA_TABLE = {
    'Ss_keys': [0.25, 0.50, 0.75, 1.00, 1.25],
    'A': [0.8, 0.8, 0.8, 0.8, 0.8],
    'B': [1.0, 1.0, 1.0, 1.0, 1.0],
    'C': [1.2, 1.2, 1.1, 1.0, 1.0],
    'D': [1.6, 1.4, 1.2, 1.1, 1.0],
    'E': [2.5, 1.7, 1.2, 0.9, 0.9]
}

# ตาราง Fv (Site Coefficient) แบบย่อ เพื่อการ Interpolation
FV_TABLE = {
    'S1_keys': [0.10, 0.20, 0.30, 0.40, 0.50],
    'A': [0.8, 0.8, 0.8, 0.8, 0.8],
    'B': [1.0, 1.0, 1.0, 1.0, 1.0],
    'C': [1.7, 1.6, 1.5, 1.4, 1.3],
    'D': [2.4, 2.0, 1.8, 1.6, 1.5],
    'E': [3.5, 3.2, 2.8, 2.4, 2.4]
}

# ==========================================
# 3. ฟังก์ชันการคำนวณทางวิศวกรรม (Engineering Logic)
# ==========================================
def get_site_coefficients(site_class: str, Ss: float, S1: float) -> tuple:
    """ฟังก์ชันคำนวณหา Fa และ Fv โดยใช้ Linear Interpolation ตามมาตรฐาน"""
    try:
        # Interpolate Fa
        f_fa = interp1d(FA_TABLE['Ss_keys'], FA_TABLE[site_class], kind='linear', fill_value="extrapolate")
        Fa = float(f_fa(Ss))
        
        # Interpolate Fv
        f_fv = interp1d(FV_TABLE['S1_keys'], FV_TABLE[site_class], kind='linear', fill_value="extrapolate")
        Fv = float(f_fv(S1))
        
        return max(Fa, 0.0), max(Fv, 0.0) # ป้องกันค่าติดลบจากการ extrapolate
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการ Interpolate ค่า Fa, Fv: {e}")
        return 1.0, 1.0

def calculate_approx_period(Ct: float, hn: float, x: float) -> float:
    """คำนวณคาบเวลาพื้นฐานโดยประมาณ (Ta)"""
    return Ct * (hn ** x)

# ==========================================
# 4. ส่วนติดต่อผู้ใช้งาน (User Interface)
# ==========================================
with st.sidebar:
    st.header("⚙️ ข้อมูลสำหรับการออกแบบ")
    
    st.subheader("1. ตำแหน่งที่ตั้งและชั้นดิน")
    location = st.selectbox("สถานที่ก่อสร้าง", list(LOCATION_DB.keys()))
    site_class = st.selectbox("ประเภทชั้นดิน (Site Class)", ['A', 'B', 'C', 'D', 'E'], index=3)
    
    st.subheader("2. ข้อมูลโครงสร้างอาคาร")
    importance_factor = st.selectbox("ตัวคูณความสำคัญ (Ie)", [1.0, 1.25, 1.5], index=0)
    r_factor = st.number_input("ตัวคูณปรับลดผลตอบสนอง (R)", min_value=1.0, max_value=8.0, value=5.0, step=0.5)
    
    st.subheader("3. น้ำหนักและมิติอาคาร")
    building_weight = st.number_input("น้ำหนักรวมอาคาร W (ตัน)", min_value=1.0, value=1500.0, step=100.0)
    building_height = st.number_input("ความสูงอาคาร hn (เมตร)", min_value=1.0, value=15.0, step=1.0)
    
    st.markdown("---")
    st.info("💡 **คำแนะนำ:** ตรวจสอบค่า R และ Ie ให้สอดคล้องกับระบบต้านทานแรงด้านข้างตาม มยผ. 1302")

# ==========================================
# 5. การประมวลผล (Processing)
# ==========================================
Ss = LOCATION_DB[location]['Ss']
S1 = LOCATION_DB[location]['S1']

Fa, Fv = get_site_coefficients(site_class, Ss, S1)

# คำนวณค่าพารามิเตอร์
SMS = Fa * Ss
SM1 = Fv * S1
SDS = (2/3) * SMS
SD1 = (2/3) * SM1

T0 = 0.2 * (SD1 / SDS) if SDS > 0 else 0
TS = SD1 / SDS if SDS > 0 else 0

# คำนวณคาบเวลา Ta (สมมติฐานโครงสร้างคอนกรีตเสริมเหล็กทนแรงดัด Ct=0.0466, x=0.9)
Ta = calculate_approx_period(Ct=0.0466, hn=building_height, x=0.9)

# คำนวณ Cs
Cs_calculated = SDS / (r_factor / importance_factor)
Cs_max = SD1 / (Ta * (r_factor / importance_factor)) if Ta > 0 else Cs_calculated
Cs_min = 0.01

Cs_design = min(max(Cs_calculated, Cs_min), Cs_max)
Base_Shear = Cs_design * building_weight

# ==========================================
# 6. การแสดงผล (Results Display)
# ==========================================
tab1, tab2, tab3 = st.tabs(["📊 พารามิเตอร์การออกแบบ", "📈 สเปกตรัมตอบสนอง", "🏢 แรงเฉือนที่ฐานอาคาร"])

with tab1:
    st.subheader("ค่าพารามิเตอร์ความเร่งตอบสนอง (อ้างอิง Site Class)")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ss (g)", f"{Ss:.3f}")
    col2.metric("S1 (g)", f"{S1:.3f}")
    col3.metric("Fa", f"{Fa:.3f}")
    col4.metric("Fv", f"{Fv:.3f}")
    
    st.markdown("---")
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("SMS (g)", f"{SMS:.3f}")
    col6.metric("SM1 (g)", f"{SM1:.3f}")
    col7.metric("SDS (g)", f"{SDS:.3f}", help="ความเร่งสเปกตรัมออกแบบที่คาบสั้น")
    col8.metric("SD1 (g)", f"{SD1:.3f}", help="ความเร่งสเปกตรัมออกแบบที่คาบ 1 วินาที")

with tab2:
    st.subheader("Design Response Spectrum (กราฟสเปกตรัมตอบสนองการออกแบบ)")
    
    T_values = np.linspace(0.0, 4.0, 200)
    Sa_values = np.piecewise(
        T_values,
        [T_values < T0, (T0 <= T_values) & (T_values <= TS), T_values > TS],
        [lambda T: SDS * (0.4 + 0.6 * (T / T0)), 
         SDS, 
         lambda T: SD1 / T]
    )
    
    chart_data = pd.DataFrame({
        'คาบเวลา T (วินาที)': T_values,
        'ความเร่งตอบสนอง Sa (g)': Sa_values
    })
    
    st.line_chart(chart_data.set_index('คาบเวลา T (วินาที)'), use_container_width=True)
    st.caption(f"จุดเปลี่ยนกราฟ: T0 = {T0:.3f} s, TS = {TS:.3f} s")

with tab3:
    st.subheader("ผลการคำนวณแรงเฉือนที่ฐาน (Base Shear Calculation)")
    
    st.markdown("จากสมการตามมาตรฐาน:")
    st.latex(r"C_s = \frac{S_{DS}}{R / I_e}")
    st.latex(r"V = C_s W")
    
    # สรุปตัวแปร
    st.markdown(f"- **คาบเวลาโครงสร้างโดยประมาณ ($T_a$):** {Ta:.3f} วินาที")
    st.markdown(f"- **สัมประสิทธิ์ผลตอบสนอง ($C_s$) ที่คำนวณได้:** {Cs_calculated:.4f}")
    st.markdown(f"- **$C_s$ สูงสุดตามข้อกำหนด (Max):** {Cs_max:.4f}")
    st.markdown(f"- **$C_s$ ต่ำสุดตามข้อกำหนด (Min):** {Cs_min:.4f}")
    
    st.success(f"**สัมประสิทธิ์ที่ใช้ในการออกแบบ ($C_s$ Design): {Cs_design:.4f}**")
    st.error(f"**แรงเฉือนที่ฐานอาคาร (V) = {Base_Shear:,.2f} ตัน**")
