# ╔══════════════════════════════════════════════════════════════════════════╗
# ║   DPT STRUCTURAL DESIGN SUITE  —  โปรแกรมคำนวณโครงสร้างตามมาตรฐานกรมโยธาธิการฯ      ║
# ║                                                                            ║
# ║   Standards implemented (มาตรฐานที่ใช้อ้างอิงในแต่ละโมดูล):                          ║
# ║   • มยผ. 1101–1106   น้ำหนักบรรทุกขั้นต่ำ (Dead Load & Live Load)                ║
# ║   • มยผ. 1311-50     การคำนวณแรงลมและการตอบสนองของอาคาร (Wind Load)            ║
# ║   • มยผ. 1301/1302-61 การออกแบบอาคารต้านทานการสั่นสะเทือนของแผ่นดินไหว (Seismic)   ║
# ║   • มยผ. 1501–1503   การออกแบบ คสล. (SDM) และโครงสร้างเหล็ก (ASD)              ║
# ║                                                                            ║
# ║   Architecture: Single-file, 3 layers                                      ║
# ║     LAYER 1  DATABASES   — code-mandated tables (ห้ามแก้โดยไม่อ้างอิงมาตรฐาน)      ║
# ║     LAYER 2  ENGINES     — pure calculation functions, one per standard    ║
# ║     LAYER 3  UI          — 3-panel layout: Input | Process Log | Results   ║
# ║                                                                            ║
# ║   ⚠️ DISCLAIMER: เครื่องมือช่วยคำนวณเบื้องต้นเท่านั้น ผลลัพธ์ทุกค่าต้องได้รับการตรวจสอบ    ║
# ║   และรับรองโดยวิศวกรโยธาที่มีใบอนุญาตประกอบวิชาชีพ (สามัญวิศวกรขึ้นไปตามขอบเขตงาน)        ║
# ╚══════════════════════════════════════════════════════════════════════════╝

import streamlit as st
import pandas as pd
import numpy as np
import io
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.interpolate import interp1d

# ==========================================================================
# SECTION 0 : PAGE CONFIG & GLOBAL STYLE
# ==========================================================================
st.set_page_config(page_title="DPT Structural Suite", page_icon="🏗️", layout="wide")

st.markdown("""
<style>
    /* กรอบ Process Log ให้อ่านง่ายแบบ engineer's calculation pad */
    .stCode { font-size: 0.78rem; }
    div[data-testid="stMetricValue"] { font-size: 1.35rem; }
    h3 { margin-top: 0.4rem; }
</style>
""", unsafe_allow_html=True)

st.title("🏗️ DPT Structural Design Suite")
st.markdown(
    "**โปรแกรมคำนวณน้ำหนักบรรทุก • แรงลม • แรงแผ่นดินไหว • และออกแบบหน้าตัด ตามมาตรฐาน มยผ.** "
    "&nbsp;|&nbsp; มยผ.1101-1106 · มยผ.1311-50 · มยผ.1301/1302-61 · มยผ.1501-1503"
)
st.caption("⚠️ เครื่องมือช่วยคำนวณเบื้องต้น — ผลลัพธ์ต้องตรวจสอบและลงนามรับรองโดยวิศวกรผู้มีใบอนุญาตเท่านั้น")

# ==========================================================================
# SECTION 1 : DATABASES  (LAYER 1)
# ==========================================================================

# --------------------------------------------------------------------------
# 1.1  น้ำหนักบรรทุกจรขั้นต่ำตามประเภทการใช้งานอาคาร
#      อ้างอิง: มยผ. 1101 ประกอบกฎกระทรวงฉบับที่ 6 (พ.ศ.2527) ข้อ 15
#      หน่วย kg/m²  — ค่าเหล่านี้คือ "ขั้นต่ำตามกฎหมาย" ผู้ใช้กรอกต่ำกว่านี้ไม่ได้
# --------------------------------------------------------------------------
LIVE_LOAD_DB = {
    "หลังคา (ไม่ใช้ประโยชน์)":                          50,
    "กันสาด / หลังคาคอนกรีต":                         100,
    "ที่พักอาศัย (บ้าน หอพัก ห้องชุด)":                  150,
    "อาคารชุด / โรงแรม / โรงพยาบาล (ห้องพัก)":          200,
    "สำนักงาน / ธนาคาร":                              250,
    "โรงเรียน / ห้องเรียน / ที่ทำการ":                    300,
    "ห้างสรรพสินค้า / หอประชุม / ภัตตาคาร":              400,
    "โรงมหรสพ / อัฒจันทร์ / ที่จอดรถยนต์":               500,
    "คลังสินค้า / โรงงานอุตสาหกรรม":                    600,
    "ห้องสมุด (ชั้นเก็บหนังสือ) / ห้องเก็บเอกสาร":          600,
}

# --------------------------------------------------------------------------
# 1.2  หน่วยน้ำหนักวัสดุสำหรับน้ำหนักบรรทุกคงที่ (Dead Load)
#      อ้างอิง: มยผ. 1101 ภาคผนวก / ตารางหน่วยน้ำหนักวัสดุก่อสร้าง  (kg/m³ หรือ kg/m²)
# --------------------------------------------------------------------------
DEAD_LOAD_MATERIAL_DB = {
    "คอนกรีตเสริมเหล็ก":      {"unit": "kg/m³", "value": 2400},
    "คอนกรีตล้วน":            {"unit": "kg/m³", "value": 2320},
    "เหล็กโครงสร้าง":          {"unit": "kg/m³", "value": 7850},
    "อิฐมอญครึ่งแผ่น (รวมฉาบ)":  {"unit": "kg/m²", "value": 180},
    "อิฐมอญเต็มแผ่น (รวมฉาบ)":  {"unit": "kg/m²", "value": 360},
    "คอนกรีตบล็อก 7 ซม. (รวมฉาบ)": {"unit": "kg/m²", "value": 120},
    "ผนังเบา / ยิปซัม 2 ด้าน":    {"unit": "kg/m²", "value": 40},
    "กระเบื้องเซรามิก+ปูนทราย":  {"unit": "kg/m²", "value": 110},
    "ฝ้าเพดาน+งานระบบ (MEP)":  {"unit": "kg/m²", "value": 50},
}

# --------------------------------------------------------------------------
# 1.3  ความเร็วลมอ้างอิงตามโซนแรงลมประเทศไทย
#      อ้างอิง: มยผ. 1311-50 รูปที่ 1 (แผนที่ความเร็วลมอ้างอิง คาบเวลากลับ 50 ปี)
#      V50 = ความเร็วลมเฉลี่ย 1 ชม. ที่ 10 ม. ในภูมิประเทศโล่ง (m/s)
#      TF  = Typhoon Factor สำหรับภาคใต้ฝั่งอ่าวไทย (กลุ่ม 4A/4B) ใช้คูณ q ที่สภาวะจำกัด
# --------------------------------------------------------------------------
WIND_ZONE_DB = {
    "โซน 1 — กทม. ภาคกลาง ภาคเหนือตอนล่าง (V50=25 m/s)":      {"V50": 25.0, "TF": 1.0},
    "โซน 2 — ภาคอีสาน ภาคตะวันออก (V50=27 m/s)":              {"V50": 27.0, "TF": 1.0},
    "โซน 3 — ภาคเหนือตอนบน ชายแดนตะวันตก (V50=29 m/s)":        {"V50": 29.0, "TF": 1.0},
    "โซน 4A — ภาคใต้ฝั่งตะวันออก (V50=25 m/s, TF=1.2)":          {"V50": 25.0, "TF": 1.2},
    "โซน 4B — ภาคใต้ฝั่งตะวันตก (V50=25 m/s, TF=1.08)":          {"V50": 25.0, "TF": 1.08},
}

# ตัวคูณความสำคัญสำหรับแรงลม (มยผ.1311-50 ตารางที่ 2) — สภาวะจำกัดด้านกำลัง (ULS)
WIND_IMPORTANCE_DB = {
    "น้อย (เกษตร/ชั่วคราว)": 0.8,
    "ปกติ (อาคารทั่วไป)": 1.0,
    "มาก (ชุมนุมชน/โรงเรียน)": 1.15,
    "สูงมาก (โรงพยาบาล/ศูนย์ภัยพิบัติ)": 1.15,
}

