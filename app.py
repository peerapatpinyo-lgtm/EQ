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

# ==========================================
# ตรวจสอบเงื่อนไขตั้งต้นและการจัดการ Error (ระบบ Dual-Path แบบไม่ใช้ค่า 0.0)
# ==========================================

# 1. ดึงค่าพารามิเตอร์ Ss และ S1 ตั้งต้นมาตรวจสอบก่อน
if input_method == "ดึงจากฐานข้อมูล":
    location_row = df_location[
        (df_location['Province'] == selected_province) & (df_location['District'] == selected_district)
    ].iloc[0]
    Ss = float(location_row['Ss'])
    S1 = float(location_row['S1'])
else:
    Ss = float(manual_Ss)
    S1 = float(manual_S1)

# 2. ตรวจสอบเงื่อนไขว่าเป็นพื้นที่แอ่งกรุงเทพฯ หรือไม่ "โดยดูจากชื่อจังหวัด" (ไม่ต้องใช้ 0.0 แล้ว)
bangkok_basin_provinces = [
    "กรุงเทพมหานคร", "นนทบุรี", "ปทุมธานี", "สมุทรปราการ", 
    "สมุทรสาคร", "สมุทรสงคราม", "นครปฐม", "ฉะเชิงเทรา"
]
is_bangkok_basin = (input_method == "ดึงจากฐานข้อมูล") and (selected_province in bangkok_basin_provinces)

if is_bangkok_basin:
    # -----------------------------------------------------------------------
    # PATH B: สำหรับพื้นที่ดินเหนียวอ่อนแอ่งกรุงเทพฯ (สเปกตรัมเฉพาะพื้นที่ มยผ. 1302-61)
    # -----------------------------------------------------------------------
    st.sidebar.success("🎯 เปิดใช้งาน: สเปกตรัมเฉพาะพื้นที่แอ่งกรุงเทพฯ อัตโนมัติ")
    
    # บังคับค่า Fa, Fv เป็น 1.0 (เนื่องจากค่า Ss, S1 ในฐานข้อมูลสำหรับพื้นที่นี้ถูกแปลงเป็นค่าที่ขยายตัวเสร็จแล้ว)
    Fa, Fv = 1.000, 1.000
    
    SMS = Fa * Ss
    SM1 = Fv * S1
    SDS = (2.0 / 3.0) * SMS
    SD1 = (2.0 / 3.0) * SM1
    
    # บังคับจุดควบคุมคาบเวลาตามพฤติกรรมดินเหนียวอ่อน
    T0 = 0.200   # จุดเริ่มโหมดความเร่งคงที่
    TS = 1.150   # จุดสิ้นสุดโหมดความเร่งคงที่ (ดินเหนียวอ่อนทำให้ช่วงคาบยาวสั่นพ้องกว้างขึ้น)
    Ta = calc.calculate_approx_period(sys_type, building_height)
    
    # กำหนดประเภทการออกแบบ (SDC) อัตโนมัติตามเกณฑ์ควบคุมพื้นที่ดินเหนียวอ่อนพิเศษ
    sdc = "ค" if importance_factor >= 1.25 else "ข"
    sdc_sds = sdc
    sdc_sd1 = sdc

