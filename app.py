import streamlit as st
import pandas as pd
import numpy as np
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.interpolate import interp1d

# ==========================================
# 1. การตั้งค่าหน้าจอและ UI
# ==========================================
st.set_page_config(page_title="DPT Seismic Calculator (Master)", page_icon="🏢", layout="wide")
st.title("🏢 โปรแกรมคำนวณแรงแผ่นดินไหว (มยผ. 1301/1302-61)")
st.markdown("**เวอร์ชันสมบูรณ์: รองรับสเปกตรัมแอ่งกรุงเทพฯ และฐานข้อมูลพื้นที่เสี่ยงภัยสูงสุด**")

# ==========================================
# 2. ฐานข้อมูล (Ultra-Expanded Dataset)
# ==========================================
csv_data = """Province,District,Ss,S1
เชียงราย,เมืองเชียงราย,1.139,0.316
เชียงราย,แม่สาย,1.332,0.370
เชียงราย,เชียงแสน,1.150,0.320
เชียงราย,แม่จัน,1.250,0.350
เชียงราย,พาน,0.950,0.270
เชียงราย,เทิง,0.880,0.250
เชียงราย,แม่ฟ้าหลวง,1.300,0.360
เชียงใหม่,เมืองเชียงใหม่,0.852,0.244
เชียงใหม่,ฝาง,1.218,0.334
เชียงใหม่,แม่ริม,0.860,0.250
เชียงใหม่,เชียงดาว,1.050,0.290
เชียงใหม่,แม่อาย,1.200,0.330
แม่ฮ่องสอน,เมืองแม่ฮ่องสอน,0.950,0.260
แม่ฮ่องสอน,ปาย,1.019,0.269
แม่ฮ่องสอน,ปางมะผ้า,1.000,0.275
ตาก,เมืองตาก,0.550,0.180
ตาก,แม่สอด,0.850,0.250
ตาก,อุ้มผาง,0.650,0.200
กาญจนบุรี,เมืองกาญจนบุรี,0.428,0.138
กาญจนบุรี,ทองผาภูมิ,0.620,0.190
กาญจนบุรี,สังขละบุรี,0.750,0.220
กาญจนบุรี,ศรีสวัสดิ์,0.500,0.150
พะเยา,เมืองพะเยา,0.820,0.240
พะเยา,เชียงคำ,0.900,0.260
ลำปาง,เมืองลำปาง,0.650,0.195
ลำพูน,เมืองลำพูน,0.780,0.230
แพร่,เมืองแพร่,0.720,0.210
น่าน,เมืองน่าน,0.750,0.220
น่าน,ปัว,0.850,0.250
ภูเก็ต,เมืองภูเก็ต,0.188,0.068
พังงา,เมืองพังงา,0.250,0.085
ระนอง,เมืองระนอง,0.350,0.110
สงขลา,เมืองสงขลา,0.085,0.038
กรุงเทพมหานคร,ทุกเขต (ดินเหนียวอ่อน),0.0,0.0
นนทบุรี,ทุกอำเภอ (ดินเหนียวอ่อน),0.0,0.0
ปทุมธานี,ทุกอำเภอ (ดินเหนียวอ่อน),0.0,0.0
สมุทรปราการ,ทุกอำเภอ (ดินเหนียวอ่อน),0.0,0.0
สมุทรสาคร,ทุกอำเภอ (ดินเหนียวอ่อน),0.0,0.0
นครปฐม,เมืองนครปฐม (ดินเหนียวอ่อน),0.0,0.0
ฉะเชิงเทรา,เมืองฉะเชิงเทรา (ดินเหนียวอ่อน),0.0,0.0"""

