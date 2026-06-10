import streamlit as st
import pandas as pd
import numpy as np

# นำเข้าโมดูลที่แยกฟังก์ชันออกมา
from data_loader import load_data
import calculations as calc
import plots

# ==========================================
# การตั้งค่าหน้าจอและ UI ตั้งต้น
# ==========================================
st.set_page_config(page_title="DPT Seismic Calculator", page_icon="🏢", layout="wide")
st.title("🏢 โปรแกรมคำนวณแรงแผ่นดินไหว (มยผ. 1301/1302)")
st.markdown("**โปรแกรมคำนวณแรงเฉือนที่ฐานอาคารและประเมินประเภทการออกแบบต้านทานแผ่นดินไหว**")

df_location = load_data()

# ==========================================
# ส่วนรับข้อมูลผู้ใช้งาน (Sidebar Inputs)
# ==========================================
with st.sidebar:
    st.header("⚙️ ข้อมูลการออกแบบ")

    st.subheader("1. ข้อมูลสถานที่ตั้ง")
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
    sys_type = st.selectbox(
        "ระบบโครงสร้าง (หา Ta)",
        ["โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก", "โครงต้านทานแรงดัดเหล็กกล้า", "โครงสร้างอื่นๆ"]
    )

    st.subheader("3. มิติและน้ำหนัก")
    building_height = st.number_input("ความสูงอาคาร hn (เมตร)", min_value=1.0, value=10.0, step=1.0)
    building_weight = st.number_input("น้ำหนักรวม W (ตัน)", min_value=1.0, value=500.0, step=100.0)

# ==========================================
# ตรวจสอบเงื่อนไขตั้งต้นและการจัดการ Error
# ==========================================
if site_class == 'F':
    st.error("🛑 ชั้นดิน F ต้องเจาะสำรวจประเมินเฉพาะพื้นที่ (Site-Specific) เท่านั้น ไม่สามารถใช้ค่าคำนวณมาตรฐานได้")
    st.stop()

if input_method == "ดึงจากฐานข้อมูล":
    if selected_province == "กรุงเทพมหานคร":
        st.warning("⚠️ สำหรับพื้นที่ดินเหนียวอ่อนกรุงเทพฯ ต้องใช้ Response Spectrum เฉพาะตาม มยผ. 1302 โปรดอ้างอิงกราฟจากมาตรฐานโดยตรง")
        st.stop()
    location_row = df_location[
        (df_location['Province'] == selected_province) & (df_location['District'] == selected_district)
    ].iloc[0]
    Ss = float(location_row['Ss'])
    S1 = float(location_row['S1'])
else:
    Ss = float(manual_Ss)
    S1 = float(manual_S1)

# เรียกใช้ Pure Engine Calculations
Fa, Fv = calc.get_site_coefficients(site_class, Ss, S1)
SMS = Fa * Ss
SM1 = Fv * S1
SDS = (2.0 / 3.0) * SMS
SD1 = (2.0 / 3.0) * SM1

T0 = 0.2 * (SD1 / SDS) if SDS > 0 else 0.0
TS = SD1 / SDS if SDS > 0 else 0.0
Ta = calc.calculate_approx_period(sys_type, building_height)

sdc, sdc_sds, sdc_sd1 = calc.evaluate_sdc_detailed(SDS, SD1, importance_factor)

# ==========================================
# จัดการแท็บการแสดงผลหลัก (Main Tabs Display)
# ==========================================
st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 รายการคำนวณพารามิเตอร์",
    "🛡️ ประเภทการออกแบบ (SDC)",
    "📈 กราฟสเปกตรัม",
    "🏢 แรงเฉือนที่ฐาน"
])

# ─────────────────────────── TAB 1 ───────────────────────────
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
    col_eq1, col_eq2 = st.columns(2)
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
        params_dict = {"โครงต้านทานแรงดัดเหล็กกล้า": (0.0724, 0.8), "โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก": (0.0466, 0.9), "โครงสร้างอื่นๆ": (0.0488, 0.75)}
        Ct, x_exp = params_dict.get(sys_type, (0.0488, 0.75))
        st.latex(r"T_a = C_t h_n^x" + rf" = {Ct} \times {building_height}^{{{x_exp}}} = {Ta:.3f} \text{{ s}}")
    with col_t2:
        st.warning("📈 **จุดเปลี่ยนผ่านบนกราฟ ($T_0, T_S$)**")
        if SDS > 0:
            st.latex(r"T_S = \frac{S_{D1}}{S_{DS}}" + rf" = \frac{{{SD1:.3f}}}{{{SDS:.3f}}} = {TS:.3f} \text{{ s}}")
            st.latex(r"T_0 = 0.2 T_S" + rf" = 0.2 \times {TS:.3f} = {T0:.3f} \text{{ s}}")
        else:
            st.latex(r"T_S = 0.000 \text{ s}")
            st.latex(r"T_0 = 0.000 \text{ s}")

