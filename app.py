import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.graph_objects as go
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

def evaluate_sdc_detailed(SDS: float, SD1: float, Ie: float) -> tuple:
    """ฟังก์ชันประเมินประเภทการออกแบบ (SDC) พร้อมคืนค่ารายละเอียด"""
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
    
    sdc_final = 'ก'
    for cat, val in sdc_order.items():
        if val == max_val: sdc_final = cat
        
    return sdc_final, sdc_sds, sdc_sd1

# ==========================================
# 4. ส่วนรับข้อมูลผู้ใช้งาน (Sidebar Inputs)
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
    sys_type = st.selectbox("ระบบโครงสร้าง (หา Ta)", ["โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก", "โครงต้านทานแรงดัดเหล็กกล้า", "โครงสร้างอื่นๆ"])
    
    st.subheader("3. มิติและน้ำหนัก")
    building_height = st.number_input("ความสูงอาคาร hn (เมตร)", min_value=1.0, value=10.0, step=1.0)
    building_weight = st.number_input("น้ำหนักรวม W (ตัน)", min_value=1.0, value=500.0, step=100.0)

# ==========================================
# 5. ประมวลผลและตรวจสอบเงื่อนไขตั้งต้น
# ==========================================
if site_class == 'F':
    st.error("🛑 ชั้นดิน F ต้องเจาะสำรวจประเมินเฉพาะพื้นที่ (Site-Specific) เท่านั้น ไม่สามารถใช้ค่าคำนวณมาตรฐานได้")
    st.stop()

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

sdc, sdc_sds, sdc_sd1 = evaluate_sdc_detailed(SDS, SD1, importance_factor)

Cs_calculated = SDS / (r_factor / importance_factor) if r_factor > 0 else 0
Cs_max = SD1 / (Ta * (r_factor / importance_factor)) if (Ta > 0 and r_factor > 0) else Cs_calculated
Cs_min = 0.01
if S1 >= 0.6: Cs_min = max(Cs_min, (0.5 * S1) / (r_factor / importance_factor))

Cs_design = min(max(Cs_calculated, Cs_min), Cs_max)
Base_Shear = Cs_design * building_weight

# ==========================================
# 6. การแสดงผล (แบบแบ่ง Tabs เต็มรูปแบบ)
# ==========================================
st.markdown("---")

# แบ่งเป็น 4 Tabs อย่างเป็นระเบียบ
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 รายการคำนวณพารามิเตอร์", 
    "🛡️ ประเภทการออกแบบ (SDC)", 
    "📈 กราฟสเปกตรัม", 
    "🏢 แรงเฉือนที่ฐาน"
])

# ----------------- TAB 1 -----------------
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
        params_dict = {"โครงต้านทานแรงดัดเหล็กกล้า": (0.0724, 0.8), "โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก": (0.0466, 0.9), "โครงสร้างอื่นๆ": (0.0488, 0.75)}
        Ct, x = params_dict.get(sys_type, (0.0488, 0.75))
        st.latex(r"T_a = C_t h_n^x" + rf" = {Ct} \times {building_height}^{{{x}}} = {Ta:.3f} \text{{ s}}")
        
    with col_t2:
        st.warning("📈 **จุดเปลี่ยนผ่านบนกราฟ ($T_0, T_S$)**")
        if SDS > 0:
            st.latex(r"T_S = \frac{S_{D1}}{S_{DS}}" + rf" = \frac{{{SD1:.3f}}}{{{SDS:.3f}}} = {TS:.3f} \text{{ s}}")
            st.latex(r"T_0 = 0.2 T_S" + rf" = 0.2 \times {TS:.3f} = {T0:.3f} \text{{ s}}")
        else:
            st.latex(r"T_S = 0.000 \text{ s}")
            st.latex(r"T_0 = 0.000 \text{ s}")