# --------------------------------------------------------------------------
# 1.4  ฐานข้อมูลค่าความเร่งตอบสนองเชิงสเปกตรัม Ss, S1 รายอำเภอ
#      อ้างอิง: มยผ. 1302-61 ภาคผนวก ก. (แผนที่ความเสี่ยงภัยแผ่นดินไหว)
# --------------------------------------------------------------------------
SEISMIC_CSV = """Province,District,Ss,S1
เชียงราย,เมืองเชียงราย,1.139,0.316
เชียงราย,แม่สาย,1.332,0.370
เชียงราย,เชียงแสน,1.280,0.352
เชียงราย,เชียงของ,1.050,0.290
เชียงราย,แม่จัน,1.210,0.338
เชียงราย,พาน,0.920,0.258
เชียงราย,เวียงป่าเป้า,0.870,0.245
เชียงราย,แม่สรวย,0.895,0.252
เชียงราย,เวียงชัย,1.100,0.308
เชียงราย,แม่ลาว,0.960,0.268
เชียงใหม่,เมืองเชียงใหม่,0.852,0.244
เชียงใหม่,ฝาง,1.218,0.334
เชียงใหม่,แม่ริม,0.870,0.248
เชียงใหม่,สันทราย,0.840,0.240
เชียงใหม่,สันกำแพง,0.820,0.235
เชียงใหม่,ดอยสะเก็ด,0.835,0.238
เชียงใหม่,สะเมิง,0.890,0.252
เชียงใหม่,แม่แตง,0.920,0.260
เชียงใหม่,พร้าว,1.000,0.278
เชียงใหม่,เชียงดาว,1.050,0.292
เชียงใหม่,จอมทอง,0.780,0.225
เชียงใหม่,ฮอด,0.720,0.210
เชียงใหม่,ดอยเต่า,0.695,0.205
เชียงใหม่,อมก๋อย,0.650,0.195
เชียงใหม่,ไชยปราการ,1.100,0.308
เชียงใหม่,แม่วาง,0.800,0.230
เชียงใหม่,ดอยหล่อ,0.760,0.220
แม่ฮ่องสอน,เมืองแม่ฮ่องสอน,0.980,0.262
แม่ฮ่องสอน,ปาย,1.019,0.269
แม่ฮ่องสอน,แม่สะเรียง,0.820,0.230
แม่ฮ่องสอน,ขุนยวม,0.910,0.252
แม่ฮ่องสอน,สบเมย,0.780,0.222
แม่ฮ่องสอน,ปางมะผ้า,1.000,0.270
แม่ฮ่องสอน,แม่ลาน้อย,0.850,0.238
ลำปาง,เมืองลำปาง,0.620,0.188
ลำปาง,แม่เมาะ,0.580,0.178
ลำปาง,เกาะคา,0.610,0.185
ลำปาง,แจ้ห่ม,0.640,0.192
ลำปาง,วังเหนือ,0.700,0.205
ลำปาง,งาว,0.660,0.196
ลำปาง,เสริมงาม,0.595,0.182
ลำพูน,เมืองลำพูน,0.750,0.218
ลำพูน,บ้านโฮ่ง,0.720,0.210
ลำพูน,ลี้,0.680,0.200
ลำพูน,ทุ่งหัวช้าง,0.710,0.208
ลำพูน,ป่าซาง,0.740,0.215
ลำพูน,บ้านธิ,0.760,0.220
น่าน,เมืองน่าน,0.720,0.210
น่าน,ปัว,0.810,0.232
น่าน,ท่าวังผา,0.760,0.218
น่าน,เวียงสา,0.700,0.205
น่าน,บ้านหลวง,0.740,0.215
น่าน,นาน้อย,0.680,0.200
น่าน,ทุ่งช้าง,0.850,0.240
พะเยา,เมืองพะเยา,0.780,0.225
พะเยา,ดอกคำใต้,0.760,0.218
พะเยา,จุน,0.810,0.232
พะเยา,เชียงม่วน,0.840,0.238
พะเยา,ปง,0.870,0.245
พะเยา,แม่ใจ,0.790,0.227
แพร่,เมืองแพร่,0.650,0.195
แพร่,ร้องกวาง,0.630,0.190
แพร่,ลอง,0.610,0.185
แพร่,สูงเม่น,0.640,0.192
แพร่,เด่นชัย,0.660,0.196
แพร่,สอง,0.680,0.200
อุตรดิตถ์,เมืองอุตรดิตถ์,0.480,0.155
อุตรดิตถ์,ลับแล,0.460,0.150
อุตรดิตถ์,ตรอน,0.440,0.145
อุตรดิตถ์,น้ำปาด,0.510,0.162
อุตรดิตถ์,ฟากท่า,0.530,0.168
อุตรดิตถ์,บ้านโคก,0.550,0.172
ตาก,เมืองตาก,0.480,0.155
ตาก,แม่สอด,0.720,0.210
ตาก,แม่ระมาด,0.650,0.195
ตาก,ท่าสองยาง,0.600,0.182
ตาก,อุ้มผาง,0.620,0.188
ตาก,บ้านตาก,0.490,0.158
ตาก,สามเงา,0.520,0.165
กำแพงเพชร,เมืองกำแพงเพชร,0.280,0.100
กำแพงเพชร,คลองลาน,0.380,0.128
กำแพงเพชร,ปางศิลาทอง,0.320,0.112
กำแพงเพชร,ขาณุวรลักษบุรี,0.270,0.098
สุโขทัย,เมืองสุโขทัย,0.320,0.112
สุโขทัย,ศรีสัชนาลัย,0.380,0.128
สุโขทัย,คีรีมาศ,0.340,0.118
สุโขทัย,สวรรคโลก,0.350,0.120
สุโขทัย,ศรีสำโรง,0.355,0.122
พิษณุโลก,เมืองพิษณุโลก,0.350,0.120
พิษณุโลก,นครไทย,0.410,0.138
พิษณุโลก,วังทอง,0.360,0.122
พิษณุโลก,วัดโบสถ์,0.380,0.128
เพชรบูรณ์,เมืองเพชรบูรณ์,0.280,0.100
เพชรบูรณ์,หล่มสัก,0.320,0.112
เพชรบูรณ์,หล่มเก่า,0.340,0.118
กาญจนบุรี,เมืองกาญจนบุรี,0.428,0.138
กาญจนบุรี,ทองผาภูมิ,0.560,0.175
กาญจนบุรี,สังขละบุรี,0.620,0.188
กาญจนบุรี,ศรีสวัสดิ์,0.480,0.155
กาญจนบุรี,ไทรโยค,0.460,0.150
กาญจนบุรี,บ่อพลอย,0.390,0.130
กาญจนบุรี,พนมทวน,0.360,0.122
กาญจนบุรี,ท่ามะกา,0.340,0.118
กาญจนบุรี,ท่าม่วง,0.350,0.120
กาญจนบุรี,เลาขวัญ,0.370,0.125
ราชบุรี,เมืองราชบุรี,0.260,0.095
ราชบุรี,สวนผึ้ง,0.340,0.118
ราชบุรี,บ้านคา,0.320,0.112
ประจวบคีรีขันธ์,เมืองประจวบคีรีขันธ์,0.180,0.068
ประจวบคีรีขันธ์,ทับสะแก,0.195,0.072
ประจวบคีรีขันธ์,บางสะพาน,0.210,0.076
ประจวบคีรีขันธ์,หัวหิน,0.175,0.066
ชุมพร,เมืองชุมพร,0.160,0.062
ชุมพร,ท่าแซะ,0.175,0.066
ระนอง,เมืองระนอง,0.220,0.082
ระนอง,กระบุรี,0.250,0.090
พังงา,เมืองพังงา,0.210,0.078
พังงา,ตะกั่วป่า,0.250,0.090
พังงา,เกาะยาว,0.200,0.075
ภูเก็ต,เมืองภูเก็ต,0.188,0.068
ภูเก็ต,กะทู้,0.192,0.070
ภูเก็ต,ถลาง,0.195,0.072
กระบี่,เมืองกระบี่,0.178,0.066
กระบี่,อ่าวลึก,0.185,0.068
กระบี่,คลองท่อม,0.170,0.064
ตรัง,เมืองตรัง,0.155,0.060
ตรัง,ปะเหลียน,0.160,0.062
ตรัง,หาดสำราญ,0.165,0.063
สตูล,เมืองสตูล,0.148,0.058
สตูล,ละงู,0.152,0.059
สงขลา,เมืองสงขลา,0.085,0.038
สงขลา,หาดใหญ่,0.088,0.039
สงขลา,สะเดา,0.090,0.040
สงขลา,รัตภูมิ,0.086,0.038
กรุงเทพมหานคร,ทุกเขต (ดินเหนียวอ่อน),0.0,0.0"""

@st.cache_data
def load_seismic_db() -> pd.DataFrame:
    return pd.read_csv(io.StringIO(SEISMIC_CSV))

DF_SEISMIC = load_seismic_db()

# --------------------------------------------------------------------------
# 1.5  ตารางตัวคูณขยายอิทธิพลชั้นดิน Fa / Fv
#      อ้างอิง: มยผ. 1302-61 ตารางที่ 1.4-1 และ 1.4-2 (interpolate เชิงเส้นตามมาตรฐาน)
# --------------------------------------------------------------------------
FA_TABLE = {
    'Ss_keys': [0.25, 0.50, 0.75, 1.00, 1.25],
    'A': [0.8]*5, 'B': [1.0]*5,
    'C': [1.2, 1.2, 1.1, 1.0, 1.0],
    'D': [1.6, 1.4, 1.2, 1.1, 1.0],
    'E': [2.5, 1.7, 1.2, 0.9, 0.9],
}
FV_TABLE = {
    'S1_keys': [0.10, 0.20, 0.30, 0.40, 0.50],
    'A': [0.8]*5, 'B': [1.0]*5,
    'C': [1.7, 1.6, 1.5, 1.4, 1.3],
    'D': [2.4, 2.0, 1.8, 1.6, 1.5],
    'E': [3.5, 3.2, 2.8, 2.4, 2.4],
}

# --------------------------------------------------------------------------
# 1.6  ระบบโครงสร้างต้านทานแรงด้านข้าง R / Ω0 / Cd
#      อ้างอิง: มยผ. 1302-61 ตารางที่ 2.3-1 (ค่าตัวประกอบสำหรับระบบโครงสร้างแต่ละชนิด)
# --------------------------------------------------------------------------
SEISMIC_SYSTEM_DB = {
    "โครงต้านแรงดัด คสล. ความเหนียวพิเศษ (SMF)":        {"R": 8.0, "Omega": 3.0, "Cd": 5.5, "Ct": 0.0466, "x": 0.9},
    "โครงต้านแรงดัด คสล. ความเหนียวปานกลาง (IMF)":     {"R": 5.0, "Omega": 3.0, "Cd": 4.5, "Ct": 0.0466, "x": 0.9},
    "โครงต้านแรงดัด คสล. ความเหนียวธรรมดา (OMF)":      {"R": 3.0, "Omega": 3.0, "Cd": 2.5, "Ct": 0.0466, "x": 0.9},
    "โครงต้านแรงดัดเหล็ก ความเหนียวพิเศษ (Steel SMF)":   {"R": 8.0, "Omega": 3.0, "Cd": 5.5, "Ct": 0.0724, "x": 0.8},
    "กำแพงรับแรงเฉือน คสล. แบบพิเศษ (Special SW)":      {"R": 6.0, "Omega": 2.5, "Cd": 5.0, "Ct": 0.0488, "x": 0.75},
    "กำแพงรับแรงเฉือน คสล. แบบธรรมดา (Ordinary SW)":    {"R": 5.0, "Omega": 2.5, "Cd": 4.5, "Ct": 0.0488, "x": 0.75},
}