# ─────────────────────────── TAB 2 ───────────────────────────
with tab2:
    st.header("🛡️ ผลการประเมินประเภทการออกแบบ (Seismic Design Category)")
    sdc_actions = {
        'ก': {'title': "ประเภท ก (SDC A) - ความเสี่ยงภัยแผ่นดินไหวต่ำมาก", 'analysis': "✅ อนุญาตให้ไม่ต้องวิเคราะห์แรงแผ่นดินไหวแบบเต็มรูปแบบ", 'detailing': "🔧 ใช้รายละเอียดโครงสร้างปกติ (ไม่ต้องจัดเหล็กปลอกต้านแผ่นดินไหว)", 'action': "📝 **สิ่งที่ต้องทำต่อ:** ออกแบบให้ต้านทานแรงข้างขั้นต่ำอย่างน้อย 1%W ($0.01W$)"},
        'ข': {'title': "ประเภท ข (SDC B) - ความเสี่ยงภัยแผ่นดินไหวต่ำ", 'analysis': "✅ สามารถใช้วิธีแรงสถิตเทียบเท่า (Equivalent Static) ได้", 'detailing': "🔧 ต้องจัดรายละเอียดโครงสร้างให้มีความเหนียวจำกัด (Ordinary Ductility)", 'action': "📝 **สิ่งที่ต้องทำต่อ:** ไปที่ Tab 4 เพื่อคำนวณแรงเฉือนที่ฐาน"},
        'ค': {'title': "ประเภท ค (SDC C) - ความเสี่ยงภัยแผ่นดินไหวปานกลาง", 'analysis': "⚠️ ใช้วิธีแรงสถิตเทียบเท่าได้เฉพาะอาคารที่มีรูปทรงสม่ำเสมอ (Regular)", 'detailing': "🚨 **บังคับ:** โครงสร้างต้องออกแบบให้มีความเหนียวปานกลาง (Intermediate Ductility)", 'action': "📝 **สิ่งที่ต้องทำต่อ:** เช็กความสม่ำเสมอของรูปทรงอาคารก่อนคำนวณที่ Tab 4"},
        'ง': {'title': "ประเภท ง (SDC D) - ความเสี่ยงภัยแผ่นดินไหวสูง (เข้มงวดที่สุด)", 'analysis': "❌ **ข้อจำกัดสูง:** ใช้วิธีแรงสถิตได้เฉพาะอาคารสม่ำเสมอและสูงไม่เกินเกณฑ์", 'detailing': "🚨 **บังคับขั้นสูงสุด:** โครงสร้างต้องมีความเหนียวสูง (Special Ductility)", 'action': "📝 **สิ่งที่ต้องทำต่อ:** หากตรวจความไม่สม่ำเสมอไม่ผ่าน บังคับส่งต่อไปวิธีพลศาสตร์ทันที!"}
    }

    if sdc == 'ก':
        st.success(f"✅ **อาคารนี้จัดอยู่ในประเภทการออกแบบสุดท้าย: '{sdc}'**")
    else:
        st.warning(f"⚠️ **อาคารนี้จัดอยู่ในประเภทการออกแบบสุดท้าย: '{sdc}'**")
    st.markdown(f"👉 **ทิศทางการออกแบบถัดไป:** {sdc_actions[sdc]['action']}")
    st.markdown("---")

    st.subheader("🗺️ แผนผังขั้นตอนการเลือกวิธีวิเคราะห์ (Seismic Analysis Decision Flowchart)")
    st.graphviz_chart(plots.get_roadmap_dot())
    st.markdown("---")

    with st.expander("🔍 ดูที่มาและข้อบังคับแยกตามพารามิเตอร์อย่างละเอียด"):
        st.markdown(f"**ปัจจัยร่วม:** ตัวคูณความสำคัญของอาคาร ($I_e$) = **{importance_factor}**")
        ie_data = {"ระดับความสำคัญ": ["อาคารทั่วไป", "อาคารความสำคัญสูง", "อาคารความสำคัญสูงมาก"], "ค่า Ie": ["1.00", "1.25", "1.50"], "ลักษณะอาคาร (ตัวอย่าง)": ["ที่พักอาศัย, อาคารพาณิชย์ทั่วไป", "โรงเรียน, สถานที่ชุมนุมคนขนาดใหญ่", "โรงพยาบาล, สถานีดับเพลิง, ศูนย์ภัยพิบัติ"]}
        st.table(pd.DataFrame(ie_data).set_index("ระดับความสำคัญ"))
        st.divider()
        col_sdc1, col_sdc2 = st.columns(2)
        with col_sdc1:
            st.markdown(f"### 1. พิจารณาจากความเร่งคาบสั้น ($S_{{DS}}$)")
            st.markdown(f"📉 ค่าที่ได้: $S_{{DS}} =$ **{SDS:.3f} g**")
            st.info(f"🎯 **ตกเกณฑ์: {sdc_actions[sdc_sds]['title']}**\n\n* {sdc_actions[sdc_sds]['analysis']}\n* {sdc_actions[sdc_sds]['detailing']}")
        with col_sdc2:
            st.markdown(f"### 2. พิจารณาจากความเร่งคาบยาว ($S_{{D1}}$)")
            st.markdown(f"📉 ค่าที่ได้: $S_{{D1}} =$ **{SD1:.3f} g**")
            st.info(f"🎯 **ตกเกณฑ์: {sdc_actions[sdc_sd1]['title']}**\n\n* {sdc_actions[sdc_sd1]['analysis']}\n* {sdc_actions[sdc_sd1]['detailing']}")
        st.divider()
        st.error(f"🏆 ผลลัพธ์ที่ควบคุมการออกแบบ (Governing SDC) คือ: **ประเภท '{sdc}'**")

