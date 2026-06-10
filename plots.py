import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def get_roadmap_dot() -> str:
    """ส่งกลับ Graphviz DOT String สำหรับแสดงผลผังการตัดสินใจเลือกวิธีวิเคราะห์"""
    return """
    digraph G {
        graph [rankdir=TB, bgcolor="transparent", splines=true, nodesep=0.5, ranksep=0.4]
        node [fontname="Tahoma, Arial, sans-serif", shape=box, style="filled,rounded", color="#1e293b", fontcolor="#ffffff", fillcolor="#334155", fontsize=11, penwidth=1.5]
        edge [fontname="Tahoma, Arial, sans-serif", color="#64748b", fontsize=10, arrowhead=vee, arrowsize=0.8, penwidth=1.5]

        subgraph cluster_phase1 {
            label="[ เฟส 1: ผลลัพธ์ประเภทการออกแบบ (SDC) ]";
            fontname="Tahoma, Arial, sans-serif"; fontsize=12; fontcolor="#0f172a"; style="dashed"; color="#cbd5e1"; bgcolor="#f8fafc";
            sdc_a [label="🔹 ประเภท ก\\n(เสี่ยงภัยต่ำมาก)", fillcolor="#10b981", color="#047857"]
            sdc_b [label="🔹 ประเภท ข\\n(เสี่ยงภัยต่ำ)", fillcolor="#f59e0b", color="#b45309"]
            sdc_c [label="🔹 ประเภท ค\\n(เสี่ยงภัยปานกลาง)", fillcolor="#f97316", color="#c2410c"]
            sdc_d [label="🔹 ประเภท ง\\n(เสี่ยงภัยสูง)", fillcolor="#ef4444", color="#b91c1c"]
        }

        subgraph cluster_phase2 {
            label="[ เฟส 2: ตรวจสอบเงื่อนไขรูปทรงและมิติอาคาร ]";
            fontname="Tahoma, Arial, sans-serif"; fontsize=12; fontcolor="#0f172a"; style="dashed"; color="#cbd5e1"; bgcolor="#f8fafc";
            bypass_b [label="ไม่ต้องตรวจสอบรูปทรง\\n(ผ่านเกณฑ์สถิตโดยอัตโนมัติ)", fillcolor="#94a3b8", fontcolor="#1e293b"]
            check_rules [label="⚖️ ตรวจสอบรูปทรงอาคาร\\n(Structural Regularity)\\nและข้อจำกัดความสูง", fillcolor="#3b82f6", color="#1d4ed8"]
        }

        subgraph cluster_phase3 {
            label="[ เฟส 3: วิธีการวิเคราะห์ที่มาตรฐานอนุญาต ]";
            fontname="Tahoma, Arial, sans-serif"; fontsize=12; fontcolor="#0f172a"; style="dashed"; color="#cbd5e1"; bgcolor="#f8fafc";
            done_a [label="🟢 ใช้แรงบวกด้านข้างขั้นต่ำ 1%W\\n[ จบขั้นตอน - ไม่ต้องคิดแรงแผ่นดินไหว ]", fillcolor="#059669"]
            static_final [label="🟢 ลุยต่อวิธีแรงสถิตเทียบเท่า\\n(Equivalent Static Procedure)\\n[ เปิดไปคำนวณที่ Tab 4 ]", fillcolor="#10b981"]
            dynamic_final [label="🛑 บังคับใช้วิธีพลศาสตร์เท่านั้น\\n(Dynamic Analysis / Response Spectrum)\\n*ห้ามใช้วิธีสถิตในโปรแกรมนี้*", fillcolor="#dc2626"]
        }

        sdc_a -> done_a [weight=2]
        sdc_b -> bypass_b
        bypass_b -> static_final
        sdc_c -> check_rules
        sdc_d -> check_rules
        check_rules -> static_final [label="  โครงสร้างสม่ำเสมอ\\n  และสูงไม่เกินเกณฑ์ มยผ."]
        check_rules -> dynamic_final [label="  ❌ มีความไม่สม่ำเสมอ\\n  หรือ สูงเกินเกณฑ์กำหนด"]
    }
    """