# เหล็กเสริมมาตรฐาน มอก. (ใช้ใน Engine มยผ.1501) — fy หน่วย ksc (kg/cm²)
REBAR_GRADE_DB = {"SR24 (fy=2400 ksc)": 2400, "SD30 (fy=3000 ksc)": 3000,
                  "SD40 (fy=4000 ksc)": 4000, "SD50 (fy=5000 ksc)": 5000}

# เหล็กรูปพรรณ (ใช้ใน Engine มยผ.1503 วิธี ASD)
STEEL_GRADE_DB = {"SS400 / SM400 (Fy=2400 ksc)": 2400, "SM490 (Fy=3300 ksc)": 3300,
                  "SM520 (Fy=3600 ksc)": 3600}


# ==========================================================================
# SECTION 2 : CALCULATION ENGINES  (LAYER 2 — pure functions)
#   ทุกฟังก์ชันรับค่า → คืน dict ผลลัพธ์ + log (list ของบรรทัดคำนวณ)
#   ไม่มีการเรียก Streamlit ภายใน engine เพื่อให้ unit-test ได้ง่าย
# ==========================================================================

# ───────────────────────── ENGINE A : LOADS (มยผ.1101–1106) ─────────────────────────
def engine_loads(occupancy: str, user_LL: float, slab_t_cm: float, finish_load: float,
                 wall_load: float, mep_load: float, floor_area: float) -> dict:
    """
    คำนวณน้ำหนักบรรทุกคงที่และจร พร้อม Load Combinations
    อ้างอิง:
      • DL วัสดุ           — มยผ.1101 ตารางหน่วยน้ำหนักวัสดุ
      • LL ขั้นต่ำ          — มยผ.1101 + กฎกระทรวงฉบับที่ 6 ข้อ 15
      • Load Combinations — วิธีกำลัง (USD): U = 1.4D, U = 1.4D + 1.7L
                            (ตาม มยผ.1501 / ว.ส.ท. 1008) และชุดรวมแรงด้านข้าง
    """
    log = []
    LL_min = LIVE_LOAD_DB[occupancy]

    # --- Dead Load ---
    # น้ำหนักพื้น คสล. = ความหนา(m) × 2400 kg/m³   (มยผ.1101: คสล. = 2400 kg/m³)
    slab_DL = (slab_t_cm / 100.0) * DEAD_LOAD_MATERIAL_DB["คอนกรีตเสริมเหล็ก"]["value"]
    DL_total = slab_DL + finish_load + wall_load + mep_load      # kg/m²
    log.append(f"[1101] DL พื้น คสล. t={slab_t_cm:.0f} ซม. = {slab_t_cm/100:.2f}×2400 = {slab_DL:.0f} kg/m²")
    log.append(f"[1101] DL รวม = {slab_DL:.0f}+{finish_load:.0f}(ผิว)+{wall_load:.0f}(ผนัง)+{mep_load:.0f}(MEP) = {DL_total:.0f} kg/m²")
    log.append(f"[1101] LL ใช้ออกแบบ = {user_LL:.0f} kg/m² (ขั้นต่ำตามกฎหมาย {LL_min} kg/m²)")

    # --- Load Combinations (USD ตาม มยผ.1501) ---
    U1 = 1.4 * DL_total                          # U = 1.4D            (กรณี D เด่น)
    U2 = 1.4 * DL_total + 1.7 * user_LL          # U = 1.4D + 1.7L     (กรณีพื้นฐาน)
    U_gov = max(U1, U2)
    log.append(f"[1501] U1 = 1.4D = 1.4×{DL_total:.0f} = {U1:.0f} kg/m²")
    log.append(f"[1501] U2 = 1.4D+1.7L = 1.4×{DL_total:.0f}+1.7×{user_LL:.0f} = {U2:.0f} kg/m²")
    log.append(f"[1501] Governing wu = {U_gov:.0f} kg/m²")

    return {
        "LL_min": LL_min, "DL_total": DL_total, "slab_DL": slab_DL,
        "U1": U1, "U2": U2, "U_gov": U_gov,
        "service_total": DL_total + user_LL,
        "factored_floor_force": U_gov * floor_area / 1000.0,   # ตันต่อชั้น (ถ้ากรอกพื้นที่)
        "log": log,
    }


# ───────────────────────── ENGINE B : WIND (มยผ.1311-50) ─────────────────────────
def engine_wind(V50: float, TF: float, Iw: float, terrain: str,
                B_width: float, D_depth: float, H: float, n_strips: int = 12) -> dict:
    """
    วิธีการอย่างง่าย (Static Procedure) ตาม มยผ.1311-50
      หน่วยแรงลม:  p = Iw · q · Ce · Cg · Cp                 [สมการ (2-1)]
      q = (1/2)·ρ·V²  โดย ρ=1.25 kg/m³  →  q = 0.625·V² (Pa)  [หัวข้อ 2.2]
      Ce ภูมิประเทศ A (โล่ง):     Ce = (z/10)^0.2  ≥ 0.9        [หัวข้อ 2.3]
      Ce ภูมิประเทศ B (ชานเมือง): Ce = 0.7(z/12)^0.3 ≥ 0.7
      Cg (โครงสร้างหลัก, สถิต)  = 2.0                          [หัวข้อ 2.4]
      Cp ด้านต้นลม = +0.8 / ด้านท้ายลม = −0.5                  [ตาราง Cp อาคารทรงสี่เหลี่ยม]
    แรงเฉือนฐานคำนวณโดยแบ่งความสูงเป็นแถบ (strips) แล้วอินทิเกรตเชิงเลข
    """
    log = []
    q_ref = 0.625 * (V50 ** 2) * TF      # Pa (N/m²) — รวม Typhoon Factor สำหรับโซน 4
    log.append(f"[1311] q = 0.625·V² ×TF = 0.625×{V50:.0f}²×{TF:.2f} = {q_ref:.1f} N/m²")

    Cg, Cp_w, Cp_l = 2.0, 0.8, -0.5
    log.append(f"[1311] Cg=2.0 (โครงสร้างหลัก), Cp ต้นลม=+0.8, ท้ายลม=−0.5")

    def Ce_of(z):
        # มยผ.1311-50: Ce ขึ้นกับสภาพภูมิประเทศ (Exposure)
        if terrain.startswith("A"):
            return max((max(z, 1e-6) / 10.0) ** 0.2, 0.9)
        return max(0.7 * (max(z, 1e-6) / 12.0) ** 0.3, 0.7)

    # ── อินทิเกรตแรงลมทีละแถบความสูง ──
    z_edges = np.linspace(0, H, n_strips + 1)
    rows, V_base, M_otm = [], 0.0, 0.0
    for i in range(n_strips):
        z_mid = 0.5 * (z_edges[i] + z_edges[i + 1])
        h_strip = z_edges[i + 1] - z_edges[i]
        Ce = Ce_of(z_mid)
        # ความดันสุทธิ = (CpCe)ต้นลม − (CpCe)ท้ายลม ; Ce ท้ายลมใช้ที่ครึ่งความสูง H/2 ตามมาตรฐาน
        Ce_lee = Ce_of(H / 2.0)
        p_net = Iw * q_ref * Cg * (Cp_w * Ce - Cp_l * Ce_lee)     # N/m² (Cp_l ติดลบ → บวกเพิ่ม)
        F_strip = p_net * B_width * h_strip / 9806.65             # แปลง N → ตัน (1 ตัน = 9806.65 N)
        V_base += F_strip
        M_otm += F_strip * z_mid
        rows.append({"z (ม.)": z_mid, "Ce": Ce, "p (N/m²)": p_net, "F (ตัน)": F_strip})

    log.append(f"[1311] Ce(top z={H:.1f}ม.) = {Ce_of(H):.3f} ({terrain})")
    log.append(f"[1311] แรงเฉือนฐานจากลม V = Σp·B·Δh = {V_base:.2f} ตัน")
    log.append(f"[1311] โมเมนต์พลิกคว่ำ M = ΣF·z = {M_otm:.2f} ตัน-ม.")

    return {"q_ref": q_ref, "V_base": V_base, "M_otm": M_otm,
            "profile": pd.DataFrame(rows), "Ce_top": Ce_of(H), "log": log}


# ───────────────────────── ENGINE C : SEISMIC (มยผ.1301/1302-61) ─────────────────────────
def get_site_coefficients(site_class: str, Ss: float, S1: float) -> tuple:
    """Fa, Fv โดย linear interpolation ตามตาราง มยผ.1302-61 (clamp ปลายตาราง)"""
    if site_class == 'F':
        return 0.0, 0.0
    f_fa = interp1d(FA_TABLE['Ss_keys'], FA_TABLE[site_class], kind='linear',
                    fill_value=(FA_TABLE[site_class][0], FA_TABLE[site_class][-1]), bounds_error=False)
    f_fv = interp1d(FV_TABLE['S1_keys'], FV_TABLE[site_class], kind='linear',
                    fill_value=(FV_TABLE[site_class][0], FV_TABLE[site_class][-1]), bounds_error=False)
    return max(float(f_fa(Ss)), 0.0), max(float(f_fv(S1)), 0.0)


def evaluate_sdc(SDS: float, SD1: float, Ie: float) -> tuple:
    """
    ประเภทการออกแบบต้านทานแผ่นดินไหว (ก/ข/ค/ง)
    อ้างอิง: มยผ.1302-61 ตารางที่ 1.5-1 (จาก SDS) และ 1.5-2 (จาก SD1)
    เลือกค่าที่เข้มงวดกว่าระหว่างสองตาราง; อาคารสำคัญมาก (Ie≥1.5) เลื่อนขึ้นหนึ่งขั้น
    """
    ess = (Ie >= 1.5)
    if SDS < 0.167:  a = 'ก'
    elif SDS < 0.33: a = 'ค' if ess else 'ข'
    elif SDS < 0.50: a = 'ง' if ess else 'ค'
    else:            a = 'ง'
    if SD1 < 0.067:  b = 'ก'
    elif SD1 < 0.133: b = 'ค' if ess else 'ข'
    elif SD1 < 0.20:  b = 'ง' if ess else 'ค'
    else:             b = 'ง'
    order = {'ก': 1, 'ข': 2, 'ค': 3, 'ง': 4}
    final = a if order[a] >= order[b] else b
    return final, a, b