# ─────────────────────────── TAB 3 ───────────────────────────
# ─────────────────────────── TAB 3 ───────────────────────────
with tab3:
    st.header("📈 กราฟความเร่งตอบสนองเชิงสเปกตรัม (Design Response Spectrum)")
    
    if sdc == 'ก':
        st.info("💡 อาคารประเภท 'ก' มีความเสี่ยงภัยต่ำมาก ไม่จำเป็นต้องวิเคราะห์สเปกตรัม (กราฟด้านล่างแสดงไว้เพื่อเป็นข้อมูลอ้างอิงเท่านั้น)")
        
    st.markdown("กราฟแสดงความสัมพันธ์ระหว่างคาบเวลาการแกว่งตัวของโครงสร้าง ($T$) และความเร่งตอบสนองเชิงสเปกตรัม ($S_a$) ตามที่ระบุในมาตรฐาน มยผ. 1301/1302")

    # ปรับแกน X ของกราฟให้ครอบคลุมและดูสวยงามขึ้น
    max_T_plot = max(4.0, Ta * 1.5, TS * 2.5)
    T_values = np.linspace(0.0, max_T_plot, 500)
    Sa_values = np.array([calc.compute_spectrum_sa(t, SDS, SD1, T0, TS) for t in T_values])
    Sa_Ta = calc.compute_spectrum_sa(Ta, SDS, SD1, T0, TS)

    # 1. แสดงกราฟ Plotly ที่ปรับปรุงใหม่
    fig_spectrum = plots.create_spectrum_plot(T_values, Sa_values, Ta, Sa_Ta, T0, TS, SDS)
    st.plotly_chart(fig_spectrum, use_container_width=True)
    
    # 2. ตารางสรุปพิกัดสำคัญ (Key Coordinates Table)
    st.subheader("📌 พิกัดจุดสำคัญบนกราฟสเปกตรัม (Key Coordinates)")
    key_points = pd.DataFrame({
        "ตำแหน่ง": [
            "จุดเริ่มต้นคาบสั้น (T = 0)", 
            f"จุดเริ่มต้นโหมดความเร่งคงที่ (T0 = {T0:.3f})", 
            f"จุดสิ้นสุดโหมดความเร่งคงที่ (TS = {TS:.3f})", 
            "จุดคาบยาว (T = 1.000)", 
            f"🎯 พิกัดอาคารที่ออกแบบ (Ta = {Ta:.3f})"
        ],
        "คาบเวลาโครงสร้าง T (วินาที)": [0.0, T0, TS, 1.0, Ta],
        "ความเร่งเชิงสเปกตรัม Sa (g)": [
            calc.compute_spectrum_sa(0.0, SDS, SD1, T0, TS), 
            calc.compute_spectrum_sa(T0, SDS, SD1, T0, TS), 
            calc.compute_spectrum_sa(TS, SDS, SD1, T0, TS), 
            calc.compute_spectrum_sa(1.0, SDS, SD1, T0, TS), 
            Sa_Ta
        ]
    })
    
    st.dataframe(
        key_points.style.format({
            "คาบเวลาโครงสร้าง T (วินาที)": "{:.3f}", 
            "ความเร่งเชิงสเปกตรัม Sa (g)": "{:.3f}"
        }).apply(lambda x: ['background: #fff7ed; font-weight: bold' if i == 4 else '' for i in range(len(x))], axis=0), 
        use_container_width=True, hide_index=True
    )
    
    # 3. กล่องแสดงสมการควบคุมกราฟ
    with st.expander("🔍 ดูสมการที่ใช้สร้างกราฟสเปกตรัม (Governing Equations)"):
        st.markdown("กราฟความเร่งตอบสนองเชิงสเปกตรัม แบ่งออกเป็น 3 ช่วง (Piecewise Function) ดังนี้:")
        col_eq1, col_eq2, col_eq3 = st.columns(3)
        with col_eq1:
            st.markdown("**ช่วงที่ 1 ($T < T_0$)**")
            st.latex(r"S_a = S_{DS} \left( 0.4 + 0.6 \frac{T}{T_0} \right)")
        with col_eq2:
            st.markdown("**ช่วงที่ 2 ($T_0 \le T \le T_S$)**")
            st.latex(r"S_a = S_{DS}")
        with col_eq3:
            st.markdown("**ช่วงที่ 3 ($T > T_S$)**")
            st.latex(r"S_a = \frac{S_{D1}}{T}")

