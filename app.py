"""
app.py — โปรแกรมคำนวณแรงแผ่นดินไหว มยผ. 1301/1302-61
Streamlit Application — ปรับปรุงโครงสร้างและการคำนวณครบถ้วน
"""

import streamlit as st
import pandas as pd
import numpy as np

from data_loader import (load_data, STRUCTURAL_SYSTEMS, get_drift_limit,
                         SOFT_CLAY_PROVINCES, SOFT_CLAY_SPECTRUM, get_soft_clay_sa)
import calculations as calc
import plots

# ═══════════════════════════════════════════════════════════════════════════════
# ตั้งค่าหน้าจอ
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="DPT Seismic Calculator — มยผ. 1301/1302-61",
    page_icon="🏢",
    layout="wide"
)
st.title("🏢 โปรแกรมคำนวณแรงแผ่นดินไหว (มยผ. 1301/1302-61)")
st.caption(
    "คำนวณแรงเฉือนที่ฐาน · ประเมิน SDC · ตรวจสอบ Story Drift · P-Delta Stability"
    " — อ้างอิงมาตรฐาน มยผ. 1301/1302-61 (ฉบับปรับปรุง พ.ศ. 2561)"
)
with st.expander("⚠️ ข้อจำกัดความรับผิดชอบ (Disclaimer) — โปรดอ่านก่อนใช้งาน", expanded=False):
    st.markdown(
        """
- โปรแกรมนี้เป็น **เครื่องมือช่วยคำนวณเพื่อการศึกษาและตรวจทานเบื้องต้น** ไม่ใช่สิ่งทดแทนการตรวจสอบโดยวิศวกรผู้ได้รับใบอนุญาต
- ค่า **Ss, S1 รายอำเภอ** ในฐานข้อมูลเป็นค่าตัวอย่างประกอบการใช้งาน — ก่อนออกแบบจริง **ต้องตรวจสอบกับตารางที่ 1.4-1 ใน มยผ. 1301/1302-61 ฉบับทางการ** ของกรมโยธาธิการและผังเมือง (DPT) ทุกครั้ง
- สเปกตรัมพื้นที่ดินเหนียวอ่อน (กทม. และปริมณฑล) ในโปรแกรมใช้รูปแบบอย่างง่าย — มาตรฐานฉบับจริง**แบ่งพื้นที่แอ่งกรุงเทพฯ เป็นหลายโซน** (Zone 1–10) ซึ่งแต่ละโซนมีค่าสเปกตรัมเฉพาะ ต้องเทียบกับตารางในมาตรฐานโดยตรง
- ผลการคำนวณทั้งหมดต้องได้รับการตรวจทานและลงนามรับรองโดย**สามัญวิศวกรโยธาขึ้นไป**ตามกฎหมายวิชาชีพวิศวกรรม
        """
    )

df_location = load_data()

# ═══════════════════════════════════════════════════════════════════════════════
# Sidebar — รับข้อมูลผู้ใช้งาน
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ ข้อมูลการออกแบบ")

    # ── 1. สถานที่ตั้ง / ค่า Ss, S1 ──────────────────────────────────────────
    st.subheader("1. พารามิเตอร์ภัยแผ่นดินไหวพื้นที่")
    input_method = st.radio(
        "รูปแบบนำเข้าพารามิเตอร์",
        ["ดึงจากฐานข้อมูล มยผ.", "กรอกค่า Ss, S1 ด้วยตนเอง"]
    )

    if input_method == "ดึงจากฐานข้อมูล มยผ.":
        province_list    = df_location['Province'].unique()
        selected_province = st.selectbox("จังหวัด", province_list)
        district_list    = df_location[df_location['Province'] == selected_province]['District']
        selected_district = st.selectbox("อำเภอ", district_list)
    else:
        selected_province = selected_district = "กำหนดเอง"
        manual_Ss = st.number_input("Ss (g)", 0.000, 3.000, 0.500, 0.010, "%.3f")
        manual_S1 = st.number_input("S1 (g)", 0.000, 2.000, 0.200, 0.010, "%.3f")

    site_class = st.selectbox(
        "ประเภทชั้นดิน", ['A', 'B', 'C', 'D', 'E', 'F'], index=3,
        help="A=หินแข็ง  B=หินแข็งปานกลาง  C=ดินแข็ง  D=ดินแข็งปานกลาง  E=ดินอ่อน  F=ต้องศึกษาเฉพาะพื้นที่"
    )

    # ── 2. ข้อมูลอาคาร ────────────────────────────────────────────────────────
    st.subheader("2. ข้อมูลอาคารและโครงสร้าง")
    importance_factor = st.selectbox(
        "ตัวคูณความสำคัญ Ie",
        [1.0, 1.25, 1.5], index=0,
        format_func=lambda v: {1.0: "1.0 — อาคารทั่วไป",
                               1.25: "1.25 — อาคารสำคัญสูง",
                               1.5: "1.5 — โรงพยาบาล/โรงไฟฟ้า"}[v]
    )

    sys_type = st.selectbox(
        "ประเภทโครงสร้าง (สำหรับคำนวณ Ta)",
        list(calc.PERIOD_PARAMS.keys())
    )

    building_height = st.number_input("ความสูงอาคาร hn (ม.)", 1.0, 500.0, 12.0, 1.0)

    # ── 3. ตัวคูณซ้ำซ้อน ρ ────────────────────────────────────────────────────
    st.subheader("3. ตัวคูณความซ้ำซ้อน (ρ)")
    num_bays   = st.number_input("จำนวนช่วง Bay (แต่ละแนว)", 1, 20, 2, 1)
    num_frames = st.number_input("จำนวนแนวโครงต้านแรงด้านข้าง", 1, 10, 2, 1)

# ═══════════════════════════════════════════════════════════════════════════════
# Guard Conditions
# ═══════════════════════════════════════════════════════════════════════════════
if site_class == 'F':
    st.error(
        "🛑 **ชั้นดิน F** ต้องทำการศึกษาเฉพาะพื้นที่ (Site-Specific Response Analysis) "
        "ไม่สามารถใช้ค่าคำนวณมาตรฐานจากโปรแกรมนี้ได้"
    )
    st.stop()

# ดึงหรือรับค่า Ss, S1
# ตรวจสอบว่าเป็นพื้นที่ดินเหนียวอ่อนหรือไม่
is_soft_clay = (
    input_method == "ดึงจากฐานข้อมูล มยผ." and
    selected_province in SOFT_CLAY_PROVINCES
)

if is_soft_clay:
    # พื้นที่ดินเหนียวอ่อน: ใช้พารามิเตอร์คงที่จาก มยผ. 1302 โดยตรง
    Ss = SOFT_CLAY_SPECTRUM["SDS"]   # ใช้เป็นค่าอ้างอิง (SDS_bkk)
    S1 = SOFT_CLAY_SPECTRUM["SD1_eff"] / SOFT_CLAY_SPECTRUM["TL"]  # ≈ 0.20 g
    Fa = 1.0; Fv = 1.0   # ไม่ใช้ตาราง Fa/Fv (สเปกตรัมกำหนดโดยตรง)
    SMS = Ss; SM1 = S1
    SDS = SOFT_CLAY_SPECTRUM["SDS"]
    SD1 = SOFT_CLAY_SPECTRUM["SD1_eff"]
    T0  = SOFT_CLAY_SPECTRUM["T0"]
    TS  = SOFT_CLAY_SPECTRUM["TS"]