def create_spectrum_plot(T_values: np.ndarray, Sa_values: np.ndarray, Ta: float, Sa_Ta: float, T0: float, TS: float, SDS: float) -> go.Figure:
    """
    สร้างกราฟความเร่งตอบสนองเชิงสเปกตรัมสำหรับการออกแบบ (Design Response Spectrum)
    ตามมาตรฐาน มยผ. 1301/1302-61 บทที่ 4 และอ้างอิงโครงสร้างสมการจาก ASCE 7-16 Chapter 11
    
    พฤติกรรมโครงสร้างที่แสดงบนกราฟแบ่งออกเป็น 3 ช่วงตามหลักวิศวกรรมแผ่นดินไหว:
    1. ช่วงคาบสั้นมาก (T < T0): โครงสร้างแข็งเกร็งสูง (Rigid Building) ความเร่งไต่ระดับจาก PGA (0.4*Sds) ขึ้นไป
    2. ช่วงโหมดความเร่งคงที่ (T0 <= T <= TS): โซนอันตรายสูงสุด เกิดการกำทอน (Resonance) โครงสร้างเตี้ย-ปานกลางรับแรงสูงสุด
    3. ช่วงโหมดความเร็วคงที่ (T > TS): โครงสร้างยืดหยุ่นสูง (อาคารสูง) ความเร่งลดลงแปรผกผันกับ T แต่ระยะโยกตัว (Drift) จะเพิ่มขึ้น
    
    Parameters:
    ----------
    T_values : np.ndarray : อาเรย์ของค่าคาบเวลาธรรมชาติ (T) บนแกน X
    Sa_values : np.ndarray : อาเรย์ของค่าความเร่งเชิงสเปกตรัมตอบสนอง (Sa) บนแกน Y
    Ta : float : คาบเวลาธรรมชาติโดยประมาณของอาคารที่กำลังออกแบบ (Approximate Fundamental Period)
    Sa_Ta : float : ค่าความเร่งตอบสนองที่อาคารหลังนี้จะได้รับจริงตามคาบเวลา Ta
    T0 : float : คาบเวลาที่เป็นจุดเริ่มของช่วงความเร่งคงที่ (0.2 * SD1 / SDS)
    TS : float : คาบเวลาที่เป็นจุดสิ้นสุดของช่วงความเร่งคงที่ (SD1 / SDS)
    SDS : float : ความเร่งตอบสนองเชิงสเปกตรัมที่คาบสั้น (Short Period Design Spectral Acceleration)
    """
    fig = go.Figure()
    
    # ----------------------------------------------------
    # เส้นกราฟหลักและแรเงาพื้นที่ใต้กราฟ
    # ----------------------------------------------------
    fig.add_trace(go.Scatter(
        x=T_values, y=Sa_values, mode='lines', fill='tozeroy', 
        name='Design Spectrum (มยผ. 1301/1302)',
        line=dict(color='#1f77b4', width=3),
        fillcolor='rgba(31, 119, 180, 0.15)' # สีฟ้าโปร่งแสงเพิ่มความสวยงาม
    ))
    
    # ----------------------------------------------------
    # พล็อตจุดควบคุมพฤติกรรม (T0, SDS) และ (TS, SDS) พร้อมเส้นประแนวตั้ง
    # ----------------------------------------------------
    if SDS > 0:
        fig.add_trace(go.Scatter(
            x=[T0, TS], y=[SDS, SDS], mode='markers+text', 
            name='จุดควบคุมสเปกตรัม (T0, TS)',
            text=['T0', 'TS'], textposition="top center",
            marker=dict(color='#ef4444', size=10, symbol='circle')
        ))
        # เพิ่มเส้นขอบเขตแนวตั้งเพื่อแบ่งแยกโซนพฤติกรรมอย่างชัดเจน
        fig.add_vline(x=T0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(x=TS, line_dash="dash", line_color="gray", opacity=0.5)
        
    # ----------------------------------------------------
    # พล็อตจุดพิกัดของอาคารที่ออกแบบ (Ta, Sa_Ta) พร้อมเส้น Drop-lines นำสายตา
    # ----------------------------------------------------
    fig.add_trace(go.Scatter(
        x=[Ta], y=[Sa_Ta], mode='markers+text', name='🎯 พิกัดของอาคาร (Ta, Sa)',
        text=[f'Ta = {Ta:.3f} s<br>Sa = {Sa_Ta:.3f} g'], textposition="top right",
        marker=dict(color='#ff7f0e', size=14, symbol='star', line=dict(width=2, color='Black')) # ใช้รูปดาวเด่นชัด
    ))
    # สร้างเส้นบอกพิกัดฉายลงไปที่แกน X และ แกน Y เพื่อให้วิศวกรอ่านค่าได้ทันที
    fig.add_shape(type="line", x0=0, y0=Sa_Ta, x1=Ta, y1=Sa_Ta, line=dict(color="#ff7f0e", width=1.5, dash="dot"))
    fig.add_shape(type="line", x0=Ta, y0=0, x1=Ta, y1=Sa_Ta, line=dict(color="#ff7f0e", width=1.5, dash="dot"))
    
    # ----------------------------------------------------
    # เพิ่มข้อความอธิบายโซนพฤติกรรมโครงสร้างกลางกราฟ (Watermark Labels)
    # อ้างอิงทฤษฎี Dynamics of Structures เพื่อบอกแนวโน้มพฤติกรรมอาคาร
    # ----------------------------------------------------
    if TS > 0 and max(T_values) > TS:
        fig.add_annotation(
            x=(T0+TS)/2, y=SDS/2, 
            text="<b>โหมดความเร่งคงที่</b><br>(Constant Acceleration Region)<br>อาคารเตี้ย-ปานกลาง / เสี่ยงเกิด Resonance สูง", 
            showarrow=False, opacity=0.35, font=dict(size=11, color='black')
        )
        fig.add_annotation(
            x=TS + (max(T_values)-TS)/3, y=SDS/4, 
            text="<b>โหมดความเร็วคงที่</b><br>(Constant Velocity Region)<br>อาคารสูง / โครงสร้างยืดหยุ่น / ระวังค่า Drift", 
            showarrow=False, opacity=0.35, font=dict(size=11, color='black')
        )

    # ----------------------------------------------------
    # การตั้งค่า Layout เค้าโครงกราฟตามสไตล์รายงานทางวิศวกรรม
    # ----------------------------------------------------
    fig.update_layout(
        title="<b>กราฟความเร่งสเปกตรัมตอบสนองสำหรับการออกแบบ (Design Response Spectrum)</b>",
        xaxis_title="<b>คาบเวลาธรรมชาติของโครงสร้าง, T (วินาที)</b>",
        yaxis_title="<b>ความเร่งตอบสนองเชิงสเปกตรัม, Sa (หน่วยของแรงโน้มถ่วง, g)</b>",
        hovermode="x unified", template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99,
                    bgcolor="rgba(255,255,255,0.8)", bordercolor="Black", borderwidth=1),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray', zeroline=True, zerolinecolor='Black'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='LightGray', zeroline=True, zerolinecolor='Black', rangemode='tozero')
    )
    return fig