def engine_seismic(Ss: float, S1: float, site_class: str, Ie: float,
                   system_key: str, hn: float, story_df: pd.DataFrame) -> dict:
    """
    วิธีแรงสถิตเทียบเท่า (Equivalent Static) ตาม มยผ.1302-61 บทที่ 3
      SDS = (2/3)·Fa·Ss ; SD1 = (2/3)·Fv·S1                 [สมการ 1.4-5, 1.4-6]
      Ta  = Ct·hn^x                                          [สมการ 3.3-2 + ตาราง]
      Cs  = SDS/(R/Ie) ; Cs,max = SD1/(T·R/Ie) ;
      Cs,min = 0.01 (และ 0.5·S1/(R/Ie) เมื่อ S1 ≥ 0.6g)        [หัวข้อ 3.2]
      V   = Cs·W ; Fx = Cvx·V ; Cvx = wx·hx^k / Σwi·hi^k      [สมการ 3.4-1, 3.4-2]
      k   = 1 (T≤0.5s), 2 (T≥2.5s), interpolate ระหว่างกลาง
    """
    log = []
    sysd = SEISMIC_SYSTEM_DB[system_key]
    R, Omega0, Cd, Ct, x_exp = sysd["R"], sysd["Omega"], sysd["Cd"], sysd["Ct"], sysd["x"]

    Fa, Fv = get_site_coefficients(site_class, Ss, S1)
    SDS = (2/3) * Fa * Ss
    SD1 = (2/3) * Fv * S1
    log.append(f"[1302] Fa={Fa:.3f}, Fv={Fv:.3f} (ชั้นดิน {site_class}, interpolation)")
    log.append(f"[1302] SDS=(2/3)·{Fa:.3f}×{Ss:.3f}={SDS:.3f} g ; SD1=(2/3)·{Fv:.3f}×{S1:.3f}={SD1:.3f} g")

    T0 = 0.2 * SD1 / SDS if SDS > 0 else 0.0
    TS = SD1 / SDS if SDS > 0 else 0.0
    Ta = Ct * (hn ** x_exp)
    log.append(f"[1302] Ta = {Ct}×{hn:.1f}^{x_exp} = {Ta:.3f} s ; T0={T0:.3f}, TS={TS:.3f} s")

    sdc, sdc_a, sdc_b = evaluate_sdc(SDS, SD1, Ie)
    log.append(f"[1302] SDC: จาก SDS→'{sdc_a}', จาก SD1→'{sdc_b}' ⇒ ควบคุมด้วย '{sdc}'")

    # --- สัมประสิทธิ์แรงเฉือนฐาน Cs ---
    Cs_calc = SDS / (R / Ie)
    Cs_max = SD1 / (Ta * (R / Ie)) if Ta > 0 else Cs_calc
    Cs_min = 0.01
    if S1 >= 0.6:                                    # ข้อกำหนดเพิ่มเติมพื้นที่ใกล้รอยเลื่อน
        Cs_min = max(Cs_min, 0.5 * S1 / (R / Ie))
    Cs = max(Cs_min, min(Cs_calc, Cs_max))
    log.append(f"[1302] Cs=SDS/(R/Ie)={SDS:.3f}/({R}/{Ie})={Cs_calc:.4f} ; max={Cs_max:.4f} ; min={Cs_min:.4f}")
    log.append(f"[1302] ⇒ Cs ใช้ออกแบบ = {Cs:.4f}")

    # --- กระจายแรงเข้าชั้น (เรียงจากชั้นบนสุด→ล่างสุด ตามตารางผู้ใช้) ---
    hx = story_df["hx"].to_numpy(float)
    wx = story_df["wx"].to_numpy(float)
    W = float(wx.sum())
    V = Cs * W
    k = 1.0 if Ta <= 0.5 else (2.0 if Ta >= 2.5 else 1.0 + (Ta - 0.5) / 2.0)
    whk = wx * hx ** k
    Cvx = whk / whk.sum() if whk.sum() > 0 else np.zeros_like(whk)
    Fx = Cvx * V
    Vx = np.cumsum(Fx)                              # แรงเฉือนสะสมจากบนลงล่าง
    Mx = np.array([sum(Fx[j] * max(0.0, hx[j] - hx[i]) for j in range(i + 1))
                   for i in range(len(hx))])
    log.append(f"[1302] W={W:,.1f} ตัน ⇒ V=Cs·W={Cs:.4f}×{W:,.1f}={V:,.2f} ตัน ; k={k:.3f}")
    log.append(f"[1302] โมเมนต์พลิกคว่ำที่ฐาน = {Mx[-1] if len(Mx) else 0:,.2f} ตัน-ม.")

    return {"Fa": Fa, "Fv": Fv, "SDS": SDS, "SD1": SD1, "T0": T0, "TS": TS, "Ta": Ta,
            "sdc": sdc, "sdc_a": sdc_a, "sdc_b": sdc_b,
            "R": R, "Omega0": Omega0, "Cd": Cd, "Cs": Cs, "Cs_calc": Cs_calc,
            "Cs_max": Cs_max, "Cs_min": Cs_min, "W": W, "V": V, "k": k,
            "Fx": Fx, "Vx": Vx, "Mx": Mx, "Cvx": Cvx, "log": log}


def engine_drift(delta_e_cm: np.ndarray, hx: np.ndarray, Cd: float, Ie: float) -> dict:
    """
    ตรวจสอบการเคลื่อนตัวสัมพัทธ์ระหว่างชั้น (Story Drift)
    อ้างอิง: มยผ.1302-61 หัวข้อ 3.5  δx = Cd·δe / Ie
    เกณฑ์ยอมให้: Δa = 0.020·hsx (อาคารทั่วไป) / 0.015 (สำคัญสูง) / 0.010 (สำคัญสูงมาก)
    """
    limit = 0.010 if Ie >= 1.5 else (0.015 if Ie >= 1.25 else 0.020)
    delta_x = Cd * delta_e_cm / Ie
    n = len(hx)
    h_net = np.array([hx[i] - hx[i + 1] if i < n - 1 else hx[i] for i in range(n)])
    d_rel = np.array([delta_x[i] - delta_x[i + 1] if i < n - 1 else delta_x[i] for i in range(n)])
    ratio = np.where(h_net > 0, d_rel / (h_net * 100.0), 0.0)   # ซม./ซม.
    status = np.where(ratio <= limit, "PASS", "FAIL")
    return {"limit": limit, "delta_x": delta_x, "h_net": h_net,
            "ratio": ratio, "status": status}


# ───────────────────────── ENGINE D : RC DESIGN (มยผ.1501) — วิธีกำลัง SDM ─────────────────────────
def engine_rc_beam(Mu_tm: float, Vu_t: float, b_cm: float, h_cm: float,
                   cover_cm: float, fc: float, fy: float, fys: float) -> dict:
    """
    ออกแบบคานรับโมเมนต์ดัด (เหล็กเสริมรับแรงดึงอย่างเดียว) + เหล็กปลอกรับแรงเฉือน
    อ้างอิง มยผ.1501 (สอดคล้อง ACI 318 / ว.ส.ท. 1008) หน่วย: ksc, cm, ตัน-ม.
      • φ ดัด = 0.90 ; φ เฉือน = 0.85
      • Rn = Mu/(φ·b·d²) ; ρ = 0.85fc'/fy·(1−√(1−2Rn/0.85fc'))
      • ρmin = max(0.8√fc'/fy , 14/fy)   [มยผ.1501: เหล็กเสริมขั้นต่ำ]
      • ρmax = 0.75·ρb (ควบคุมการวิบัติแบบเหนียว)
      • Vc = 0.53·√fc'·b·d  ;  Vs = Av·fy·d/s  ;  Vs,max = 2.1√fc'·b·d
    """
    log, warns = [], []
    d = h_cm - cover_cm                                  # ความลึกประสิทธิผล
    phi_b, phi_v = 0.90, 0.85
    Mu_kgcm = Mu_tm * 1000.0 * 100.0                     # ตัน-ม. → kg·cm

    Rn = Mu_kgcm / (phi_b * b_cm * d ** 2)               # ksc
    inside = 1.0 - 2.0 * Rn / (0.85 * fc)
    if inside < 0:                                       # หน้าตัดเล็กเกินรับโมเมนต์ → ต้องขยายหน้าตัด
        return {"ok": False, "msg": f"หน้าตัด {b_cm:.0f}×{h_cm:.0f} ซม. เล็กเกินไปสำหรับ Mu={Mu_tm:.1f} ตัน-ม. (Rn={Rn:.1f} ksc) — เพิ่มขนาดหน้าตัดหรือใช้เหล็กรับแรงอัด", "log": log}
    rho = (0.85 * fc / fy) * (1.0 - np.sqrt(inside))

    # ขีดจำกัดอัตราส่วนเหล็กเสริมตาม มยผ.1501
    beta1 = 0.85 if fc <= 280 else max(0.65, 0.85 - 0.05 * (fc - 280) / 70.0)
    rho_b = 0.85 * beta1 * (fc / fy) * (6120.0 / (6120.0 + fy))
    rho_min = max(0.8 * np.sqrt(fc) / fy, 14.0 / fy)
    rho_max = 0.75 * rho_b
    rho_use = max(rho, rho_min)
    log.append(f"[1501] d = {h_cm:.0f}−{cover_cm:.0f} = {d:.1f} ซม. ; Rn = {Rn:.2f} ksc")
    log.append(f"[1501] ρ คำนวณ={rho:.5f}, ρmin={rho_min:.5f}, ρmax={rho_max:.5f} (β1={beta1:.2f})")

    if rho > rho_max:
        warns.append(f"ρ ({rho:.5f}) > ρmax ({rho_max:.5f}) — หน้าตัดวิบัติแบบเปราะ ต้องขยายหน้าตัด")
    As = rho_use * b_cm * d
    log.append(f"[1501] As = ρ·b·d = {rho_use:.5f}×{b_cm:.0f}×{d:.1f} = {As:.2f} ซม.²")

    # แนะนำจำนวนเหล็ก DB20/DB25
    n_db20 = int(np.ceil(As / 3.14))
    n_db25 = int(np.ceil(As / 4.91))

    # --- แรงเฉือน ---
    Vu_kg = Vu_t * 1000.0
    Vc = 0.53 * np.sqrt(fc) * b_cm * d                   # kg
    Vs_req = max(Vu_kg / phi_v - Vc, 0.0)
    Vs_max = 2.1 * np.sqrt(fc) * b_cm * d
    log.append(f"[1501] Vc = 0.53√{fc:.0f}×{b_cm:.0f}×{d:.1f} = {Vc:,.0f} kg ; Vs ต้องการ = {Vs_req:,.0f} kg")
    if Vs_req > Vs_max:
        warns.append(f"Vs ({Vs_req:,.0f}) > Vs,max ({Vs_max:,.0f} kg) — หน้าตัดเล็กเกินไปสำหรับแรงเฉือน")
    # ระยะเรียงปลอก RB9 สองขา (Av = 2×0.636 = 1.27 ซม.²)
    Av = 1.27
    if Vs_req > 0:
        s_req = Av * fys * d / Vs_req
    else:
        s_req = d / 2.0                                  # ปลอกขั้นต่ำเมื่อ Vu > φVc/2
    s_max = min(d / 2.0, 60.0) if Vs_req <= 1.1 * np.sqrt(fc) * b_cm * d else min(d / 4.0, 30.0)
    s_use = min(s_req, s_max)
    log.append(f"[1501] ปลอก RB9@{s_use:.0f} ซม. (s_req={s_req:.1f}, s_max={s_max:.1f})")

    return {"ok": True, "d": d, "Rn": Rn, "rho": rho_use, "rho_min": rho_min,
            "rho_max": rho_max, "As": As, "n_db20": n_db20, "n_db25": n_db25,
            "Vc": Vc, "Vs_req": Vs_req, "s_use": s_use, "warns": warns, "log": log}