elif input_method == "ดึงจากฐานข้อมูล มยผ.":
    row = df_location[
        (df_location['Province'] == selected_province) &
        (df_location['District'] == selected_district)
    ].iloc[0]
    Ss = float(row['Ss'])
    S1 = float(row['S1'])
else:
    Ss = float(manual_Ss)
    S1 = float(manual_S1)

# ═══════════════════════════════════════════════════════════════════════════════
# Engine — คำนวณพารามิเตอร์หลัก
# ═══════════════════════════════════════════════════════════════════════════════
if not is_soft_clay:
    Fa, Fv = calc.get_site_coefficients(site_class, Ss, S1)
    SMS = Fa * Ss
    SM1 = Fv * S1
    SDS = (2.0 / 3.0) * SMS
    SD1 = (2.0 / 3.0) * SM1
    T0  = 0.2 * (SD1 / SDS) if SDS > 0 else 0.0
    TS  = SD1 / SDS if SDS > 0 else 0.0
# is_soft_clay: SDS, SD1, T0, TS, Fa, Fv already set above from SOFT_CLAY_SPECTRUM

Ta       = calc.calculate_approx_period(sys_type, building_height)
T_design = calc.get_period_upper_bound(SD1, Ta)   # = Cu·Ta

sdc, sdc_sds, sdc_sd1, sdc_notes = calc.evaluate_sdc_detailed(SDS, SD1, S1, importance_factor)
rho, rho_note = calc.get_redundancy_factor(sdc, int(num_bays), int(num_frames))

# ═══════════════════════════════════════════════════════════════════════════════
# แถบสรุปผลด่วน (แสดงตลอดเวลา เหนือแท็บ)
# ═══════════════════════════════════════════════════════════════════════════════
st.markdown("---")
sdc_emoji = {'ก': '🟢', 'ข': '🟡', 'ค': '🟠', 'ง': '🔴'}
sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
sc1.metric("พื้นที่", f"{selected_province}" if not is_soft_clay else "กทม./ปริมณฑล",
           "ดินเหนียวอ่อน มยผ.1302" if is_soft_clay else f"ชั้นดิน {site_class}")
sc2.metric("SDS", f"{SDS:.3f} g")
sc3.metric("SD1", f"{SD1:.3f} g")
sc4.metric("Ta / Cu·Ta", f"{Ta:.2f} / {T_design:.2f} s")
sc5.metric("SDC", f"{sdc_emoji.get(sdc,'')} ประเภท {sdc}")
sc6.metric("ρ", f"{rho}")

# ═══════════════════════════════════════════════════════════════════════════════
# แท็บหลัก
# ═══════════════════════════════════════════════════════════════════════════════
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 พารามิเตอร์สเปกตรัม",
    "🛡️ SDC & ผังตัดสินใจ",
    "📈 กราฟสเปกตรัม",
    "🏢 แรงสถิตเทียบเท่า",
    "📏 Drift & P-Delta",
    "📚 อ้างอิง & สัญลักษณ์",
])

