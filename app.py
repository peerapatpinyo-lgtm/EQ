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

# ───────────────────────────────────────────────────────────────────────────
# TAB 3: การแสดงผลกราฟและบทวิเคราะห์ Design Response Spectrum (มยผ. 1301/1302)
# ───────────────────────────────────────────────────────────────────────────
with tab3:
    st.header("📈 กราฟความเร่งตอบสนองเชิงสเปกตรัม (Design Response Spectrum)")
    
    if sdc == 'ก':
        st.info("💡 **ข้อแนะนำทางกฎหมาย:** โครงสร้างจัดอยู่ในประเภท SDC 'ก' ซึ่งมีความเสี่ยงภัยแผ่นดินไหวต่ำมาก ตามมาตรฐาน มยผ. ไม่บังคับให้ต้องวิเคราะห์แรงลมหรือสเปกตรัมโดยวิธีขั้นสูง กราฟแสดงไว้เพื่อการตรวจสอบเชิงวิศวกรรมเท่านั้น")
        
    # ส่วนคำอธิบายพฤติกรรมเชิงลึกเพื่อรายงานวิศวกรรม
    st.markdown("""
    ### 🔬 บทวิเคราะห์พฤติกรรมโครงสร้าง (Structural Dynamic Analysis)
    กราฟด้านล่างแสดงความสัมพันธ์ระหว่าง **คาบเวลาธรรมชาติ ($T$)** และ **ความเร่งตอบสนองเชิงสเปกตรัม ($S_a$)** ซึ่งเป็นตัวแทนของแรงสูงสุดที่โครงสร้างจะได้รับในรูปแบบของสัดส่วนแรงโน้มถ่วง ($g$) โดยจะถูกแปลงเป็นแรงเฉือนที่ฐานอาคาร (Base Shear) ต่อไป
    """)

    # คำนวณพิกัดแกน X และ Y สำหรับสร้างเส้นกราฟสเปกตรัม
    max_T_plot = max(4.0, Ta * 1.5, TS * 2.5) # ปรับสเกลอัตโนมัติให้เห็นพิกัดอาคารชัดเจน
    T_values = np.linspace(0.0, max_T_plot, 500)
    Sa_values = np.array([calc.compute_spectrum_sa(t, SDS, SD1, T0, TS) for t in T_values])
    Sa_Ta = calc.compute_spectrum_sa(Ta, SDS, SD1, T0, TS)

    # 1. แสดงผลกราฟที่ดึงมาจาก plots.py
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
    
    # ตกแต่งตารางข้อมูล ไฮไลท์บรรทัดของอาคารปัจจุบันเป็นสีส้มเด่นชัด
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
    st.header("🏢 การวิเคราะห์ด้วยวิธีแรงสถิตเทียบเท่า (Equivalent Static Procedure)")
    
    if sdc in ['ก']:
        st.warning("⚠️ โครงสร้างประเภท 'ก' ไม่บังคับให้ต้องคำนวณแรงแผ่นดินไหวด้วยวิธีนี้ (สามารถข้ามแท็บนี้ได้)")
    
    st.markdown("""
    วิธีแรงสถิตเทียบเท่าใช้ประเมินแรงเฉือนที่ฐานอาคาร (Base Shear, $V$) และกระจายแรงกระทำด้านข้างเข้าสู่แต่ละชั้นของอาคาร ($F_x$) 
    วิธีนี้เหมาะสำหรับอาคารที่มีความสม่ำเสมอและมีความสูงไม่เกินข้อกำหนดของ มยผ.
    """)

    # ==========================================
    # ส่วนที่ 1: การกระจายแรงแผ่นดินไหว (Vertical Distribution of Seismic Forces)
    # ==========================================
    st.subheader("1️⃣ การกระจายแรงเฉือนที่ฐานเข้าสู่แต่ละชั้นอาคาร")
    
    col_v1, col_v2 = st.columns([1, 2])
    with col_v1:
        st.info(f"**แรงเฉือนที่ฐานอาคาร (Base Shear):**\n### V = {Cs_gov * total_weight:,.2f} ตัน")
        st.caption(f"มาจากสมการ $V = C_s W$ (โดยที่ $C_s$ = {Cs_gov:.4f}, $W$ = {total_weight:,.2f} ตัน)")
    with col_v2:
        st.markdown("**สมการกระจายแรงตามแนวดิ่ง (Vertical Distribution):**")
        st.latex(r"F_x = C_{vx} V \quad \text{โดยที่} \quad C_{vx} = \frac{w_x h_x^k}{\sum_{i=1}^{n} w_i h_i^k}")
        st.caption(f"💡 สำหรับอาคารนี้ คาบเวลา $T_a$ = {Ta:.3f} s จึงใช้ค่าตัวคูณกระจายแรง (Exponent) **$k$ = {k:.3f}**")

    # กำหนดค่าเริ่มต้นสำหรับตารางข้อมูลชั้นอาคาร
    st.markdown("**กรุณาระบุความสูง (นับจากฐาน) และน้ำหนักของแต่ละชั้น (Floor Data):**")
    default_floors = pd.DataFrame({
        "ชั้นที่": ["Roof", "Floor 3", "Floor 2", "Floor 1"],
        "ความสูงสะสม hx (ม.)": [12.0, 9.0, 6.0, 3.0],
        "น้ำหนักชั้น wx (ตัน)": [200.0, 250.0, 250.0, 250.0]
    })
    
    edited_floors = st.data_editor(default_floors, num_rows="dynamic", use_container_width=True)
    
    # คำนวณและพล็อตพารามิเตอร์ของแรงแผ่นดินไหว
    hx = edited_floors["ความสูงสะสม hx (ม.)"].to_numpy()
    wx = edited_floors["น้ำหนักชั้น wx (ตัน)"].to_numpy()
    
    if len(hx) > 0 and len(wx) > 0:
        Fx, Vx, Mx = calc.calculate_story_forces(hx, wx, Cs_gov, Ta)
        fig_forces = plots.create_force_plot(hx, Fx, Vx, Mx)
        st.plotly_chart(fig_forces, use_container_width=True)
        
        # แสดงตารางผลลัพธ์
        df_forces = pd.DataFrame({
            "ชั้นที่": edited_floors["ชั้นที่"],
            "แรงกระทำด้านข้าง Fx (ตัน)": Fx,
            "แรงเฉือนสะสม Vx (ตัน)": Vx,
            "โมเมนต์พลิกคว่ำ Mx (ตัน-ม.)": Mx
        })
        with st.expander("📊 ดูตารางสรุปแรงประจำชั้น (Story Forces Table)"):
            st.dataframe(df_forces.style.format({"แรงกระทำด้านข้าง Fx (ตัน)": "{:.2f}", "แรงเฉือนสะสม Vx (ตัน)": "{:.2f}", "โมเมนต์พลิกคว่ำ Mx (ตัน-ม.)": "{:.2f}"}), hide_index=True)

    st.markdown("---")

    # ==========================================
    # ส่วนที่ 2: การตรวจสอบระยะการโยกตัว (Inter-story Drift Check)
    # ==========================================
    
    st.subheader("2️⃣ การตรวจสอบระยะการโยกตัวระหว่างชั้น (Inter-story Drift Check)")
    st.markdown("การตรวจสอบ Drift เป็นการการันตีว่าอาคารมีความแข็งเกร็ง (Stiffness) เพียงพอที่จะไม่ทำให้โครงสร้างรองหรือสถาปัตยกรรมเกิดความเสียหายจากแผ่นดินไหว")
    
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.markdown("**สมการขยายระยะโยกตัวแบบยืดหยุ่นให้เป็นระยะโยกตัวจริง:**")
        st.latex(r"\delta_x = \frac{C_d \delta_{ex}}{I_e}")
    with col_d2:
        st.info(f"**ขีดจำกัดระยะโยกตัว (Drift Limit) สำหรับอาคารความสำคัญ $I_e$ = {Ie}:**\n### Δ_{{max}} = {drift_limit_factor}% ของความสูงชั้น")

    st.markdown("**กรุณาระบุระยะโยกตัวแบบยืดหยุ่น ($\delta_e$) ที่ได้จากการรันโปรแกรมวิเคราะห์โครงสร้าง:**")
    default_drift = pd.DataFrame({
        "ชั้นที่": edited_floors["ชั้นที่"],
        "ความสูงสะสม hx (ม.)": hx,
        "Elastic Displacement δe (ซม.)": [3.5, 2.8, 1.5, 0.5]
    })
    
    edited_drift = st.data_editor(default_drift, use_container_width=True)
    
    if st.button("🚀 ประเมินความปลอดภัยระยะการโยกตัว (Check Drift)", type="primary"):
        de_x = edited_drift["Elastic Displacement δe (ซม.)"].to_numpy()
        delta_x = (Cd * de_x) / Ie
        
        n = len(hx)
        story_h, drift_ratio, status = np.zeros(n), np.zeros(n), []
        
        for i in range(n):
            if i < n - 1:
                h_net = hx[i] - hx[i+1]
                delta_diff = delta_x[i] - delta_x[i+1]
            else:
                h_net = hx[i]
                delta_diff = delta_x[i]
                
            h_net = max(h_net, 0.001)
            story_h[i] = h_net
            drift_ratio[i] = delta_diff / (h_net * 100.0) # แปลง h_net เป็นเซนติเมตร
            status.append("✅ PASS" if drift_ratio[i] <= drift_limit_factor else "❌ FAIL")
            
        res_drift = edited_drift.copy()
        res_drift["ความสูงชั้นสุทธิ (ม.)"] = story_h
        res_drift["ระยะโยกจริงในสนาม δx (ซม.)"] = delta_x
        res_drift["Drift Ratio (Δ/h) %"] = drift_ratio * 100 # โชว์เป็นเปอร์เซ็นต์
        res_drift["Limit (Max) %"] = drift_limit_factor
        res_drift["ผลการประเมิน"] = status
        
        st.markdown("### 🏆 ผลการประเมินความปลอดภัยโครงสร้างอาคาร")
        st.dataframe(
            res_drift.style.map(
                lambda v: 'background-color: #dcfce7; color: #166534; font-weight: bold;' if 'PASS' in str(v) else ('background-color: #fee2e2; color: #991b1b; font-weight: bold;' if 'FAIL' in str(v) else ''),
                subset=['ผลการประเมิน']
            ).format({
                "ความสูงชั้นสุทธิ (ม.)": "{:.2f}",
                "ระยะโยกจริงในสนาม δx (ซม.)": "{:.2f}",
                "Drift Ratio (Δ/h) %": "{:.3f}%",
                "Limit (Max) %": "{:.2f}%"
            }),
            use_container_width=True, hide_index=True
        )
        
        # แสดงรูป Schematic แผนภาพการโยกตัว
        fig_model = plots.create_drift_model_plot()
        st.plotly_chart(fig_model, use_container_width=True)