def create_force_plot(floor_names: np.ndarray, Fx: np.ndarray, Vx: np.ndarray, Mx: np.ndarray) -> go.Figure:
    """สร้างกราฟแท่งแบบกลุ่มเปรียบเทียบ Fx, Vx และ Mx ของแต่ละชั้นอาคาร"""
    fig_force = make_subplots(
        rows=1, cols=3, shared_yaxes=True, horizontal_spacing=0.06,
        subplot_titles=("แรงผลักแผ่นดินไหว (Fx)", "แรงเฉือนสะสม (Vx)", "โมเมนต์พลิกคว่ำ (Mx)")
    )
    fig_force.add_trace(go.Bar(y=floor_names, x=Fx, orientation='h', marker_color='#3b82f6'), row=1, col=1)
    fig_force.add_trace(go.Bar(y=floor_names, x=Vx, orientation='h', marker_color='#10b981'), row=1, col=2)
    fig_force.add_trace(go.Bar(y=floor_names, x=Mx, orientation='h', marker_color='#f59e0b'), row=1, col=3)
    fig_force.update_layout(height=400, showlegend=False, template="plotly_white",
                            margin=dict(l=10, r=10, t=40, b=20))
    fig_force.update_yaxes(autorange="reversed", title_text="ชั้นอาคาร", row=1, col=1)
    return fig_force