# ╔══════════════════════════════════════════════════════════════════════════════
# TAB 1 — พารามิเตอร์สเปกตรัม (Step-by-Step)
# ╔══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.header("📋 รายการคำนวณพารามิเตอร์ Response Spectrum")

    if is_soft_clay:
        st.error(
            "🏙️ **พื้นที่ดินเหนียวอ่อน — มยผ. 1302-61** | "
            f"จ.**{selected_province}** | "
            "สเปกตรัมกำหนดโดยตรงจากมาตรฐาน **ไม่ใช้** Fa/Fv จากตาราง มยผ. 1301"
        )
        st.warning(
            "⚠️ **หมายเหตุสำคัญ:** มาตรฐานฉบับจริงแบ่งแอ่งกรุงเทพฯ เป็น**หลายโซน** "
            "ซึ่งแต่ละโซนมีค่าสเปกตรัมต่างกัน — โปรแกรมนี้ใช้รูปแบบสเปกตรัมอย่างง่าย "
            "(SDS = 0.20 g, Plateau 0.3–1.5 s) เพื่อการประมาณเบื้องต้นเท่านั้น "
            "ก่อนออกแบบจริงต้องตรวจสอบโซนที่ตั้งโครงการและใช้ค่าจากตารางใน มยผ. 1302 โดยตรง"
        )
    else:
        st.markdown(
            f"อ้างอิงมาตรฐาน **มยผ. 1301-61** | "
            f"สถานที่: **อ.{selected_district}  จ.{selected_province}** | "
            f"ชั้นดิน: **{site_class}** | Ie = **{importance_factor}**"
        )

    # ── ขั้นที่ 1: Ss, S1 / มยผ. 1302 Parameters ────────────────────────────
    if is_soft_clay:
        with st.expander("ขั้นที่ 1 — พารามิเตอร์สเปกตรัม มยผ. 1302 (ดินเหนียวอ่อน)", expanded=True):
            p = SOFT_CLAY_SPECTRUM
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("SDS (Plateau)", f"{p['SDS']:.2f} g")
            c2.metric("T₀ (เริ่ม Plateau)", f"{p['T0']:.2f} s")
            c3.metric("TL (สิ้นสุด Plateau)", f"{p['TL']:.2f} s")
            c4.metric("SD1_eff = SDS × TL", f"{p['SD1_eff']:.2f} g")
            st.caption(
                f"ที่มา: {p['source']} — สเปกตรัมนี้สะท้อนการขยายคลื่นในชั้นดินเหนียวอ่อน "
                f"ซึ่งทำให้ช่วง Plateau ยาวมาก ({p['T0']} – {p['TL']} วินาที)"
            )
    else:
        with st.expander("ขั้นที่ 1 — ความเร่งตอบสนองสเปกตรัมระดับหินฐาน", expanded=True):
            c1, c2 = st.columns(2)
            c1.metric("Ss — ความเร่งที่คาบ 0.2 s", f"{Ss:.3f} g")
            c2.metric("S1 — ความเร่งที่คาบ 1.0 s", f"{S1:.3f} g")
            if S1 >= 0.60:
                st.warning(f"⚠️ S1 = {S1:.3f} g ≥ 0.60 g → เงื่อนไขพิเศษ Cs,min จะถูกนำมาใช้ใน Tab 4")
            if S1 >= 0.75:
                st.error(f"🛑 S1 = {S1:.3f} g ≥ 0.75 g → บังคับ SDC ง ทันที")

    # ── ขั้นที่ 2: Fa, Fv — ข้ามสำหรับดินเหนียวอ่อน ──────────────────────
    if not is_soft_clay:
        with st.expander("ขั้นที่ 2 — ตัวคูณขยายอิทธิพลชั้นดิน Fa และ Fv", expanded=True):
            st.markdown(f"ประเมินสำหรับชั้นดิน **{site_class}** ด้วย Linear Interpolation จากตาราง มยผ.")
            c3, c4 = st.columns(2)
            c3.metric(f"Fa (จาก Ss = {Ss:.3f} g)", f"{Fa:.3f}")
            c4.metric(f"Fv (จาก S1 = {S1:.3f} g)", f"{Fv:.3f}")
            st.caption("ที่มา: ตารางสัมประสิทธิ์ Fa และ Fv ใน มยผ. 1301/1302-61 บทที่ 1 "
                       "(ค่าระหว่างช่วงใช้ Linear Interpolation)")
    else:
        with st.expander("ขั้นที่ 2 — ตัวคูณขยายอิทธิพลชั้นดิน Fa และ Fv", expanded=False):
            st.info("ℹ️ **ไม่ใช้ Fa/Fv** สำหรับพื้นที่ดินเหนียวอ่อน — "
                    "มยผ. 1302 กำหนดรูปทรงสเปกตรัมสำเร็จรูปโดยตรง "
                    "โดยรวมผลขยายของชั้นดินไว้แล้ว")

    # ── ขั้นที่ 3: SMS, SM1, SDS, SD1 ───────────────────────────────────────
    with st.expander("ขั้นที่ 3 — ความเร่งสเปกตรัมออกแบบ SDS และ SD1", expanded=True):
        col_s, col_l = st.columns(2)
        with col_s:
            st.info("**ช่วงคาบสั้น (0.2 s)**")
            st.latex(rf"S_{{MS}} = F_a S_S = {Fa:.3f} \times {Ss:.3f} = {SMS:.4f}\ \text{{g}}")
            st.latex(rf"S_{{DS}} = \tfrac{{2}}{{3}} S_{{MS}} = \tfrac{{2}}{{3}} \times {SMS:.4f} = {SDS:.4f}\ \text{{g}}")
        with col_l:
            st.info("**ช่วงคาบยาว (1.0 s)**")
            st.latex(rf"S_{{M1}} = F_v S_1 = {Fv:.3f} \times {S1:.3f} = {SM1:.4f}\ \text{{g}}")
            st.latex(rf"S_{{D1}} = \tfrac{{2}}{{3}} S_{{M1}} = \tfrac{{2}}{{3}} \times {SM1:.4f} = {SD1:.4f}\ \text{{g}}")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("SDS", f"{SDS:.4f} g")
        m2.metric("SD1", f"{SD1:.4f} g")
        m3.metric("T₀", f"{T0:.4f} s")
        m4.metric("Tₛ", f"{TS:.4f} s")
        st.caption("ตัวคูณ ⅔ คือสัดส่วนระดับการออกแบบ (DBE) ต่อระดับแผ่นดินไหวรุนแรงสูงสุด (MCE) "
                   "ตาม มยผ. 1301/1302-61")

    # ── ขั้นที่ 4: Ta, Cu·Ta ─────────────────────────────────────────────────
    with st.expander("ขั้นที่ 4 — คาบเวลาโครงสร้าง Ta และขีดจำกัด Cu·Ta", expanded=True):
        Ct_val, x_val = calc.PERIOD_PARAMS.get(sys_type, (0.0488, 0.75))
        col_ta, col_cu = st.columns(2)
        with col_ta:
            st.success("**คาบเวลาประมาณ Ta**")
            st.latex(
                rf"T_a = C_t \cdot h_n^x = {Ct_val} \times {building_height:.1f}^{{{x_val}}} = {Ta:.4f}\ \text{{s}}"
            )
        with col_cu:
            st.success("**ขีดจำกัดบน T_design = Cu · Ta**")
            Cu = T_design / Ta if Ta > 0 else 1.0
            st.latex(rf"T_{{design}} = C_u \cdot T_a = {Cu:.2f} \times {Ta:.4f} = {T_design:.4f}\ \text{{s}}")
            st.caption("T_design ใช้เป็น T ในสูตร Cs,max เท่านั้น ไม่ใช้คำนวณ Fx "
                       "(Cu จากตารางใน มยผ. ขึ้นกับค่า SD1)")

    # ── สรุปผล ────────────────────────────────────────────────────────────────
    with st.expander("🔖 สรุปพารามิเตอร์ทั้งหมด", expanded=False):
        summary = {
            "พารามิเตอร์": ["Ss", "S1", "Fa", "Fv", "SMS", "SM1",
                            "SDS", "SD1", "T₀", "Tₛ", "Ta", "Cu·Ta"],
            "ค่า":         [f"{Ss:.4f} g", f"{S1:.4f} g",
                            f"{Fa:.4f}", f"{Fv:.4f}",
                            f"{SMS:.4f} g", f"{SM1:.4f} g",
                            f"{SDS:.4f} g", f"{SD1:.4f} g",
                            f"{T0:.4f} s", f"{TS:.4f} s",
                            f"{Ta:.4f} s", f"{T_design:.4f} s"],
            "ที่มา": ["แผนที่ มยผ.", "แผนที่ มยผ.",
                     "ตาราง 11.4-1", "ตาราง 11.4-2",
                     "Fa×Ss", "Fv×S1",
                     "2/3 SMS", "2/3 SM1",
                     "0.2 Ts", "SD1/SDS",
                     "Ct·hn^x", "Cu·Ta"],
        }
        st.dataframe(pd.DataFrame(summary), use_container_width=True, hide_index=True)