def engine_rc_column(Pu_t: float, b_cm: float, h_cm: float, fc: float, fy: float,
                     rho_g: float) -> dict:
    """
    เสาสั้นปลอกเดี่ยวรับแรงตามแนวแกน (ไม่มีโมเมนต์ — ตรวจสอบเบื้องต้น)
    อ้างอิง มยผ.1501:  φPn(max) = 0.80·φ·[0.85·fc'·(Ag−Ast) + fy·Ast] ; φ(tied) = 0.65
    """
    log = []
    phi = 0.65
    Ag = b_cm * h_cm
    Ast = rho_g * Ag
    Pn_max = 0.80 * (0.85 * fc * (Ag - Ast) + fy * Ast)      # kg
    phiPn = phi * Pn_max / 1000.0                            # ตัน
    ratio = (Pu_t / phiPn) if phiPn > 0 else 9.99
    log.append(f"[1501] Ag={Ag:.0f} ซม.², Ast=ρg·Ag={rho_g:.3f}×{Ag:.0f}={Ast:.1f} ซม.²")
    log.append(f"[1501] φPn = 0.65×0.80×[0.85×{fc:.0f}×({Ag:.0f}−{Ast:.1f})+{fy:.0f}×{Ast:.1f}] = {phiPn:,.1f} ตัน")
    log.append(f"[1501] D/C ratio = {Pu_t:,.1f}/{phiPn:,.1f} = {ratio:.2f} → {'✅ PASS' if ratio<=1.0 else '❌ FAIL'}")
    return {"Ag": Ag, "Ast": Ast, "phiPn": phiPn, "ratio": ratio,
            "ok": ratio <= 1.0, "log": log}


# ───────────────────────── ENGINE E : STEEL DESIGN (มยผ.1503 — ASD) ─────────────────────────
def engine_steel_beam(M_tm: float, V_t: float, Fy: float, Sx_cm3: float,
                      Aw_cm2: float, compact: bool) -> dict:
    """
    ตรวจสอบคานเหล็กรูปพรรณวิธีหน่วยแรงที่ยอมให้ (ASD)
    อ้างอิง มยผ.1503:
      • หน้าตัด compact + ค้ำยันเพียงพอ:  Fb = 0.66·Fy   มิฉะนั้น Fb = 0.60·Fy
      • แรงเฉือน:                        Fv = 0.40·Fy
      fb = M/Sx ≤ Fb ; fv = V/Aw ≤ Fv
    """
    log = []
    Fb = (0.66 if compact else 0.60) * Fy
    Fv = 0.40 * Fy
    fb = (M_tm * 1000.0 * 100.0) / Sx_cm3 if Sx_cm3 > 0 else 9e9   # ksc
    fv = (V_t * 1000.0) / Aw_cm2 if Aw_cm2 > 0 else 9e9
    rb, rv = fb / Fb, fv / Fv
    log.append(f"[1503] Fb = {'0.66' if compact else '0.60'}·Fy = {Fb:,.0f} ksc ; Fv = 0.40·Fy = {Fv:,.0f} ksc")
    log.append(f"[1503] fb = M/Sx = {fb:,.1f} ksc (ratio {rb:.2f}) ; fv = V/Aw = {fv:,.1f} ksc (ratio {rv:.2f})")
    return {"Fb": Fb, "Fv": Fv, "fb": fb, "fv": fv,
            "ok_b": rb <= 1.0, "ok_v": rv <= 1.0, "rb": rb, "rv": rv, "log": log}


# ==========================================================================
# SECTION 3 : VALIDATION MODULE  (กฎหมาย/ขั้นต่ำตามมาตรฐาน)
# ==========================================================================
def validate_inputs(occupancy, user_LL, hn, site_class, fc, sdc, system_key) -> tuple:
    """
    คืน (errors, warnings)
    errors   = ผิดข้อบังคับ → หยุดการคำนวณส่วนที่เกี่ยวข้อง
    warnings = เข้าข่ายต้องพิจารณาเพิ่ม → แสดงเตือนแต่คำนวณต่อได้
    """
    errors, warns = [], []

    # (ก) น้ำหนักบรรทุกจรต่ำกว่าขั้นต่ำตามกฎกระทรวง — ผิดกฎหมาย
    LL_min = LIVE_LOAD_DB[occupancy]
    if user_LL < LL_min:
        errors.append(f"🛑 [มยผ.1101] LL ที่กรอก ({user_LL:.0f} kg/m²) ต่ำกว่าขั้นต่ำตามกฎหมาย "
                      f"({LL_min} kg/m²) สำหรับ '{occupancy}' — ต้องแก้ไขก่อนคำนวณต่อ")

    # (ข) ชั้นดิน F ต้องวิเคราะห์เฉพาะพื้นที่
    if site_class == 'F':
        errors.append("🛑 [มยผ.1302] ชั้นดินประเภท F ต้องทำ Site-Specific Response Analysis เท่านั้น")

    # (ค) กำลังคอนกรีตต่ำกว่าขั้นต่ำที่ยอมรับในงานโครงสร้าง
    if fc < 180:
        errors.append(f"🛑 [มยผ.1501] fc' = {fc:.0f} ksc ต่ำกว่าขั้นต่ำ 180 ksc สำหรับงานโครงสร้าง คสล.")

    # (ง) ข้อจำกัดความสูงของวิธีแรงสถิตเทียบเท่า — SDC ง โครงสร้างต้องสม่ำเสมอ + ความสูงจำกัด
    if sdc == 'ง':
        if "OMF" in system_key or "ธรรมดา" in system_key:
            errors.append("🛑 [มยผ.1302 ตาราง 2.3-1] ระบบความเหนียวธรรมดา (OMF/Ordinary) "
                          "ห้ามใช้ในพื้นที่ SDC 'ง' — ต้องเปลี่ยนเป็นระบบความเหนียวปานกลาง/พิเศษ")
        if hn > 23.0 and "IMF" in system_key:
            warns.append(f"⚠️ [มยผ.1302] SDC 'ง' + IMF สูง {hn:.0f} ม. (>23 ม.) — ตรวจสอบข้อจำกัดความสูง "
                         "ของระบบในตาราง 2.3-1 และพิจารณาวิธีพลศาสตร์")
        warns.append("⚠️ SDC 'ง' — วิธีแรงสถิตเทียบเท่าใช้ได้เฉพาะอาคารรูปทรงสม่ำเสมอ (Regular) เท่านั้น "
                     "หากมี irregularity ต้องใช้ Response Spectrum / Dynamic Analysis")
    elif sdc == 'ค':
        warns.append("⚠️ SDC 'ค' — ต้องจัดรายละเอียดความเหนียวอย่างน้อยระดับปานกลาง (Intermediate)")

    if hn > 90:
        warns.append(f"⚠️ อาคารสูง {hn:.0f} ม. (>90 ม.) — มยผ.1311-50 แนะนำวิธี Detailed/Wind Tunnel "
                     "สำหรับการตอบสนองพลศาสตร์จากลม")
    return errors, warns


# ==========================================================================
# SECTION 4 : UI — 3-PANEL LAYOUT  (LAYER 3)
#   ┌──────────────┬───────────────────────┬─────────────────────┐
#   │  LEFT        │  CENTER               │  RIGHT              │
#   │  Input Panel │  Live Process Log     │  Results & Summary  │
#   └──────────────┴───────────────────────┴─────────────────────┘
# ==========================================================================
st.markdown("---")
col_in, col_log, col_res = st.columns([1.00, 1.25, 1.05], gap="medium")