@st.cache_data
def load_data():
    df = pd.read_csv(io.StringIO(csv_data))
    return df.sort_values(by=['Province', 'District']).reset_index(drop=True)

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
    is_essential = (Ie >= 1.5)
    sdc_sds = 'ก' if SDS < 0.167 else ('ค' if is_essential and SDS < 0.33 else ('ข' if SDS < 0.33 else ('ง' if is_essential else ('ค' if SDS < 0.50 else 'ง'))))
    sdc_sd1 = 'ก' if SD1 < 0.067 else ('ค' if is_essential and SD1 < 0.133 else ('ข' if SD1 < 0.133 else ('ง' if is_essential else ('ค' if SD1 < 0.20 else 'ง'))))
    sdc_order = {'ก': 1, 'ข': 2, 'ค': 3, 'ง': 4}
    sdc_final = next(cat for cat, val in sdc_order.items() if val == max(sdc_order[sdc_sds], sdc_order[sdc_sd1]))
    return sdc_final, sdc_sds, sdc_sd1

def compute_spectrum_sa(T: float, SDS: float, SD1: float, T0: float, TS: float, TL: float = 4.0) -> float:
    if T0 > 0 and T < T0:
        return SDS * (0.4 + 0.6 * (T / T0))
    elif T <= TS:
        return SDS
    elif T <= TL:
        return SD1 / T if T > 0 else SDS
    else:
        return (SD1 * TL) / (T ** 2) if T > 0 else SDS

# ==========================================
# 4. ส่วนรับข้อมูลผู้ใช้งาน (Sidebar Inputs)
# ==========================================
with st.sidebar:
    st.header("⚙️ ข้อมูลการออกแบบ")

    st.subheader("1. ข้อมูลสถานที่ตั้ง")
    input_method = st.radio("รูปแบบการนำเข้าพารามิเตอร์", ["ดึงจากฐานข้อมูล", "กรอกค่า Ss, S1 ด้วยตนเอง"])

    is_bangkok_basin = False

    if input_method == "ดึงจากฐานข้อมูล":
        province_list = df_location['Province'].unique()
        selected_province = st.selectbox("เลือกจังหวัด", province_list, index=list(province_list).index("กรุงเทพมหานคร") if "กรุงเทพมหานคร" in province_list else 0)
        district_list = df_location[df_location['Province'] == selected_province]['District']
        selected_district = st.selectbox("เลือกอำเภอ", district_list)
        
        location_row = df_location[(df_location['Province'] == selected_province) & (df_location['District'] == selected_district)].iloc[0]
        
        if "ดินเหนียวอ่อน" in str(location_row['District']):
            is_bangkok_basin = True
            Ss, S1 = 0.0, 0.0
        else:
            Ss = float(location_row['Ss'])
            S1 = float(location_row['S1'])
    else:
        selected_province, selected_district = "กำหนดเอง", "กำหนดเอง"
        is_bb_manual = st.checkbox("📐 เป็นพื้นที่แอ่งดินอ่อนกรุงเทพฯ")
        if is_bb_manual:
            is_bangkok_basin = True
            Ss, S1 = 0.0, 0.0
        else:
            Ss = st.number_input("ค่า Ss (g)", min_value=0.000, value=0.500, step=0.010, format="%.3f")
            S1 = st.number_input("ค่า S1 (g)", min_value=0.000, value=0.200, step=0.010, format="%.3f")

    if not is_bangkok_basin:
        site_class = st.selectbox("ประเภทชั้นดิน", ['A', 'B', 'C', 'D', 'E', 'F'], index=3)
    else:
        st.info("ℹ️ พื้นที่แอ่งกรุงเทพฯ: ใช้สเปกตรัมเฉพาะของดินเหนียวอ่อนหนาพิเศษ")
        site_class = "E"

    st.subheader("2. ข้อมูลโครงสร้าง")
    importance_factor = st.selectbox("ตัวคูณความสำคัญ (Ie)", [1.0, 1.25, 1.5], index=0)
    sys_type = st.selectbox("ระบบโครงสร้าง (หา Ta)", ["โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก", "โครงต้านทานแรงดัดเหล็กกล้า", "โครงสร้างอื่นๆ"])

    st.subheader("3. มิติอาคาร")
    building_height = st.number_input("ความสูงอาคาร hn (เมตร)", min_value=1.0, value=10.0, step=1.0)

