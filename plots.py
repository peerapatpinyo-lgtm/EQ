"""
plots.py — ฟังก์ชันสร้างกราฟและแผนภาพ (Plotly + Graphviz DOT)
"""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# ──────────────────────────────────────────────────────────────────────────────
# 1. Roadmap DOT (ผังการตัดสินใจเลือกวิธีวิเคราะห์)
# ──────────────────────────────────────────────────────────────────────────────

def get_roadmap_dot() -> str:
    """ส่งกลับ Graphviz DOT String สำหรับแสดงผังการตัดสินใจเลือกวิธีวิเคราะห์"""
    return """
    digraph G {
        graph [rankdir=TB, bgcolor="transparent", splines=true, nodesep=0.6, ranksep=0.5]
        node [fontname="Tahoma, Arial, sans-serif", shape=box, style="filled,rounded",
              color="#1e293b", fontcolor="#ffffff", fillcolor="#334155",
              fontsize=11, penwidth=1.5, margin="0.15,0.10"]
        edge [fontname="Tahoma, Arial, sans-serif", color="#64748b", fontsize=10,
              arrowhead=vee, arrowsize=0.8, penwidth=1.5]

        subgraph cluster_phase1 {
            label="[ เฟส 1: ผลลัพธ์ประเภทการออกแบบ (SDC) ]";
            fontname="Tahoma, Arial, sans-serif"; fontsize=12; fontcolor="#0f172a";
            style="dashed"; color="#cbd5e1"; bgcolor="#f8fafc";
            sdc_a [label="🔹 ประเภท ก\n(เสี่ยงภัยต่ำมาก)", fillcolor="#10b981", color="#047857"]
            sdc_b [label="🔹 ประเภท ข\n(เสี่ยงภัยต่ำ)",     fillcolor="#f59e0b", color="#b45309"]
            sdc_c [label="🔹 ประเภท ค\n(เสี่ยงภัยปานกลาง)", fillcolor="#f97316", color="#c2410c"]
            sdc_d [label="🔹 ประเภท ง\n(เสี่ยงภัยสูง)",     fillcolor="#ef4444", color="#b91c1c"]
        }

        subgraph cluster_phase2 {
            label="[ เฟส 2: ตรวจสอบเงื่อนไขรูปทรงและมิติ ]";
            fontname="Tahoma, Arial, sans-serif"; fontsize=12; fontcolor="#0f172a";
            style="dashed"; color="#cbd5e1"; bgcolor="#f8fafc";
            bypass_b [label="ไม่ต้องตรวจสอบรูปทรง\n(ผ่านเกณฑ์สถิตโดยอัตโนมัติ)", fillcolor="#94a3b8", fontcolor="#1e293b"]
            check_rules [label="⚖️ ตรวจสอบ Structural Regularity\nและข้อจำกัดความสูงตาม SDC\n(ตาราง 12.6-1 มยผ.)", fillcolor="#3b82f6", color="#1d4ed8"]
        }

        subgraph cluster_phase3 {
            label="[ เฟส 3: วิธีการวิเคราะห์ที่มาตรฐานอนุญาต ]";
            fontname="Tahoma, Arial, sans-serif"; fontsize=12; fontcolor="#0f172a";
            style="dashed"; color="#cbd5e1"; bgcolor="#f8fafc";
            done_a  [label="🟢 ใช้แรงบวกด้านข้างขั้นต่ำ 1%W\n[ จบขั้นตอน — ไม่ต้องคิดแรงแผ่นดินไหวเต็มรูปแบบ ]", fillcolor="#059669"]
            static_final  [label="🟢 วิธีแรงสถิตเทียบเท่า\n(Equivalent Static Procedure — ESP)\n[ คำนวณที่ Tab 4 ]", fillcolor="#10b981"]
            modal_final   [label="🟡 วิธีพลศาสตร์โหมด (Modal RSA)\nอนุญาต แต่ต้องปรับสเกลผล V ≥ 85% Vstatic", fillcolor="#d97706", fontcolor="#1e293b"]
            dynamic_final [label="🛑 บังคับใช้วิธีพลศาสตร์เท่านั้น\n(Response Spectrum / Time-History)\n*ห้ามใช้วิธีสถิตในโปรแกรมนี้*", fillcolor="#dc2626"]
        }

        sdc_a -> done_a  [weight=2]
        sdc_b -> bypass_b
        bypass_b -> static_final
        sdc_c -> check_rules
        sdc_d -> check_rules
        check_rules -> static_final  [label="  ✅ โครงสร้างสม่ำเสมอ\n  และสูงไม่เกินเกณฑ์"]
        check_rules -> modal_final   [label="  ⚡ โครงสร้างค่อนข้างไม่สม่ำเสมอ\n  หรือ สูงปานกลาง-สูง"]
        check_rules -> dynamic_final [label="  ❌ มีความไม่สม่ำเสมอรุนแรง\n  หรือ สูงเกิน 50 ม. (SDC ง)"]
    }
    """