# ════════════════════════ LEFT : INPUT PANEL ════════════════════════
with col_in:
    st.markdown("### 📥 Input Panel")

    # ---- 4.1 ข้อมูลทั่วไปของโครงการ ----
    with st.expander("1️⃣ ข้อมูลโครงการ / รูปทรงอาคาร", expanded=True):
        project_name = st.text_input("ชื่อโครงการ", "อาคารสำนักงาน 4 ชั้น")
        B_width  = st.number_input("ความกว้างด้านรับลม B (ม.)", 1.0, 200.0, 20.0, 1.0)
        D_depth  = st.number_input("ความลึกอาคาร D (ม.)", 1.0, 200.0, 15.0, 1.0)
        hn       = st.number_input("ความสูงอาคาร hn (ม.)", 1.0, 300.0, 14.0, 0.5)
        floor_area = st.number_input("พื้นที่ต่อชั้น (ม.²)", 1.0, 50000.0, 300.0, 10.0)

    # ---- 4.2 น้ำหนักบรรทุก (มยผ.1101-1106) ----
    with st.expander("2️⃣ น้ำหนักบรรทุก (มยผ.1101-1106)", expanded=True):
        occupancy = st.selectbox("ประเภทการใช้งานอาคาร", list(LIVE_LOAD_DB.keys()), index=4)
        st.caption(f"ขั้นต่ำตามกฎหมาย: **{LIVE_LOAD_DB[occupancy]} kg/m²**")
        user_LL  = st.number_input("Live Load ใช้ออกแบบ (kg/m²)", 0.0, 5000.0,
                                   float(LIVE_LOAD_DB[occupancy]), 10.0)
        slab_t   = st.number_input("ความหนาพื้น คสล. (ซม.)", 8.0, 50.0, 15.0, 1.0)
        finish_w = st.number_input("วัสดุผิวพื้น (kg/m²)", 0.0, 500.0, 110.0, 10.0)
        wall_w   = st.number_input("ผนังเฉลี่ยต่อพื้นที่ (kg/m²)", 0.0, 800.0, 100.0, 10.0)
        mep_w    = st.number_input("ฝ้า+งานระบบ (kg/m²)", 0.0, 300.0, 50.0, 10.0)

    # ---- 4.3 แรงลม (มยผ.1311-50) ----
    with st.expander("3️⃣ แรงลม (มยผ.1311-50)"):
        wind_zone = st.selectbox("โซนความเร็วลม", list(WIND_ZONE_DB.keys()))
        terrain   = st.selectbox("สภาพภูมิประเทศ (Exposure)",
                                 ["A — โล่ง/ชายฝั่ง (Open)", "B — ชานเมือง/ป่าโปร่ง (Rough)"])
        wind_imp  = st.selectbox("ความสำคัญอาคาร (แรงลม)", list(WIND_IMPORTANCE_DB.keys()), index=1)

    # ---- 4.4 แรงแผ่นดินไหว (มยผ.1301/1302-61) ----
    with st.expander("4️⃣ แผ่นดินไหว (มยผ.1302-61)", expanded=True):
        seismic_mode = st.radio("ที่มาค่า Ss/S1", ["ฐานข้อมูลรายอำเภอ", "กรอกเอง"], horizontal=True)
        if seismic_mode == "ฐานข้อมูลรายอำเภอ":
            prov = st.selectbox("จังหวัด", DF_SEISMIC["Province"].unique())
            dist = st.selectbox("อำเภอ", DF_SEISMIC[DF_SEISMIC["Province"] == prov]["District"])
            row = DF_SEISMIC[(DF_SEISMIC["Province"] == prov) & (DF_SEISMIC["District"] == dist)].iloc[0]
            Ss_in, S1_in = float(row["Ss"]), float(row["S1"])
            st.caption(f"Ss = {Ss_in:.3f} g | S1 = {S1_in:.3f} g")
        else:
            prov, dist = "กำหนดเอง", "กำหนดเอง"
            Ss_in = st.number_input("Ss (g)", 0.0, 3.0, 0.50, 0.01, format="%.3f")
            S1_in = st.number_input("S1 (g)", 0.0, 2.0, 0.20, 0.01, format="%.3f")
        site_class = st.selectbox("ประเภทชั้นดิน", ['A', 'B', 'C', 'D', 'E', 'F'], index=3)
        Ie = st.selectbox("ตัวคูณความสำคัญ Ie (แผ่นดินไหว)", [1.0, 1.25, 1.5], index=0)
        system_key = st.selectbox("ระบบต้านแรงด้านข้าง (ตาราง 2.3-1)", list(SEISMIC_SYSTEM_DB.keys()), index=1)

        st.markdown("**ตารางชั้นอาคาร** (บนสุด→ล่างสุด)")
        default_stories = pd.DataFrame({
            "Floor": ["ชั้น 4 (ดาดฟ้า)", "ชั้น 3", "ชั้น 2", "ชั้น 1"],
            "hx": [14.0, 10.5, 7.0, 3.5],
            "wx": [150.0, 200.0, 200.0, 220.0],
        })
        story_df = st.data_editor(
            default_stories, num_rows="dynamic", use_container_width=True, key="stories",
            column_config={
                "Floor": st.column_config.TextColumn("ชั้น", required=True),
                "hx": st.column_config.NumberColumn("hx (ม.)", min_value=0.0, format="%.2f", required=True),
                "wx": st.column_config.NumberColumn("wx (ตัน)", min_value=0.0, format="%.2f", required=True),
            })
        story_df = story_df.dropna(subset=["hx", "wx"]).copy()

    # ---- 4.5 ออกแบบหน้าตัด (มยผ.1501 / 1503) ----
    with st.expander("5️⃣ ออกแบบหน้าตัด (มยผ.1501/1503)"):
        design_member = st.radio("ชิ้นส่วนที่ต้องการออกแบบ",
                                 ["คาน คสล. (1501)", "เสา คสล. (1501)", "คานเหล็ก ASD (1503)"])
        fc  = st.number_input("fc' คอนกรีต (ksc)", 100.0, 800.0, 240.0, 10.0)
        fy  = REBAR_GRADE_DB[st.selectbox("ชั้นเหล็กเสริมหลัก", list(REBAR_GRADE_DB.keys()), index=2)]
        fys = REBAR_GRADE_DB[st.selectbox("ชั้นเหล็กปลอก", list(REBAR_GRADE_DB.keys()), index=0)]
        if design_member == "คาน คสล. (1501)":
            Mu_in = st.number_input("Mu (ตัน-ม.)", 0.1, 2000.0, 18.0, 1.0)
            Vu_in = st.number_input("Vu (ตัน)", 0.1, 2000.0, 12.0, 1.0)
            b_in  = st.number_input("ความกว้าง b (ซม.)", 10.0, 200.0, 25.0, 5.0)
            h_in  = st.number_input("ความลึก h (ซม.)", 20.0, 300.0, 50.0, 5.0)
            cov_in = st.number_input("ระยะหุ้มถึง C.G. เหล็ก (ซม.)", 3.0, 10.0, 6.0, 0.5)
        elif design_member == "เสา คสล. (1501)":
            Pu_in  = st.number_input("Pu (ตัน)", 1.0, 10000.0, 180.0, 10.0)
            cb_in  = st.number_input("ด้านกว้างเสา b (ซม.)", 15.0, 300.0, 40.0, 5.0)
            ch_in  = st.number_input("ด้านลึกเสา h (ซม.)", 15.0, 300.0, 40.0, 5.0)
            rho_in = st.slider("อัตราส่วนเหล็กยืน ρg", 0.01, 0.06, 0.02, 0.005)
        else:
            Fy_st = STEEL_GRADE_DB[st.selectbox("ชั้นเหล็กรูปพรรณ", list(STEEL_GRADE_DB.keys()))]
            Ms_in = st.number_input("M ใช้งาน (ตัน-ม.)", 0.1, 2000.0, 10.0, 1.0)
            Vs_in = st.number_input("V ใช้งาน (ตัน)", 0.1, 2000.0, 8.0, 1.0)
            Sx_in = st.number_input("Section Modulus Sx (ซม.³)", 10.0, 100000.0, 775.0, 10.0)
            Aw_in = st.number_input("พื้นที่เอว Aw = d·tw (ซม.²)", 1.0, 1000.0, 27.0, 1.0)
            compact_in = st.checkbox("หน้าตัด Compact + ค้ำยันด้านข้างเพียงพอ", value=True)

# ════════════════════════ RUN ALL ENGINES ════════════════════════
master_log: list = [f"════ DPT STRUCTURAL SUITE — PROCESS LOG ════",
                    f"โครงการ: {project_name} | วันที่คำนวณ: {datetime.now():%d/%m/%Y %H:%M}", ""]

# --- Loads ---
res_loads = engine_loads(occupancy, user_LL, slab_t, finish_w, wall_w, mep_w, floor_area)
master_log += ["── โมดูล 1: น้ำหนักบรรทุก (มยผ.1101-1106) ──"] + res_loads["log"] + [""]

# --- Wind ---
wz = WIND_ZONE_DB[wind_zone]
Iw = WIND_IMPORTANCE_DB[wind_imp]
res_wind = engine_wind(wz["V50"], wz["TF"], Iw, terrain, B_width, D_depth, hn)
master_log += ["── โมดูล 2: แรงลม (มยผ.1311-50) ──",
               f"[1311] โซน: {wind_zone.split('—')[0].strip()} | Iw={Iw}"] + res_wind["log"] + [""]

# --- Seismic (ข้าม กทม. ดินอ่อน ตามข้อกำหนดเดิม) ---
bkk_softsoil = (seismic_mode == "ฐานข้อมูลรายอำเภอ" and prov == "กรุงเทพมหานคร")
if not bkk_softsoil and site_class != 'F' and not story_df.empty:
    res_seis = engine_seismic(Ss_in, S1_in, site_class, Ie, system_key, hn, story_df)
    master_log += ["── โมดูล 3: แผ่นดินไหว (มยผ.1302-61) ──"] + res_seis["log"] + [""]
