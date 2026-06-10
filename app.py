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
st.markdown("**โปรแกรมคำนวณแรงเฉือนที่ฐานอาคารและสเปกตรัมตอบสนอง ตามมาตรฐานกรมโยธาธิการและผังเมือง**")

# ==========================================
# 2. ฐานข้อมูล (Data)
# ==========================================
# จำลองข้อมูล CSV (ในการใช้งานจริง ให้ลบส่วนนี้และใช้ pd.read_csv('ชื่อไฟล์.csv') แทน)
csv_data = """Province,District,Ss,S1
เชียงราย,เมืองเชียงราย,1.139,0.316
เชียงราย,แม่สาย,1.332,0.370
เชียงราย,แม่สรวย,1.401,0.384
เชียงราย,เชียงแสน,1.107,0.309
เชียงราย,เชียงของ,0.923,0.258
เชียงราย,เวียงป่าเป้า,1.216,0.334
เชียงราย,พาน,1.102,0.303
เชียงใหม่,เมืองเชียงใหม่,0.852,0.244
เชียงใหม่,ฝาง,1.218,0.334
เชียงใหม่,แม่อาย,1.157,0.318
เชียงใหม่,เชียงดาว,1.105,0.305
เชียงใหม่,แม่ริม,0.916,0.261
เชียงใหม่,สันทราย,0.884,0.253
เชียงใหม่,สันกำแพง,0.841,0.240
เชียงใหม่,หางดง,0.803,0.231
เชียงใหม่,จอมทอง,0.613,0.177
แม่ฮ่องสอน,เมืองแม่ฮ่องสอน,0.962,0.227
แม่ฮ่องสอน,ปาย,1.019,0.269
แม่ฮ่องสอน,ปางมะผ้า,1.059,0.270
แม่ฮ่องสอน,ขุนยวม,0.888,0.208
แม่ฮ่องสอน,แม่ลาน้อย,0.837,0.199
แม่ฮ่องสอน,แม่สะเรียง,0.832,0.195
แม่ฮ่องสอน,สบเมย,0.834,0.201
พะเยา,เมืองพะเยา,0.725,0.201
พะเยา,แม่ใจ,0.797,0.156
กาญจนบุรี,เมืองกาญจนบุรี,0.428,0.138
กาญจนบุรี,สังขละบุรี,0.865,0.247
กาญจนบุรี,ทองผาภูมิ,0.790,0.228
กาญจนบุรี,ไทรโยค,0.627,0.187
กาญจนบุรี,ศรีสวัสดิ์,0.686,0.202
พังงา,เมืองพังงา,0.272,0.114
พังงา,กะปง,0.253,0.117
พังงา,เกาะยาว,0.282,0.117
พังงา,คุระบุรี,0.323,0.116
พังงา,ตะกั่วทุ่ง,0.273,0.118
พังงา,ตะกั่วป่า,0.261,0.119
พังงา,ทับปุด,0.267,0.109
พังงา,ท้ายเหมือง,0.267,0.125
ระนอง,เมืองระนอง,0.310,0.098
ระนอง,กระบุรี,0.184,0.089
ระนอง,กะเปอร์,0.352,0.105
ระนอง,ละอุ่น,0.249,0.092
ระนอง,สุขสำราญ,0.355,0.112
ภูเก็ต,เมืองภูเก็ต,0.188,0.068
ภูเก็ต,กะทู้,0.198,0.073
ภูเก็ต,ถลาง,0.205,0.076
สงขลา,เมืองสงขลา,0.085,0.038
สงขลา,หาดใหญ่,0.092,0.042
กรุงเทพมหานคร,ทุกเขต,0.000,0.000
นนทบุรี,ทุกอำเภอ,0.000,0.000
ปทุมธานี,ทุกอำเภอ,0.000,0.000
สมุทรปราการ,ทุกอำเภอ,0.000,0.000
สมุทรสาคร,ทุกอำเภอ,0.000,0.000
กรุงเทพมหานคร,ทุกเขต (ดินเหนียวอ่อน),0.0,0.0"""

@st.cache_data
def load_data():
    # อ่านข้อมูลจาก String ที่จำลองไว้ (เปลี่ยนเป็น pd.read_csv("seismic_data.csv") เมื่อใช้จริง)
    return pd.read_csv(io.StringIO(csv_data))

df_location = load_data()

# ตาราง Fa (Site Coefficient)
FA_TABLE = {
    'Ss_keys': [0.25, 0.50, 0.75, 1.00, 1.25],
    'A': [0.8, 0.8, 0.8, 0.8, 0.8],
    'B': [1.0, 1.0, 1.0, 1.0, 1.0],
    'C': [1.2, 1.2, 1.1, 1.0, 1.0],
    'D': [1.6, 1.4, 1.2, 1.1, 1.0],
    'E': [2.5, 1.7, 1.2, 0.9, 0.9]
}