# ╔══════════════════════════════════════════════════════════════════════════════
# TAB 2 — SDC & ผังการตัดสินใจ
# ╔══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.header("🛡️ ประเภทการออกแบบต้านทานแผ่นดินไหว (SDC)")

    # Badge สรุป SDC
    sdc_colors = {'ก': '#10b981', 'ข': '#f59e0b', 'ค': '#f97316', 'ง': '#ef4444'}
    sdc_color  = sdc_colors.get(sdc, '#64748b')
    st.markdown(
        f"<div style='background:{sdc_color};color:white;padding:18px 28px;"
        f"border-radius:12px;font-size:26px;font-weight:700;display:inline-block;'>"
        f"SDC ประเภท {sdc}</div>",
        unsafe_allow_html=True
    )
    st.markdown("")

    # เหตุผลการกำหนด SDC
    with st.container(border=True):
        c_sds, c_sd1, c_final = st.columns(3)
        c_sds.metric("SDC จาก SDS", f"ประเภท {sdc_sds}", f"SDS = {SDS:.4f} g")
        c_sd1.metric("SDC จาก SD1", f"ประเภท {sdc_sd1}", f"SD1 = {SD1:.4f} g")
        c_final.metric("SDC สุดท้าย (ค่ามากกว่า)", f"ประเภท {sdc}", "ใช้ค่านี้ในการออกแบบ")

    for note in sdc_notes:
        st.warning(note)

    # ρ
    with st.container(border=True):
        st.markdown(f"**ตัวคูณความซ้ำซ้อน ρ = {rho}**  |  {rho_note}")

    # ข้อกำหนดตาม SDC
    SDC_INFO = {
        'ก': {
            'analysis':   "✅ ไม่ต้องคำนวณแรงแผ่นดินไหวเต็มรูปแบบ",
            'minimum':    "📌 ออกแบบต้านทานแรงด้านข้างขั้นต่ำ = 0.01W",
            'detailing':  "🔧 ใช้รายละเอียดโครงสร้างปกติ ไม่ต้องจัดเหล็กปลอกต้านแผ่นดินไหว",
            'restriction':"ℹ️ ไม่มีข้อจำกัดพิเศษ",
        },
        'ข': {
            'analysis':   "✅ ใช้วิธีแรงสถิตเทียบเท่า (ESP) ได้",
            'minimum':    "📌 ต้องคำนวณและออกแบบตามแรงแผ่นดินไหวจริง",
            'detailing':  "🔧 ต้องจัดรายละเอียดโครงสร้างระดับ Ordinary (OMF/OSW)",
            'restriction':"ℹ️ ข้อจำกัดน้อย — เน้น detailing ขั้นต้น",
        },
        'ค': {
            'analysis':   "✅ ใช้ ESP ได้ หากโครงสร้างสม่ำเสมอและสูงไม่เกินเกณฑ์",
            'minimum':    "📌 ต้องคำนวณแรงแผ่นดินไหวและออกแบบตาม SDC ค",
            'detailing':  "🔧 ต้องจัดรายละเอียดระดับ Intermediate (IMF/ISW)",
            'restriction':"⚠️ ห้ามใช้ OMF/OSW โดยไม่มีข้อกำหนดพิเศษ",
        },
        'ง': {
            'analysis':   "⚡ หากโครงสร้างไม่สม่ำเสมอหรือสูงเกินเกณฑ์ → บังคับใช้ Modal RSA หรือ Time-History",
            'minimum':    "📌 ต้องคำนวณแรงแผ่นดินไหวและออกแบบตาม SDC ง อย่างเข้มงวด",
            'detailing':  "🔧 ต้องจัดรายละเอียดระดับ Special (SMF/SSW) เท่านั้น",
            'restriction':"🛑 ห้ามใช้ OMF/IMF และ Ordinary SW โดยเด็ดขาด",
        },
    }

    info = SDC_INFO.get(sdc, {})
    with st.expander(f"ข้อกำหนดสำหรับ SDC ประเภท {sdc}", expanded=True):
        for k, v in info.items():
            st.markdown(f"- {v}")

    # ผังการตัดสินใจ
    st.subheader("ผังการตัดสินใจเลือกวิธีวิเคราะห์")
    st.graphviz_chart(plots.get_roadmap_dot(), use_container_width=True)


# ╔══════════════════════════════════════════════════════════════════════════════
# TAB 3 — กราฟสเปกตรัม
# ╔══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header("📈 กราฟ Design Response Spectrum")

    if sdc == 'ก':
        st.info("💡 อาคาร SDC ประเภท ก ไม่ต้องวิเคราะห์สเปกตรัมเต็มรูปแบบ "
                "(แสดงไว้เพื่ออ้างอิง)")

    if is_soft_clay:
        Sa_Ta  = get_soft_clay_sa(Ta)
        Sa_Td  = get_soft_clay_sa(T_design)
        fig_spec = plots.create_soft_clay_spectrum_plot(Ta, T_design, Sa_Ta, Sa_Td)
    else:
        T_plot  = np.linspace(0.0, max(4.0, Ta * 2.0, TS * 3.0), 800)
        Sa_plot = np.array([calc.compute_spectrum_sa(t, SDS, SD1, T0, TS) for t in T_plot])
        Sa_Ta   = calc.compute_spectrum_sa(Ta, SDS, SD1, T0, TS)
        Sa_Td   = calc.compute_spectrum_sa(T_design, SDS, SD1, T0, TS)
        fig_spec = plots.create_spectrum_plot(
            T_plot, Sa_plot, Ta, T_design, Sa_Ta, Sa_Td, T0, TS, SDS, SD1
        )
    st.plotly_chart(fig_spec, use_container_width=True)

    # ตารางค่าที่คาบสำคัญ
    with st.expander("ตารางค่า Sa ณ คาบสำคัญ"):
        p1302 = SOFT_CLAY_SPECTRUM
        key_T = sorted(set([round(t, 4) for t in
            ([0.0, p1302["T0"], p1302["TL"], Ta, T_design, 1.0, 2.0, 3.0, 4.0]
             if is_soft_clay else
             [0.0, T0, TS, Ta, T_design, 1.0, 2.0, 3.0, 4.0])
            if t >= 0]))
        if is_soft_clay:
            rows = [(t, get_soft_clay_sa(t)) for t in key_T]
        else:
            rows = [(t, calc.compute_spectrum_sa(t, SDS, SD1, T0, TS)) for t in key_T]
        st.dataframe(
            pd.DataFrame(rows, columns=["T (s)", "Sa (g)"]).style.format({"T (s)": "{:.4f}", "Sa (g)": "{:.4f}"}),
            use_container_width=True, hide_index=True
        )


