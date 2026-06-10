import numpy as np
from scipy.interpolate import interp1d
from data_loader import FA_TABLE, FV_TABLE

def get_site_coefficients(site_class: str, Ss: float, S1: float) -> tuple:
    """คำนวณหาค่า Fa และ Fv ด้วยวิธี Linear Interpolation"""
    if site_class == 'F':
        return 0.0, 0.0
    try:
        f_fa = interp1d(
            FA_TABLE['Ss_keys'], FA_TABLE[site_class], kind='linear',
            fill_value=(FA_TABLE[site_class][0], FA_TABLE[site_class][-1]), bounds_error=False
        )
        f_fv = interp1d(
            FV_TABLE['S1_keys'], FV_TABLE[site_class], kind='linear',
            fill_value=(FV_TABLE[site_class][0], FV_TABLE[site_class][-1]), bounds_error=False
        )
        return max(float(f_fa(Ss)), 0.0), max(float(f_fv(S1)), 0.0)
    except Exception:
        return 1.0, 1.0

def calculate_approx_period(sys_type: str, hn: float) -> float:
    """คำนวณหาคาบเวลาธรรมชาติโดยประมาณของอาคาร (Ta)"""
    params = {
        "โครงต้านทานแรงดัดเหล็กกล้า": (0.0724, 0.8),
        "โครงต้านทานแรงดัดคอนกรีตเสริมเหล็ก": (0.0466, 0.9),
        "โครงสร้างอื่นๆ": (0.0488, 0.75)
    }
    Ct, x = params.get(sys_type, (0.0488, 0.75))
    return Ct * (hn ** x)

def evaluate_sdc_detailed(SDS: float, SD1: float, Ie: float) -> tuple:
    """ประเมินประเภทการออกแบบต้านทานแผ่นดินไหว (Seismic Design Category: SDC)"""
    is_essential = (Ie >= 1.5)

    if SDS < 0.167:
        sdc_sds = 'ก'
    elif SDS < 0.33:
        sdc_sds = 'ค' if is_essential else 'ข'
    elif SDS < 0.50:
        sdc_sds = 'ง' if is_essential else 'ค'
    else:
        sdc_sds = 'ง'

    if SD1 < 0.067:
        sdc_sd1 = 'ก'
    elif SD1 < 0.133:
        sdc_sd1 = 'ค' if is_essential else 'ข'
    elif SD1 < 0.20:
        sdc_sd1 = 'ง' if is_essential else 'ค'
    else:
        sdc_sd1 = 'ง'

    sdc_order = {'ก': 1, 'ข': 2, 'ค': 3, 'ง': 4}
    max_val = max(sdc_order[sdc_sds], sdc_order[sdc_sd1])
    sdc_final = next(cat for cat, val in sdc_order.items() if val == max_val)

    return sdc_final, sdc_sds, sdc_sd1

def compute_spectrum_sa(T: float, SDS: float, SD1: float, T0: float, TS: float) -> float:
    """คำนวณความเร่งตอบสนองเชิงสเปกตรัม ณ คาบเวลา T แบบจุดเดี่ยว"""
    if T0 > 0 and T < T0:
        return SDS * (0.4 + 0.6 * (T / T0))
    elif T <= TS:
        return SDS
    else:
        return SD1 / T if T > 0 else SDS

def calculate_story_forces(hx: np.ndarray, wx: np.ndarray, Cs_gov: float, Ta: float) -> tuple:
    """คำนวณการกระจายแรงแผ่นดินไหวประจำชั้น แรงเฉือนสะสม และโมเมนต์พลิกคว่ำ"""
    total_W = float(np.sum(wx))
    total_V = float(Cs_gov * total_W)
    k_exp   = 1.0 if Ta <= 0.5 else (2.0 if Ta >= 2.5 else 1.0 + (Ta - 0.5) / 2.0)

    w_hx_k    = wx * (hx ** k_exp)
    sum_w_hx_k = float(np.sum(w_hx_k)) if np.sum(w_hx_k) > 0 else 1.0
    cvx = w_hx_k / sum_w_hx_k
    Fx  = cvx * total_V
    Vx  = np.cumsum(Fx)

    Mx = np.zeros_like(Fx)
    for i in range(len(hx)):
        moment = 0.0
        for j in range(i + 1):
            moment += Fx[j] * max(0.0, hx[j] - hx[i])
        Mx[i] = moment
        
    return total_W, total_V, k_exp, sum_w_hx_k, cvx, Fx, Vx, Mx