# ตาราง Fv (Site Coefficient)
FV_TABLE = {
    'S1_keys': [0.10, 0.20, 0.30, 0.40, 0.50],
    'A': [0.8, 0.8, 0.8, 0.8, 0.8],
    'B': [1.0, 1.0, 1.0, 1.0, 1.0],
    'C': [1.7, 1.6, 1.5, 1.4, 1.3],
    'D': [2.4, 2.0, 1.8, 1.6, 1.5],
    'E': [3.5, 3.2, 2.8, 2.4, 2.4]
}

# ==========================================
# 3. ฟังก์ชันการคำนวณทางวิศวกรรม
# ==========================================
def get_site_coefficients(site_class: str, Ss: float, S1: float) -> tuple:
    if site_class == 'F':
        return 0.0, 0.0 # ต้องทำการสำรวจเฉพาะที่ (Site-specific)
        
    try:
        f_fa = interp1d(FA_TABLE['Ss_keys'], FA_TABLE[site_class], kind='linear', fill_value=(FA_TABLE[site_class][0], FA_TABLE[site_class][-1]), bounds_error=False)
        Fa = float(f_fa(Ss))
        
        f_fv = interp1d(FV_TABLE['S1_keys'], FV_TABLE[site_class], kind='linear', fill_value=(FV_TABLE[site_class][0], FV_TABLE[site_class][-1]), bounds_error=False)
        Fv = float(f_fv(S1))
        
        return max(Fa, 0.0), max(Fv, 0.0)
    except Exception as e:
        st.error(f"Error Interpolating: {e}")
        return 1.0, 1.0

def calculate_approx_period(sys_type: str, hn: float) -> float:
    # ค่า Ct และ x สำหรับระบบต้านทานแรงด้านข้างแต่ละประเภท
    params = {
        "โครงต้านทานแรงดัดเหล็กกล้า": (0.0724, 0.8),
        "โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก": (0.0466, 0.9),
        "โครงสร้างต้านทานแรงด้านข้างอื่นๆ": (0.0488, 0.75)
    }
    Ct, x = params.get(sys_type, (0.0488, 0.75))
    return Ct * (hn ** x)

# ==========================================
# 4. ส่วนรับข้อมูลผู้ใช้งาน (Sidebar Inputs)
# ==========================================
with st.sidebar:
    st.header("⚙️ ข้อมูลการออกแบบ")
    
    st.subheader("1. ตำแหน่งที่ตั้ง")
    province_list = df_location['Province'].unique()
    selected_province = st.selectbox("เลือกจังหวัด", province_list)
    
    district_list = df_location[df_location['Province'] == selected_province]['District']
    selected_district = st.selectbox("เลือกอำเภอ", district_list)
    
    site_class = st.selectbox("ประเภทชั้นดิน (Site Class)", ['A', 'B', 'C', 'D', 'E', 'F'], index=3, help="ชั้นดิน F ต้องประเมินเฉพาะพื้นที่")
    
    st.subheader("2. ข้อมูลโครงสร้างอาคาร")
    importance_factor = st.selectbox("ตัวคูณความสำคัญ (Ie)", [1.0, 1.25, 1.5], index=0)
    r_factor = st.number_input("ตัวคูณปรับลดผลตอบสนอง (R)", min_value=1.0, max_value=8.0, value=5.0, step=0.5)
    
    sys_type = st.selectbox("ระบบโครงสร้าง (สำหรับหา Ta)", [
        "โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก",
        "โครงต้านทานแรงดัดเหล็กกล้า",
        "โครงสร้างต้านทานแรงด้านข้างอื่นๆ"
    ])
    
    st.subheader("3. มิติและน้ำหนักอาคาร")
    building_height = st.number_input("ความสูงอาคาร hn (เมตร)", min_value=1.0, value=15.0, step=1.0)
    building_weight = st.number_input("น้ำหนักรวมอาคาร W (ตัน)", min_value=1.0, value=1000.0, step=100.0)

# ==========================================
# 5. การประมวลผลและการแสดงผล
# ==========================================
# ดักจับกรณีกรุงเทพมหานคร (ต้องใช้ Response Spectrum เฉพาะตาม มยผ.)
if selected_province == "กรุงเทพมหานคร":
    st.warning("⚠️ **คำเตือนทางวิศวกรรม:** สำหรับพื้นที่กรุงเทพมหานครและปริมณฑล (ชั้นดินเหนียวอ่อน) มาตรฐาน มยผ. กำหนดให้ใช้กราฟสเปกตรัมตอบสนองแบบเฉพาะเจาะจง (Site-specific Response Spectrum) ตามระยะห่างจากรอยเลื่อน ไม่สามารถใช้วิธีหา Fa, Fv แบบปกติได้ โปรดอ้างอิง มยผ. 1302 โดยตรง")
    st.stop() # หยุดรันโค้ดส่วนด้านล่าง