# ==========================================
# 5. ประมวลผลและตรวจสอบเงื่อนไข
# ==========================================
if site_class == 'F' and not is_bangkok_basin:
    st.error("🛑 ชั้นดิน F ต้องเจาะสำรวจประเมินเฉพาะพื้นที่ (Site-Specific) เท่านั้น ไม่สามารถใช้ค่ามาตรฐานได้")
    st.stop()

if is_bangkok_basin:
    # สเปกตรัมแอ่งกรุงเทพฯ (มยผ. 1302)
    SDS, SD1 = 0.220, 0.285
    T0, TS, TL = 0.26, 1.30, 4.0
    Fa, Fv = 1.0, 1.0
    SMS, SM1 = SDS, SD1
else:
    # สเปกตรัมมาตรฐาน
    Fa, Fv = get_site_coefficients(site_class, Ss, S1)
    SMS, SM1 = Fa * Ss, Fv * S1
    SDS, SD1 = (2.0 / 3.0) * SMS, (2.0 / 3.0) * SM1
    TS = SD1 / SDS if SDS > 0 else 0.0
    T0 = 0.2 * TS
    TL = 4.0

Ta = calculate_approx_period(sys_type, building_height)
sdc, sdc_sds, sdc_sd1 = evaluate_sdc_detailed(SDS, SD1, importance_factor)

# ==========================================
# 6. การแสดงผล (Tabs)
# ==========================================
st.markdown("---")
tab1, tab2, tab3, tab4 = st.tabs(["📋 พารามิเตอร์ & SDC", "📈 กราฟสเปกตรัม", "🏢 คำนวณแรงประจำชั้น", "📏 ตรวจสอบการโยกตัว (Drift)"])

# ─────────────────────────── TAB 1 ───────────────────────────
with tab1:
    st.header("📋 รายการคำนวณพารามิเตอร์ และประเภทการออกแบบ (SDC)")
    
    if is_bangkok_basin:
        st.success("🔔 **ระบบประยุกต์ใช้สเปกตรัมการออกแบบเฉพาะสำหรับพื้นที่แอ่งดินเหนียวอ่อนกรุงเทพฯ และปริมณฑล**")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Short Period Design (SDS)", f"{SDS:.3f} g")
    col2.metric("1-Sec Period Design (SD1)", f"{SD1:.3f} g")
    col3.metric("ระดับความเสี่ยงภัย (SDC)", f"ประเภท {sdc}")
    
    st.divider()
    st.warning(f"**อาคารนี้จัดอยู่ในประเภทการออกแบบต้านทานแผ่นดินไหว: '{sdc}'**")
    if sdc == 'ก': st.write("✅ ไม่ต้องคิดแรงแผ่นดินไหวเต็มรูปแบบ ใช้อย่างน้อย 1%W")
    elif sdc == 'ข': st.write("✅ ใช้วิธีแรงสถิตเทียบเท่าได้ โครงสร้างความเหนียวจำกัด (OMF)")
    elif sdc == 'ค': st.write("⚠️ ใช้วิธีแรงสถิตได้ถ้าอาคารสม่ำเสมอ โครงสร้างความเหนียวปานกลาง (IMF)")
    else: st.write("🚨 ใช้วิธีแรงสถิตได้ยาก บังคับโครงสร้างความเหนียวสูง (SMF)")

