"""
calculations.py — เครื่องยนต์คำนวณหลัก มยผ. 1301/1302-61
ปรับปรุงแก้ไข: เพิ่มเติมสูตรครบถ้วน รวม Cu·Ta, θ P-Delta, ρ, SDC ครบ
"""

import numpy as np
from scipy.interpolate import interp1d
from data_loader import FA_TABLE, FV_TABLE, SOFT_CLAY_SPECTRUM, get_soft_clay_sa


# ──────────────────────────────────────────────────────────────────────────────
# 1. ตัวคูณขยายชั้นดิน  Fa / Fv
# ──────────────────────────────────────────────────────────────────────────────

def get_site_coefficients(site_class: str, Ss: float, S1: float) -> tuple[float, float]:
    """
    คำนวณ Fa และ Fv ด้วย Linear Interpolation จากตาราง มยผ.
    ชั้นดิน F: ต้องใช้ Site-Specific Study → คืน (0, 0)
    """
    if site_class == 'F':
        return 0.0, 0.0
    try:
        fa_interp = interp1d(
            FA_TABLE['Ss_keys'], FA_TABLE[site_class], kind='linear',
            fill_value=(FA_TABLE[site_class][0], FA_TABLE[site_class][-1]),
            bounds_error=False
        )
        fv_interp = interp1d(
            FV_TABLE['S1_keys'], FV_TABLE[site_class], kind='linear',
            fill_value=(FV_TABLE[site_class][0], FV_TABLE[site_class][-1]),
            bounds_error=False
        )
        return max(float(fa_interp(Ss)), 0.0), max(float(fv_interp(S1)), 0.0)
    except Exception:
        return 1.0, 1.0


# ──────────────────────────────────────────────────────────────────────────────
# 2. คาบเวลาโครงสร้าง Ta และ Cu·Ta (Period Upper Bound)
# ──────────────────────────────────────────────────────────────────────────────

# ตัวคูณขยาย Cu จากตาราง มยผ. (ขึ้นกับ SD1)
_CU_SD1_KEYS   = [0.10, 0.15, 0.20, 0.30, 0.40, 0.50]
_CU_VALUES     = [1.70, 1.65, 1.60, 1.50, 1.45, 1.40]

# ค่า Ct, x ตามประเภทโครงสร้าง
PERIOD_PARAMS: dict[str, tuple[float, float]] = {
    "โครงต้านทานแรงดัดเหล็กกล้า":            (0.0724, 0.80),
    "โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก":    (0.0466, 0.90),
    "โครงค้ำยันเหล็กกล้าแบบศูนย์กลาง (SCBF)": (0.0488, 0.75),
    "โครงค้ำยันเหล็กกล้าแบบเยื้องศูนย์ (EBF)": (0.0731, 0.75),
    "กำแพงรับแรงเฉือน คสล.":                   (0.0488, 0.75),
    "โครงสร้างอื่นๆ / ทั่วไป":                 (0.0488, 0.75),
}


def calculate_approx_period(sys_type: str, hn: float) -> float:
    """คาบเวลาโครงสร้างโดยประมาณ Ta = Ct · hn^x"""
    Ct, x = PERIOD_PARAMS.get(sys_type, (0.0488, 0.75))
    return Ct * (hn ** x)


def get_period_upper_bound(SD1: float, Ta: float) -> float:
    """
    คาบเวลาสูงสุดที่ใช้ออกแบบ T_design = min(Cu·Ta, T_measured)
    (ใน Tab นี้ไม่มีค่าวัดจริง จึงใช้ Cu·Ta เป็น upper bound)
    ถ้า SD1 ≤ 0 หรือ Ta = 0 → คืน Ta ตามเดิม
    """
    if SD1 <= 0 or Ta <= 0:
        return Ta
    cu_interp = interp1d(
        _CU_SD1_KEYS, _CU_VALUES, kind='linear',
        fill_value=(_CU_VALUES[0], _CU_VALUES[-1]),
        bounds_error=False
    )
    Cu = float(cu_interp(SD1))
    return Cu * Ta