# ╔══════════════════════════════════════════════════════════════════════════════
# TAB 4 — แรงสถิตเทียบเท่า (Equivalent Static Procedure)
# ╔══════════════════════════════════════════════════════════════════════════════
with tab4:
    st.header("🏢 วิธีแรงสถิตเทียบเท่า (Equivalent Static Procedure)")

    # เตือนถ้า SDC ง และต้องพิจารณา Dynamic
    if sdc == 'ง':
        st.warning(
            "⚠️ **SDC ประเภท ง** — ต้องตรวจสอบความสม่ำเสมอโครงสร้างก่อน "
            "หากโครงสร้างไม่สม่ำเสมอหรือสูงเกิน 50 ม. ต้องใช้วิธีพลศาสตร์ (Modal RSA) แทน"
        )
    if sdc == 'ก':
        st.info("ℹ️ SDC ก — ใช้แรงด้านข้างขั้นต่ำ 1%W ไม่ต้องคำนวณด้านล่าง")

    # ── เลือกระบบโครงสร้าง ────────────────────────────────────────────────────
    st.subheader("ขั้นที่ 1 — เลือกระบบต้านทานแรงด้านข้าง")

    # จัดกลุ่มระบบโครงสร้าง
    categories = {}
    for name, info in STRUCTURAL_SYSTEMS.items():
        cat = info["category"]
        categories.setdefault(cat, []).append(name)

    selected_cat = st.selectbox("กลุ่มระบบโครงสร้าง", list(categories.keys()))
    selected_sys = st.selectbox("ระบบโครงสร้างต้านทานแรงด้านข้าง", categories[selected_cat])

    sys_info = STRUCTURAL_SYSTEMS[selected_sys]
    R_sys    = sys_info["R"]
    Omega0   = sys_info["Omega0"]
    Cd       = sys_info["Cd"]
    hn_max_d = sys_info["hn_max_d"]

    m1, m2, m3 = st.columns(3)
    m1.metric("R — ตัวคูณลดผลตอบสนอง",     str(R_sys))
    m2.metric("Ω₀ — ตัวคูณขยายกำลังส่วนวิกฤต", str(Omega0))
    m3.metric("Cd — ตัวคูณขยายระยะโยก",       str(Cd))
    if sys_info.get("note"):
        st.caption(f"ℹ️ {sys_info['note']}")
    if hn_max_d and building_height > hn_max_d and sdc == 'ง':
        st.error(f"🛑 ระบบนี้จำกัดความสูง {hn_max_d} ม. ใน SDC ง — ความสูงอาคาร {building_height} ม. เกินเกณฑ์")

    # ── Cs ────────────────────────────────────────────────────────────────────
    st.subheader("ขั้นที่ 2 — สัมประสิทธิ์แรงเฉือนที่ฐาน Cs")

    if is_soft_clay:
        cs = calc.compute_cs_soft_clay(T_design, R_sys, importance_factor)
    else:
        cs = calc.compute_cs(SDS, SD1, S1, T_design, R_sys, importance_factor, TS)

    with st.container(border=True):
        st.markdown("**สูตรและผลลัพธ์ Cs**")
        if is_soft_clay:
            st.info(
                "🏙️ **มยผ. 1302 (ดินเหนียวอ่อน):** Cs คำนวณจาก Sa(T_design) ของสเปกตรัม มยผ. 1302 โดยตรง"
            )
            ce1, ce2 = st.columns(2)
            with ce1:
                st.latex(
                    rf"Sa(T_{{design}}) = {cs['Sa_T']:.4f}\ \text{{g}} "
                    rf"\quad (T_{{design}} = {T_design:.3f}\ \text{{s}})"
                )
                st.latex(
                    rf"C_{{s,basic}} = \frac{{Sa(T)}}{{{R_sys:.1f}/{importance_factor:.2f}}} "
                    rf"= \frac{{{cs['Sa_T']:.4f}}}{{{cs['RIe']:.3f}}} = {cs['cs_basic']:.5f}"
                )
            with ce2:
                st.latex(
                    rf"C_{{s,min}} = \max(0.01,\ 0.044 \times {cs['SDS_bkk']:.2f} \times {importance_factor:.2f}) "
                    rf"= {cs['cs_min']:.5f}"
                )
        else:
            ce1, ce2 = st.columns(2)
            with ce1:
                st.latex(
                    rf"C_{{s,basic}} = \frac{{S_{{DS}}}}{{R/I_e}} "
                    rf"= \frac{{{SDS:.4f}}}{{{R_sys:.1f}/{importance_factor:.2f}}} = {cs['cs_basic']:.5f}"
                )
                st.latex(
                    rf"C_{{s,max}} = \frac{{S_{{D1}}}}{{T_{{design}} \cdot (R/I_e)}} "
                    rf"= \frac{{{SD1:.4f}}}{{{T_design:.4f} \times {cs['RIe']:.3f}}} = {cs['cs_max']:.5f}"
                )
            with ce2:
                st.latex(
                    rf"C_{{s,min}} = \max(0.01,\ 0.044 S_{{DS}} I_e) = {cs['cs_min']:.5f}"
                )
                if S1 >= 0.6:
                    st.latex(
                        rf"C_{{s,min,S1}} = \frac{{0.5 S_1}}{{R/I_e}} "
                        rf"= \frac{{0.5 \times {S1:.3f}}}{{{cs['RIe']:.3f}}} = {cs['cs_min_s1']:.5f}"
                    )
                    st.caption("S1 ≥ 0.6 g → นำ Cs,min,S1 มาเปรียบเทียบด้วย")

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Cs ที่ควบคุม", f"{cs['cs_gov']:.5f}", cs['controls'])
    mc2.metric("ρ (Redundancy)", f"{rho}", rho_note[:40] + "…" if len(rho_note) > 40 else rho_note)
    mc3.metric("ρ × Cs (ใช้ออกแบบจริง)", f"{rho * cs['cs_gov']:.5f}")

    st.plotly_chart(plots.create_cs_bar(cs), use_container_width=True)

    # ── กระจายแรงประจำชั้น ────────────────────────────────────────────────────
    st.subheader("ขั้นที่ 3 — กระจายแรงแผ่นดินไหวประจำชั้น")
    st.markdown("กรอกข้อมูลชั้นอาคาร (เรียงจาก**ชั้นบนสุด**ลงล่าง)")

    default_stories = pd.DataFrame([
        {"ชั้น": "ดาดฟ้า", "hx สะสม (ม.)": 14.0, "wx (ตัน)": 150.0},
        {"ชั้น": "ชั้น 3",  "hx สะสม (ม.)": 10.5, "wx (ตัน)": 200.0},
        {"ชั้น": "ชั้น 2",  "hx สะสม (ม.)":  7.0, "wx (ตัน)": 200.0},
        {"ชั้น": "ชั้น 1",  "hx สะสม (ม.)":  3.5, "wx (ตัน)": 220.0},
    ])
    edited_df = st.data_editor(
        default_stories, num_rows="dynamic", use_container_width=True,
        column_config={
            "ชั้น":           st.column_config.TextColumn("ชั้น", required=True),
            "hx สะสม (ม.)":   st.column_config.NumberColumn("hx สะสม (ม.)", min_value=0.0, format="%.2f", required=True),
            "wx (ตัน)":       st.column_config.NumberColumn("wx (ตัน)",      min_value=0.0, format="%.2f", required=True),
        }, key="force_editor"
    )

    clean_df = edited_df.dropna(subset=["hx สะสม (ม.)", "wx (ตัน)"]).copy()
    tab4_ready = not clean_df.empty
    if not tab4_ready:
        st.warning("⚠️ กรุณากรอกข้อมูลชั้นอาคารอย่างน้อย 1 ชั้น")
        st.session_state['computed'] = False