# ─────────────────────────── TAB 2 ───────────────────────────
with tab2:
    st.header(f"📈 กราฟความเร่งสเปกตรัมตอบสนอง {'(แอ่งกรุงเทพฯ)' if is_bangkok_basin else '(มาตรฐานทั่วไป)'}")
    
    T_values = np.linspace(0.01, max(5.0, Ta * 1.5, TS * 2), 500)
    Sa_values = [compute_spectrum_sa(t, SDS, SD1, T0, TS, TL) for t in T_values]
    Sa_Ta = compute_spectrum_sa(Ta, SDS, SD1, T0, TS, TL)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=T_values, y=Sa_values, mode='lines', name='Design Spectrum (Sa)', line=dict(color='firebrick', width=3)))
    fig.add_trace(go.Scatter(x=[Ta], y=[Sa_Ta], mode='markers+text', name='จุดพิกัดอาคาร (Ta)', text=[f'Ta = {Ta:.2f} s<br>Sa = {Sa_Ta:.3f} g'], textposition="top right", marker=dict(color='#ff7f0e', size=14, symbol='star', line=dict(width=2, color='Black'))))
    fig.add_vline(x=T0, line_dash="dash", line_color="green", annotation_text=f" T0={T0:.2f}s")
    fig.add_vline(x=TS, line_dash="dash", line_color="blue", annotation_text=f" TS={TS:.2f}s")
    
    fig.update_layout(xaxis_title="คาบเวลาการสั่นธรรมชาติอาคาร T (วินาที)", yaxis_title="ความเร่งตอบสนองการออกแบบ Sa (g)", template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# ─────────────────────────── TAB 3 ───────────────────────────
with tab3:
    st.header("🏢 วิธีแรงสถิตเทียบเท่า (Equivalent Static Procedure)")

    structural_systems = {
        "โครงนำแรงดัด คสล. ความเหนียวสูง (SMF)": {"R": 8.0, "Omega": 3.0, "Cd": 5.5},
        "โครงนำแรงดัด คสล. ความเหนียวปานกลาง (IMF)": {"R": 5.0, "Omega": 3.0, "Cd": 4.5},
        "โครงนำแรงดัด คสล. ความเหนียวธรรมดา (OMF)": {"R": 3.0, "Omega": 3.0, "Cd": 2.5},
        "กำแพงรับแรงเฉือน คสล. ความเหนียวสูง (Special SW)": {"R": 6.0, "Omega": 2.5, "Cd": 5.0}
    }
    selected_system = st.selectbox("🔷 เลือกระบบโครงสร้าง (Seismic Resisting System):", list(structural_systems.keys()))
    R_sys, Omega0, Cd = structural_systems[selected_system]["R"], structural_systems[selected_system]["Omega"], structural_systems[selected_system]["Cd"]

    Cs_basic = SDS / (R_sys / importance_factor) if R_sys > 0 else 0.0
    Cs_max = SD1 / (Ta * (R_sys / importance_factor)) if Ta > 0 else Cs_basic
    Cs_min = max(0.011 * SDS * importance_factor, 0.01) if not is_bangkok_basin else 0.01
    Cs_gov = max(Cs_min, min(Cs_basic, Cs_max))

    st.markdown(f"**สัมประสิทธิ์แรงเฉือนที่ฐาน (Cs):** :blue[{Cs_gov:.4f}] | **R:** {R_sys} | **Cd:** {Cd}")
    st.divider()

    st.markdown("##### 📝 กรอกข้อมูลมิติและน้ำหนักอาคาร (เรียงจากชั้นบนสุดลงล่างสุด)")
    default_stories = pd.DataFrame([
        {"ชื่อชั้น": "ชั้น 4 (ดาดฟ้า)", "ความสูงสะสม hx (ม.)": 14.0, "น้ำหนักรวม wx (ตัน)": 150.0},
        {"ชื่อชั้น": "ชั้น 3", "ความสูงสะสม hx (ม.)": 10.5, "น้ำหนักรวม wx (ตัน)": 200.0},
        {"ชื่อชั้น": "ชั้น 2", "ความสูงสะสม hx (ม.)": 7.0, "น้ำหนักรวม wx (ตัน)": 200.0},
        {"ชื่อชั้น": "ชั้น 1", "ความสูงสะสม hx (ม.)": 3.5, "น้ำหนักรวม wx (ตัน)": 220.0},
    ])

    edited_df = st.data_editor(default_stories, num_rows="dynamic", use_container_width=True)
    clean_df = edited_df.dropna(subset=["ความสูงสะสม hx (ม.)", "น้ำหนักรวม wx (ตัน)"]).copy()

    if not clean_df.empty:
        names, hx, wx = clean_df["ชื่อชั้น"].values, clean_df["ความสูงสะสม hx (ม.)"].astype(float).values, clean_df["น้ำหนักรวม wx (ตัน)"].astype(float).values
        total_W = float(np.sum(wx))
        total_V = float(Cs_gov * total_W)
        
        k_exp = 1.0 if Ta <= 0.5 else (2.0 if Ta >= 2.5 else 1.0 + (Ta - 0.5) / 2.0)
        cvx = (wx * (hx ** k_exp)) / np.sum(wx * (hx ** k_exp))
        Fx = cvx * total_V
        Vx = np.cumsum(Fx) # แรงเฉือนสะสมจากบนลงล่าง

        res_force = pd.DataFrame({"ชื่อชั้น": names, "hx (ม.)": hx, "wx (ตัน)": wx, "Fx (ตัน)": Fx, "Vx (ตัน)": Vx})
        st.markdown(f"### 🏆 แรงเฉือนที่ฐานอาคาร (Base Shear, V) = {total_V:,.2f} ตัน")
        st.dataframe(res_force.style.format({"hx (ม.)": "{:.2f}", "wx (ตัน)": "{:,.2f}", "Fx (ตัน)": "{:,.2f}", "Vx (ตัน)": "{:,.2f}"}), use_container_width=True)

        fig_force = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=("แรงผลักแผ่นดินไหว (Fx)", "แรงเฉือนสะสม (Vx)"))
        fig_force.add_trace(go.Bar(y=names, x=Fx, orientation='h', marker_color='#3b82f6'), row=1, col=1)
        fig_force.add_trace(go.Bar(y=names, x=Vx, orientation='h', marker_color='#10b981'), row=1, col=2)
        fig_force.update_yaxes(autorange="reversed")
        st.plotly_chart(fig_force, use_container_width=True)