# ──────────────────────────────────────────────────────────────────────────────
# 3. ประเภทการออกแบบต้านทานแผ่นดินไหว (SDC)
# ──────────────────────────────────────────────────────────────────────────────

_SDC_RANK = {'ก': 1, 'ข': 2, 'ค': 3, 'ง': 4}
_SDC_FROM_RANK = {v: k for k, v in _SDC_RANK.items()}


def evaluate_sdc_detailed(SDS: float, SD1: float, S1: float, Ie: float) -> tuple[str, str, str, list[str]]:
    """
    ประเมิน SDC (ก/ข/ค/ง) ตาม มยผ. 1301-61 ตารางที่ 11.6-1 และ 11.6-2
    คืน: (sdc_final, sdc_from_sds, sdc_from_sd1, notes_list)

    กฎพิเศษ:
    - ถ้า S1 ≥ 0.75 g → บังคับ SDC ง ทันที
    - อาคารความสำคัญสูงมาก (Ie = 1.5) ขยาย SDC เพิ่มหนึ่งระดับ
    """
    notes: list[str] = []
    is_essential = (Ie >= 1.5)

    # ─── จาก SDS ───
    if SDS < 0.167:
        sdc_sds = 'ก'
    elif SDS < 0.33:
        sdc_sds = 'ค' if is_essential else 'ข'
    elif SDS < 0.50:
        sdc_sds = 'ง' if is_essential else 'ค'
    else:
        sdc_sds = 'ง'

    # ─── จาก SD1 ───
    if SD1 < 0.067:
        sdc_sd1 = 'ก'
    elif SD1 < 0.133:
        sdc_sd1 = 'ค' if is_essential else 'ข'
    elif SD1 < 0.20:
        sdc_sd1 = 'ง' if is_essential else 'ค'
    else:
        sdc_sd1 = 'ง'

    sdc_final = _SDC_FROM_RANK[max(_SDC_RANK[sdc_sds], _SDC_RANK[sdc_sd1])]

    # ─── กฎพิเศษ S1 ≥ 0.75 g ───
    if S1 >= 0.75:
        sdc_final = 'ง'
        notes.append("⚠️ S1 ≥ 0.75 g → บังคับ SDC ง ตามมาตรา 11.6 มยผ. โดยอัตโนมัติ")

    if is_essential and _SDC_RANK[sdc_final] < 4:
        notes.append("ℹ️ อาคารความสำคัญสูงมาก (Ie = 1.5): ระดับ SDC อาจถูกยกขึ้นหนึ่งระดับ")

    return sdc_final, sdc_sds, sdc_sd1, notes


# ──────────────────────────────────────────────────────────────────────────────
# 4. กราฟ Design Response Spectrum
# ──────────────────────────────────────────────────────────────────────────────

def compute_spectrum_sa(T: float, SDS: float, SD1: float, T0: float, TS: float) -> float:
    """ความเร่งตอบสนองเชิงสเปกตรัม Sa ณ คาบ T"""
    if SDS <= 0:
        return 0.0
    if T0 > 0 and T < T0:
        return SDS * (0.4 + 0.6 * T / T0)
    elif T <= TS:
        return SDS
    else:
        return SD1 / T if T > 0 else SDS


# ──────────────────────────────────────────────────────────────────────────────
# 5. สัมประสิทธิ์แรงเฉือนที่ฐาน Cs
# ──────────────────────────────────────────────────────────────────────────────