# ──────────────────────────────────────────────────────────────────────────────
# 2. Design Response Spectrum
# ──────────────────────────────────────────────────────────────────────────────

def create_spectrum_plot(
    T_values: np.ndarray,
    Sa_values: np.ndarray,
    Ta: float,
    T_design: float,
    Sa_Ta: float,
    Sa_Tdesign: float,
    T0: float,
    TS: float,
    SDS: float,
    SD1: float,
) -> go.Figure:
    """สร้างกราฟ Design Response Spectrum พร้อมแสดง Ta และ T_design (Cu·Ta)"""
    fig = go.Figure()

    # เส้น Spectrum
    fig.add_trace(go.Scatter(
        x=T_values, y=Sa_values, mode='lines',
        name='Design Spectrum (Sa)',
        line=dict(color='#1f77b4', width=3)
    ))

    # จุดควบคุม T0, TS
    if SDS > 0:
        fig.add_trace(go.Scatter(
            x=[T0, TS], y=[SDS, SDS],
            mode='markers', name=f'T₀ = {T0:.3f} s, Tₛ = {TS:.3f} s',
            marker=dict(color='red', size=9, symbol='circle')
        ))

    # จุด Ta (Approximate Period)
    fig.add_trace(go.Scatter(
        x=[Ta], y=[Sa_Ta], mode='markers+text',
        name=f'Ta = {Ta:.3f} s (ประมาณ)',
        text=[f'Ta = {Ta:.2f} s<br>Sa = {Sa_Ta:.3f} g'],
        textposition="top right",
        marker=dict(color='#ff7f0e', size=13, symbol='star',
                    line=dict(width=2, color='DarkSlateGrey'))
    ))

    # จุด T_design = Cu·Ta (upper bound)
    if abs(T_design - Ta) > 0.001:
        fig.add_trace(go.Scatter(
            x=[T_design], y=[Sa_Tdesign], mode='markers+text',
            name=f'T_design = Cu·Ta = {T_design:.3f} s',
            text=[f'T_design = {T_design:.2f} s<br>Sa = {Sa_Tdesign:.3f} g'],
            textposition="top left",
            marker=dict(color='#9467bd', size=11, symbol='diamond',
                        line=dict(width=1.5, color='DarkSlateGrey'))
        ))

    # เส้น SD1/T
    T_hyp = np.linspace(TS if TS > 0.01 else 0.01, max(T_values), 200)
    Sa_hyp = SD1 / T_hyp if SD1 > 0 else T_hyp * 0
    fig.add_trace(go.Scatter(
        x=T_hyp, y=Sa_hyp, mode='lines', name='SD1/T (เส้นอ้างอิง)',
        line=dict(color='gray', width=1.5, dash='dot')
    ))

    # แรเงาโซนรูปทรงสเปกตรัม
    if SDS > 0 and TS > 0:
        fig.add_vrect(x0=0, x1=T0, fillcolor='rgba(59,130,246,0.05)', line_width=0,
                      annotation_text="ช่วงขาขึ้น", annotation_position="bottom left",
                      annotation_font_size=10, annotation_font_color="#1d4ed8")
        fig.add_vrect(x0=T0, x1=TS, fillcolor='rgba(16,185,129,0.07)', line_width=0,
                      annotation_text="Plateau (Sa = SDS)", annotation_position="top left",
                      annotation_font_size=10, annotation_font_color="#047857")
        fig.add_vrect(x0=TS, x1=max(T_values), fillcolor='rgba(245,158,11,0.05)', line_width=0,
                      annotation_text="ช่วงขาลง (Sa = SD1/T)", annotation_position="top right",
                      annotation_font_size=10, annotation_font_color="#b45309")

    fig.update_layout(
        title="<b>กราฟความเร่งตอบสนองเชิงสเปกตรัม (Design Response Spectrum)</b>",
        xaxis_title="<b>คาบเวลา T (วินาที)</b>",
        yaxis_title="<b>Sa (g)</b>",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99,
                    bgcolor="rgba(255,255,255,0.8)", bordercolor="Black", borderwidth=1),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray',
                   zeroline=True, zerolinecolor='Black'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray',
                   zeroline=True, zerolinecolor='Black', rangemode='tozero'),
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# 3. Cs waterfall (แสดง Cs,basic / Cs,max / Cs,min / Cs,gov)
# ──────────────────────────────────────────────────────────────────────────────

