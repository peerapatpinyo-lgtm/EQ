import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.interpolate import interp1d

# นำเข้าข้อมูลจาก data_loader
from data_loader import load_data, FA_TABLE, FV_TABLE

# ==========================================
# 1. การตั้งค่าหน้าจอและ UI
# ==========================================
st.set_page_config(page_title="DPT Seismic Calculator (Bangkok Basin Covered)", page_icon="🏢", layout="wide")
st.title("🏢 โปรแกรมคำนวณแรงแผ่นดินไหว (มยผ. 1301/1302-61)")
st.markdown("**เวอร์ชันอัปเดต: รองรับสเปกตรัมการออกแบบเฉพาะสำหรับพื้นที่แอ่งกรุงเทพฯ และปริมณฑล**")

# โหลดฐานข้อมูลพื้นที่
df_location = load_data()

# ==========================================
# 2. ส่วนควบคุมด้านข้าง (Sidebar Input)
# ==========================================
st.sidebar.header("📍 1. เลือกพิกัดและชั้นดิน")

input_method = st.sidebar.radio("วิธีการระบุค่าความเร่งแผ่นดินไหว:", ["ดึงจากฐานข้อมูล", "ป้อนค่าด้วยตนเอง (Manual)"])

is_bangkok_basin = False

if input_method == "ดึงจากฐานข้อมูล":
    provinces = sorted(df_location['Province'].unique())
    selected_province = st.sidebar.selectbox("จังหวัด:", provinces, index=provinces.index("เชียงราย") if "เชียงราย" in provinces else 0)
    
    districts = sorted(df_location[df_location['Province'] == selected_province]['District'].unique())
    selected_district = st.sidebar.selectbox("อำเภอ/เขต:", districts)
    
    location_row = df_location[(df_location['Province'] == selected_province) & (df_location['District'] == selected_district)].iloc[0]
    
    # เช็กว่าเป็นพื้นที่แอ่งดินอ่อนกรุงเทพและปริมณฑลหรือไม่
    if "ดินเหนียวอ่อน" in str(location_row['District']):
        is_bangkok_basin = True
        Ss = 0.0
        S1 = 0.0
    else:
        Ss = float(location_row['Ss'])
        S1 = float(location_row['S1'])
else:
    # กรณีป้อนค่าเอง ให้สิทธิ์ผู้ใช้เลือกว่าเป็นแอ่งกรุงเทพฯ หรือไม่
    is_bb_manual = st.sidebar.checkbox("📐 เป็นพื้นที่แอ่งดินอ่อนกรุงเทพฯ (มยผ. 1302)")
    if is_bb_manual:
        is_bangkok_basin = True
        Ss, S1 = 0.0, 0.0
    else:
        Ss = st.sidebar.number_input("ค่าความเร่งคาบสั้น Ss (g):", min_value=0.0, max_value=3.0, value=0.85, step=0.01)
        S1 = st.sidebar.number_input("ค่าความเร่งคาบ 1 วินาที S1 (g):", min_value=0.0, max_value=1.5, value=0.25, step=0.01)

# การเลือกประเภทชั้นดิน (ข้ามขั้นตอนนี้หากเป็นแอ่งกรุงเทพฯ เพราะสเปกตรัมถูกกำหนดเฉพาะแล้ว)
if not is_bangkok_basin:
    soil_type = st.sidebar.selectbox(
        "ประเภทชั้นดิน (Soil Site Class):",
        ["A (หินแข็ง)", "B (หินปานกลาง)", "C (ดินแข็ง/หนาแน่น)", "D (ดินนิ่มปานกลาง)", "E (ดินนิ่ม)"]
    )
    soil_class = soil_type.split()[0]
else:
    st.sidebar.info("ℹ️ พื้นที่แอ่งกรุงเทพฯ: ใช้ลักษณะสเปกตรัมเฉพาะของชั้นดินเหนียวอ่อนหนาพิเศษ ไม่ต้องเลือก Site Class")
    soil_class = "E"  # กำหนดค่า default ภายในเพื่อป้องกัน Error ในจุดอื่น