# ─────────────────────────── TAB 4 ───────────────────────────
with tab4:
    st.header("🏢 วิธีแรงสถิตเทียบเท่า (Equivalent Static Procedure)")
    st.markdown("ระบบคำนวณกระจายแรงแผ่นดินไหว และตรวจสอบเสถียรภาพอาคารตามมาตรฐาน **มยผ. 1301/1302**")

    st.subheader("⚡ สเต็ปที่ 1: กำหนดสัมประสิทธิ์โครงสร้าง")
    structural_systems = {
        "โครงนำแรงดัด คสล. ความเหนียวสูง (SMF)":              {"R": 8.0, "Omega": 3.0, "Cd": 5.5},
        "โครงนำแรงดัด คสล. ความเหนียวปานกลาง (IMF)":           {"R": 5.0, "Omega": 3.0, "Cd": 4.5},
        "โครงนำแรงดัด คสล. ความเหนียวธรรมดา (OMF)":            {"R": 3.0, "Omega": 3.0, "Cd": 2.5},
        "กำแพงรับแรงเฉือน คสล. ความเหนียวสูง (Special SW)":    {"R": 6.0, "Omega": 2.5, "Cd": 5.0},
        "กำแพงรับแรงเฉือน คสล. ความเหนียวธรรมดา (Ordinary SW)": {"R": 5.0, "Omega": 2.5, "Cd": 4.5}
    }

    selected_system = st.selectbox("🔷 เลือกระบบโครงสร้างต้านทานแรงด้านข้าง (Seismic Resisting System):", list(structural_systems.keys()))
    R_sys   = structural_systems[selected_system]["R"]
    Omega0  = structural_systems[selected_system]["Omega"]
    Cd      = structural_systems[selected_system]["Cd"]

    Cs_tab4_basic = SDS / (R_sys / importance_factor) if R_sys > 0 else 0.0
    Cs_tab4_max   = SD1 / (Ta * (R_sys / importance_factor)) if (Ta > 0 and R_sys > 0) else Cs_tab4_basic
    Cs_tab4_min   = 0.01
    if S1 >= 0.6:
        Cs_tab4_min = max(Cs_tab4_min, (0.5 * S1) / (R_sys / importance_factor))
    Cs_gov = max(Cs_tab4_min, min(Cs_tab4_basic, Cs_tab4_max))

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("ลดแรงออกแบบ (R)", f"{R_sys}")
    col_m2.metric("เพิ่มกำลังส่วนวิกฤต (Ω₀)", f"{Omega0}")
    col_m3.metric("ขยายระยะโยก (Cd)", f"{Cd}")
    col_m4.metric("แรงเฉือนที่ฐาน (Cs)", f"{Cs_gov:.4f}")
    st.divider()

    sub_tab1, sub_tab2 = st.tabs(["🏗️ 1. รายงานการคำนวณแรงประจำชั้น", "📏 2. รายงานการตรวจสอบการโยกตัว"])

    with sub_tab1:
        st.markdown("##### 📝 กรอกข้อมูลมิติอาคาร (เรียงจากชั้นบนสุดลงล่างสุด)")
        default_stories = pd.DataFrame([
            {"ชื่อชั้น (Floor)": "ชั้น 4 (ดาดฟ้า)", "ความสูงสะสม hx (ม.)": 14.0, "น้ำหนักรวม wx (ตัน)": 150.0},
            {"ชื่อชั้น (Floor)": "ชั้น 3",           "ความสูงสะสม hx (ม.)": 10.5, "น้ำหนักรวม wx (ตัน)": 200.0},
            {"ชื่อชั้น (Floor)": "ชั้น 2",           "ความสูงสะสม hx (ม.)":  7.0, "น้ำหนักรวม wx (ตัน)": 200.0},
            {"ชื่อชั้น (Floor)": "ชั้น 1",           "ความสูงสะสม hx (ม.)":  3.5, "น้ำหนักรวม wx (ตัน)": 220.0},
        ])

        edited_df = st.data_editor(
            default_stories, num_rows="dynamic", use_container_width=True,
            column_config={
                "ชื่อชั้น (Floor)": st.column_config.TextColumn("ชื่อชั้น (Floor)", required=True),
                "ความสูงสะสม hx (ม.)": st.column_config.NumberColumn("ความสูงสะสม hx (ม.)", min_value=0.0, format="%.2f", required=True),
                "น้ำหนักรวม wx (ตัน)": st.column_config.NumberColumn("น้ำหนักรวม wx (ตัน)", min_value=0.0, format="%.2f", required=True),
            }, key="force_editor"
        )

        clean_df = edited_df.dropna(subset=["ความสูงสะสม hx (ม.)", "น้ำหนักรวม wx (ตัน)"]).copy()

        if clean_df.empty:
            st.warning("⚠️ กรุณากรอกข้อมูลในตารางอย่างน้อย 1 ชั้น")
        else:
            floor_names = clean_df["ชื่อชั้น (Floor)"].astype(str).values
            hx = clean_df["ความสูงสะสม hx (ม.)"].astype(float).values
            wx = clean_df["น้ำหนักรวม wx (ตัน)"].astype(float).values

            # เรียกใช้ฟังก์ชันประมวลผลแรงประจำชั้นจาก Engine Module
            total_W, total_V, k_exp, sum_w_hx_k, cvx, Fx, Vx, Mx = calc.calculate_story_forces(hx, wx, Cs_gov, Ta)

            res_force = pd.DataFrame({
                "ชื่อชั้น (Floor)": floor_names, "ความสูงสะสม hx (ม.)": hx, "น้ำหนักรวม wx (ตัน)": wx,
                "ตัวคูณ Cvx": cvx, "แรงผลัก Fx (ตัน)": Fx, "แรงเฉือนสะสม Vx (ตัน)": Vx, "โมเมนต์พลิกคว่ำ Mx (ตัน-ม.)": Mx,
            })

            st.markdown("### 📊 ตารางสรุปแรงออกแบบโครงสร้าง")
            st.dataframe(res_force.style.format({
                "ความสูงสะสม hx (ม.)": "{:.2f}", "น้ำหนักรวม wx (ตัน)": "{:,.2f}", "ตัวคูณ Cvx": "{:.4f}",
                "แรงผลัก Fx (ตัน)": "{:,.2f}", "แรงเฉือนสะสม Vx (ตัน)": "{:,.2f}", "โมเมนต์พลิกคว่ำ Mx (ตัน-ม.)": "{:,.2f}",
            }), use_container_width=True)

            # แสดงผลกราฟจำลองแรงทางสถาปัตยกรรม
            fig_forces = plots.create_force_plot(floor_names, Fx, Vx, Mx)
            st.plotly_chart(fig_forces, use_container_width=True)

    with sub_tab2:
        st.markdown("##### 📏 ตรวจสอบระยะเคลื่อนตัวขยับพังทลาย (Story Drift Safety Check)")
        drift_limit_factor = 0.010 if importance_factor >= 1.5 else (0.015 if importance_factor >= 1.25 else 0.020)
        cat_text = "อาคารความสำคัญสูงมาก (Limit = 1.0%)" if importance_factor >= 1.5 else ("อาคารความสำคัญสูง (Limit = 1.5%)" if importance_factor >= 1.25 else "อาคารทั่วไป (Limit = 2.0%)")

        with st.container(border=True):
            st.markdown(f"🎯 **เกณฑ์ที่ใช้ประเมินระบบในโครงการนี้:** {cat_text} ของความสูงชั้นสุทธิ")
            col_pic1, col_pic2 = st.columns([1, 1.2])
            with col_pic1:
                st.markdown("⚙️ **สมการและสัญลักษณ์ที่ควบคุมเสถียรภาพ:**")
                st.latex(r"\delta_x = \frac{C_d \times \delta_e}{I_e}")
                st.latex(r"\text{Drift Ratio} = \frac{\delta_{top} - \delta_{bot}}{h_{net}} \le \text{Limit}")
            with col_pic2:
                st.plotly_chart(plots.create_drift_model_plot(), use_container_width=True, config={'displayModeBar': False})

        if clean_df.empty:
            st.info("💡 รอข้อมูลมิติอาคารจากแท็บที่ 1")
        else:
            drift_df = pd.DataFrame({"ชื่อชั้น (Floor)": floor_names, "ความสูงสะสม hx (ม.)": hx, "ระยะโยกพืดหยุ่นจากโปรแกรม δe (ซม.)": np.linspace(2.0, 0.4, len(hx))})
            edited_drift = st.data_editor(
                drift_df, num_rows="fixed", use_container_width=True,
                column_config={
                    "ชื่อชั้น (Floor)": st.column_config.TextColumn(disabled=True),
                    "ความสูงสะสม hx (ม.)": st.column_config.NumberColumn(disabled=True, format="%.2f"),
                    "ระยะโยกพืดหยุ่นจากโปรแกรม δe (ซม.)": st.column_config.NumberColumn(min_value=0.0, format="%.3f")
                }, key=f"drift_editor_{len(hx)}"
            )

            delta_e = edited_drift["ระยะโยกพืดหยุ่นจากโปรแกรม δe (ซม.)"].values.astype(float)
            delta_x = (Cd * delta_e) / importance_factor

            n = len(hx)
            story_h, drift_ratio, status = np.zeros(n), np.zeros(n), []

            for i in range(n):
                if i < n - 1:
                    h_net = hx[i] - hx[i + 1]
                    delta_diff = delta_x[i] - delta_x[i + 1]
                else:
                    h_net = hx[i]
                    delta_diff = delta_x[i]

                h_net = max(h_net, 0.001)
                story_h[i] = h_net
                drift_ratio[i] = delta_diff / (h_net * 100.0)
                status.append("✅ PASS" if drift_ratio[i] <= drift_limit_factor else "❌ FAIL")

            res_drift = edited_drift.copy()
            res_drift["ความสูงชั้นสุทธิ (ม.)"] = story_h
            res_drift["ระยะโยกจริงในสนาม δx (ซม.)"] = delta_x
            res_drift["Drift Ratio (Δ/h)"] = drift_ratio
            res_drift["Limit (Max)"] = drift_limit_factor
            res_drift["ผลการประเมิน"] = status

            st.markdown("### 🏆 ตารางประเมินผลความปลอดภัยโครงสร้างอาคาร")
            st.dataframe(
                res_drift.style.map(
                    lambda v: 'background-color: #dcfce7; color: #166534; font-weight: bold;' if 'PASS' in str(v) else ('background-color: #fee2e2; color: #991b1b; font-weight: bold;' if 'FAIL' in str(v) else ''),
                    subset=['ผลการประเมิน']
                ).format({"ความสูงชั้นสุทธิ (ม.)": "{:.2f}", "ระยะโยกจริงในสนาม δx (ซม.)": "{:.2f}", "Drift Ratio (Δ/h)": "{:.4f}", "Limit (Max)": "{:.4f}"}),
                use_container_width=True
            )
