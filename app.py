import streamlit as st
import pandas as pd
import numpy as np
import io
from scipy.interpolate import interp1d

# ==========================================
# 1. การตั้งค่าหน้าจอและ UI
# ==========================================
st.set_page_config(page_title="DPT Seismic Calculator", page_icon="🏢", layout="wide")
st.title("🏢 โปรแกรมคำนวณแรงแผ่นดินไหว (มยผ. 1301/1302)")
st.markdown("**โปรแกรมคำนวณแรงเฉือนที่ฐานอาคารและประเมินประเภทการออกแบบต้านทานแผ่นดินไหว**")

# ==========================================
# 2. ฐานข้อมูล (Data)
# ==========================================
csv_data = """Province,District,Ss,S1
เชียงราย,เมืองเชียงราย,1.139,0.316
เชียงราย,แม่สาย,1.332,0.370
เชียงใหม่,เมืองเชียงใหม่,0.852,0.244
เชียงใหม่,ฝาง,1.218,0.334
แม่ฮ่องสอน,ปาย,1.019,0.269
กาญจนบุรี,เมืองกาญจนบุรี,0.428,0.138
ภูเก็ต,เมืองภูเก็ต,0.188,0.068
สงขลา,เมืองสงขลา,0.085,0.038
กรุงเทพมหานคร,ทุกเขต (ดินเหนียวอ่อน),0.0,0.0"""

@st.cache_data
def load_data():
    return pd.read_csv(io.StringIO(csv_data))

df_location = load_data()

FA_TABLE = {
    'Ss_keys': [0.25, 0.50, 0.75, 1.00, 1.25],
    'A': [0.8, 0.8, 0.8, 0.8, 0.8], 'B': [1.0, 1.0, 1.0, 1.0, 1.0],
    'C': [1.2, 1.2, 1.1, 1.0, 1.0], 'D': [1.6, 1.4, 1.2, 1.1, 1.0], 'E': [2.5, 1.7, 1.2, 0.9, 0.9]
}
FV_TABLE = {
    'S1_keys': [0.10, 0.20, 0.30, 0.40, 0.50],
    'A': [0.8, 0.8, 0.8, 0.8, 0.8], 'B': [1.0, 1.0, 1.0, 1.0, 1.0],
    'C': [1.7, 1.6, 1.5, 1.4, 1.3], 'D': [2.4, 2.0, 1.8, 1.6, 1.5], 'E': [3.5, 3.2, 2.8, 2.4, 2.4]
}

# ==========================================
# 3. ฟังก์ชันการคำนวณทางวิศวกรรม
# ==========================================
def get_site_coefficients(site_class: str, Ss: float, S1: float) -> tuple:
    if site_class == 'F': return 0.0, 0.0
    try:
        f_fa = interp1d(FA_TABLE['Ss_keys'], FA_TABLE[site_class], kind='linear', fill_value=(FA_TABLE[site_class][0], FA_TABLE[site_class][-1]), bounds_error=False)
        f_fv = interp1d(FV_TABLE['S1_keys'], FV_TABLE[site_class], kind='linear', fill_value=(FV_TABLE[site_class][0], FV_TABLE[site_class][-1]), bounds_error=False)
        return max(float(f_fa(Ss)), 0.0), max(float(f_fv(S1)), 0.0)
    except Exception:
        return 1.0, 1.0

def calculate_approx_period(sys_type: str, hn: float) -> float:
    params = {"โครงต้านทานแรงดัดเหล็กกล้า": (0.0724, 0.8), "โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก": (0.0466, 0.9), "โครงสร้างอื่นๆ": (0.0488, 0.75)}
    Ct, x = params.get(sys_type, (0.0488, 0.75))
    return Ct * (hn ** x)