# ╔══════════════════════════════════════════════════════════════════════════════
# ส่วนประมวลผลและแสดงรายการคำนวณโดยละเอียดเมื่อข้อมูลชั้นพร้อม
# ╔══════════════════════════════════════════════════════════════════════════════
if tab4_ready:
  with tab4:
    # จัดเรียงจากชั้นบนสุดลงล่าง (hx มาก → น้อย) เพื่อให้ Vx สะสมถูกต้องเสมอ
    clean_df = clean_df.sort_values("hx สะสม (ม.)", ascending=False).reset_index(drop=True)

    floor_names = clean_df["ชั้น"].astype(str).values
    hx = clean_df["hx สะสม (ม.)"].astype(float).values
    wx = clean_df["wx (ตัน)"].astype(float).values

    # ตรวจสอบ hx ซ้ำ
    if len(set(hx)) != len(hx):
        st.error("🛑 พบค่า hx ซ้ำกัน — แต่ละชั้นต้องมีความสูงสะสมต่างกัน")
        st.stop()

    # เรียกใช้ Engine คำนวณหลักจาก calculations.py
    total_W, total_V, k_exp, sum_whxk, cvx, Fx, Vx, Mx = calc.calculate_story_forces(
        hx, wx, cs['cs_gov'], Ta
    )

    st.success("✅ คำนวณและกระจายแรงแผ่นดินไหวเสร็จสิ้น")

    # ─── เพิ่มส่วนรายการคำนวณโดยละเอียด (Calculation Report) ─────────────────────
    with st.container(border=True):
        st.subheader("🧾 รายการคำนวณวิธีแรงสถิตเทียบเท่า (Detailed Calculation Report)")
        
        # 1. แรงเฉือนที่ฐาน (V)
        st.markdown("#### 1) การคำนวณแรงเฉือนที่ฐานรวม (Base Shear, $V$)")
        st.markdown(f"""
        อ้างอิงจากสมการหลักตามมาตรฐาน มยผ. 1301/1302-61:
        $$ V = C_{{s,gov}} \\times W $$
        * **สัมประสิทธิ์แรงเฉือนที่ฐานควบคุม ($C_{{s,gov}}$):** $\\mathbf{{{cs['cs_gov']:.5f}}}$ *(คำนวณได้จากขั้นที่ 2)*
        * **น้ำหนักประสิทธิผลรวมของอาคาร ($W$):** $\\mathbf{{{total_W:,.2f}}}$ ตัน *(ผลรวมน้ำหนักทุกชั้น)*
        
        แทนค่าในสมการ:
        $$ V = {cs['cs_gov']:.5f} \\times {total_W:,.2f} = \\mathbf{{{total_V:,.3f}}}\\ \\text{{ตัน}} $$
        """)
        
        st.divider()

        # 2. ตัวคูณเลขชี้กำลัง (k)
        st.markdown("#### 2) การคำนวณหาค่าเลขชี้กำลังตามแนวดิ่ง (Exponent, $k$)")
        if Ta <= 0.5:
            k_rule = "T_a \\le 0.5\\ \\text{s} \\rightarrow k = 1.0"
        elif Ta >= 2.5:
            k_rule = "T_a \\ge 2.5\\ \\text{s} \\rightarrow k = 2.0"
        else:
            k_rule = rf"0.5 < T_a < 2.5\\ \\text{{s}} \\rightarrow k = 1.0 + \\frac{{T_a - 0.5}}{{2.0}}"
            
        st.markdown(f"""
        ค่าเลขชี้กำลัง $k$ พิจารณาจากคาบเวลาพื้นฐานของโครงสร้าง ($T_a = {Ta:.3f}$ วินาที):
        $$ {k_rule} $$
        แทนค่าได้พารามิเตอร์: **$k = {k_exp:.3f}$**
        """)
        
        st.divider()

        # 3. สัมประสิทธิ์การกระจายแรง (Cvx) และแรงประจำชั้น (Fx)
        st.markdown("#### 3) หลักการกระจายแรงเข้าสู่แต่ละระดับชั้น ($C_{vx}$ และ $F_x$)")
        st.markdown(f"""
        คำนวณตัวประกอบการกระจายแรงตามแนวดิ่ง ($C_{{vx}}$) และแรงประจำชั้น ($F_x$) ด้วยสมการ:
        $$ C_{{vx}} = \\frac{{w_x h_x^k}}{{\\sum_{{i=1}}^{{n}} w_i h_i^k}} \\qquad F_x = C_{{vx}} \\times V $$
        
        จากการรวมพารามิเตอร์ของทุกชั้นอาคาร จะได้ค่าตัวหารร่วมส่วนคือ:
        $$ \\sum_{{i=1}}^{{n}} w_i h_i^k = \\mathbf{{{sum_whxk:,.2f}}} $$
        
        *💡 **ตัวอย่างการแตกรายการคำนวณของชั้นบนสุด** ({floor_names[0]}):*
        * น้ำหนักชั้น ($w_x$): ${wx[0]:,.2f}$ ตัน | ความสูงสะสม ($h_x$): ${hx[0]:.2f}$ ม.
        * ค่าตัวคูณยกกำลัง ($w_x h_x^k$): ${wx[0]:,.2f} \\times {hx[0]:.2f}^{{{k_exp:.3f}}} = {wx[0]*(hx[0]**k_exp):,.2f}$
        * หาค่า $C_{{vx}}$ ประจําชั้น:
        $$ C_{{vx}} = \\frac{{{wx[0]*(hx[0]**k_exp):,.2f}}}{{{sum_whxk:,.2f}}} = \\mathbf{{{cvx[0]:.5f}}} $$
        * คำนวณแรงแผ่นดินไหวประจำชั้น $F_x$:
        $$ F_x = {cvx[0]:.5f} \\times {total_V:,.3f} = \\mathbf{{{Fx[0]:,.3f}}}\\ \\text{{ตัน}} $$
        """)
    # ─── จบส่วนรายการคำนวณโดยละเอียด ──────────────────────────────────────────

    st.subheader("📊 ตารางสรุปผลลัพธ์การกระจายแรงประจำชั้น")
    res_df = pd.DataFrame({
        "ชั้น": floor_names,
        "hx (ม.)": hx,
        "wx (ตัน)": wx,
        "wx·hxᵏ": wx * (hx ** k_exp),
        "Cvx": cvx,
        "Fx (ตัน)": Fx,
        "Vx (ตัน)": Vx,
        "Mx (ตัน·ม.)": Mx,
    })
    st.dataframe(
        res_df.style.format({
            "hx (ม.)": "{:.2f}",
            "wx (ตัน)": "{:,.2f}",
            "wx·hxᵏ": "{:,.2f}",
            "Cvx": "{:.5f}",
            "Fx (ตัน)": "{:,.3f}",
            "Vx (ตัน)": "{:,.3f}",
            "Mx (ตัน·ม.)": "{:,.2f}",
        }),
        use_container_width=True, hide_index=True
    )

    st.plotly_chart(plots.create_force_plot(floor_names, Fx, Vx, Mx), use_container_width=True)

    # เก็บข้อมูลสำหรับ Tab 5
    st.session_state['floor_names'] = floor_names
    st.session_state['hx']          = hx
    st.session_state['wx']          = wx
    st.session_state['Fx']          = Fx
    st.session_state['Vx']          = Vx
    st.session_state['Cd']          = Cd
    st.session_state['computed']    = True