else:
    res_seis = None
    if bkk_softsoil:
        master_log += ["── โมดูล 3: แผ่นดินไหว ──",
                       "[1302] ⚠️ กทม. ดินเหนียวอ่อน — ต้องใช้ Response Spectrum เฉพาะตามภาคผนวก มยผ.1302", ""]

# --- Member design ---
master_log += ["── โมดูล 4: ออกแบบหน้าตัด ──"]
res_beam = res_col = res_steel = None
if design_member == "คาน คสล. (1501)":
    res_beam = engine_rc_beam(Mu_in, Vu_in, b_in, h_in, cov_in, fc, fy, fys)
    master_log += res_beam["log"] if res_beam.get("ok") else [f"[1501] ❌ {res_beam.get('msg','')}"]
elif design_member == "เสา คสล. (1501)":
    res_col = engine_rc_column(Pu_in, cb_in, ch_in, fc, fy, rho_in)
    master_log += res_col["log"]
else:
    res_steel = engine_steel_beam(Ms_in, Vs_in, Fy_st, Sx_in, Aw_in, compact_in)
    master_log += res_steel["log"]

# --- Validation (หลังทราบ SDC) ---
sdc_now = res_seis["sdc"] if res_seis else "-"
errors, warns = validate_inputs(occupancy, user_LL, hn, site_class, fc, sdc_now, system_key)

# ════════════════════════ CENTER : LIVE PROCESS LOG ════════════════════════
with col_log:
    st.markdown("### 🧮 Live Calculation Log")
    for e in errors:
        st.error(e)
    for w in warns:
        st.warning(w)
    st.code("\n".join(master_log), language="text")

# ════════════════════════ RIGHT : RESULTS & SUMMARY ════════════════════════
with col_res:
    st.markdown("### 📊 Results & Summary")

    # --- สรุปน้ำหนักบรรทุก ---
    st.markdown("**🧱 น้ำหนักบรรทุก (มยผ.1101)**")
    c1, c2 = st.columns(2)
    c1.metric("DL รวม", f"{res_loads['DL_total']:.0f} kg/m²")
    c2.metric("wu (1.4D+1.7L)", f"{res_loads['U_gov']:.0f} kg/m²")

    # --- สรุปแรงลม vs แผ่นดินไหว ---
    st.markdown("**🌪️ vs 🌏 แรงด้านข้างที่ฐาน**")
    c3, c4 = st.columns(2)
    c3.metric("Wind Base Shear", f"{res_wind['V_base']:,.1f} ตัน")
    if res_seis:
        c4.metric("Seismic Base Shear", f"{res_seis['V']:,.1f} ตัน")
        gov_lat = "แผ่นดินไหว" if res_seis['V'] > res_wind['V_base'] else "แรงลม"
        st.info(f"🏆 แรงด้านข้าง **{gov_lat}** เป็นตัวควบคุมการออกแบบ")
        c5, c6 = st.columns(2)
        c5.metric("SDC", f"ประเภท {res_seis['sdc']}")
        c6.metric("Cs", f"{res_seis['Cs']:.4f}")
        c7, c8 = st.columns(2)
        c7.metric("OTM แผ่นดินไหว", f"{res_seis['Mx'][-1]:,.0f} ตัน-ม." if len(res_seis['Mx']) else "—")
        c8.metric("OTM แรงลม", f"{res_wind['M_otm']:,.0f} ตัน-ม.")
    else:
        c4.metric("Seismic", "N/A")

    # --- สรุปหน้าตัด ---
    st.markdown("**🔩 ผลออกแบบหน้าตัด**")
    if res_beam is not None:
        if res_beam.get("ok"):
            st.success(f"คาน {b_in:.0f}×{h_in:.0f} ซม. → As = {res_beam['As']:.2f} ซม.² "
                       f"(≈ {res_beam['n_db25']}-DB25) | ปลอก RB9@{res_beam['s_use']:.0f} ซม.")
            for w in res_beam["warns"]:
                st.warning(w)
        else:
            st.error(res_beam.get("msg", "หน้าตัดไม่ผ่าน"))
    if res_col is not None:
        (st.success if res_col["ok"] else st.error)(
            f"เสา {cb_in:.0f}×{ch_in:.0f} ซม. → φPn = {res_col['phiPn']:,.1f} ตัน | "
            f"D/C = {res_col['ratio']:.2f} → {'PASS' if res_col['ok'] else 'FAIL'}")
    if res_steel is not None:
        ok_all = res_steel["ok_b"] and res_steel["ok_v"]
        (st.success if ok_all else st.error)(
            f"คานเหล็ก: fb/Fb = {res_steel['rb']:.2f}, fv/Fv = {res_steel['rv']:.2f} → "
            f"{'PASS' if ok_all else 'FAIL'}")


# ==========================================================================
# SECTION 5 : DETAIL TABS  (รายละเอียดแยกตามมาตรฐาน)
# ==========================================================================
st.markdown("---")
tabA, tabB, tabC, tabD, tabE = st.tabs([
    "📦 มยผ.1101 น้ำหนักบรรทุก", "🌪️ มยผ.1311 แรงลม",
    "🌏 มยผ.1302 แผ่นดินไหว", "📏 Story Drift", "📤 Export รายงาน",
])

# ───────── TAB A : LOADS DETAIL ─────────
with tabA:
    st.subheader("รายละเอียดน้ำหนักบรรทุก (มยผ.1101-1106)")
    colA1, colA2 = st.columns(2)
    with colA1:
        st.latex(rf"DL = {res_loads['slab_DL']:.0f} + {finish_w:.0f} + {wall_w:.0f} + {mep_w:.0f} = {res_loads['DL_total']:.0f}\ \mathrm{{kg/m^2}}")
        st.latex(rf"w_u = 1.4({res_loads['DL_total']:.0f}) + 1.7({user_LL:.0f}) = {res_loads['U2']:.0f}\ \mathrm{{kg/m^2}}")
        st.metric("น้ำหนักประลัยต่อชั้น (พื้นที่ {:.0f} ม.²)".format(floor_area),
                  f"{res_loads['factored_floor_force']:,.1f} ตัน")
    with colA2:
        st.markdown("**ตารางน้ำหนักบรรทุกจรขั้นต่ำตามกฎหมาย**")
        st.dataframe(pd.DataFrame({"ประเภทการใช้งาน": LIVE_LOAD_DB.keys(),
                                   "LL ขั้นต่ำ (kg/m²)": LIVE_LOAD_DB.values()}),
                     use_container_width=True, height=320)

# ───────── TAB B : WIND DETAIL ─────────
with tabB:
    st.subheader("รายละเอียดแรงลม (มยผ.1311-50 — วิธีการอย่างง่าย)")
    st.latex(r"p = I_w \cdot q \cdot C_e \cdot C_g \cdot C_p \quad ; \quad q = 0.625\,V^2\ \mathrm{(N/m^2)}")
    colB1, colB2 = st.columns([1.1, 1])
    with colB1:
        prof = res_wind["profile"]
        figw = make_subplots(rows=1, cols=2, shared_yaxes=True,
                             subplot_titles=("ความดันลมสุทธิ p(z)", "แรงต่อแถบ F(z)"))
        figw.add_trace(go.Scatter(x=prof["p (N/m²)"], y=prof["z (ม.)"], mode="lines+markers",
                                  line=dict(color="#0ea5e9", width=3)), row=1, col=1)
        figw.add_trace(go.Bar(x=prof["F (ตัน)"], y=prof["z (ม.)"], orientation="h",
                              marker_color="#6366f1"), row=1, col=2)
        figw.update_layout(height=380, showlegend=False, template="plotly_white",
                           margin=dict(l=10, r=10, t=40, b=10))
        figw.update_yaxes(title_text="ความสูง z (ม.)", row=1, col=1)
        st.plotly_chart(figw, use_container_width=True)
    with colB2:
        st.dataframe(prof.style.format({"z (ม.)": "{:.1f}", "Ce": "{:.3f}",
                                        "p (N/m²)": "{:,.0f}", "F (ตัน)": "{:.2f}"}),
                     use_container_width=True, height=380)