def evaluate_sdc(SDS: float, SD1: float, Ie: float) -> str:
    is_essential = (Ie >= 1.5)
    
    if SDS < 0.167: sdc_sds = 'ก'
    elif SDS < 0.33: sdc_sds = 'ค' if is_essential else 'ข'
    elif SDS < 0.50: sdc_sds = 'ง' if is_essential else 'ค'
    else: sdc_sds = 'ง'
        
    if SD1 < 0.067: sdc_sd1 = 'ก'
    elif SD1 < 0.133: sdc_sd1 = 'ค' if is_essential else 'ข'
    elif SD1 < 0.20: sdc_sd1 = 'ง' if is_essential else 'ค'
    else: sdc_sd1 = 'ง'
        
    sdc_order = {'ก': 1, 'ข': 2, 'ค': 3, 'ง': 4}
    max_val = max(sdc_order[sdc_sds], sdc_order[sdc_sd1])
    
    for cat, val in sdc_order.items():
        if val == max_val: return cat
    return 'ก'

# ==========================================
# 4. ส่วนรับข้อมูลผู้ใช้งาน (Sidebar Inputs)
# ==========================================
with st.sidebar:
    st.header("⚙️ ข้อมูลการออกแบบ")
    
    st.subheader("1. ข้อมูลสถานที่ตั้ง")
    # เพิ่มตัวเลือกว่าจะกรอกเองหรือดึงจากฐานข้อมูล
    input_method = st.radio("รูปแบบการนำเข้าพารามิเตอร์", ["ดึงจากฐานข้อมูล", "กรอกค่า Ss, S1 ด้วยตนเอง"])
    
    if input_method == "ดึงจากฐานข้อมูล":
        province_list = df_location['Province'].unique()
        selected_province = st.selectbox("เลือกจังหวัด", province_list)
        district_list = df_location[df_location['Province'] == selected_province]['District']
        selected_district = st.selectbox("เลือกอำเภอ", district_list)
    else:
        selected_province = "กำหนดเอง"
        selected_district = "กำหนดเอง"
        manual_Ss = st.number_input("ค่า Ss (g)", min_value=0.000, max_value=3.000, value=0.500, step=0.010, format="%.3f")
        manual_S1 = st.number_input("ค่า S1 (g)", min_value=0.000, max_value=2.000, value=0.200, step=0.010, format="%.3f")
    
    site_class = st.selectbox("ประเภทชั้นดิน", ['A', 'B', 'C', 'D', 'E', 'F'], index=3)
    
    st.subheader("2. ข้อมูลโครงสร้าง")
    importance_factor = st.selectbox("ตัวคูณความสำคัญ (Ie)", [1.0, 1.25, 1.5], index=0)
    r_factor = st.number_input("ตัวคูณปรับลดผลตอบสนอง (R)", min_value=1.0, max_value=8.0, value=5.0, step=0.5)
    sys_type = st.selectbox("ระบบโครงสร้าง (หา Ta)", ["โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก", "โครงต้านทานแรงดัดเหล็กกล้า", "โครงสร้างอื่นๆ"])
    
    st.subheader("3. มิติและน้ำหนัก")
    building_height = st.number_input("ความสูงอาคาร hn (เมตร)", min_value=1.0, value=10.0, step=1.0)
    building_weight = st.number_input("น้ำหนักรวม W (ตัน)", min_value=1.0, value=500.0, step=100.0)

# ==========================================
# 5. ประมวลผลและตรวจสอบเงื่อนไข
# ==========================================
if site_class == 'F':
    st.error("🛑 ชั้นดิน F ต้องเจาะสำรวจประเมินเฉพาะพื้นที่ (Site-Specific) เท่านั้น ไม่สามารถใช้ค่าคำนวณมาตรฐานได้")
    st.stop()

# ประมวลผลค่า Ss และ S1 ตามเงื่อนไขที่เลือก
if input_method == "ดึงจากฐานข้อมูล":
    if selected_province == "กรุงเทพมหานคร":
        st.warning("⚠️ สำหรับพื้นที่ดินเหนียวอ่อนกรุงเทพฯ ต้องใช้ Response Spectrum เฉพาะตาม มยผ. 1302 โปรดอ้างอิงกราฟจากมาตรฐานโดยตรง")
        st.stop()
    location_row = df_location[(df_location['Province'] == selected_province) & (df_location['District'] == selected_district)].iloc[0]
    Ss = float(location_row['Ss'])
    S1 = float(location_row['S1'])
else:
    Ss = float(manual_Ss)
    S1 = float(manual_S1)

Fa, Fv = get_site_coefficients(site_class, Ss, S1)
SDS = (2/3) * (Fa * Ss)
SD1 = (2/3) * (Fv * S1)