# ╔══════════════════════════════════════════════════════════════════════════════
# TAB 5 — Story Drift & P-Delta
# ╔══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.header("📏 ตรวจสอบ Story Drift และ P-Delta Stability")

    if not st.session_state.get('computed', False):
        st.info("💡 กรอกข้อมูลและคำนวณแรงใน Tab 4 ก่อน จากนั้นกลับมาที่นี่")
        st.stop()

    floor_names = st.session_state['floor_names']
    hx          = st.session_state['hx']
    wx          = st.session_state['wx']
    Fx          = st.session_state['Fx']
    Vx          = st.session_state['Vx']
    Cd_val      = st.session_state['Cd']

    drift_limit, drift_label = get_drift_limit(importance_factor)

    # ── แสดงสมการและแผนภาพ ────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown(f"🎯 **เกณฑ์ขีดจำกัด Drift Ratio:** {drift_label}")
        col_eq, col_pic = st.columns([1, 1])
        with col_eq:
            st.latex(r"\delta_x = \frac{C_d \cdot \delta_e}{I_e}")
            st.latex(r"\text{Drift Ratio} = \frac{\delta_{x,top} - \delta_{x,bot}}{h_{sx}} \leq \text{Limit}")
            st.latex(r"\theta = \frac{P_x \cdot \Delta_x}{V_x \cdot h_{sx} \cdot (C_d/I_e)}")
        with col_pic:
            st.plotly_chart(plots.create_drift_model_plot(), use_container_width=True,
                            config={'displayModeBar': False})

    # ── ตารางกรอก δe ──────────────────────────────────────────────────────────
    st.markdown("##### กรอกระยะโยกพืดยืดหยุ่น δe จากโปรแกรมโครงสร้าง (ซม.)")
    n = len(hx)
    drift_input = pd.DataFrame({
        "ชั้น":            floor_names,
        "hx (ม.)":        hx,
        "δe จากโปรแกรม (ซม.)": np.linspace(2.0, 0.3, n),
    })
    edited_drift = st.data_editor(
        drift_input, num_rows="fixed", use_container_width=True,
        column_config={
            "ชั้น":     st.column_config.TextColumn(disabled=True),
            "hx (ม.)": st.column_config.NumberColumn(disabled=True, format="%.2f"),
            "δe จากโปรแกรม (ซม.)": st.column_config.NumberColumn(min_value=0.0, format="%.4f"),
        }, key=f"drift_ed_{n}"
    )

    delta_e = edited_drift["δe จากโปรแกรม (ซม.)"].values.astype(float)
    delta_x = (Cd_val * delta_e) / importance_factor   # ระยะโยกจริง (ซม.)

    # คำนวณ Drift
    story_h     = np.zeros(n)
    drift_ratio = np.zeros(n)
    status      = []

    for i in range(n):
        h_net    = (hx[i] - hx[i + 1]) * 100 if i < n - 1 else hx[i] * 100
        h_net    = max(h_net, 1.0)
        d_diff   = delta_x[i] - delta_x[i + 1] if i < n - 1 else delta_x[i]
        story_h[i]     = h_net / 100      # เก็บเป็นเมตร
        drift_ratio[i] = d_diff / h_net   # ratio (dimensionless)
        status.append("✅ PASS" if drift_ratio[i] <= drift_limit else "❌ FAIL")

    # P-Delta θ
    Px = np.array([np.sum(wx[:i + 1]) for i in range(n)])   # น้ำหนักสะสมเหนือชั้น i
    theta = calc.compute_stability_coeff(Px, delta_x, Vx, hx, Cd_val, importance_factor)
    theta_status = [
        "🛑 เกิน θ_max" if t > 0.25 else ("⚠️ ต้องพิจารณา P-Δ" if t > 0.10 else "✅ ปกติ")
        for t in theta
    ]

    # ── ตาราง Drift ────────────────────────────────────────────────────────────
    st.subheader("ผลการตรวจสอบ Story Drift")
    res_drift = pd.DataFrame({
        "ชั้น": floor_names,
        "hsx (ม.)": story_h,
        "δe (ซม.)": delta_e,
        "δx = Cd·δe/Ie (ซม.)": delta_x,
        "Drift Ratio (Δ/hsx)": drift_ratio,
        "Limit": drift_limit,
        "ผล": status,
    })
    st.dataframe(
        res_drift.style.map(
            lambda v: ('background-color:#dcfce7;color:#166534;font-weight:bold;'
                       if 'PASS' in str(v)
                       else ('background-color:#fee2e2;color:#991b1b;font-weight:bold;'
                             if 'FAIL' in str(v) else '')),
            subset=['ผล']
        ).format({
            "hsx (ม.)": "{:.2f}",
            "δe (ซม.)": "{:.4f}",
            "δx = Cd·δe/Ie (ซม.)": "{:.4f}",
            "Drift Ratio (Δ/hsx)": "{:.5f}",
            "Limit": "{:.4f}",
        }),
        use_container_width=True, hide_index=True
    )

    # ── ตาราง P-Delta ──────────────────────────────────────────────────────────
    st.subheader("ผลการตรวจสอบ P-Delta Stability (θ)")
    res_theta = pd.DataFrame({
        "ชั้น": floor_names,
        "Px สะสม (ตัน)": Px,
        "Δx (ซม.)": [delta_x[i] - delta_x[i + 1] if i < n - 1 else delta_x[i] for i in range(n)],
        "Vx (ตัน)": Vx,
        "hsx (ม.)": story_h,
        "θ": theta,
        "ผล": theta_status,
    })
    st.dataframe(
        res_theta.style.map(
            lambda v: ('background-color:#fef9c3;color:#854d0e;font-weight:bold;'
                       if '⚠️' in str(v)
                       else ('background-color:#fee2e2;color:#991b1b;font-weight:bold;'
                             if '🛑' in str(v) else '')),
            subset=['ผล']
        ).format({
            "Px สะสม (ตัน)": "{:,.2f}",
            "Δx (ซม.)": "{:.4f}",
            "Vx (ตัน)": "{:,.3f}",
            "hsx (ม.)": "{:.2f}",
            "θ": "{:.5f}",
        }),
        use_container_width=True, hide_index=True
    )
    st.plotly_chart(plots.create_theta_plot(floor_names, theta), use_container_width=True)

    if any("🛑" in s for s in theta_status):
        st.error("🛑 มีชั้นที่ θ > θ_max — โครงสร้างอาจไม่มีเสถียรภาพ ต้องปรับปรุงหน้าตัดหรือระบบโครงสร้าง")
    elif any("⚠️" in s for s in theta_status):
        st.warning("⚠️ มีชั้นที่ 0.10 < θ ≤ 0.25 — ต้องขยายแรงภายในด้วยตัวคูณ 1/(1-θ) ตาม มยผ. 12.8.7")