def create_drift_model_plot() -> go.Figure:
    """สร้างแผนภาพจำลองพฤติกรรมการโยกขยับของโครงสร้างอาคาร (Story Drift Model)"""
    fig_model = go.Figure()
    x_orig = [0, 3]; y_orig = [0, 3, 6, 9]; dx = [0, 0.6, 1.5, 2.2]
    
    for i in range(4):
        fig_model.add_trace(go.Scatter(
            x=x_orig, y=[y_orig[i], y_orig[i]], mode='lines',
            line=dict(color='#d1d5db', width=2, dash='dash')
        ))
    for xv in x_orig:
        fig_model.add_trace(go.Scatter(
            x=[xv, xv], y=[0, 9], mode='lines',
            line=dict(color='#d1d5db', width=2, dash='dash')
        ))
    for i in range(1, 4):
        fig_model.add_trace(go.Scatter(
            x=[x_orig[0]+dx[i], x_orig[1]+dx[i]], y=[y_orig[i], y_orig[i]],
            mode='lines+markers', line=dict(color='#3b82f6', width=4),
            marker=dict(size=6, color='#1e3a8a')
        ))
        fig_model.add_trace(go.Scatter(
            x=[x_orig[0]+dx[i-1], x_orig[0]+dx[i]], y=[y_orig[i-1], y_orig[i]],
            mode='lines', line=dict(color='#3b82f6', width=4)
        ))
        fig_model.add_trace(go.Scatter(
            x=[x_orig[1]+dx[i-1], x_orig[1]+dx[i]], y=[y_orig[i-1], y_orig[i]],
            mode='lines', line=dict(color='#3b82f6', width=4)
        ))
        
    fig_model.add_annotation(x=dx[3], y=9, ax=-1.5, ay=9, xref='x', yref='y', axref='x', ayref='y',
                             showarrow=True, arrowhead=2, arrowcolor='#ef4444')
    fig_model.add_annotation(x=-0.5, y=9.6, text="<b>Fx</b>", showarrow=False, font=dict(color='#ef4444'))
    fig_model.add_annotation(x=x_orig[1], y=9, ax=x_orig[1]+dx[3], ay=9,
                             xref='x', yref='y', axref='x', ayref='y',
                             showarrow=True, arrowhead=2, arrowcolor='#9333ea')
    fig_model.add_annotation(x=x_orig[1]+dx[3]/2, y=9.7, text="<b>δe</b>", showarrow=False, font=dict(color='#9333ea'))
    fig_model.add_annotation(x=x_orig[1]+dx[2], y=7.5, ax=x_orig[1]+dx[3], ay=7.5,
                             xref='x', yref='y', axref='x', ayref='y',
                             showarrow=True, arrowhead=2, arrowcolor='#db2777')
    fig_model.add_annotation(x=x_orig[1]+(dx[2]+dx[3])/2+0.5, y=7.5, text="<b>Δ (Drift)</b>", showarrow=False, font=dict(color='#db2777'))
    
    fig_model.update_layout(
        xaxis=dict(visible=False, range=[-2, 6]),
        yaxis=dict(visible=False, range=[-1, 10]),
        plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=0, r=0, t=0, b=0), height=200, showlegend=False
    )
    return fig_model