# ─────────────────────────── TAB 4 ───────────────────────────
with tab4:
    st.header("📏 ตรวจสอบการโยกตัว (Story Drift Safety Check)")
    drift_limit = 0.010 if importance_factor >= 1.5 else (0.015 if importance_factor >= 1.25 else 0.020)
    
    st.info(f"🎯 **เกณฑ์ที่ใช้ประเมิน:** โครงสร้างยอมให้เยื้องตัวได้สูงสุด **{drift_limit*100}%** ของความสูงชั้นสุทธิ")

    if not clean_df.empty:
        drift_df = pd.DataFrame({"ชื่อชั้น": names, "ความสูงสะสม hx (ม.)": hx, "ระยะโยกจากโปรแกรม δe (ซม.)": np.linspace(2.0, 0.4, len(hx))})
        edited_drift = st.data_editor(drift_df, use_container_width=True, column_config={"ชื่อชั้น": st.column_config.TextColumn(disabled=True), "ความสูงสะสม hx (ม.)": st.column_config.NumberColumn(disabled=True)})
        
        delta_e = edited_drift["ระยะโยกจากโปรแกรม δe (ซม.)"].values.astype(float)
        delta_x = (Cd * delta_e) / importance_factor
        
        story_h, drift_ratio, status = np.zeros(len(hx)), np.zeros(len(hx)), []
        
        for i in range(len(hx)):
            h_net = (hx[i] - hx[i + 1]) if i < len(hx) - 1 else hx[i]
            delta_diff = (delta_x[i] - delta_x[i + 1]) if i < len(hx) - 1 else delta_x[i]
            
            story_h[i] = max(h_net, 0.001)
            drift_ratio[i] = delta_diff / (story_h[i] * 100.0)
            status.append("✅ PASS" if drift_ratio[i] <= drift_limit else "❌ FAIL")

        res_drift = edited_drift.copy()
        res_drift["ความสูงชั้นสุทธิ (ม.)"] = story_h
        res_drift["ระยะโยกจริง δx (ซม.)"] = delta_x
        res_drift["Drift Ratio (Δ/h)"] = drift_ratio
        res_drift["ผลการประเมิน"] = status

        st.dataframe(res_drift.style.map(lambda v: 'background-color: #dcfce7; color: #166534;' if 'PASS' in str(v) else ('background-color: #fee2e2; color: #991b1b;' if 'FAIL' in str(v) else ''), subset=['ผลการประเมิน']).format({"ความสูงชั้นสุทธิ (ม.)": "{:.2f}", "ระยะโยกจริง δx (ซม.)": "{:.2f}", "Drift Ratio (Δ/h)": "{:.4f}"}), use_container_width=True)