T0 = 0.2 * (SD1 / SDS) if SDS > 0 else 0
TS = SD1 / SDS if SDS > 0 else 0
Ta = calculate_approx_period(sys_type, building_height)

# ประเมินประเภทการออกแบบแผ่นดินไหว (SDC)
sdc = evaluate_sdc(SDS, SD1, importance_factor)

st.header("🛡️ ผลการประเมินประเภทการออกแบบ (Seismic Design Category)")

if sdc == 'ก':
    st.success(f"✅ **อาคารนี้จัดอยู่ในประเภทการออกแบบ: '{sdc}' (SDC A) - ความเสี่ยงต่ำมาก**")
    st.info("💡 **ข้อกำหนด มยผ.:** อาคารประเภท 'ก' ไม่ต้องวิเคราะห์แรงแผ่นดินไหวแบบเต็มรูปแบบ ให้คิดแรงกระทำด้านข้างอย่างน้อย **1% ของน้ำหนักอาคาร ($0.01W$)** ก็เพียงพอ")
    v_min_sdc_a = 0.01 * building_weight
    st.metric("แรงเฉือนที่ฐานขั้นต่ำ (1% W)", f"{v_min_sdc_a:,.2f} ตัน")
    st.stop()
else:
    st.warning(f"⚠️ **อาคารนี้จัดอยู่ในประเภทการออกแบบ: '{sdc}'**")
    st.markdown(f"**ต้องวิเคราะห์แรงแผ่นดินไหวเต็มรูปแบบ** เนื่องจากค่า $S_{{DS}}$ และ $S_{{D1}}$ เกินเกณฑ์ยกเว้น โปรดดูผลการคำนวณด้านล่าง")

st.markdown("---")

# ==========================================
# 6. การแสดงผล (กรณี SDC เป็น ข, ค, ง)
# ==========================================
Cs_calculated = SDS / (r_factor / importance_factor)
Cs_max = SD1 / (Ta * (r_factor / importance_factor)) if Ta > 0 else Cs_calculated
Cs_min = 0.01
if S1 >= 0.6: Cs_min = max(Cs_min, (0.5 * S1) / (r_factor / importance_factor))

Cs_design = min(max(Cs_calculated, Cs_min), Cs_max)
Base_Shear = Cs_design * building_weight

tab1, tab2, tab3 = st.tabs(["📋 รายการคำนวณพารามิเตอร์", "📈 กราฟสเปกตรัม", "🏢 แรงเฉือนที่ฐาน"])