# ----------------- TAB 2 -----------------
with tab2:
    st.header("🛡️ ผลการประเมินประเภทการออกแบบ (Seismic Design Category)")
    
    # 1. นิยามข้อกำหนดตามเกณฑ์ มยผ. สำหรับแต่ละประเภท
    sdc_actions = {
        'ก': {
            'title': "ประเภท ก (SDC A) - ความเสี่ยงภัยแผ่นดินไหวต่ำมาก",
            'analysis': "✅ อนุญาตให้ไม่ต้องวิเคราะห์แรงแผ่นดินไหวแบบเต็มรูปแบบ",
            'detailing': "🔧 ใช้รายละเอียดโครงสร้างคอนกรีตเสริมเหล็กตามมาตรฐานปกติ (ไม่ต้องจัดเหล็กปลอกต้านแผ่นดินไหว)",
            'action': "📝 **สิ่งที่ต้องทำต่อ:** ออกแบบให้โครงสร้างต้านทานแรงกระทำด้านข้างขั้นต่ำอย่างน้อย 1% ของน้ำหนักอาคาร ($0.01W$)"
        },
        'ข': {
            'title': "ประเภท ข (SDC B) - ความเสี่ยงภัยแผ่นดินไหวต่ำ",
            'analysis': "✅ สามารถใช้วิธีแรงสถิตเทียบเท่า (Equivalent Static) ในการคำนวณได้",
            'detailing': "🔧 ต้องจัดรายละเอียดโครงสร้างให้มีความเหนียวจำกัด (Ordinary Ductility)",
            'action': "📝 **สิ่งที่ต้องทำต่อ:** ไปที่ Tab 4 เพื่อคำนวณแรงเฉือนที่ฐาน และกระจายแรงเข้าแต่ละชั้น"
        },
        'ค': {
            'title': "ประเภท ค (SDC C) - ความเสี่ยงภัยแผ่นดินไหวปานกลาง",
            'analysis': "⚠️ ใช้วิธีแรงสถิตเทียบเท่าได้เฉพาะอาคารที่มีรูปทรงสม่ำเสมอ (Regular) เท่านั้น",
            'detailing': "🚨 **บังคับ:** โครงสร้างต้องออกแบบให้มีความเหนียวปานกลาง (Intermediate Ductility)",
            'action': "📝 **สิ่งที่ต้องทำต่อ:** เช็กความสม่ำเสมอของรูปทรงอาคารก่อน ถ้าผ่าน ให้คำนวณแรงใน Tab 4 ต่อได้เลย"
        },
        'ง': {
            'title': "ประเภท ง (SDC D) - ความเสี่ยงภัยแผ่นดินไหวสูง (เข้มงวดที่สุด)",
            'analysis': "❌ **ข้อจำกัดสูง:** ใช้วิธีแรงสถิตเทียบเท่าได้เฉพาะอาคารทั่วไปที่ 'สม่ำเสมอ' และ 'สูงไม่เกินเกณฑ์' เท่านั้น",
            'detailing': "🚨 **บังคับขั้นสูงสุด:** โครงสร้างต้องออกแบบให้มีความเหนียวสูง (Special Ductility)",
            'action': "📝 **สิ่งที่ต้องทำต่อ:** ต้องประเมินความไม่สม่ำเสมอ (Irregularity) อย่างละเอียด หากไม่ผ่าน บังคับส่งต่อไปวิธีพลศาสตร์ทันที!"
        }
    }

    # แสดงข้อสรุปภาพรวมตามผลคำนวณจริง
    if sdc == 'ก':
        st.success(f"✅ **อาคารนี้จัดอยู่ในประเภทการออกแบบสุดท้าย: '{sdc}'**")
        st.markdown(f"👉 {sdc_actions[sdc]['action']}")
    else:
        st.warning(f"⚠️ **อาคารนี้จัดอยู่ในประเภทการออกแบบสุดท้าย: '{sdc}'**")
        st.markdown(f"👉 **ทิศทางการออกแบบถัดไป:** {sdc_actions[sdc]['action']}")

    st.markdown("---")

    # 🗺️ ส่วนแผนผังเส้นทางการออกแบบระดับโปร (Engineered Roadmap)
    st.subheader("🗺️ แผนผังขั้นตอนการเลือกวิธีวิเคราะห์ (Seismic Analysis Decision Flowchart)")
    st.markdown("ผังแสดงเงื่อนไขบังคับตามมาตรฐาน **มยผ. 1301/1302** เพื่อเลือกระหว่างวิธีแรงสถิตเทียบเท่าหรือวิธีพลศาสตร์")
    
    # อัปเกรดความสวยงามของโครงสร้างต้นไม้ (ใช้ Subgraph แบ่งกลุ่มอย่างชัดเจน)
    roadmap_dot = """
    digraph G {
        graph [rankdir=TB, bgcolor="transparent", splines=true, nodesep=0.5, ranksep=0.4]
        node [fontname="Tahoma, Arial, sans-serif", shape=box, style="filled,rounded", color="#1e293b", fontcolor="#ffffff", fillcolor="#334155", fontsize=11, penwidth=1.5]
        edge [fontname="Tahoma, Arial, sans-serif", color="#64748b", fontsize=10, arrowhead=vee, arrowsize=0.8, penwidth=1.5]

        // Phase 1: การคัดแยกประเภท SDC
        subgraph cluster_phase1 {
            label="[ เฟส 1: ผลลัพธ์ประเภทการออกแบบ (SDC) ]";
            fontname="Tahoma, Arial, sans-serif"; fontsize=12; fontcolor="#0f172a"; style="dashed"; color="#cbd5e1"; bgcolor="#f8fafc";
            
            sdc_a [label="🔹 ประเภท ก\\n(เสี่ยงภัยต่ำมาก)", fillcolor="#10b981", color="#047857"]
            sdc_b [label="🔹 ประเภท ข\\n(เสี่ยงภัยต่ำ)", fillcolor="#f59e0b", color="#b45309"]
            sdc_c [label="🔹 ประเภท ค\\n(เสี่ยงภัยปานกลาง)", fillcolor="#f97316", color="#c2410c"]
            sdc_d [label="🔹 ประเภท ง\\n(เสี่ยงภัยสูง)", fillcolor="#ef4444", color="#b91c1c"]
        }

        // Phase 2: จุดคัดกรองทางวิศวกรรม
        subgraph cluster_phase2 {
            label="[ เฟส 2: ตรวจสอบเงื่อนไขรูปทรงและมิติอาคาร ]";
            fontname="Tahoma, Arial, sans-serif"; fontsize=12; fontcolor="#0f172a"; style="dashed"; color="#cbd5e1"; bgcolor="#f8fafc";
            
            bypass_b [label="ไม่ต้องตรวจสอบรูปทรง\\n(ผ่านเกณฑ์สถิตโดยอัตโนมัติ)", fillcolor="#94a3b8", fontcolor="#1e293b"]
            check_rules [label="⚖️ ตรวจสอบรูปทรงอาคาร\\n(Structural Regularity)\\nและข้อจำกัดความสูง", fillcolor="#3b82f6", color="#1d4ed8"]
        }

        // Phase 3: บทสรุปวิธีวิเคราะห์
        subgraph cluster_phase3 {
            label="[ เฟส 3: วิธีการวิเคราะห์ที่มาตรฐานอนุญาต ]";
            fontname="Tahoma, Arial, sans-serif"; fontsize=12; fontcolor="#0f172a"; style="dashed"; color="#cbd5e1"; bgcolor="#f8fafc";
            
            done_a [label="🟢 ใช้แรงบวกด้านข้างขั้นต่ำ 1%W\\n[ จบขั้นตอน - ไม่ต้องคิดแรงแผ่นดินไหว ]", fillcolor="#059669"]
            static_final [label="🟢 ลุยต่อวิธีแรงสถิตเทียบเท่า\\n(Equivalent Static Procedure)\\n[ เปิดไปคำนวณที่ Tab 4 ]", fillcolor="#10b981"]
            dynamic_final [label="🛑 บังคับใช้วิธีพลศาสตร์เท่านั้น\\n(Dynamic Analysis / Response Spectrum)\\n*ห้ามใช้วิธีสถิตในโปรแกรมนี้*", fillcolor="#dc2626"]
        }

        // การโยงเส้นความสัมพันธ์ (Workflow Connections)
        sdc_a -> done_a [weight=2]
        
        sdc_b -> bypass_b
        bypass_b -> static_final
        
        sdc_c -> check_rules
        sdc_d -> check_rules
        
        check_rules -> static_final [label="  โครงสร้างสม่ำเสมอ\\n  และสูงไม่เกินเกณฑ์ มยผ."]
        check_rules -> dynamic_final [label="  ❌ มีความไม่สม่ำเสมอ\\n  หรือ สูงเกินเกณฑ์กำหนด"]
    }
    """
    st.graphviz_chart(roadmap_dot)

    st.markdown("---")

    # 3. กล่องขยายแสดงวิธีคิดแบบละเอียดเดิม
    with st.expander("🔍 ดูที่มาและข้อบังคับแยกตามพารามิเตอร์อย่างละเอียด", expanded=False):
        st.markdown(f"**ปัจจัยร่วม:** ตัวคูณความสำคัญของอาคาร ($I_e$) = **{importance_factor}**")
        
        ie_data = {
            "ระดับความสำคัญ": ["อาคารทั่วไป", "อาคารความสำคัญสูง", "อาคารความสำคัญสูงมาก"],
            "ค่า Ie": ["1.00", "1.25", "1.50"],
            "ลักษณะอาคาร (ตัวอย่าง)": [
                "ที่พักอาศัย, อาคารพาณิชย์, สำนักงานทั่วไป",
                "โรงเรียน, สถานที่ชุมนุมคนจำนวนมาก, อาคารสาธารณะใหญ่",
                "โรงพยาบาล, สถานีดับเพลิง, ศูนย์ภัยพิบัติ"
            ]
        }
        st.table(pd.DataFrame(ie_data).set_index("ระดับความสำคัญ"))
        
        st.divider()
        
        col_sdc1, col_sdc2 = st.columns(2)
        with col_sdc1:
            st.markdown(f"### 1. พิจารณาจากความเร่งคาบสั้น ($S_{{DS}}$)")
            st.markdown(f"📉 ค่าที่ได้: $S_{{DS}} =$ **{SDS:.3f} g**")
            st.info(f"🎯 **ตกเกณฑ์: {sdc_actions[sdc_sds]['title']}**\n\n"
                    f"* **วิธีวิเคราะห์:** {sdc_actions[sdc_sds]['analysis']}\n"
                    f"* **การจัดรายละเอียด:** {sdc_actions[sdc_sds]['detailing']}\n"
                    f"* **แนวทางปฏิบัติ:** {sdc_actions[sdc_sds]['action']}")
            
        with col_sdc2:
            st.markdown(f"### 2. พิจารณาจากความเร่งคาบยาว ($S_{{D1}}$)")
            st.markdown(f"📉 ค่าที่ได้: $S_{{D1}} =$ **{SD1:.3f} g**")
            st.info(f"🎯 **ตกเกณฑ์: {sdc_actions[sdc_sd1]['title']}**\n\n"
                    f"* **วิธีวิเคราะห์:** {sdc_actions[sdc_sd1]['analysis']}\n"
                    f"* **การจัดรายละเอียด:** {sdc_actions[sdc_sd1]['detailing']}\n"
                    f"* **แนวทางปฏิบัติ:** {sdc_actions[sdc_sd1]['action']}")
            
        st.divider()
        st.subheader("💡 สรุปเกณฑ์ตัดสินตัวท้ายสุด")
        st.markdown(f"ตามมาตรฐานกำหนดให้เลือกประเภทที่ **เข้มงวดที่สุด (Max)** ระหว่างขา คาบสั้น (**{sdc_sds}**) และ คาบยาว (**{sdc_sd1}**)")
        st.error(f"🏆 ผลลัพธ์ที่ควบคุมการออกแบบ (Governing SDC) คือ: **ประเภท '{sdc}'** ซึ่งมีข้อบังคับดังระบุข้างต้น")
        