else:
    # -----------------------------------------------------------------------
    # PATH A: สำหรับพื้นที่ทั่วไปในประเทศไทย (คำนวณตามขั้นตอนมาตรฐาน มยผ.)
    # -----------------------------------------------------------------------
    # ดักจับกรณีผู้ใช้เลือกชั้นดิน F ในพื้นที่ทั่วไป
    if site_class == 'F':
        st.error("🛑 ชั้นดิน F สำหรับพื้นที่ทั่วไป ต้องเจาะสำรวจประเมินเฉพาะพื้นที่ (Site-Specific) เท่านั้น ไม่สามารถใช้ค่าคำนวณมาตรฐานได้")
        st.stop()
        
    # เรียกใช้ Pure Engine Calculations ตามขั้นตอนปกติ
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
# เพิ่ม tab_dynamic เข้าไปด้านซ้าย เพื่อให้ครบ 6 ตัวพอดีกับชื่อด้านขวา
tab1, tab2, tab3, tab4, tab5, tab_dynamic, tab_dynamic_calc = st.tabs([
    "📋 1. พารามิเตอร์ออกแบบ", 
    "🚦 2. ประเภท SDC", 
    "📈 3. Response Spectrum", 
    "🏢 4. Equivalent Static",
    "🧠 5. สรุป Mind Map (ESP)",
    "📊 6. โฟลว์ชาร์ต Dynamic",
    "⚙️ 7. คำนวณ Dynamic (Scaling)" # <-- แท็บใหม่
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
with tab3:
    st.header("📈 กราฟความเร่งตอบสนองเชิงสเปกตรัม (Response Spectrum)")
    
    if sdc == 'ก':
        st.info("💡 **ข้อแนะนำทางกฎหมาย:** โครงสร้างจัดอยู่ในประเภท SDC 'ก' ซึ่งมีความเสี่ยงภัยแผ่นดินไหวต่ำมาก ตามมาตรฐาน มยผ. ไม่บังคับให้ต้องวิเคราะห์สเปกตรัมโดยวิธีขั้นสูง กราฟแสดงไว้เพื่อการตรวจสอบเชิงวิศวกรรมเท่านั้น")
        
    st.markdown("""
    ### 🔬 บทวิเคราะห์พฤติกรรมโครงสร้าง (Structural Dynamic Analysis)
    กราฟด้านล่างแสดงความสัมพันธ์ระหว่าง **คาบเวลาธรรมชาติ ($T$)** และ **ความเร่งตอบสนองเชิงสเปกตรัม ($S_a$)** ซึ่งเป็นตัวแทนของแรงสูงสุดที่โครงสร้างจะได้รับในรูปแบบของสัดส่วนแรงโน้มถ่วง ($g$) โดยจะถูกแปลงเป็นแรงเฉือนที่ฐานอาคาร (Base Shear) ต่อไป
    """)

    # ปรับสเกลแกน X อัตโนมัติให้สวยงาม ครอบคลุมจุดสำคัญ
    max_T_plot = max(4.0, Ta * 1.5, TS * 2.5)
    T_values = np.linspace(0.0, max_T_plot, 500)
    Sa_values = np.array([calc.compute_spectrum_sa(t, SDS, SD1, T0, TS) for t in T_values])
    Sa_Ta = calc.compute_spectrum_sa(Ta, SDS, SD1, T0, TS)

    # 1. แสดงผลกราฟสเปกตรัมตอบสนองเชิงปฏิสัมพันธ์ (Interactive Plotly Curve)
    fig_spectrum = plots.create_spectrum_plot(T_values, Sa_values, Ta, Sa_Ta, T0, TS, SDS)
    st.plotly_chart(fig_spectrum, use_container_width=True)
    
    # 2. ตารางสรุปพิกัดสำคัญ (Key Coordinates Table) สำหรับนำไปใช้เขียนรายงาน
    st.subheader("📌 สรุปพิกัดและค่าพารามิเตอร์สำคัญบนสเปกตรัม (Key Spectrum Coordinates)")
    st.markdown("วิศวกรสามารถใช้ค่าพิกัดเหล่านี้ในการตรวจสอบความถูกต้องของพฤติกรรมโครงสร้าง หรือนำไปป้อนลงในโปรแกรมคำนวณสำเร็จรูปอื่นๆ ได้:")
    
    key_points = pd.DataFrame({
        "ขอบเขตพฤติกรรม / จุดควบคุม": [
            "จุดเริ่มต้นคาบสั้น (T = 0) [ค่า Peak Ground Acceleration, PGA]", 
            f"จุดเริ่มโหมดความเร่งคงที่ (T0 = {T0:.3f} วินาที)", 
            f"จุดสิ้นสุดโหมดความเร่งคงที่ (TS = {TS:.3f} วินาที)", 
            "จุดอ้างอิงพฤติกรรมคาบยาว (T = 1.000 วินาที)", 
            f"🎯 พิกัดของอาคารที่กำลังคำนวณ (Ta = {Ta:.3f} วินาที)"
        ],
        "คาบเวลา T (วินาที)": [0.0, T0, TS, 1.0, Ta],
        "ความเร่งเชิงสเปกตรัม Sa (g)": [
            calc.compute_spectrum_sa(0.0, SDS, SD1, T0, TS), 
            calc.compute_spectrum_sa(T0, SDS, SD1, T0, TS), 
            calc.compute_spectrum_sa(TS, SDS, SD1, T0, TS), 
            calc.compute_spectrum_sa(1.0, SDS, SD1, T0, TS), 
            Sa_Ta
        ]
    })
    
    # ตกแต่งตารางข้อมูล ไฮไลท์บรรทัดของอาคารปัจจุบันเป็นสีส้มเด่นชัดเพื่อความเป็นมืออาชีพ
    st.dataframe(
        key_points.style.format({
            "คาบเวลา T (วินาที)": "{:.3f}", 
            "ความเร่งเชิงสเปกตรัม Sa (g)": "{:.3f}"
        }).apply(lambda x: ['background: #fff7ed; color: #c2410c; font-weight: bold; border-left: 4px solid #ff7f0e' if i == 4 else '' for i in range(len(x))], axis=0), 
        use_container_width=True, hide_index=True
    )
    
    # 3. กล่องพับแสดงสมการและแหล่งอ้างอิงตามกฎหมายควบคุมอาคาร
    with st.expander("📚 เอกสารอ้างอิงและสมการควบคุมตามมาตรฐาน มยผ. (Governing Equations & References)"):
        st.markdown("""
        #### 🏛️ กฎหมายและมาตรฐานอ้างอิง (Legal References)
        1. **มาตรฐาน มยผ. 1301/1302-61:** มาตรฐานการออกแบบอาคารต้านทานการสั่นสะเทือนของแผ่นดินไหว กรมโยธาธิการและผังเมือง (บทที่ 4 หน้า 23-25)
        2. **มาตรฐานสากล ASCE/SEI 7-16:** Minimum Design Loads and Associated Criteria for Buildings and Other Structures (Chapter 11 - Seismic Design Criteria)
        
        #### 🔢 เงื่อนไขฟังก์ชันคณิตศาสตร์แบบแบ่งช่วง (Piecewise Functions)
        กราฟความเร่งสเปกตรัมตอบสนองแบ่งออกเป็นสมการควบคุมตามช่วงเวลาดังนี้:
        """)
        
        col_eq1, col_eq2, col_eq3 = st.columns(3)
        with col_eq1:
            st.markdown("**ช่วงที่ 1: คาบสั้นมาก ($0 \le T < T_0$)**")
            st.latex(r"S_a = S_{DS} \left( 0.4 + 0.6 \frac{T}{T_0} \right)")
            st.caption("โครงสร้างขยับตัวตามแผ่นดินไหวแบบ Rigid Body")
        with col_eq2:
            st.markdown("**ช่วงที่ 2: ความเร่งคงที่ ($T_0 \le T \le T_S$)**")
            st.latex(r"S_a = S_{DS}")
            st.caption("เกิดผลของการขยายตัวสั่นสะเทือนสูงสุด (Resonance Zone)")
        with col_eq3:
            st.markdown("**ช่วงที่ 3: คาบยาว ($T > T_S$)**")
            st.latex(r"S_a = \frac{S_{D1}}{T}")
            st.caption("อาคารสูง/ยืดหยุ่น ความเร่งลดลงแต่ระยะโยกตัวเพิ่มสูงขึ้น")


# ───────────────────────────────────────────────────────────────────────────
# TAB 4: การวิเคราะห์โครงสร้างด้วยวิธีแรงสถิตเทียบเท่า (Equivalent Static Procedure)
# ───────────────────────────────────────────────────────────────────────────
with tab4:
    st.header("🏢 วิธีแรงสถิตเทียบเท่า (Equivalent Static Procedure)")
    st.markdown("""
    ระบบคำนวณการกระจายแรงแผ่นดินไหวตามแนวดิ่ง และประเมินเสถียรภาพการโยกตัวของอาคารตามมาตรฐาน **มยผ. 1301/1302-61**
    *(วิธีนี้เหมาะสำหรับอาคารที่มีรูปทรงสม่ำเสมอและมีความสูงอยู่ในเกณฑ์ที่มาตรฐานกำหนด)*
    """)

    # ==========================================
    # สเต็ปที่ 1: การกำหนดระบบโครงสร้างและคำนวณสัมประสิทธิ์ Cs
    # ==========================================
    st.subheader("⚡ สเต็ปที่ 1: กำหนดสัมประสิทธิ์โครงสร้างและตรวจสอบค่า Cs ตัวควบคุม")
    
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

    # คำนวณขีดจำกัดสัมประสิทธิ์ผลตอบสนองแผ่นดินไหว (Cs) ตามกฎหมายควบคุมอาคาร
    Cs_tab4_basic = SDS / (R_sys / importance_factor) if R_sys > 0 else 0.0
    Cs_tab4_max   = SD1 / (Ta * (R_sys / importance_factor)) if (Ta > 0 and R_sys > 0) else Cs_tab4_basic
    Cs_tab4_min   = 0.01
    if S1 >= 0.6:
        Cs_tab4_min = max(Cs_tab4_min, (0.5 * S1) / (R_sys / importance_factor))
    
    # ค่า Cs ที่ใช้จริง (Governing Cs)
    Cs_gov = max(Cs_tab4_min, min(Cs_tab4_basic, Cs_tab4_max))

    # แสดงพารามิเตอร์หลักผ่านระบบ Metric Layout ให้เห็นชัดเจน
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("ตัวคูณลดแรงออกแบบ (R)", f"{R_sys:.1f}")
    col_m2.metric("ตัวคูณเพิ่มกำลังส่วนวิกฤต (Ω₀)", f"{Omega0:.1f}")
    col_m3.metric("ตัวคูณขยายระยะโยก (Cd)", f"{Cd:.1f}")
    col_m4.metric("สัมประสิทธิ์แรงเฉือนที่ฐาน (Cs)", f"{Cs_gov:.4f}")

    # แสดงที่มาของ Cs เพื่อให้วิศวกรใช้ตรวจสอบความถูกต้อง (Engineering Transparency)
    with st.expander("🔍 ดูรายละเอียดเกณฑ์ขีดจำกัดสัมประสิทธิ์ Cs (Seismic Response Coefficient Limits)"):
        col_cs1, col_cs2 = st.columns(2)
        with col_cs1:
            st.markdown("**สมการควบคุมตาม มยผ. 1302:**")
            st.latex(r"C_{s,\text{basic}} = \frac{S_{DS}}{R / I_e}")
            st.latex(r"C_{s,\text{max}} = \frac{S_{D1}}{T_a (R / I_e)}")
            st.latex(r"C_{s,\text{min}} = 0.01 \quad \left(\text{หรือ } \frac{0.5 S_1}{R / I_e} \text{ ถ้า } S_1 \ge 0.6g\right)")
        with col_cs2:
            st.markdown("**ค่าที่คำนวณได้รายสมการ:**")
            st.write(f"• $C_{{s,\\text{{basic}}}}$ = `{Cs_tab4_basic:.4f}`")
            st.write(f"• $C_{{s,\\text{{max}}}}$ = `{Cs_tab4_max:.4f}` *(ขีดจำกัดบน)*")
            st.write(f"• $C_{{s,\\text{{min}}}}$ = `{Cs_tab4_min:.4f}` *(ขีดจำกัดล่าง)*")
            st.info(f"🎯 **ค่าควบคุมที่เลือกใช้:** $C_s$ = **{Cs_gov:.4f}** (ผ่านการคัดกรองตามข้อกำหนดแล้ว)")

    st.divider()

    # ==========================================
    # สเต็ปที่ 2: แท็บย่อยรายงานผลคำนวณและประเมินระบบ
    # ==========================================
    sub_tab1, sub_tab2 = st.tabs(["🏗️ 1. รายงานการคำนวณแรงประจำชั้น", "📏 2. รายงานการตรวจสอบการโยกตัวระหว่างชั้น"])

    # --- แท็บย่อยที่ 1: การกระจายแรงตามแนวดิ่ง ---
    with sub_tab1:
        st.markdown("##### 📝 ข้อมูลมิติและน้ำหนักอาคารรายชั้น (กรอกเรียงจาก ชั้นบนสุด ลงไป ชั้นล่างสุด)")
        
        # ตารางตั้งต้นที่ผู้ใช้สามารถแก้ไข เพิ่ม หรือลบชั้นได้อิสระ
        default_stories = pd.DataFrame([
            {"ชื่อชั้น (Floor)": "ชั้น 4 (ดาดฟ้า)", "ความสูงสะสม hx (ม.)": 14.0, "น้ำหนักรวม wx (ตัน)": 150.0},
            {"ชื่อชั้น (Floor)": "ชั้น 3",           "ความสูงสะสม hx (ม.)": 10.5, "น้ำหนักรวม wx (ตัน)": 200.0},
            {"ชื่อชั้น (Floor)": "ชั้น 2",           "ความสูงสะสม hx (ม.)":  7.0, "น้ำหนักรวม wx (ตัน)": 200.0},
            {"ชื่อชั้น (Floor)": "ชั้น 1",           "ความสูงสะสม hx (ม.)":  3.5, "น้ำหนักรวม wx (ตัน)": 220.0},
        ])

        edited_df = st.data_editor(
            default_stories, num_rows="dynamic", use_container_width=True,
            column_config={
                "ชื่อชั้น (Floor)": st.column_config.TextColumn("ชื่อชั้น (Floor)", required=True, help="ระบุชื่อเรียกชั้น เช่น Floor 1, Roof"),
                "ความสูงสะสม hx (ม.)": st.column_config.NumberColumn("ความสูงสะสม hx (ม.)", min_value=0.0, format="%.2f", required=True, help="ความสูงวัดจากฐานหรือจุดรองรับถึงระดับชั้นนั้นๆ"),
                "น้ำหนักรวม wx (ตัน)": st.column_config.NumberColumn("น้ำหนักรวม wx (ตัน)", min_value=0.0, format="%.2f", required=True, help="น้ำหนักบรรทุกคงที่รวมกับน้ำหนักบรรทุกจรตามสัดส่วนที่มาตรฐานกำหนด"),
            }, key="force_editor"
        )

        clean_df = edited_df.dropna(subset=["ความสูงสะสม hx (ม.)", "น้ำหนักรวม wx (ตัน)"]).copy()

        if clean_df.empty:
            st.warning("⚠️ กรุณากรอกข้อมูลระดับความสูงและน้ำหนักในตารางอย่างน้อย 1 ชั้น เพื่อเริ่มทำการคำนวณ")
        else:
            floor_names = clean_df["ชื่อชั้น (Floor)"].astype(str).values
            hx = clean_df["ความสูงสะสม hx (ม.)"].astype(float).values
            wx = clean_df["น้ำหนักรวม wx (ตัน)"].astype(float).values

            # ประมวลผลกระจายแรงผ่านฟังก์ชันแกนหลักใน calculations.py
            total_W, total_V, k_exp, sum_w_hx_k, cvx, Fx, Vx, Mx = calc.calculate_story_forces(hx, wx, Cs_gov, Ta)

            # กล่องสรุปผลวิเคราะห์ภาพรวมโครงสร้าง (Executive Summary Card)
            st.info(f"""
            📊 **สรุปผลลัพธ์วิเคราะห์แรงสถิตเทียบเท่า:**
            * น้ำหนักรวมของโครงสร้างที่พิจารณา ($W$) = **{total_W:,.2f} ตัน**
            * แรงเฉือนที่ฐานอาคารทั้งหมด ($V = C_s \\times W$) = **{total_V:,.2f} ตัน**
            * ตัวคูณเลขชี้กำลังการกระจายแรงตามแนวดิ่ง ($k$) = **{k_exp:.3f}** *(แปรผันตามคาบเวลาโครงสร้าง $T_a$)*
            """)

            # สร้าง DataFrame สรุปรายงานสำหรับนำไปออกเล่มคำนวณ
            res_force = pd.DataFrame({
                "ชื่อชั้น (Floor)": floor_names, 
                "ความสูงสะสม hx (ม.)": hx, 
                "น้ำหนักรวม wx (ตัน)": wx,
                "ตัวคูณกระจายแรง Cvx": cvx, 
                "แรงผลักด้านข้าง Fx (ตัน)": Fx, 
                "แรงเฉือนสะสมประจำชั้น Vx (ตัน)": Vx, 
                "โมเมนต์พลิกคว่ำ Mx (ตัน-ม.)": Mx,
            })

            st.markdown("### 📊 ตารางสรุปแรงออกแบบแผ่นดินไหวประจำชั้น (Story Forces Summary Report)")
            st.dataframe(
                res_force.style.format({
                    "ความสูงสะสม hx (ม.)": "{:.2f}", 
                    "น้ำหนักรวม wx (ตัน)": "{:,.2f}", 
                    "ตัวคูณกระจายแรง Cvx": "{:.4f}",
                    "แรงผลักด้านข้าง Fx (ตัน)": "{:,.2f}", 
                    "แรงเฉือนสะสมประจำชั้น Vx (ตัน)": "{:,.2f}", 
                    "โมเมนต์พลิกคว่ำ Mx (ตัน-ม.)": "{:,.2f}",
                }), use_container_width=True, hide_index=True
            )

            # แสดงผลแผนภาพกราฟแรงเฉือนและโมเมนต์พลิกคว่ำ (Interactive Engineering Plots)
            st.markdown("### 📈 แผนภาพแสดงพฤติกรรมแรงและโมเมนต์ตามความสูงอาคาร")
            fig_forces = plots.create_force_plot(floor_names, Fx, Vx, Mx)
            st.plotly_chart(fig_forces, use_container_width=True)


    # --- แท็บย่อยที่ 2: การตรวจสอบระยะการโยกตัว ---
    with sub_tab2:
        st.markdown("##### 📏 ตรวจสอบเกณฑ์ระยะเคลื่อนตัวและการโยกตัวระหว่างชั้น (Story Drift Safety Check)")
        
        # คำนวณเกณฑ์ควบคุมตามตัวคูณความสำคัญตามมาตรฐาน มยผ.
        drift_limit_factor = 0.010 if importance_factor >= 1.5 else (0.015 if importance_factor >= 1.25 else 0.020)
        cat_text = "อาคารความสำคัญสูงมาก (Limit = 1.0%)" if importance_factor >= 1.5 else ("อาคารความสำคัญสูง (Limit = 1.5%)" if importance_factor >= 1.25 else "อาคารทั่วไป (Limit = 2.0%)")

        with st.container(border=True):
            st.markdown(f"🎯 **ขีดจำกัดระยะโยกตัว (Drift Limit) ที่ควบคุมโครงการนี้:** **{drift_limit_factor * 100:.1f}%** ของความสูงชั้นสุทธิ ({cat_text})")
            col_pic1, col_pic2 = st.columns([1, 1.2])
            with col_pic1:
                st.markdown("⚙️ **หลักการคำนวณพิจารณาเสถียรภาพ:**")
                st.latex(r"\delta_x = \frac{C_d \times \delta_e}{I_e}")
                st.latex(r"\Delta_{\text{story}} = \delta_{x,\text{top}} - \delta_{x,\text{bot}}")
                st.latex(r"\text{Drift Ratio} = \frac{\Delta_{\text{story}}}{h_{\text{net}}} \le \text{Limit}")
                st.caption("💡 ค่า δe คือระยะเคลื่อนตัวที่ได้จากการใส่แรง Fx เข้าไปในแบบจำลองโครงสร้างยืดหยุ่น (Elastic Analysis)")
            with col_pic2:
                fig_drift_model = plots.create_drift_model_plot()
                st.plotly_chart(fig_drift_model, use_container_width=True, config={'displayModeBar': False})

        if clean_df.empty:
            st.info("💡 ระบบกำลังรอข้อมูลมิติอาคารรายชั้นจากแท็บย่อยที่ 1 เพื่อสร้างตารางตรวจสอบ Drift อัตโนมัติ")
        else:
            # สร้างอินพุตตารางตรวจสอบการโยกตัวที่สอดรับกับรายชื่อชั้นในแท็บแรกโดยอัตโนมัติ
            drift_df = pd.DataFrame({
                "ชื่อชั้น (Floor)": floor_names, 
                "ความสูงสะสม hx (ม.)": hx, 
                "ระยะเคลื่อนตัวยืดหยุ่นจากโปรแกรม δe (ซม.)": np.linspace(2.0, 0.4, len(hx))
            })
            
            st.markdown("**กรุณาป้อนระยะเคลื่อนตัวยืดหยุ่น ($\delta_e$) จากโปรแกรมวิเคราะห์โครงสร้าง (เช่น ETABS, SAP2000):**")
            edited_drift = st.data_editor(
                drift_df, num_rows="fixed", use_container_width=True,
                column_config={
                    "ชื่อชั้น (Floor)": st.column_config.TextColumn(disabled=True),
                    "ความสูงสะสม hx (ม.)": st.column_config.NumberColumn(disabled=True, format="%.2f"),
                    "ระยะเคลื่อนตัวยืดหยุ่นจากโปรแกรม δe (ซม.)": st.column_config.NumberColumn("ระยะเคลื่อนตัวยืดหยุ่นจากโปรแกรม δe (ซม.)", min_value=0.0, format="%.3f", help="ใส่ค่า Displacement สะสมประจำชั้นในหน่วยเซนติเมตร")
                }, key=f"drift_editor_{len(hx)}"
            )

            # คำนวณระยะเคลื่อนตัวจริงรวมพฤติกรรมเหนียวเหนือแรงพิกัด (Inelastic Displacement, δx)
            delta_e = edited_drift["ระยะเคลื่อนตัวยืดหยุ่นจากโปรแกรม δe (ซม.)"].values.astype(float)
            delta_x = (Cd * delta_e) / importance_factor

            n = len(hx)
            story_h, drift_ratio, status = np.zeros(n), np.zeros(n), []

            for i in range(n):
                # คำนวณหาความสูงชั้นสุทธิ และระยะเยื้องศูนย์สัมพัทธ์ระหว่างชั้น (Interstory Drift)
                if i < n - 1:
                    h_net = hx[i] - hx[i + 1]
                    delta_diff = delta_x[i] - delta_x[i + 1]
                else:
                    h_net = hx[i]
                    delta_diff = delta_x[i]

                h_net = max(h_net, 0.001)  # ป้องกันข้อผิดพลาดในการหารด้วยศูนย์
                story_h[i] = h_net
                drift_ratio[i] = delta_diff / (h_net * 100.0) # แปลง h_net (เมตร) -> ซม. เพื่อหาสัดส่วนไร้มิติ
                status.append("✅ PASS" if drift_ratio[i] <= drift_limit_factor else "❌ FAIL")

            # ประกอบข้อมูลตารางสรุปเกณฑ์ความปลอดภัย
            res_drift = edited_drift.copy()
            res_drift["ความสูงชั้นสุทธิ h_net (ม.)"] = story_h
            res_drift["ระยะเคลื่อนตัวจริงในสนาม δx (ซม.)"] = delta_x
            res_drift["อัตราส่วนการโยกตัว Drift Ratio (%)"] = drift_ratio * 100  # แปลงเป็น % ให้อ่านและเทียบง่าย
            res_drift["ค่าจำกัดสูงสุด Limit (%)"] = drift_limit_factor * 100
            res_drift["ผลการประเมิน"] = status

            st.markdown("### 🏆 ตารางประเมินเกณฑ์ความปลอดภัยการโยกตัวระหว่างชั้น (Story Drift Evaluation Table)")
            st.dataframe(
                res_drift.style.map(
                    lambda v: 'background-color: #dcfce7; color: #166534; font-weight: bold;' if 'PASS' in str(v) else ('background-color: #fee2e2; color: #991b1b; font-weight: bold;' if 'FAIL' in str(v) else ''),
                    subset=['ผลการประเมิน']
                ).format({
                    "ความสูงสะสม hx (ม.)": "{:.2f}", 
                    "ระยะเคลื่อนตัวยืดหยุ่นจากโปรแกรม δe (ซม.)": "{:.3f}", 
                    "ความสูงชั้นสุทธิ h_net (ม.)": "{:.2f}", 
                    "ระยะเคลื่อนตัวจริงในสนาม δx (ซม.)": "{:.2f}", 
                    "อัตราส่วนการโยกตัว Drift Ratio (%)": "{:.3f}%", 
                    "ค่าจำกัดสูงสุด Limit (%)": "{:.2f}%"
                }),
                use_container_width=True, hide_index=True
            )
            
            # สรุปภาพรวมความปลอดภัยให้ชัดเจน
            if "❌ FAIL" in status:
                st.error("🛑 **ผลการตรวจสอบ:** โครงสร้างอาคารของคุณ **ไม่ผ่านเกณฑ์การโยกตัวระหว่างชั้น** ในบางชั้น! กรุณาเพิ่มขนาดของเสา (Column) หรือใส่กำแพงรับแรงเฉือน (Shear Wall) เพื่อเพิ่มความแข็งเกร็ง (Stiffness) ให้กับอาคาร")
            else:
                st.success("✅ **ผลการตรวจสอบ:** โครงสร้างอาคารมีความแข็งเกร็งเพียงพอ **ผ่านเกณฑ์มาตรฐานเรื่องระยะโยกตัว (Drift Limit)** ทุกชั้น สามารถใช้เป็นเอกสารแนบประกอบรายการคำนวณได้ทันที")

# ───────────────────────────────────────────────────────────────────────────
# TAB 5: แผนผังกระบวนการและพารามิเตอร์ออกแบบอาคาร (Project Design Flowchart)
# ───────────────────────────────────────────────────────────────────────────
with tab5:
    st.header("📋 แผนผังกระบวนการและพารามิเตอร์ออกแบบอาคาร (Project Design Flowchart)")

    # 1. ดักจับและเตรียมข้อมูล (Safe Variable Extraction) 
    _Ta = f"{Ta:.3f}" if 'Ta' in locals() else "-"
    _SDS = f"{SDS:.3f}" if 'SDS' in locals() else "-"
    _SD1 = f"{SD1:.3f}" if 'SD1' in locals() else "-"
    _sdc = sdc if 'sdc' in locals() else "-"
    _R = f"{R_sys:.1f}" if 'R_sys' in locals() else "-"
    _Ie = f"{importance_factor:.2f}" if 'importance_factor' in locals() else "-"
    _Cd = f"{Cd:.1f}" if 'Cd' in locals() else "-"
    _Cs = f"{Cs_gov:.4f}" if 'Cs_gov' in locals() else "-"
    
    _W = f"{total_W:,.2f}" if 'total_W' in locals() else "รอข้อมูล"
    _V = f"{total_V:,.2f}" if 'total_V' in locals() else "รอข้อมูล"
    _k = f"{k_exp:.3f}" if 'k_exp' in locals() else "-"
    
    limit_pct = (0.010 if importance_factor >= 1.5 else (0.015 if importance_factor >= 1.25 else 0.020)) * 100
    
    # ประเมินสถานะภาพรวมของอาคาร (Overall Status) - โทนสีสุขุมและเป็นทางการ
    if 'status' in locals() and len(status) > 0:
        overall_drift = "❌ ไม่ผ่านเกณฑ์ (FAIL)" if "❌ FAIL" in status else "✅ ผ่านเกณฑ์ (PASS)"
        drift_color = "#991B1B" if "FAIL" in overall_drift else "#166534" # แดงเข้มเลือดหมู / เขียวเข้ม
    else:
        overall_drift = "รอผลการคำนวณ"
        drift_color = "#475569" # เทากลาง

    # 2. สร้าง Graphviz DOT โทนสี Premium Corporate (Modern UI Style)
    pro_flowchart_dot = f"""
    digraph ExecutiveSummary {{
        rankdir=TB;
        nodesep=0.8;
        ranksep=0.6;
        bgcolor="transparent";
        splines=ortho;
        pad=0.5;

        node [shape=plaintext, fontname="Helvetica, Arial, Tahoma, sans-serif", fontsize=12];
        edge [color="#94A3B8", penwidth=2, arrowsize=0.7]; 

        // 🎯 CARD 1: ข้อมูลพื้นที่และภัยแผ่นดินไหว
        Card_Site [label=<
            <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10" COLOR="#CBD5E1" STYLE="ROUNDED">
                <TR><TD BGCOLOR="#0F172A" COLSPAN="2"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>📍 1. ข้อมูลสถานที่และภัยแผ่นดินไหว</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">ชั้นดิน (Site Class):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{site_class}</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">S<SUB>DS</SUB> / S<SUB>D1</SUB> (g):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_SDS} / {_SD1}</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">ประเภทการออกแบบ (SDC):</FONT></TD><TD BGCOLOR="#FFFBEB"><FONT COLOR="#D97706"><B>ประเภท {_sdc}</B></FONT></TD></TR>
            </TABLE>
        >];

        // 🎯 CARD 2: ระบบโครงสร้างอาคาร
        Card_System [label=<
            <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10" COLOR="#CBD5E1" STYLE="ROUNDED">
                <TR><TD BGCOLOR="#0F172A" COLSPAN="4"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>🏢 2. พารามิเตอร์ระบบโครงสร้าง</B></FONT></TD></TR>
                <TR>
                    <TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">ตัวคูณสำคัญ (Ie):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_Ie}</B></FONT></TD>
                    <TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">ลดแรงออกแบบ (R):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_R}</B></FONT></TD>
                </TR>
                <TR>
                    <TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">คาบเวลาอาคาร (Ta):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_Ta} s.</B></FONT></TD>
                    <TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">ขยายระยะโยก (Cd):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_Cd}</B></FONT></TD>
                </TR>
            </TABLE>
        >];

        // 🎯 CARD 3: แรงเฉือนที่ฐาน
        Card_BaseShear [label=<
            <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10" COLOR="#CBD5E1" STYLE="ROUNDED">
                <TR><TD BGCOLOR="#0F172A" COLSPAN="2"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>⚖️ 3. แรงเฉือนที่ฐานอาคาร</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">สัมประสิทธิ์การตอบสนอง (Cs):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_Cs}</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">น้ำหนักประสิทธิผล (W):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_W} ตัน</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">แรงเฉือนออกแบบ (V):</FONT></TD><TD BGCOLOR="#FEF2F2"><FONT COLOR="#B91C1C"><B>{_V} ตัน</B></FONT></TD></TR>
            </TABLE>
        >];

        // 🎯 CARD 4: การกระจายแรง
        Card_Dist [label=<
            <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10" COLOR="#CBD5E1" STYLE="ROUNDED">
                <TR><TD BGCOLOR="#0F172A" COLSPAN="2"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>📉 4. การกระจายแรงแนวดิ่ง</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">เลขชี้กำลัง (k):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_k}</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">สมการควบคุม:</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A">F<SUB>x</SUB> = C<SUB>vx</SUB> × V</FONT></TD></TR>
            </TABLE>
        >];

        // 🎯 CARD 5: การตรวจสอบเสถียรภาพ
        Card_Drift [label=<
            <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10" COLOR="#CBD5E1" STYLE="ROUNDED">
                <TR><TD BGCOLOR="#0F172A" COLSPAN="2"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>🛡️ 5. การประเมินระยะโยกตัว</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">เกณฑ์ขีดจำกัด (Limit):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{limit_pct:.1f}%</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">สถานะความปลอดภัย:</FONT></TD><TD BGCOLOR="{drift_color}"><FONT COLOR="#FFFFFF"><B>{overall_drift}</B></FONT></TD></TR>
            </TABLE>
        >];

        // 🔗 เชื่อมโยง Flow
        Card_Site -> Card_System;
        Card_System -> Card_BaseShear;
        Card_BaseShear -> Card_Dist;
        Card_BaseShear -> Card_Drift;
        
        // จัดให้ Dist กับ Drift อยู่ระดับเดียวกัน (Rank)
        {{ rank=same; Card_Dist; Card_Drift; }}
    }}
    """
    
    # 3. แสดงผล Flowchart
    st.graphviz_chart(pro_flowchart_dot, use_container_width=True)

# ───────────────────────────────────────────────────────────────────────────
# TAB 6: แผนผังกระบวนการวิเคราะห์ทางพลศาสตร์ (Dynamic Analysis Flowchart)
# ───────────────────────────────────────────────────────────────────────────
with tab_dynamic:
    st.header("📋 แผนผังพารามิเตอร์การวิเคราะห์ทางพลศาสตร์ (Dynamic Analysis Summary)")

    # 1. ดักจับและเตรียมข้อมูลสำหรับการวิเคราะห์แบบ Response Spectrum
    # (เปลี่ยนตัวแปรให้ตรงกับในโค้ดจริงของคุณ)
    _SDS = f"{SDS:.3f}" if 'SDS' in locals() else "-"
    _SD1 = f"{SD1:.3f}" if 'SD1' in locals() else "-"
    _Ts = f"{Ts:.3f}" if 'Ts' in locals() else "-"
    
    _T1 = f"{T1:.3f}" if 'T1' in locals() else "รอข้อมูล"
    _modes = f"{num_modes}" if 'num_modes' in locals() else "-"
    _mass_part = f"{mass_part:.1f}" if 'mass_part' in locals() else "รอข้อมูล"
    
    _V_static = f"{V_static:,.2f}" if 'V_static' in locals() else "รอข้อมูล"
    _V_dynamic = f"{V_dynamic:,.2f}" if 'V_dynamic' in locals() else "รอข้อมูล"
    _scale_factor = f"{scale_factor:.3f}" if 'scale_factor' in locals() else "-"
    
    limit_pct = (0.010 if importance_factor >= 1.5 else (0.015 if importance_factor >= 1.25 else 0.020)) * 100 if 'importance_factor' in locals() else 1.5

    # ประเมินสถานะการมีส่วนร่วมของมวล (Mass Participation >= 90%)
    if 'mass_part' in locals():
        mass_status_color = "#166534" if mass_part >= 90.0 else "#991B1B" # เขียว / แดง
        mass_bg_color = "#F0FDF4" if mass_part >= 90.0 else "#FEF2F2"
    else:
        mass_status_color = "#0F172A"
        mass_bg_color = "#FFFFFF"

    # ประเมินสถานะระยะโยกตัว
    if 'dynamic_status' in locals() and len(dynamic_status) > 0:
        overall_drift = "❌ ไม่ผ่านเกณฑ์ (FAIL)" if "❌ FAIL" in dynamic_status else "✅ ผ่านเกณฑ์ (PASS)"
        drift_color = "#991B1B" if "FAIL" in overall_drift else "#166534" 
    else:
        overall_drift = "รอผลการคำนวณ"
        drift_color = "#475569"

    # 2. สร้าง Graphviz DOT สำหรับ Dynamic Analysis (Modern UI Style)
    dynamic_flowchart_dot = f"""
    digraph DynamicSummary {{
        rankdir=TB;
        nodesep=0.8;
        ranksep=0.6;
        bgcolor="transparent";
        splines=ortho;
        pad=0.5;

        node [shape=plaintext, fontname="Helvetica, Arial, Tahoma, sans-serif", fontsize=12];
        edge [color="#94A3B8", penwidth=2, arrowsize=0.7]; 

        // 🎯 CARD 1: สเปกตรัมตอบสนอง
        Card_Spectrum [label=<
            <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10" COLOR="#CBD5E1" STYLE="ROUNDED">
                <TR><TD BGCOLOR="#0F172A" COLSPAN="4"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>📈 1. พารามิเตอร์สเปกตรัมตอบสนอง (Response Spectrum)</B></FONT></TD></TR>
                <TR>
                    <TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">S<SUB>DS</SUB> (g):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_SDS}</B></FONT></TD>
                    <TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">S<SUB>D1</SUB> (g):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_SD1}</B></FONT></TD>
                </TR>
                <TR>
                    <TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">คาบเวลา T<SUB>0</SUB> (s):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{f"{0.2 * float(_Ts):.3f}" if _Ts != "-" else "-"}</B></FONT></TD>
                    <TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">คาบเวลา T<SUB>S</SUB> (s):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_Ts}</B></FONT></TD>
                </TR>
            </TABLE>
        >];

        // 🎯 CARD 2: การวิเคราะห์โหมดและการมีส่วนร่วมของมวล
        Card_Modal [label=<
            <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10" COLOR="#CBD5E1" STYLE="ROUNDED">
                <TR><TD BGCOLOR="#0F172A" COLSPAN="2"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>🏢 2. การวิเคราะห์โหมด (Modal Analysis)</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">คาบเวลาโหมดที่ 1 (T<SUB>1</SUB>):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_T1} s.</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">จำนวนโหมดที่วิเคราะห์ (N):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_modes} โหมด</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">มวลที่เข้าร่วม (Mass Part. ≥ 90%):</FONT></TD><TD BGCOLOR="{mass_bg_color}"><FONT COLOR="{mass_status_color}"><B>{_mass_part}%</B></FONT></TD></TR>
            </TABLE>
        >];

        // 🎯 CARD 3: การปรับแก้แรงเฉือนที่ฐาน
        Card_Scaling [label=<
            <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10" COLOR="#CBD5E1" STYLE="ROUNDED">
                <TR><TD BGCOLOR="#0F172A" COLSPAN="2"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>⚖️ 3. การปรับแก้แรงเฉือนที่ฐาน (Base Shear Scaling)</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">แรงเฉือนสถิตยศาสตร์ (V<SUB>static</SUB>):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_V_static} ตัน</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">แรงเฉือนพลศาสตร์ (V<SUB>dynamic</SUB>):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{_V_dynamic} ตัน</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">ตัวคูณปรับแก้ (Scale Factor):</FONT></TD><TD BGCOLOR="#FFFBEB"><FONT COLOR="#D97706"><B>{_scale_factor}</B></FONT></TD></TR>
            </TABLE>
        >];

        // 🎯 CARD 4: การรวมผลตอบสนอง
        Card_Effects [label=<
            <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10" COLOR="#CBD5E1" STYLE="ROUNDED">
                <TR><TD BGCOLOR="#0F172A" COLSPAN="2"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>🔄 4. การรวมผลตอบสนอง (Combination Rules)</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">ทิศทางร่วม (Modal Comb.):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>CQC</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">แรงตั้งฉาก (Orthogonal):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A">100% / 30%</FONT></TD></TR>
            </TABLE>
        >];

        // 🎯 CARD 5: การตรวจสอบเสถียรภาพ (Dynamic)
        Card_Drift [label=<
            <TABLE BORDER="1" CELLBORDER="1" CELLSPACING="0" CELLPADDING="10" COLOR="#CBD5E1" STYLE="ROUNDED">
                <TR><TD BGCOLOR="#0F172A" COLSPAN="2"><FONT COLOR="#FFFFFF" POINT-SIZE="13"><B>🛡️ 5. การประเมินระยะโยกตัว (Dynamic Drift)</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">เกณฑ์ขีดจำกัด (Limit):</FONT></TD><TD BGCOLOR="#FFFFFF"><FONT COLOR="#0F172A"><B>{limit_pct:.1f}%</B></FONT></TD></TR>
                <TR><TD ALIGN="LEFT" BGCOLOR="#F8FAFC"><FONT COLOR="#475569">สถานะความปลอดภัย:</FONT></TD><TD BGCOLOR="{drift_color}"><FONT COLOR="#FFFFFF"><B>{overall_drift}</B></FONT></TD></TR>
            </TABLE>
        >];

        // 🔗 เชื่อมโยง Flow
        Card_Spectrum -> Card_Modal;
        Card_Modal -> Card_Scaling;
        Card_Scaling -> Card_Effects;
        Card_Scaling -> Card_Drift;
        
        // จัดให้ Effects กับ Drift อยู่ระดับเดียวกัน (Rank)
        {{ rank=same; Card_Effects; Card_Drift; }}
    }}
    """
    
    # 3. แสดงผล Flowchart
    st.graphviz_chart(dynamic_flowchart_dot, use_container_width=True)

# ───────────────────────────────────────────────────────────────────────────
# TAB 7: หน้าคำนวณและปรับแก้ผลการวิเคราะห์พลศาสตร์ (Dynamic Analysis Calculation)
# ───────────────────────────────────────────────────────────────────────────
with tab_dynamic_calc:
    st.header("⚙️ การปรับแก้ผลการวิเคราะห์ทางพลศาสตร์ (Response Spectrum Scaling)")
    st.markdown("""
    หน้าต่างนี้ใช้สำหรับนำผลลัพธ์จากซอฟต์แวร์วิเคราะห์โครงสร้าง 3 มิติ มาตรวจสอบการมีส่วนร่วมของมวล (Mass Participation) 
    และคำนวณหาตัวคูณปรับแก้แรงเฉือนที่ฐาน (Base Shear Scale Factor) ให้สอดคล้องกับแรงเฉือนสถิตยศาสตร์เทียบเท่า (Equivalent Static Base Shear) ตามมาตรฐาน
    """)
    st.divider()

    # สมมติฐานดึงค่า V_static จากแท็บก่อนหน้า (ถ้าไม่มีให้ตั้งค่าเริ่มต้น)
    _v_stat = total_V if 'total_V' in locals() else 100.0

    st.subheader("1. พารามิเตอร์เป้าหมาย (Target Parameters)")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        v_static_input = st.number_input("แรงเฉือนสถิตยศาสตร์เทียบเท่า (V_static) [ตัน]", value=float(_v_stat), step=10.0)
    with col_t2:
        target_ratio = st.radio("เกณฑ์แรงเฉือนเป้าหมาย (Target Base Shear Limit)", 
                                options=["100% ของ V_static (อาคารทั่วไป/ASCE 7-16)", "85% ของ V_static (อาคารมีความสม่ำเสมอ/มาตรฐานเดิม)"],
                                index=0)
    
    target_multiplier = 1.0 if "100%" in target_ratio else 0.85
    v_target = v_static_input * target_multiplier

    st.info(f"💡 **แรงเฉือนเป้าหมายที่ต้องการ (Target Base Shear):** **{v_target:,.2f}** ตัน")
    st.divider()

    st.subheader("2. ข้อมูลจากซอฟต์แวร์ 3D Analysis (Modal & Response Spectrum Results)")
    
    # แบ่งคอลัมน์ซ้ายขวา สำหรับทิศทาง X และ Y
    col_x, col_y = st.columns(2)
    
    with col_x:
        st.markdown("#### 🎯 การวิเคราะห์ทิศทาง X (X-Direction)")
        mass_part_x = st.number_input("มวลร่วมสะสม ทิศทาง X (Mass Participation X) [%]", min_value=0.0, max_value=100.0, value=90.0, step=1.0)
        v_dynamic_x = st.number_input("แรงเฉือนพลศาสตร์ ทิศทาง X (V_dynamic X) [ตัน]", min_value=0.1, value=v_static_input*0.7, step=10.0)
        
        # ตรวจสอบ Mass Participation
        if mass_part_x >= 90.0:
            st.success(f"✅ มวลร่วม {mass_part_x:.1f}% (ผ่านเกณฑ์ $\ge$ 90%)")
        else:
            st.error(f"❌ มวลร่วม {mass_part_x:.1f}% (ไม่ผ่านเกณฑ์ 90% โปรดเพิ่มจำนวนโหมด N)")

        # คำนวณ Scale Factor X
        sf_x = v_target / v_dynamic_x
        sf_x_final = max(1.0, sf_x) # ถ้า V_dyn > V_target ไม่ต้องลดค่า (ใช้ 1.0)
        
        st.metric(label="ตัวคูณปรับแก้ทิศทาง X (Scale Factor X)", value=f"{sf_x_final:.4f}")
        if sf_x > 1.0:
            st.caption(f"สมการ: $Scale\ Factor = \\frac{{{v_target:,.2f}}}{{{v_dynamic_x:,.2f}}}$")
        else:
            st.caption("แรงเฉือนพลศาสตร์มากกว่าเกณฑ์เป้าหมาย ไม่จำเป็นต้องปรับแก้ (ใช้ Scale Factor = 1.0)")

    with col_y:
        st.markdown("#### 🎯 การวิเคราะห์ทิศทาง Y (Y-Direction)")
        mass_part_y = st.number_input("มวลร่วมสะสม ทิศทาง Y (Mass Participation Y) [%]", min_value=0.0, max_value=100.0, value=92.0, step=1.0)
        v_dynamic_y = st.number_input("แรงเฉือนพลศาสตร์ ทิศทาง Y (V_dynamic Y) [ตัน]", min_value=0.1, value=v_static_input*0.8, step=10.0)
        
        # ตรวจสอบ Mass Participation
        if mass_part_y >= 90.0:
            st.success(f"✅ มวลร่วม {mass_part_y:.1f}% (ผ่านเกณฑ์ $\ge$ 90%)")
        else:
            st.error(f"❌ มวลร่วม {mass_part_y:.1f}% (ไม่ผ่านเกณฑ์ 90% โปรดเพิ่มจำนวนโหมด N)")

        # คำนวณ Scale Factor Y
        sf_y = v_target / v_dynamic_y
        sf_y_final = max(1.0, sf_y)
        
        st.metric(label="ตัวคูณปรับแก้ทิศทาง Y (Scale Factor Y)", value=f"{sf_y_final:.4f}")
        if sf_y > 1.0:
            st.caption(f"สมการ: $Scale\ Factor = \\frac{{{v_target:,.2f}}}{{{v_dynamic_y:,.2f}}}$")
        else:
            st.caption("แรงเฉือนพลศาสตร์มากกว่าเกณฑ์เป้าหมาย ไม่จำเป็นต้องปรับแก้ (ใช้ Scale Factor = 1.0)")
            
    st.divider()
    st.markdown("### 📌 สรุปผลการปรับแก้เพื่อนำไปตั้งค่าในซอฟต์แวร์ (ETABS / SAFE / STAAD)")
    st.markdown(f"""
    * **1. ทิศทาง X:** นำค่า Scale Factor = **{sf_x_final:.4f}** ไปคูณเข้ากับ Load Case ของ Response Spectrum ทิศทาง X 
    * **2. ทิศทาง Y:** นำค่า Scale Factor = **{sf_y_final:.4f}** ไปคูณเข้ากับ Load Case ของ Response Spectrum ทิศทาง Y
    * **3. โหมดรูปร่าง (Modal):** {'ผ่านเกณฑ์จำนวนโหมดแล้ว' if (mass_part_x >= 90 and mass_part_y >= 90) else '**จำเป็นต้องเพิ่มจำนวนโหมด (Number of Modes) ในการวิเคราะห์ให้มากขึ้น เนื่องจากมวลร่วมยังไม่ถึง 90%**'}
    """)