# ปัจจัยความสำคัญของอาคาร (Importance Factor, Ie)
st.sidebar.header("🏢 2. ข้อมูลอาคาร")
occupancy_category = st.sidebar.selectbox(
    "ประเภทการใช้งานอาคาร (Occupancy Category):",
    ["ประเภทที่ 1: อาคารทั่วไป/ที่พักอาศัย (Ie = 1.0)", 
     "ประเภทที่ 2: อาคารสาธารณะ/คนชุมนุมมาก (Ie = 1.25)", 
     "ประเภทที่ 3: อาคารจำเป็นต่อการบรรเทาภัย เช่น โรงพยาบาล/ดับเพลิง (Ie = 1.5)"]
)
Ie = 1.0 if "ประเภทที่ 1" in occupancy_category else (1.25 if "ประเภทที่ 2" in occupancy_category else 1.5)

# ระบบโครงสร้างต้านทานแรงด้านข้าง (R)
r_value_choice = st.sidebar.selectbox(
    "ระบบโครงสร้างต้านทานแรงแผ่นดินไหว (R):",
    ["โครงต้านแรงดัดคอนกรีตเสริมเหล็กเหนียวพิเศษ (SMF) [R = 8.5]",
     "โครงต้านแรงดัดคอนกรีตเสริมเหล็กเหนียวปานกลาง (IMF) [R = 5.0]",
     "โครงต้านแรงดัดคอนกรีตเสริมเหล็กเหนียวธรรมดา (OMF) [R = 3.0]",
     "กำแพงรับแรงเฉือนคอนกรีตเสริมเหล็กเหนียวพิเศษ [R = 6.0]",
     "กำแพงรับแรงเฉือนคอนกรีตเสริมเหล็กเหนียวธรรมดา [R = 4.0]"]
)
R = float(r_value_choice.split("[R = ")[1].replace("]", ""))

# ==========================================
# 3. ฟังก์ชันคำนวณทางวิศวกรรม (Engineering Calculations)
# ==========================================
def interpolate_coefficient(keys, values, target):
    if target <= keys[0]: return values[0]
    if target >= keys[-1]: return values[-1]
    f = interp1d(keys, values, kind='linear')
    return float(f(target))

# ประมวลผลพารามิเตอร์หลัก
if is_bangkok_basin:
    # ค่าสัมประสิทธิ์ออกแบบเฉพาะสำหรับแอ่งกรุงเทพฯ (Bangkok Basin Design Parametersตาม มยผ. 1302-61)
    # สะท้อนการขยายคาบยาวช่วงกว้าง (Broadened Long-period plateau)
    SDS = 0.220
    SD1 = 0.285
    T0 = 0.26  # วินาที
    Ts = 1.30  # วินาที (คาบวิกฤตยาวกว่าปกติเนื่องจากแอ่งดินนิ่มมาก)
    TL = 4.0   # คาบระยะยาวปลายสุด
    Fa, Fv = 1.0, 1.0  # ไม่ใช้ตารางทั่วไป
    SMS, SM1 = SDS, SD1
else:
    # คำนวณตามมาตรฐานทั่วไปผ่านตารางสเปกตรัมหินฐาน
    Fa = interpolate_coefficient(FA_TABLE['Ss_keys'], FA_TABLE[soil_class], Ss)
    Fv = interpolate_coefficient(FV_TABLE['S1_keys'], FV_TABLE[soil_class], S1)
    SMS = Ss * Fa
    SM1 = S1 * Fv
    SDS = (2.0 / 3.0) * SMS
    SD1 = (2.0 / 3.0) * SM1
    
    # หาค่าคาบการเปลี่ยนผ่านช่วงเวลา (Control Periods)
    if SDS > 0:
        Ts = SD1 / SDS
        T0 = 0.2 * Ts
    else:
        Ts, T0 = 0.5, 0.1
    TL = 4.0

# คำนวณประเภทการออกแบบต้านทานแผ่นดินไหว (Seismic Design Category: SDC)
def determine_sdc(sds, sd1):
    if sds < 0.167 and sd1 < 0.067: return "A"
    if (0.167 <= sds < 0.33) or (0.067 <= sd1 < 0.133): return "B"
    if (0.33 <= sds < 0.50) or (0.133 <= sd1 < 0.20): return "C"
    return "D"

SDC = determine_sdc(SDS, SD1)