with tab1:
    st.header("📋 รายการคำนวณพารามิเตอร์ (Step-by-Step)")
    st.markdown("แสดงลำดับการคำนวณพารามิเตอร์การตอบสนองเชิงสเปกตรัมตามมาตรฐาน **มยผ. 1301/1302**")
    
    st.subheader("1. ความเร่งตอบสนองเชิงสเปกตรัมระดับหินฐาน")
    if input_method == "ดึงจากฐานข้อมูล":
        st.markdown(f"อ้างอิงจากแผนที่เสี่ยงภัยแผ่นดินไหว (สถานที่: อ.**{selected_district}** จ.**{selected_province}**)")
    else:
        st.markdown("อ้างอิงจาก **ข้อมูลพารามิเตอร์ที่ผู้ใช้งานกำหนดเอง**")
        
    col1, col2 = st.columns(2)
    col1.metric("Ss (ความเร่งที่คาบ 0.2 วินาที)", f"{Ss:.3f} g")
    col2.metric("S1 (ความเร่งที่คาบ 1.0 วินาที)", f"{S1:.3f} g")
    
    st.divider()
    
    st.subheader("2. ตัวคูณขยายอิทธิพลของชั้นดิน (Site Coefficients)")
    st.markdown(f"ประเมินสำหรับชั้นดินประเภท **{site_class}** (ใช้วิธี Linear Interpolation จากตารางมาตรฐาน)")
    col3, col4 = st.columns(2)
    col3.metric(f"Fa (พิจารณาจาก Ss = {Ss:.3f})", f"{Fa:.3f}")
    col4.metric(f"Fv (พิจารณาจาก S1 = {S1:.3f})", f"{Fv:.3f}")
    
    st.divider()
    
    st.subheader("3. ความเร่งสเปกตรัมตอบสนองสำหรับการออกแบบ")
    st.markdown("คำนวณปรับแก้พารามิเตอร์เพื่อใช้ในการสร้างกราฟและหาแรงเฉือนที่ฐานอาคาร")
    
    col_eq1, col_eq2 = st.columns(2)
    SMS = Fa * Ss
    SM1 = Fv * S1
    
    with col_eq1:
        st.info("🔹 **การพิจารณาช่วงคาบสั้น (0.2 วินาที)**")
        st.latex(r"S_{MS} = F_a S_S" + rf" = {Fa:.3f} \times {Ss:.3f} = {SMS:.3f} \text{{ g}}")
        st.latex(r"S_{DS} = \frac{2}{3} S_{MS}" + rf" = \frac{{2}}{{3}} \times {SMS:.3f} = {SDS:.3f} \text{{ g}}")
        
    with col_eq2:
        st.info("🔹 **การพิจารณาช่วงคาบยาว (1.0 วินาที)**")
        st.latex(r"S_{M1} = F_v S_1" + rf" = {Fv:.3f} \times {S1:.3f} = {SM1:.3f} \text{{ g}}")
        st.latex(r"S_{D1} = \frac{2}{3} S_{M1}" + rf" = \frac{{2}}{{3}} \times {SM1:.3f} = {SD1:.3f} \text{{ g}}")

    st.divider()
    
    st.subheader("4. คาบเวลาโครงสร้างและจุดควบคุมกราฟสเปกตรัม")
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.success("🏗️ **คาบเวลาโครงสร้างโดยประมาณ ($T_a$)**")
        st.markdown(f"ระบบโครงสร้าง: **{sys_type}**")
        
        params = {"โครงต้านทานแรงดัดเหล็กกล้า": (0.0724, 0.8), "โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก": (0.0466, 0.9), "โครงสร้างอื่นๆ": (0.0488, 0.75)}
        Ct, x = params.get(sys_type, (0.0488, 0.75))
        
        st.latex(r"T_a = C_t h_n^x" + rf" = {Ct} \times {building_height}^{{{x}}} = {Ta:.3f} \text{{ s}}")
        
    with col_t2:
        st.warning("📈 **จุดเปลี่ยนผ่านบนกราฟ ($T_0, T_S$)**")
        if SDS > 0:
            st.latex(r"T_S = \frac{S_{D1}}{S_{DS}}" + rf" = \frac{{{SD1:.3f}}}{{{SDS:.3f}}} = {TS:.3f} \text{{ s}}")
            st.latex(r"T_0 = 0.2 T_S" + rf" = 0.2 \times {TS:.3f} = {T0:.3f} \text{{ s}}")
        else:
            st.latex(r"T_S = 0.000 \text{ s}")
            st.latex(r"T_0 = 0.000 \text{ s}")

with tab2:
    T_values = np.linspace(0.0, max(4.0, Ta * 1.5), 300)
    Sa_values = np.piecewise(
        T_values,
        [T_values < T0, (T0 <= T_values) & (T_values <= TS), T_values > TS],
        [lambda T: SDS * (0.4 + 0.6 * (T / T0)), SDS, lambda T: SD1 / T]
    )
    chart_data = pd.DataFrame({'คาบเวลา T (sec)': T_values, 'Sa (g)': Sa_values})
    st.line_chart(chart_data.set_index('คาบเวลา T (sec)'), use_container_width=True)

with tab3:
    st.latex(r"C_s = \frac{S_{DS}}{R / I_e}")
    st.latex(r"V = C_s W")
    st.markdown(f"- **Cs (จากการคำนวณ):** {Cs_calculated:.4f}")
    st.markdown(f"- **Cs (สูงสุด/ต่ำสุด):** {Cs_max:.4f} / {Cs_min:.4f}")
    st.success(f"**สัมประสิทธิ์การออกแบบ (Cs): {Cs_design:.4f}**")
    st.error(f"**แรงเฉือนที่ฐานอาคาร (V) = {Base_Shear:,.2f} ตัน**")