if site_class == 'F':
    st.error("🛑 ชั้นดินประเภท F ต้องการการประเมินการตอบสนองเฉพาะพื้นที่ (Site-Specific Evaluation) ไม่สามารถคำนวณผ่านพารามิเตอร์ปกติได้")
    st.stop()

# ดึงค่าพารามิเตอร์ของพื้นที่
location_row = df_location[(df_location['Province'] == selected_province) & (df_location['District'] == selected_district)].iloc[0]
Ss = float(location_row['Ss'])
S1 = float(location_row['S1'])

st.info(f"📍 **พื้นที่ออกแบบ:** อ.{selected_district} จ.{selected_province} | **Ss** = {Ss} g, **S1** = {S1} g")

# คำนวณทางวิศวกรรม
Fa, Fv = get_site_coefficients(site_class, Ss, S1)
SMS = Fa * Ss
SM1 = Fv * S1
SDS = (2/3) * SMS
SD1 = (2/3) * SM1

T0 = 0.2 * (SD1 / SDS) if SDS > 0 else 0
TS = SD1 / SDS if SDS > 0 else 0

Ta = calculate_approx_period(sys_type, building_height)

# คำนวณ Base Shear Coefficient (Cs)
Cs_calculated = SDS / (r_factor / importance_factor)
Cs_max = SD1 / (Ta * (r_factor / importance_factor)) if Ta > 0 else Cs_calculated
Cs_min = 0.01 # ค่าควบคุมต่ำสุดทั่วไปตาม มยผ. (ไม่รวมกรณี S1 >= 0.6g ซึ่งต้องใช้ 0.5S1/(R/Ie))

# อัปเดต Cs_min หากพื้นที่มีความเสี่ยงสูงมาก (S1 >= 0.6g)
if S1 >= 0.6:
    Cs_min_high_risk = (0.5 * S1) / (r_factor / importance_factor)
    Cs_min = max(Cs_min, Cs_min_high_risk)

Cs_design = min(max(Cs_calculated, Cs_min), Cs_max)
Base_Shear = Cs_design * building_weight

# จัดหน้าจอเป็น Tabs
tab1, tab2, tab3 = st.tabs(["📊 พารามิเตอร์การออกแบบ", "📈 กราฟสเปกตรัม (Response Spectrum)", "🏢 แรงเฉือนที่ฐาน (Base Shear)"])

with tab1:
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Site Coefficient Fa", f"{Fa:.3f}")
    col2.metric("Site Coefficient Fv", f"{Fv:.3f}")
    col3.metric("SDS (g)", f"{SDS:.3f}")
    col4.metric("SD1 (g)", f"{SD1:.3f}")
    
    st.markdown("---")
    st.markdown(f"**คาบเวลาโครงสร้างโดยประมาณ (Ta):** {Ta:.3f} วินาที")
    st.markdown(f"**คาบเวลาเปลี่ยนผ่าน T0:** {T0:.3f} วินาที | **TS:** {TS:.3f} วินาที")

with tab2:
    T_values = np.linspace(0.0, max(4.0, Ta * 1.5), 300)
    Sa_values = np.piecewise(
        T_values,
        [T_values < T0, (T0 <= T_values) & (T_values <= TS), T_values > TS],
        [lambda T: SDS * (0.4 + 0.6 * (T / T0)), 
         SDS, 
         lambda T: SD1 / T]
    )
    
    chart_data = pd.DataFrame({'คาบเวลา T (วินาที)': T_values, 'ความเร่งตอบสนอง Sa (g)': Sa_values})
    st.line_chart(chart_data.set_index('คาบเวลา T (วินาที)'), use_container_width=True)

with tab3:
    st.markdown("### สมการแรงเฉือนที่ฐานอาคาร")
    st.latex(r"C_s = \frac{S_{DS}}{R / I_e}")
    st.latex(r"V = C_s W")
    
    st.markdown("---")
    st.markdown(f"- **Cs (จากการคำนวณ):** {Cs_calculated:.4f}")
    st.markdown(f"- **Cs (สูงสุดที่ยอมให้ใช้):** {Cs_max:.4f}")
    st.markdown(f"- **Cs (ต่ำสุดตามมาตรฐาน):** {Cs_min:.4f}")
    
    st.success(f"**สัมประสิทธิ์การออกแบบที่เลือกใช้ (Cs Design): {Cs_design:.4f}**")
    st.error(f"**แรงเฉือนที่ฐานอาคาร (Base Shear, V): {Base_Shear:,.2f} ตัน**")