# ==========================================
# 4. การแสดงผลหน้าจอหลัก (Tabs Layout)
# ==========================================
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 พารามิเตอร์เริ่มต้น", 
    "📈 กราฟสเปกตรัมการออกแบบ", 
    "🧮 คำนวณแรงเฉือนที่ฐานอาคาร", 
    "📐 ประเมินความปลอดภัย (Story Drift)"
])

# ------------------------------------------
# Tab 1: แสดงพารามิเตอร์การออกแบบ
# ------------------------------------------
with tab1:
    if is_bangkok_basin:
        st.success("🔔 **ระบบตรวจพบพิกัดในพื้นที่แอ่งดินเหนียวอ่อนกรุงเทพฯ และปริมณฑล**")
        st.info("💡 ตัวคูณขยายชั้นดินทั่วไป (Fa, Fv) จะถูกข้าม โดยโปรแกรมจะประยุกต์ใช้เส้นโค้งสเปกตรัมสำหรับแอ่งกรุงเทพฯ (Bangkok Basin Response Spectrum) โดยตรงเพื่อความปลอดภัยสูงสุดและสอดคล้องต่อ มยผ. 1302-61")
    else:
        st.write(f"🗺️ **พิกัดปัจจุบัน:** {selected_province} - {selected_district}" if input_method == "ดึงจากฐานข้อมูล" else "🔧 โหมดป้อนค่าพารามิเตอร์ด้วยตนเอง")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Short Period Acceleration (Ss)", f"{Ss:.3f} g" if not is_bangkok_basin else "N/A (Bangkok Clay)")
        st.metric("Short Period Design Value (SDS)", f"{SDS:.3f} g")
    with col2:
        st.metric("1-Sec Period Acceleration (S1)", f"{S1:.3f} g" if not is_bangkok_basin else "N/A (Bangkok Clay)")
        st.metric("1-Sec Design Value (SD1)", f"{SD1:.3f} g")
    with col3:
        st.metric("ตัวคูณขยายระดับดิน Fa / Fv", f"{Fa:.2f} / {Fv:.2f}" if not is_bangkok_basin else "สเปกตรัมเฉพาะแอ่ง")
        st.subheader(f"ระดับความเสี่ยงภัย (SDC): :red[{SDC}]")

    st.markdown("""
    ### 📝 สรุปข้อกำหนดทางวิศวกรรมสำหรับระดับ SDC ปัจจุบัน:
    * **SDC A & B:** อนุญาตให้ใช้วิธีแรงสถิตเทียบเท่าอย่างง่าย โครงสร้างทั่วไปไม่ต้องใช้รายละเอียดความเหนียวพิเศษ
    * **SDC C:** จำเป็นต้องเริ่มใช้โครงสร้างความเหนียวปานกลาง (IMF) ขึ้นไป และตรวจสอบรอยต่อคาน-เสาอย่างละเอียด
    * **SDC D:** โครงสร้างหลักต้องเป็นแบบเหนียวพิเศษ (SMF / Special Shear Wall) ห้ามใช้โครงสร้างรับแรงต้านทานต่ำเด็ดขาด
    """)