# ----------------- TAB 3 -----------------
with tab3:
    st.header("📈 กราฟความเร่งตอบสนองเชิงสเปกตรัม (Response Spectrum)")
    
    if sdc == 'ก':
        st.info("💡 อาคารประเภท 'ก' ไม่จำเป็นต้องใช้วิธีกราฟสเปกตรัมตอบสนองในการคำนวณแรงเฉือน (แต่แสดงกราฟไว้เพื่อเป็นข้อมูลอ้างอิง)")
        
    # สร้างข้อมูลแกน X ให้ละเอียดขึ้นและครอบคลุมคาบเวลาอาคาร
    T_values = np.linspace(0.0, max(4.0, Ta * 1.5, TS * 2), 500) 
    Sa_values = np.piecewise(
        T_values,
        [T_values < T0, (T0 <= T_values) & (T_values <= TS), T_values > TS],
        [lambda T: SDS * (0.4 + 0.6 * (T / T0)), SDS, lambda T: SD1 / T]
    )
    
    # คำนวณค่า Sa เฉพาะจุดที่คาบเวลาอาคาร Ta ตกอยู่
    if Ta < T0:
        Sa_Ta = SDS * (0.4 + 0.6 * (Ta / T0))
    elif Ta <= TS:
        Sa_Ta = SDS
    else:
        Sa_Ta = SD1 / Ta if Ta > 0 else 0

    # --- สร้างกราฟด้วย Plotly ---
    fig = go.Figure()
    
    # 1. เส้นกราฟ Response Spectrum หลัก
    fig.add_trace(go.Scatter(
        x=T_values, y=Sa_values, 
        mode='lines', name='Design Spectrum', 
        line=dict(color='#1f77b4', width=3)
    ))
    
    # 2. มาร์กจุด T0 และ TS
    if SDS > 0:
        fig.add_trace(go.Scatter(
            x=[T0, TS], y=[SDS, SDS], 
            mode='markers', name='จุดควบคุม (T0, TS)', 
            marker=dict(color='red', size=8, symbol='circle')
        ))
    
    # 3. มาร์กจุดคาบเวลาของอาคาร (Ta) ด้วยรูปดาว
    fig.add_trace(go.Scatter(
        x=[Ta], y=[Sa_Ta], 
        mode='markers+text', name='จุดพิกัดอาคาร (Ta)', 
        text=[f'Ta = {Ta:.2f} s<br>Sa = {Sa_Ta:.3f} g'], 
        textposition="top right",
        marker=dict(color='#ff7f0e', size=14, symbol='star', line=dict(width=2, color='DarkSlateGrey'))
    ))

    # 4. ปรับแต่ง Layout ของกราฟให้ดูสวยงาม
    fig.update_layout(
        title="<b>กราฟความเร่งสเปกตรัมตอบสนองสำหรับการออกแบบ (Design Response Spectrum)</b>",
        xaxis_title="<b>คาบเวลาโครงสร้าง, T (วินาที)</b>",
        yaxis_title="<b>ความเร่งตอบสนองเชิงสเปกตรัม, Sa (g)</b>",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(
            yanchor="top", y=0.99, 
            xanchor="right", x=0.99,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor="Black", borderwidth=1
        ),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray', zeroline=True, zerolinecolor='Black'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray', zeroline=True, zerolinecolor='Black', rangemode='tozero')
    )
    
    # แสดงกราฟใน Streamlit
    st.plotly_chart(fig, use_container_width=True)