# ───────── TAB C : SEISMIC DETAIL ─────────
with tabC:
    st.subheader("รายละเอียดแรงแผ่นดินไหว (มยผ.1302-61 — Equivalent Static)")
    if res_seis is None:
        st.warning("ยังไม่สามารถคำนวณได้ — ตรวจสอบชั้นดิน F / กทม.ดินอ่อน / ตารางชั้นว่าง")
    else:
        rs = res_seis
        # กราฟสเปกตรัม (กัน T0=0 ตาม bug fix เดิม)
        if rs["SDS"] > 0 and rs["T0"] > 0:
            Tv = np.linspace(0, max(4.0, rs["Ta"] * 1.5, rs["TS"] * 2), 400)
            Sa = np.piecewise(Tv, [Tv < rs["T0"], (Tv >= rs["T0"]) & (Tv <= rs["TS"]), Tv > rs["TS"]],
                              [lambda T: rs["SDS"] * (0.4 + 0.6 * T / rs["T0"]), rs["SDS"],
                               lambda T: rs["SD1"] / T])
        else:
            Tv = np.linspace(0, 4, 400); Sa = np.zeros_like(Tv)
        Sa_Ta = (rs["SDS"] * (0.4 + 0.6 * rs["Ta"] / rs["T0"]) if rs["Ta"] < rs["T0"] and rs["T0"] > 0
                 else (rs["SDS"] if rs["Ta"] <= rs["TS"] else (rs["SD1"] / rs["Ta"] if rs["Ta"] > 0 else 0)))

        colC1, colC2 = st.columns(2)
        with colC1:
            figs = go.Figure()
            figs.add_trace(go.Scatter(x=Tv, y=Sa, mode="lines", name="Design Spectrum",
                                      line=dict(color="#1f77b4", width=3)))
            figs.add_trace(go.Scatter(x=[rs["Ta"]], y=[Sa_Ta], mode="markers+text",
                                      text=[f"Ta={rs['Ta']:.2f}s"], textposition="top right",
                                      marker=dict(color="#f59e0b", size=13, symbol="star")))
            figs.update_layout(title="Design Response Spectrum", template="plotly_white",
                               xaxis_title="T (s)", yaxis_title="Sa (g)", height=350,
                               margin=dict(l=10, r=10, t=40, b=10), showlegend=False)
            st.plotly_chart(figs, use_container_width=True)
        with colC2:
            tbl = pd.DataFrame({"ชั้น": story_df["Floor"], "hx (ม.)": story_df["hx"],
                                "wx (ตัน)": story_df["wx"], "Cvx": rs["Cvx"],
                                "Fx (ตัน)": rs["Fx"], "Vx (ตัน)": rs["Vx"], "Mx (ตัน-ม.)": rs["Mx"]})
            st.dataframe(tbl.style.format({"hx (ม.)": "{:.2f}", "wx (ตัน)": "{:,.1f}", "Cvx": "{:.4f}",
                                           "Fx (ตัน)": "{:,.2f}", "Vx (ตัน)": "{:,.2f}",
                                           "Mx (ตัน-ม.)": "{:,.2f}"}),
                         use_container_width=True, height=350)

        figf = make_subplots(rows=1, cols=3, shared_yaxes=True,
                             subplot_titles=("Fx (ตัน)", "Vx (ตัน)", "Mx (ตัน-ม.)"))
        figf.add_trace(go.Bar(y=story_df["Floor"], x=rs["Fx"], orientation="h", marker_color="#3b82f6"), 1, 1)
        figf.add_trace(go.Bar(y=story_df["Floor"], x=rs["Vx"], orientation="h", marker_color="#10b981"), 1, 2)
        figf.add_trace(go.Bar(y=story_df["Floor"], x=rs["Mx"], orientation="h", marker_color="#f59e0b"), 1, 3)
        figf.update_layout(height=340, showlegend=False, template="plotly_white",
                           margin=dict(l=10, r=10, t=40, b=10))
        figf.update_yaxes(autorange="reversed", row=1, col=1)
        st.plotly_chart(figf, use_container_width=True)

# ───────── TAB D : STORY DRIFT ─────────
with tabD:
    st.subheader("ตรวจสอบการเคลื่อนตัวระหว่างชั้น (มยผ.1302-61 หัวข้อ 3.5)")
    st.latex(r"\delta_x = \frac{C_d\,\delta_e}{I_e} \quad ; \quad \frac{\Delta}{h_{sx}} \le \Delta_a")
    if res_seis is None or story_df.empty:
        st.info("ต้องคำนวณแผ่นดินไหวสำเร็จก่อนจึงตรวจ Drift ได้")
    else:
        drift_in = pd.DataFrame({"ชั้น": story_df["Floor"].values,
                                 "hx (ม.)": story_df["hx"].values,
                                 "δe (ซม.)": np.linspace(2.0, 0.4, len(story_df))})
        drift_edit = st.data_editor(drift_in, num_rows="fixed", use_container_width=True,
                                    key=f"drift_{len(story_df)}",
                                    column_config={
                                        "ชั้น": st.column_config.TextColumn(disabled=True),
                                        "hx (ม.)": st.column_config.NumberColumn(disabled=True, format="%.2f"),
                                        "δe (ซม.)": st.column_config.NumberColumn(min_value=0.0, format="%.3f")})
        dr = engine_drift(drift_edit["δe (ซม.)"].to_numpy(float),
                          story_df["hx"].to_numpy(float), res_seis["Cd"], Ie)
        out = drift_edit.copy()
        out["δx (ซม.)"] = dr["delta_x"]; out["h ชั้น (ม.)"] = dr["h_net"]
        out["Drift Ratio"] = dr["ratio"]; out["Limit"] = dr["limit"]; out["ผล"] = dr["status"]
        st.dataframe(out.style.map(
            lambda v: 'background-color:#dcfce7;color:#166534;font-weight:bold' if v == "PASS"
            else ('background-color:#fee2e2;color:#991b1b;font-weight:bold' if v == "FAIL" else ''),
            subset=["ผล"]).format({"δx (ซม.)": "{:.2f}", "h ชั้น (ม.)": "{:.2f}",
                                   "Drift Ratio": "{:.4f}", "Limit": "{:.4f}"}),
            use_container_width=True)
        if (dr["status"] == "FAIL").any():
            st.error("❌ มีชั้นที่ Drift เกินเกณฑ์ — เพิ่มสติฟเนสของระบบต้านแรงด้านข้าง")
        else:
            st.success("✅ Drift ทุกชั้นผ่านเกณฑ์ มยผ.1302-61")

# ───────── TAB E : EXPORT ─────────
with tabE:
    st.subheader("📤 ส่งออกรายงานการคำนวณ")

    # --- สร้างรายงานข้อความ (TXT) ---
    rpt = []
    rpt.append("=" * 72)
    rpt.append("DPT STRUCTURAL DESIGN SUITE — CALCULATION REPORT")
    rpt.append(f"โครงการ: {project_name}")
    rpt.append(f"วันที่: {datetime.now():%d/%m/%Y %H:%M}  |  สถานที่: อ.{dist} จ.{prov}")
    rpt.append("=" * 72)
    rpt.append("")
    rpt.append("[1] น้ำหนักบรรทุก (มยผ.1101-1106)")
    rpt.append(f"    ประเภทอาคาร: {occupancy} | LL = {user_LL:.0f} kg/m² (ขั้นต่ำ {res_loads['LL_min']})")
    rpt.append(f"    DL รวม = {res_loads['DL_total']:.0f} kg/m² | wu = {res_loads['U_gov']:.0f} kg/m²")
    rpt.append("")
    rpt.append("[2] แรงลม (มยผ.1311-50)")
    rpt.append(f"    โซน: {wind_zone} | Iw = {Iw} | ภูมิประเทศ {terrain[:1]}")
    rpt.append(f"    Base Shear (ลม) = {res_wind['V_base']:,.2f} ตัน | OTM = {res_wind['M_otm']:,.2f} ตัน-ม.")
    rpt.append("")
    if res_seis:
        rpt.append("[3] แผ่นดินไหว (มยผ.1302-61)")
        rpt.append(f"    Ss={Ss_in:.3f} S1={S1_in:.3f} ชั้นดิน {site_class} | SDS={res_seis['SDS']:.3f} SD1={res_seis['SD1']:.3f}")
        rpt.append(f"    SDC = '{res_seis['sdc']}' | ระบบ: {system_key} (R={res_seis['R']}, Cd={res_seis['Cd']})")
        rpt.append(f"    Cs = {res_seis['Cs']:.4f} | W = {res_seis['W']:,.1f} ตัน | V = {res_seis['V']:,.2f} ตัน")
        rpt.append(f"    OTM ที่ฐาน = {res_seis['Mx'][-1]:,.2f} ตัน-ม." if len(res_seis['Mx']) else "")
    rpt.append("")
    rpt.append("[4] ออกแบบหน้าตัด")
    if res_beam is not None and res_beam.get("ok"):
        rpt.append(f"    คาน {b_in:.0f}×{h_in:.0f} ซม. fc'={fc:.0f} fy={fy} | As={res_beam['As']:.2f} ซม.² "
                   f"(≈{res_beam['n_db25']}-DB25) | ปลอก RB9@{res_beam['s_use']:.0f} ซม.")
    if res_col is not None:
        rpt.append(f"    เสา {cb_in:.0f}×{ch_in:.0f} ซม. φPn={res_col['phiPn']:,.1f} ตัน D/C={res_col['ratio']:.2f} "
                   f"→ {'PASS' if res_col['ok'] else 'FAIL'}")
    if res_steel is not None:
        rpt.append(f"    คานเหล็ก fb/Fb={res_steel['rb']:.2f} fv/Fv={res_steel['rv']:.2f} "
                   f"→ {'PASS' if res_steel['ok_b'] and res_steel['ok_v'] else 'FAIL'}")
    rpt.append("")
    rpt.append("-" * 72)
    rpt.append("PROCESS LOG (สำหรับตรวจสอบย้อนกลับ)")
    rpt += ["  " + line for line in master_log]
    rpt.append("")
    rpt.append("หมายเหตุ: รายงานนี้เป็นผลคำนวณเบื้องต้น ต้องตรวจสอบและลงนามรับรองโดย")
    rpt.append("วิศวกรโยธาผู้มีใบอนุญาตประกอบวิชาชีพก่อนนำไปใช้ก่อสร้างจริง")
    report_txt = "\n".join(rpt)

    cE1, cE2, cE3 = st.columns(3)
    with cE1:
        st.download_button("⬇️ รายงาน TXT", report_txt,
                           file_name=f"DPT_Report_{datetime.now():%Y%m%d_%H%M}.txt",
                           mime="text/plain", use_container_width=True)
    with cE2:
        if res_seis:
            csv_force = pd.DataFrame({"Floor": story_df["Floor"], "hx_m": story_df["hx"],
                                      "wx_ton": story_df["wx"], "Cvx": res_seis["Cvx"],
                                      "Fx_ton": res_seis["Fx"], "Vx_ton": res_seis["Vx"],
                                      "Mx_ton_m": res_seis["Mx"]}).to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ ตารางแรง CSV", csv_force,
                               file_name="seismic_forces.csv", mime="text/csv",
                               use_container_width=True)
        else:
            st.button("ตารางแรง CSV (ไม่พร้อม)", disabled=True, use_container_width=True)
    with cE3:
        csv_wind = res_wind["profile"].to_csv(index=False).encode("utf-8-sig")
        st.download_button("⬇️ โปรไฟล์ลม CSV", csv_wind,
                           file_name="wind_profile.csv", mime="text/csv",
                           use_container_width=True)

    st.text_area("👁️ ตัวอย่างรายงาน", report_txt, height=380)