# ------------------------------------------
# Tab 2: พล็อตกราฟ Design Response Spectrum
# ------------------------------------------
with tab2:
    st.subheader("📊 กราฟความเร่งตอบสนองการออกแบบ (Design Response Spectrum, Sa)")
    
    # คำนวณเส้นกราฟ Response Spectrum
    T_curve = np.linspace(0.01, 5.0, 500)
    Sa_curve = []
    for T in T_curve:
        if T < T0:
            Sa = SDS * (0.4 + 0.6 * (T / T0))
        elif T <= Ts:
            Sa = SDS
        elif T <= TL:
            Sa = SD1 / T
        else:
            Sa = (SD1 * TL) / (T ** 2)
        Sa_curve.append(Sa)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=T_curve, y=Sa_curve, mode='lines', name='Design Spectrum (Sa)', line=dict(color='firebrick', width=3)))
    
    # เพิ่มขอบเขตช่วงคงที่ (Plateau) เพื่อให้วิศวกรมองภาพออกง่าย
    fig.add_vline(x=T0, line_dash="dash", line_color="green", annotation_text=f"T0={T0:.2f}s")
    fig.add_vline(x=Ts, line_dash="dash", line_color="blue", annotation_text=f"Ts={Ts:.2f}s (จุดหักคาบยาว)")

    fig.update_layout(
        title=f"Design Response Spectrum ({'Bangkok Basin Spectrum' if is_bangkok_basin else 'Standard DPT Spectrum'})",
        xaxis_title="คาบเวลาการสั่นธรรมชาติอาคาร T (วินาที)",
        yaxis_title="ความเร่งตอบสนองการออกแบบ Sa (g)",
        grid=dict(rows=1, columns=1),
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------
# Tab 3: การคำนวณแรงเฉือนที่ฐานอาคาร (Base Shear, V)
# ------------------------------------------
with tab3:
    st.subheader("🧮 การคำนวณแรงสถิตเทียบเท่า (Equivalent Lateral Force Procedure)")
    
    col1, col2 = st.columns(2)
    with col1:
        W = st.number_input("น้ำหนักรวมคงที่ของอาคาร W (กิโลนิวตัน, kN):", min_value=10.0, value=5000.0, step=100.0)
        building_height = st.number_input("ความสูงอาคารรวมจากฐานถึงดาดฟ้า H (เมตร):", min_value=1.0, value=25.0, step=0.5)
        
        # คาบเวลาการสั่นธรรมชาติเบื้องต้นทางฟิสิกส์อาคาร T_approx
        # คอนกรีตเสริมเหล็กทั่วไป Ct = 0.0466, x = 0.9 ตามมาตรฐาน มยผ.
        T_approx = 0.0466 * (building_height ** 0.9)
        st.info(f"⏱️ คาบเวลาธรรมชาติอาคารโดยประมาณ (T_approx) = {T_approx:.3f} วินาที")

    with col2:
        # ดึงความเร่ง Sa ณ คาบอาคารจริงจากกราฟ
        if T_approx < T0:
            Sa_design = SDS * (0.4 + 0.6 * (T_approx / T0))
        elif T_approx <= Ts:
            Sa_design = SDS
        elif T_approx <= TL:
            Sa_design = SD1 / T_approx
        else:
            Sa_design = (SD1 * TL) / (T_approx ** 2)
            
        # คำนวณหาค่าสัมประสิทธิ์แรงเฉือนที่ฐาน Cs
        Cs = Sa_design / (R / I_e)
        
        # ตรวจสอบขีดจำกัดขั้นต่ำตามกฎหมาย (Cs min limits)
        Cs_min = max(0.011 * SDS * I_e, 0.01)
        if Cs < Cs_min:
            Cs = Cs_min
            st.warning(f"⚠️ ค่า Cs ต่ำกว่าเกณฑ์ขั้นต่ำ ระบบปรับขึ้นมาใช้ค่าขีดจำกัดล่าง = {Cs_min:.4f}")

        st.metric("สัมประสิทธิ์แรงแผ่นดินไหว Cs", f"{Cs:.4f}")
        
    # สรุปผลลัพธ์แรงเฉือนที่ฐานอาคาร
    Base_Shear_V = Cs * W
    st.markdown("---")
    st.subheader(f"🏆 แรงเฉือนที่ฐานอาคารรวม (Total Base Shear, V) = :blue[{Base_Shear_V:,.2f} kN]")
    
    # แสดงสูตรการกระจายแรงสู่รายชั้นแบบคร่าว ๆ
    st.markdown(f"""
    **สมการอ้างอิง:** $V = C_s \times W$
    * สัมประสิทธิ์ขยายพฤติกรรมโครงสร้าง $R$ = {R} | ตัวคูณความสำคัญอาคาร $I_e$ = {I_e}
    * แรงกระทบด้านข้างนี้จะต้องนำไปกระจายเข้าสัดส่วนความสูงแต่ละชั้นอาคาร ($F_x$) เพื่อใช้ออกแบบชิ้นส่วนโครงสร้าง เสา คาน และผนังรับแรง ต่อไป
    """)

# ------------------------------------------
# Tab 4: ประเมินการเยื้องตัวระหว่างชั้น (Story Drift Ratio)
# ------------------------------------------
with tab4:
    st.subheader("📐 การตรวจสอบการโยกตัวและการเยื้องตัวอาคาร (Story Drift Limitations)")
    st.markdown("กรอกระยะการเคลื่อนตัวที่ได้จากการวิเคราะห์โครงสร้าง (Elastic Displacement, $\delta_{xe}$) เพื่อเทียบกับขีดจำกัดความปลอดภัย")

    drift_limit_factor = 0.020  # สำหรับอาคารทั่วไปตาม มยผ. 1302-61
    
    # จำลองตารางรับข้อมูลชั้นอาคารจำนวน 4 ชั้น (สามารถแก้ไขเพิ่มได้แบบ Dynamic)
    init_drift_data = {
        "ชื่อชั้น": ["ชั้นที่ 4", "ชั้นที่ 3", "ชั้นที่ 2", "ชั้นที่ 1"],
        "ความสูงระหว่างชั้น h (ม.)": [3.50, 3.50, 3.50, 4.00],
        "ระยะเคลื่อนตัวสะสมจากโมเดล δxe (ซม.)": [3.20, 2.50, 1.60, 0.70]
    }
    df_drift = pd.DataFrame(init_drift_data)
    
    edited_drift = st.data_editor(df_drift, num_rows="dynamic", use_container_width=True)
    
    if st.button("📊 ประมวลผลและตรวจสอบความปลอดภัยโครงสร้าง"):
        try:
            # คำนวณระยะเยื้องตัวจริงหลังพิจารณาพฤติกรรมพลาสติก (Inelastic Drift, δx = Cd * δxe / Ie)
            # ใน มยผ. แนะนำให้ประเมินจากอัตราขยาย และหาความต่างระยะเยื้องตัวสุทธิระหว่างชั้น (Δ)
            Cd = R  # ในแบบจำลองอย่างง่ายให้ประมาณค่าอัตราขยายการเคลื่อนตัวผันกลับเท่ากับตัวคูณ R
            
            delta_x = []
            for idx, row in edited_drift.iterrows():
                d_xe = float(row["ระยะเคลื่อนตัวสะสมจากโมเดล δxe (ซม.)"])
                # คำนวณค่าพลาสติกจริงในสนาม
                d_x = (Cd * d_xe) / Ie
                delta_x.append(d_x)
            
            # คำนวณค่าความต่างระหว่างชั้น (Interstory Drift, Delta)
            drift_ratio = []
            status = []
            story_h = []
            
            for i in range(len(delta_x)):
                h_net = float(edited_drift.iloc[i]["ความสูงระหว่างชั้น h (ม.)"])
                
                if i == len(delta_x) - 1:
                    # ชั้นล่างสุด
                    delta_diff = delta_x[i]
                else:
                    # ชั้นบนลบชั้นถัดลงมา
                    delta_diff = delta_x[i] - delta_x[i+1]
                
                # ตรวจสอบขีดจำกัดความปลอดภัย
                story_h.append(h_net)
                drift_ratio_val = delta_diff / (h_net * 100.0)
                drift_ratio.append(drift_ratio_val)
                status.append("✅ PASS" if drift_ratio_val <= drift_limit_factor else "❌ FAIL")

            res_drift = edited_drift.copy()
            res_drift["ความสูงชั้นสุทธิ (ม.)"] = story_h
            res_drift["ระยะโยกจริงในสนาม δx (ซม.)"] = delta_x
            res_drift["Drift Ratio (Δ/h)"] = drift_ratio
            res_drift["Limit (Max)"] = drift_limit_factor
            res_drift["ผลการประเมิน"] = status

            st.markdown("### 🏆 ตารางประเมินผลความปลอดภัยโครงสร้างอาคาร")
            st.dataframe(
                res_drift.style.map(
                    lambda v: (
                        'background-color: #dcfce7; color: #166534; font-weight: bold;' if 'PASS' in str(v)
                        else ('background-color: #fee2e2; color: #991b1b; font-weight: bold;' if 'FAIL' in str(v) else '')
                    ),
                    subset=['ผลการประเมิน']
                ).format({
                    "ความสูงชั้นสุทธิ (ม.)": "{:.2f}",
                    "ระยะโยกจริงในสนาม δx (ซม.)": "{:.2f}",
                    "Drift Ratio (Δ/h)": "{:.4f}",
                    "Limit (Max)": "{:.3f}"
                }),
                use_container_width=True
            )
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการประมวลผล กรุณาตรวจสอบข้อมูลนำเข้า: {e}")