def create_cs_bar(cs_dict: dict) -> go.Figure:
    """Bar chart เปรียบเทียบค่า Cs ต่างๆ"""
    labels = ["Cs,basic\nSDS/(R/Ie)", "Cs,max\nSD1/[T(R/Ie)]",
              "Cs,min\n0.044·SDS·Ie\n(หรือ 0.5S1/(R/Ie))", "Cs ที่ใช้\n(Governing)"]
    values = [cs_dict["cs_basic"], cs_dict["cs_max"],
              cs_dict["cs_min"],   cs_dict["cs_gov"]]
    colors = ["#3b82f6", "#f59e0b", "#ef4444", "#10b981"]

    fig = go.Figure(go.Bar(
        x=labels, y=values, marker_color=colors,
        text=[f"{v:.4f}" for v in values], textposition="outside"
    ))
    fig.update_layout(
        title="<b>เปรียบเทียบค่า Cs (Base Shear Coefficient)</b>",
        yaxis_title="Cs", template="plotly_white",
        height=350, margin=dict(t=50, b=20),
        yaxis=dict(rangemode="tozero")
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# 4. แรงประจำชั้น (Fx, Vx, Mx)
# ──────────────────────────────────────────────────────────────────────────────

def create_force_plot(
    floor_names: np.ndarray,
    Fx: np.ndarray,
    Vx: np.ndarray,
    Mx: np.ndarray,
) -> go.Figure:
    """กราฟแท่งเปรียบเทียบ Fx, Vx, Mx แต่ละชั้น"""
    fig = make_subplots(
        rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0.06,
        subplot_titles=("แรงผลักแผ่นดินไหว Fx (ตัน)",
                        "แรงเฉือนสะสม Vx (ตัน)",
                        "โมเมนต์พลิกคว่ำ Mx (ตัน·ม.)")
    )
    bar_kw = dict(orientation='h')
    fig.add_trace(go.Bar(y=floor_names, x=Fx, marker_color='#3b82f6', **bar_kw), row=1, col=1)
    fig.add_trace(go.Bar(y=floor_names, x=Vx, marker_color='#10b981', **bar_kw), row=1, col=2)
    fig.add_trace(go.Bar(y=floor_names, x=Mx, marker_color='#f59e0b', **bar_kw), row=1, col=3)
    fig.update_layout(
        height=420, showlegend=False, template="plotly_white",
        margin=dict(l=10, r=10, t=45, b=20)
    )
    fig.update_yaxes(autorange="reversed", title_text="ชั้นอาคาร", row=1, col=1)
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# 5. Story Drift Model Diagram
# ──────────────────────────────────────────────────────────────────────────────

def create_drift_model_plot() -> go.Figure:
    """แผนภาพจำลองพฤติกรรมการโยกขยับของโครงสร้าง (Story Drift)"""
    fig = go.Figure()
    x_orig = [0, 3]
    y_orig = [0, 3, 6, 9]
    dx     = [0, 0.5, 1.3, 2.0]

    # เส้นอาคารก่อนเคลื่อนตัว (dash)
    for i in range(4):
        fig.add_trace(go.Scatter(
            x=x_orig, y=[y_orig[i], y_orig[i]], mode='lines',
            line=dict(color='#d1d5db', width=2, dash='dash'), showlegend=False
        ))
    for xv in x_orig:
        fig.add_trace(go.Scatter(
            x=[xv, xv], y=[0, 9], mode='lines',
            line=dict(color='#d1d5db', width=2, dash='dash'), showlegend=False
        ))

    # เส้นอาคารหลังเคลื่อนตัว
    for i in range(1, 4):
        fig.add_trace(go.Scatter(
            x=[x_orig[0] + dx[i], x_orig[1] + dx[i]], y=[y_orig[i], y_orig[i]],
            mode='lines+markers', line=dict(color='#3b82f6', width=4),
            marker=dict(size=6, color='#1e3a8a'), showlegend=False
        ))
        for side in range(2):
            fig.add_trace(go.Scatter(
                x=[x_orig[side] + dx[i - 1], x_orig[side] + dx[i]],
                y=[y_orig[i - 1], y_orig[i]], mode='lines',
                line=dict(color='#3b82f6', width=4), showlegend=False
            ))

    # Annotation: Fx arrow
    fig.add_annotation(x=dx[3], y=9, ax=-1.5, ay=9,
                       xref='x', yref='y', axref='x', ayref='y',
                       showarrow=True, arrowhead=2, arrowcolor='#ef4444')
    fig.add_annotation(x=-0.6, y=9.6, text="<b>Fx</b>",
                       showarrow=False, font=dict(color='#ef4444'))
    # δe
    fig.add_annotation(x=x_orig[1], y=9, ax=x_orig[1] + dx[3], ay=9,
                       xref='x', yref='y', axref='x', ayref='y',
                       showarrow=True, arrowhead=2, arrowcolor='#9333ea')
    fig.add_annotation(x=x_orig[1] + dx[3] / 2, y=9.8,
                       text="<b>δe (elastic)</b>",
                       showarrow=False, font=dict(color='#9333ea'))
    # Δ Drift
    fig.add_annotation(x=x_orig[1] + dx[2], y=7.5,
                       ax=x_orig[1] + dx[3], ay=7.5,
                       xref='x', yref='y', axref='x', ayref='y',
                       showarrow=True, arrowhead=2, arrowcolor='#db2777')
    fig.add_annotation(x=x_orig[1] + (dx[2] + dx[3]) / 2 + 0.6, y=7.5,
                       text="<b>Δ (Story Drift)</b>",
                       showarrow=False, font=dict(color='#db2777'))

    fig.update_layout(
        xaxis=dict(visible=False, range=[-2, 6.5]),
        yaxis=dict(visible=False, range=[-0.5, 11]),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0),
        height=220, showlegend=False
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# 6. P-Delta Stability Check Plot
# ──────────────────────────────────────────────────────────────────────────────

def create_theta_plot(floor_names: np.ndarray, theta: np.ndarray) -> go.Figure:
    """กราฟแสดง Stability Coefficient θ รายชั้น และเส้น θ_max = 0.10 / 0.25"""
    fig = go.Figure()
    colors = ['#ef4444' if t > 0.10 else '#3b82f6' for t in theta]
    fig.add_trace(go.Bar(
        y=floor_names, x=theta, orientation='h',
        marker_color=colors,
        text=[f"{t:.4f}" for t in theta], textposition="outside"
    ))
    # เส้นขีดจำกัด
    fig.add_vline(x=0.10, line_dash="dash", line_color="#f59e0b",
                  annotation_text="θ = 0.10 (ต้องพิจารณา P-Δ)", annotation_position="top right")
    fig.add_vline(x=0.25, line_dash="dash", line_color="#ef4444",
                  annotation_text="θ_max ≈ 0.25 (ไม่อนุญาต)", annotation_position="bottom right")
    fig.update_layout(
        title="<b>ค่าสัมประสิทธิ์เสถียรภาพ θ (P-Delta Stability Coefficient)</b>",
        xaxis_title="θ", template="plotly_white",
        height=380, showlegend=False,
        yaxis=dict(autorange="reversed"),
        margin=dict(l=10, r=20, t=50, b=20)
    )
    return fig


# ──────────────────────────────────────────────────────────────────────────────
# 7. กราฟ Design Response Spectrum — มยผ. 1302 (Soft Clay / Bangkok)
# ──────────────────────────────────────────────────────────────────────────────

def create_soft_clay_spectrum_plot(
    Ta: float,
    T_design: float,
    Sa_Ta: float,
    Sa_Tdesign: float,
) -> go.Figure:
    """
    กราฟสเปกตรัม มยผ. 1302 สำหรับพื้นที่ดินเหนียวอ่อนกรุงเทพฯ
    แสดงรูปทรงแบบ plateau กว้าง (T0=0.3s → TL=1.5s) + เส้น 1/T
    """
    from data_loader import SOFT_CLAY_SPECTRUM, get_soft_clay_sa

    p   = SOFT_CLAY_SPECTRUM
    SDS = p["SDS"]
    T0  = p["T0"]
    TL  = p["TL"]
    SD1eff = p["SD1_eff"]

    T_max = max(4.0, T_design * 1.5, 3.5)
    T_arr = np.linspace(0.0, T_max, 800)
    Sa_arr = np.array([get_soft_clay_sa(t) for t in T_arr])

    fig = go.Figure()

    # ── เส้นสเปกตรัม ──
    fig.add_trace(go.Scatter(
        x=T_arr, y=Sa_arr, mode='lines',
        name='Design Spectrum มยผ. 1302 (Soft Clay)',
        line=dict(color='#dc2626', width=3)
    ))

    # ── เส้น 1/T reference ──
    T_hyp = np.linspace(TL, T_max, 200)
    fig.add_trace(go.Scatter(
        x=T_hyp, y=SD1eff / T_hyp, mode='lines',
        name=f'SD1_eff/T = {SD1eff:.2f}/T',
        line=dict(color='gray', width=1.5, dash='dot')
    ))

    # ── จุดควบคุม T0, TL ──
    fig.add_trace(go.Scatter(
        x=[T0, TL], y=[SDS, SDS], mode='markers+text',
        name=f'T₀ = {T0} s,  TL = {TL} s',
        text=[f'T₀ = {T0} s', f'TL = {TL} s'],
        textposition=['top right', 'top left'],
        marker=dict(color='#b91c1c', size=9, symbol='circle')
    ))

    # ── จุด Ta ──
    fig.add_trace(go.Scatter(
        x=[Ta], y=[Sa_Ta], mode='markers+text',
        name=f'Ta = {Ta:.3f} s',
        text=[f'Ta = {Ta:.2f} s<br>Sa = {Sa_Ta:.3f} g'],
        textposition='top right',
        marker=dict(color='#f97316', size=13, symbol='star',
                    line=dict(width=2, color='DarkSlateGrey'))
    ))

    # ── จุด T_design = Cu·Ta ──
    if abs(T_design - Ta) > 0.001:
        fig.add_trace(go.Scatter(
            x=[T_design], y=[Sa_Tdesign], mode='markers+text',
            name=f'T_design = Cu·Ta = {T_design:.3f} s',
            text=[f'T_design = {T_design:.2f} s<br>Sa = {Sa_Tdesign:.3f} g'],
            textposition='top left',
            marker=dict(color='#7c3aed', size=11, symbol='diamond',
                        line=dict(width=1.5, color='DarkSlateGrey'))
        ))

    # ── Zone annotation ──
    fig.add_vrect(x0=T0, x1=TL, fillcolor='rgba(220,38,38,0.06)',
                  line_width=0,
                  annotation_text="Plateau (ดินอ่อน)",
                  annotation_position="top left",
                  annotation_font_color="#991b1b")

    fig.update_layout(
        title="<b>กราฟความเร่งตอบสนองเชิงสเปกตรัม — มยผ. 1302 (พื้นที่ดินเหนียวอ่อน กทม.)</b>",
        xaxis_title="<b>คาบเวลา T (วินาที)</b>",
        yaxis_title="<b>Sa (g)</b>",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99,
                    bgcolor="rgba(255,255,255,0.8)", bordercolor="Black", borderwidth=1),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray',
                   zeroline=True, zerolinecolor='Black'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray',
                   zeroline=True, zerolinecolor='Black', rangemode='tozero'),
    )
    return fig