# ----------------- TAB 4 -----------------
with tab4:
    st.header("🏢 วิธีแรงสถิตเทียบเท่า (Equivalent Static Procedure)")
    st.markdown("ตามมาตรฐาน **มยผ. 1301/1302** วิธีนี้จะแปลงแรงแผ่นดินไหวให้เป็นแรงผลักด้านข้างเสมือนกระทำที่จุดศูนย์กลางมวลของแต่ละชั้น")

    # สมมติค่า R (ตัวคูณการลดแรงเนื่องจากความเหนียว) หากยังไม่มีในระบบ ให้ผู้ใช้เลือก
    st.subheader("⚡ สเต็ปที่ 1: กำหนดค่าพารามิเตอร์และคำนวณค่า $C_s$")
    
    col_param1, col_param2 = st.columns(2)
    with col_param1:
        # ให้วิศวกรเลือกประเภทโครงสร้างเพื่อหาค่า R
        r_options = {
            "โครงนำแรงดัด คสล. ความเหนียวสูง (Special Moment Frame) [R = 8.0]": 8.0,
            "โครงนำแรงดัด คสล. ความเหนียวปานกลาง (Intermediate Moment Frame) [R = 5.0]": 5.0,
            "โครงนำแรงดัด คสล. ความเหนียวธรรมดา (Ordinary Moment Frame) [R = 3.0]": 3.0,
            "กำแพงรับแรงเฉือน คสล. (Shear Wall) [R = 5.0]": 5.0
        }
        selected_r = st.selectbox("🔷 เลือกประเภทระบบโครงสร้างต้านทานแรงด้านข้าง (ค่า R):", list(r_options.keys()))
        R = r_options[selected_r]

    # --- คำนวณสัมประสิทธิ์ผลตอบสนองแผ่นดินไหว (Cs) ---
    # สูตร: Cs = SDS / (R / Ie)
    Ie = importance_factor # ดึงค่าความสำคัญมาจากโค้ดเดิมของคุณ
    
    Cs_compute = SDS / (R / Ie)
    
    # ขีดจำกัดบน (Upper Limit): Cs_max = SD1 / (T * (R / Ie))
    if Ta > 0:
        Cs_max = SD1 / (Ta * (R / Ie))
    else:
        Cs_max = Cs_compute
        
    # ขีดจำกัดล่าง (Lower Limit): Cs_min = 0.01 (หรือตามเกณฑ์พิเศษอื่นๆ)
    Cs_min = 0.01
    
    # สรุปค่า Cs ที่ใช้จริง
    Cs_governing = max(Cs_min, min(Cs_compute, Cs_max))

    with col_param2:
        # แสดงผลลัพธ์พารามิเตอร์หลักแบบ Metric
        st.metric(label="สัมประสิทธิ์แรงเฉือนที่ฐานที่ควบคุม ($C_s$)", value=f"{Cs_governing:.4f}")
        st.caption(f"สูตรคำนวณ: $V = C_s \\times W$ (แรงเฉือนที่ฐาน = $C_s$ คูณน้ำหนักอาคารทั้งหมด)")

    # แสดงรายละเอียดสูตรให้เข้าใจง่าย (เปิด-ปิดดูได้)
    with st.expander("🔍 ดูรายละเอียดการตรวจสอบขีดจำกัดของค่า $C_s$"):
        st.latex(r"C_s = \frac{S_{DS}}{R/I_e}")
        st.markdown(f"- ค่าคำนวณพื้นฐาน: $C_s = {SDS:.3f} / ({R} / {Ie}) = {Cs_compute:.4f}$")
        st.markdown(f"- ค่าขีดจำกัดบน ($C_{{s,max}}$): {f'{Cs_max:.4f}' if Ta > 0 else 'N/A'} *(ควบคุมเมื่ออาคารสูงหรือคาบยาว)*")
        st.markdown(f"- ค่าขีดจำกัดล่าง ($C_{{s,min}}$): {Cs_min:.4f} *(ควบคุมเมื่ออาคารเตี้ยหรือแรงแผ่นดินไหวต่ำมาก)*")
        st.info(f"🎯 **สรุปค่าที่เลือกใช้:** $C_s = {Cs_governing:.4f}$")

    st.divider()

    # สเต็ปที่ 2: ตารางกรอกน้ำหนักความสูงแต่ละชั้น
    st.subheader("📊 สเต็ปที่ 2: กรอกข้อมูลน้ำหนักและความสูงของแต่ละชั้น (Story Data)")
    st.markdown("โปรดแก้ตัวเลขในตารางด้านล่างนี้ให้ตรงกับแบบอาคารของคุณ (สามารถคลิกดับเบิ้ลคลิกแก้ไข หรือกดเพิ่มแถวได้ที่มุมตาราง)")

    # สร้างข้อมูลเริ่มต้นสำหรับอาคาร 4 ชั้น (Default Data)
    default_stories = pd.DataFrame([
        {"ชื่อชั้น (Floor)": "ชั้น 4 (ดาดฟ้า)", "ความสูงสะสมจากฐาน, hx (ม.)": 14.0, "น้ำหนักรวมของชั้น, wx (ตัน)": 150.0},
        {"ชื่อชั้น (Floor)": "ชั้น 3", "ความสูงสะสมจากฐาน, hx (ม.)": 10.5, "น้ำหนักรวมของชั้น, wx (ตัน)": 200.0},
        {"ชื่อชั้น (Floor)": "ชั้น 2", "ความสูงสะสมจากฐาน, hx (ม.)": 7.0, "น้ำหนักรวมของชั้น, wx (ตัน)": 200.0},
        {"ชื่อชั้น (Floor)": "ชั้น 1", "ความสูงสะสมจากฐาน, hx (ม.)": 3.5, "น้ำหนักรวมของชั้น, wx (ตัน)": 220.0},
    ])

    # ใช้ st.data_editor ให้ผู้ใช้ปรับแต่งตารางได้สดๆ
    edited_df = st.data_editor(
        default_stories, 
        num_rows="dynamic", 
        use_container_width=True,
        key="story_editor"
    )

    # --- เริ่มกระบวนการคำนวณกระจายแรง (Vertical Distribution) ---
    if edited_df is not None and not edited_df.empty:
        try:
            # ดึงข้อมูลจากตารางมาคำนวณ
            hx = edited_df.iloc[:, 1].astype(float).values
            wx = edited_df.iloc[:, 2].astype(float).values
            floor_names = edited_df.iloc[:, 0].astype(str).values
            
            # 1. คำนวณน้ำหนักรวมอาคาร (W) และแรงเฉือนที่ฐานรวม (V)
            total_W = np.sum(wx)
            total_V = Cs_governing * total_W
            
            # 2. หาค่าตัวแปร k (Exponent) ตามคาบเวลา Ta
            # Ta <= 0.5 s -> k = 1.0 || Ta >= 2.5 s -> k = 2.0 || ระหว่างนั้นให้ Interpolate
            if Ta <= 0.5:
                k_exp = 1.0
            elif Ta >= 2.5:
                k_exp = 2.0
            else:
                k_exp = 1.0 + (Ta - 0.5) * (2.0 - 1.0) / (2.5 - 0.5)

            # 3. คำนวณพจน์ wx * (hx^k) ของแต่ละชั้น
            w_hx_k = wx * (hx ** k_exp)
            sum_w_hx_k = np.sum(w_hx_k)

            if sum_w_hx_k > 0:
                # 4. คำนวณตัวคูณกระจายแรง Cvx และ แรงผลัก Fx
                cvx = w_hx_k / sum_w_hx_k
                Fx = cvx * total_V
                
                # 5. คำนวณแรงเฉือนประจำชั้น (Story Shear, Vx) สะสมจากบนลงล่าง
                # (แรงเฉือนชั้นล่างสุดจะเท่ากับ Base Shear V เสมอ)
                Vx = np.cumsum(Fx) # เนื่องจากเรียงลำดับชั้นจากบนลงล่างอยู่แล้ว
                
                # ประกอบข้อมูลกลับเข้าตารางสรุปผล
                result_df = edited_df.copy()
                result_df["ตัวคูณกระจายแรง (Cvx)"] = cvx
                result_df["แรงผลักประจำชั้น, Fx (ตัน)"] = Fx
                result_df["แรงเฉือนสะสมในชั้น, Vx (ตัน)"] = Vx
                
                st.divider()
                
                # สเต็ปที่ 3: สรุปผลลัพธ์
                st.subheader("🏆 สเต็ปที่ 3: สรุปผลการกระจายแรงแผ่นดินไหวแนวตั้ง")
                
                # โชว์ยอดสรุปแบบกล่องทอง
                col_sum1, col_sum2, col_sum3 = st.columns(3)
                with col_sum1:
                    st.inner_value = st.metric("น้ำหนักอาคารรวม ($W$)", f"{total_W:,.2f} ตน")
                with col_sum2:
                    st.metric("แรงเฉือนที่ฐานรวม ($V$)", f"{total_V:,.2f} ตน")
                with col_sum3:
                    st.metric("ค่าดัชนีการกระจายแรง ($k$)", f"{k_exp:.3f}")

                # แสดงตารางผลลัพธ์สุดท้าย
                st.markdown("**📋 ตารางรายการคำนวณแรงแต่ละชั้น (วิศวกรนำค่า Fx ไปป้อนเข้าโปรแกรมโครงสร้างได้ทันที):**")
                st.dataframe(
                    result_df.style.format({
                        "ความสูงสะสมจากฐาน, hx (ม.)": "{:.2f}",
                        "น้ำหนักรวมของชั้น, wx (ตัน)": "{:,.2f}",
                        "ตัวคูณกระจายแรง (Cvx)": "{:.4f}",
                        "แรงผลักประจำชั้น, Fx (ตัน)": "{:,.2f}",
                        "แรงเฉือนสะสมในชั้น, Vx (ตัน)": "{:,.2f}"
                    }),
                    use_container_width=True
                )
                
                # วาดกราฟแท่งแนวนอนเพื่อสร้างความเข้าใจเชิงภาพ (Visual Understanding)
                st.markdown("**📊 กราฟเปรียบเทียบแรงผลัก ($F_x$) และ แรงเฉือนสะสม ($V_x$) ในแต่ละชั้น**")
                
                import plotly.graph_objects as go
                fig_bar = go.Figure()
                
                # แท่งแรงผลักประจำชั้น Fx
                fig_bar.add_trace(go.Bar(
                    y=floor_names, x=Fx,
                    name='แรงผลักประจำชั้น (Fx) - ผลักที่จุด CG ชั้น',
                    orientation='h', marker=dict(color='#3b82f6')
                ))
                
                # แท่งแรงเฉือนสะสม Vx
                fig_bar.add_trace(go.Bar(
                    y=floor_names, x=Vx,
                    name='แรงเฉือนสะสมในชั้น (Vx) - สะสมลงสู่ฐาน',
                    orientation='h', marker=dict(color='#10b981'),
                    opacity=0.6
                ))
                
                fig_bar.update_layout(
                    barmode='group',
                    template='plotly_white',
                    xaxis_title="แรงกระทำ (หน่วย: ตัน)",
                    yaxis=dict(autorange="reverse"), # บังคับให้ชั้นดาดฟ้าอยู่บนสุด
                    margin=dict(l=20, r=20, t=20, b=20),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                
        except Exception as e:
            st.error(f"⚠️ เกิดข้อผิดพลาดในการคำนวณ: โปรดตรวจสอบว่าข้อมูลในตารางกรอกครบถ้วนและเป็นตัวเลข")