def compute_cs(SDS: float, SD1: float, S1: float, T_design: float,
               R: float, Ie: float, TS: float = 0.0) -> dict[str, float]:
    """
    คำนวณ Cs ตามมาตรา 12.8.1.1 มยผ.

    สูตรที่ใช้:
        Cs,basic = SDS / (R/Ie)                           … (1)
        Cs,max   = SD1 / [T · (R/Ie)]   (T > TS)          … (2a)
                 = SDS / (R/Ie)         (T ≤ TS)          … (2b)
        Cs,min   = max(0.01, 0.044·SDS·Ie)               … (3)
        ถ้า S1 ≥ 0.6 g: Cs,min = max(Cs,min, 0.5·S1/(R/Ie))  … (4)
        Cs,gov   = clamp(Cs,min, Cs,basic, Cs,max)

    คืน dict ของทุกค่าเพื่อแสดงในตารางคำนวณ
    """
    RIe = R / Ie if Ie > 0 else R

    cs_basic = SDS / RIe if RIe > 0 else 0.0

    if T_design > TS and TS > 0:
        cs_max = SD1 / (T_design * RIe) if T_design > 0 and RIe > 0 else cs_basic
    else:
        cs_max = cs_basic  # ไม่ตัดยอดถ้าอยู่ในช่วง plateau

    cs_min = max(0.01, 0.044 * SDS * Ie)

    cs_min_s1 = 0.0
    if S1 >= 0.6:
        cs_min_s1 = (0.5 * S1) / RIe if RIe > 0 else 0.0
        cs_min = max(cs_min, cs_min_s1)

    cs_gov = max(cs_min, min(cs_basic, cs_max))

    return {
        "cs_basic":  cs_basic,
        "cs_max":    cs_max,
        "cs_min":    cs_min,
        "cs_min_s1": cs_min_s1,
        "cs_gov":    cs_gov,
        "RIe":       RIe,
        "controls":  ("ต่ำสุด (Cs,min)" if cs_gov == cs_min
                      else ("สูงสุด (Cs,max)" if cs_gov == cs_max
                            else "ปกติ (Cs,basic)")),
    }


# ──────────────────────────────────────────────────────────────────────────────
# 6. กระจายแรงแผ่นดินไหวประจำชั้น
# ──────────────────────────────────────────────────────────────────────────────