# ╔══════════════════════════════════════════════════════════════════════════════
# TAB 6 — อ้างอิง มาตรฐาน และตารางสัญลักษณ์
# ╔══════════════════════════════════════════════════════════════════════════════
with tab6:
    st.header("📚 เอกสารอ้างอิงและตารางสัญลักษณ์")

    col_ref, col_sym = st.columns([1, 1])

    with col_ref:
        st.subheader("เอกสารอ้างอิงหลัก")
        st.markdown(
            """
| ลำดับ | เอกสาร | เนื้อหาที่ใช้ |
|---|---|---|
| 1 | **มยผ. 1301/1302-61** มาตรฐานการออกแบบอาคารต้านทานการสั่นสะเทือนของแผ่นดินไหว (กรมโยธาธิการและผังเมือง, 2561) | ค่า Ss, S1 รายพื้นที่ · ตาราง Fa/Fv · SDC · สูตร Cs · การกระจายแรง · Drift Limit · สเปกตรัมดินเหนียวอ่อน กทม. |
| 2 | **กฎกระทรวง** กำหนดการรับน้ำหนัก ความต้านทาน ความคงทนของอาคาร และพื้นดินที่รองรับอาคารในการต้านทานแรงสั่นสะเทือนของแผ่นดินไหว **พ.ศ. 2564** | ขอบเขตบังคับใช้ตามพื้นที่ (บริเวณที่ 1, 2, 3) และประเภทอาคารควบคุม |
| 3 | **ASCE/SEI 7** Minimum Design Loads (มาตรฐานต้นแบบ) | โครงสร้างสูตร ESP · ตาราง R, Ω₀, Cd · θ P-Delta · ρ Redundancy |
| 4 | **ACI 318** / **AISC 341** | ข้อกำหนด Detailing ระดับ Ordinary / Intermediate / Special |
            """
        )
        st.caption(
            "ดาวน์โหลดมาตรฐานฉบับเต็มได้จากเว็บไซต์กรมโยธาธิการและผังเมือง "
            "(subsites.dpt.go.th) — โปรดใช้ฉบับล่าสุดเสมอ"
        )

        st.subheader("ที่มาของสูตรหลักในโปรแกรม")
        st.markdown(
            """
| สูตร | ที่มาใน มยผ. |
|---|---|
| SMS = Fa·Ss, SM1 = Fv·S1 | บทที่ 1 (พารามิเตอร์พื้นที่) |
| SDS = ⅔SMS, SD1 = ⅔SM1 | บทที่ 1 |
| Ta = Ct·hₙˣ และ Cu·Ta | บทที่ 3 (วิธีแรงสถิตเทียบเท่า) |
| Cs = SDS/(R/Ie) พร้อม max/min | บทที่ 3 |
| Fx = Cvx·V, Cvx = wₓhₓᵏ/Σwh^k | บทที่ 3 |
| δx = Cd·δe/Ie, Drift Limit | บทที่ 3 (ตารางขีดจำกัดการเคลื่อนตัว) |
| θ = PₓΔIe/(VₓhₛₓCd) | บทที่ 3 (ผล P-Delta) |
| สเปกตรัมดินเหนียวอ่อน กทม. | มยผ. 1302 ส่วนพื้นที่แอ่งกรุงเทพฯ |
            """
        )

    with col_sym:
        st.subheader("ตารางสัญลักษณ์ (Nomenclature)")
        sym_df = pd.DataFrame([
            ("Ss",   "g",    "ความเร่งตอบสนองสเปกตรัมที่คาบ 0.2 s (หินฐาน)"),
            ("S1",   "g",    "ความเร่งตอบสนองสเปกตรัมที่คาบ 1.0 s (หินฐาน)"),
            ("Fa, Fv","-",   "ตัวคูณขยายอิทธิพลชั้นดิน คาบสั้น/คาบยาว"),
            ("SDS",  "g",    "ความเร่งสเปกตรัมออกแบบช่วงคาบสั้น"),
            ("SD1",  "g",    "ความเร่งสเปกตรัมออกแบบที่คาบ 1 วินาที"),
            ("T0, TS","s",   "คาบควบคุมรูปทรงสเปกตรัม"),
            ("Ta",   "s",    "คาบธรรมชาติโดยประมาณของอาคาร"),
            ("Cu",   "-",    "ตัวคูณขีดจำกัดบนของคาบ (ขึ้นกับ SD1)"),
            ("Ie",   "-",    "ตัวคูณความสำคัญของอาคาร (1.0/1.25/1.5)"),
            ("R",    "-",    "ตัวคูณปรับลดผลตอบสนอง (ความเหนียว)"),
            ("Ω₀",   "-",    "ตัวคูณขยายกำลังส่วนวิกฤต"),
            ("Cd",   "-",    "ตัวคูณขยายการเคลื่อนตัว"),
            ("ρ",    "-",    "ตัวคูณความซ้ำซ้อนของระบบ (1.0/1.3)"),
            ("Cs",   "-",    "สัมประสิทธิ์แรงเฉือนที่ฐาน"),
            ("V",    "ตัน",  "แรงเฉือนที่ฐานรวม = Cs·W"),
            ("W",    "ตัน",  "น้ำหนักประสิทธิผลของอาคาร"),
            ("k",    "-",    "เลขชี้กำลังการกระจายแรงตามความสูง"),
            ("Fx",   "ตัน",  "แรงแผ่นดินไหวประจำชั้น x"),
            ("Vx",   "ตัน",  "แรงเฉือนสะสมที่ชั้น x"),
            ("Mx",   "ตัน·ม.","โมเมนต์พลิกคว่ำที่ระดับชั้น x"),
            ("δe",   "ซม.",  "การเคลื่อนตัวอิลาสติกจากการวิเคราะห์"),
            ("δx",   "ซม.",  "การเคลื่อนตัวออกแบบ = Cd·δe/Ie"),
            ("Δ",    "ซม.",  "Story Drift = δx,บน − δx,ล่าง"),
            ("hsx",  "ม.",   "ความสูงระหว่างชั้น"),
            ("θ",    "-",    "สัมประสิทธิ์เสถียรภาพ P-Delta"),
            ("SDC",  "-",    "ประเภทการออกแบบต้านทานแผ่นดินไหว (ก/ข/ค/ง)"),
        ], columns=["สัญลักษณ์", "หน่วย", "ความหมาย"])
        st.dataframe(sym_df, use_container_width=True, hide_index=True, height=560)

    st.divider()
    st.subheader("ขั้นตอนการใช้งานโปรแกรม (Workflow)")
    st.markdown(
        """
1. **Sidebar** — เลือกพื้นที่ (หรือกรอก Ss/S1 เอง), ชั้นดิน, Ie, ประเภทโครงสร้าง, ความสูงอาคาร
2. **Tab 1** — ตรวจทานพารามิเตอร์สเปกตรัมทีละขั้น (Ss → Fa/Fv → SDS/SD1 → Ta/Cu·Ta)
3. **Tab 2** — ดูผล SDC, ρ, ข้อกำหนด Detailing และผังเลือกวิธีวิเคราะห์
4. **Tab 3** — ตรวจสอบกราฟสเปกตรัมและตำแหน่ง Ta บนกราฟ
5. **Tab 4** — เลือกระบบโครงสร้าง (R, Ω₀, Cd) → ได้ Cs → กรอกชั้นอาคาร → ได้ Fx, Vx, Mx
6. **Tab 5** — นำ δe จากโปรแกรมวิเคราะห์โครงสร้าง (เช่น ETABS/SAP2000) มาตรวจ Drift และ θ
        """
    )