def calculate_story_forces(
    hx: np.ndarray,
    wx: np.ndarray,
    Cs_gov: float,
    Ta: float
) -> tuple[float, float, float, float, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    กระจายแรง V ลงสู่แต่ละชั้นตาม มยผ. มาตรา 12.8.3
    k = 1.0  (T ≤ 0.5 s)
      = interpolate (0.5 < T < 2.5 s)
      = 2.0  (T ≥ 2.5 s)
    คืน: total_W, total_V, k, sum_w_hx_k, cvx, Fx, Vx, Mx
    """
    total_W = float(np.sum(wx))
    total_V = float(Cs_gov * total_W)

    if Ta <= 0.5:
        k = 1.0
    elif Ta >= 2.5:
        k = 2.0
    else:
        k = 1.0 + (Ta - 0.5) / 2.0

    w_hxk      = wx * (hx ** k)
    sum_w_hxk  = float(np.sum(w_hxk)) if np.sum(w_hxk) > 0 else 1.0
    cvx = w_hxk / sum_w_hxk
    Fx  = cvx * total_V

    # Vx = แรงเฉือนสะสม (บนลงล่าง)
    Vx = np.cumsum(Fx)

    # Mx = โมเมนต์พลิกคว่ำ ณ ระดับชั้นที่ i
    n  = len(hx)
    Mx = np.zeros(n)
    for i in range(n):
        for j in range(i + 1):
            Mx[i] += Fx[j] * max(0.0, hx[j] - hx[i])

    return total_W, total_V, k, sum_w_hxk, cvx, Fx, Vx, Mx


# ──────────────────────────────────────────────────────────────────────────────
# 7. ตรวจสอบ P-Delta (Stability Coefficient θ)
# ──────────────────────────────────────────────────────────────────────────────

def compute_stability_coeff(
    Px: np.ndarray,   # น้ำหนักรวมสะสมเหนือชั้น i (ตัน)
    delta_x: np.ndarray,  # การเคลื่อนตัวจริง δx (ซม.)
    Vx: np.ndarray,   # แรงเฉือนสะสม (ตัน)
    hx: np.ndarray,   # ความสูงสะสม (ม.)
    Cd: float,
    Ie: float
) -> np.ndarray:
    """
    θ = Px · Δx / (Vx · hsx · Cd/Ie)
    ตาม มยผ. มาตรา 12.8.7
    ถ้า θ > θ_max = 0.5/(β·Cd) ≈ 0.25 (ประมาณ β = 1) → ต้องพิจารณา P-Delta
    """
    n = len(hx)
    theta = np.zeros(n)
    for i in range(n):
        hsx_cm  = (hx[i] - hx[i + 1]) * 100 if i < n - 1 else hx[i] * 100
        delta_i = delta_x[i] - delta_x[i + 1] if i < n - 1 else delta_x[i]
        denom   = Vx[i] * max(hsx_cm, 1.0) * (Cd / Ie)
        theta[i] = (Px[i] * delta_i) / denom if denom > 0 else 0.0
    return theta


# ──────────────────────────────────────────────────────────────────────────────
# 8. ตัวคูณความซ้ำซ้อน ρ (Redundancy Factor)
# ──────────────────────────────────────────────────────────────────────────────

def get_redundancy_factor(sdc: str, num_bays: int, num_frames: int) -> tuple[float, str]:
    """
    ρ ตาม มยผ. มาตรา 12.3.4
    - SDC ก, ข  → ρ = 1.0 เสมอ
    - SDC ค, ง  → ρ = 1.0 ถ้าโครงสร้างผ่านเงื่อนไข redundancy
                   ρ = 1.3 ถ้าไม่ผ่าน (conservative default)
    เงื่อนไขอย่างง่าย: โครงมีอย่างน้อย 2 ช่วง (bay) × 2 แนวโครงต้านทาน
    """
    if sdc in ('ก', 'ข'):
        return 1.0, "SDC ก/ข → ρ = 1.0 เสมอ"
    if num_bays >= 2 and num_frames >= 2:
        return 1.0, "ผ่านเกณฑ์ redundancy (≥2 ช่วงและ ≥2 แนวโครง) → ρ = 1.0"
    return 1.3, "ไม่ผ่านเกณฑ์ redundancy → ρ = 1.3 (conservative)"


# ──────────────────────────────────────────────────────────────────────────────
# 9. Cs สำหรับพื้นที่ดินเหนียวอ่อน มยผ. 1302 (Bangkok Soft Clay)
# ──────────────────────────────────────────────────────────────────────────────

def compute_cs_soft_clay(T_design: float, R: float, Ie: float, S1_bkk: float = 0.10) -> dict:
    """
    คำนวณ Cs สำหรับพื้นที่ดินเหนียวอ่อน (มยผ. 1302-61)
    ใช้สเปกตรัม Sa ที่ T_design แทน SDS/(R/Ie) แบบปกติ

    สูตร:
        Cs,basic  = Sa(T_design) / (R/Ie)
        Cs,max    = Sa(T_design) / (R/Ie)   ← เหมือน basic (สเปกตรัมรวม amplification แล้ว)
        Cs,min    = max(0.01, 0.044 × SDS_bkk × Ie)
        Cs,gov    = max(Cs,min, Cs,basic)

    หมายเหตุ: ไม่ใช้สูตร SD1/[T·(R/Ie)] แยก เพราะ มยผ. 1302
    กำหนดรูปทรงสเปกตรัมสมบูรณ์โดยตรง
    """
    p      = SOFT_CLAY_SPECTRUM
    SDS    = p["SDS"]
    RIe    = R / Ie if Ie > 0 else R

    Sa_T   = get_soft_clay_sa(T_design)
    cs_basic = Sa_T / RIe if RIe > 0 else 0.0
    cs_min   = max(0.01, 0.044 * SDS * Ie)
    cs_gov   = max(cs_min, cs_basic)

    return {
        "cs_basic":   cs_basic,
        "cs_max":     cs_basic,   # ไม่มีการตัดยอดแยก
        "cs_min":     cs_min,
        "cs_min_s1":  0.0,
        "cs_gov":     cs_gov,
        "RIe":        RIe,
        "Sa_T":       Sa_T,
        "SDS_bkk":    SDS,
        "controls":   ("ต่ำสุด (Cs,min)" if cs_gov == cs_min else "ปกติ (Sa(T)/[R/Ie])"),
        "mode":       "soft_clay",
    }
