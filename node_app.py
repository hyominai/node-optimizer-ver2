import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import platform
from matplotlib import rcParams

import subprocess
try:
    subprocess.run(["apt-get", "install", "-y", "fonts-nanum"], capture_output=True)
    import matplotlib.font_manager as fm
    fm._load_fontmanager(try_read_cache=False)
except:
    pass

if platform.system() == "Windows":
    plt.rcParams["font.family"] = "Malgun Gothic"
elif platform.system() == "Darwin":
    plt.rcParams["font.family"] = "AppleGothic"
else:
    # Streamlit Cloud (Linux)
    nanum = [f.name for f in fm.fontManager.ttflist if 'Nanum' in f.name]
    if nanum:
        plt.rcParams["font.family"] = nanum[0]
    else:
        plt.rcParams["font.family"] = "DejaVu Sans"
rcParams["axes.unicode_minus"] = False

st.set_page_config(page_title="결절점 자동 최적화 모델", page_icon="🏢", layout="wide")

st.markdown("""
<style>
    .main { background-color: #f8f9fa; }
    h1 { color: #1a1a2e; font-size: 1.8rem !important; }
    h2 { color: #16213e; font-size: 1.2rem !important; border-bottom: 2px solid #0f3460; padding-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

st.title("🏢 결절점(Node) 자동 최적화 모델")
st.caption("전국 범용 버전 — 지역 데이터를 입력하면 최적 주·상·커 비율 및 사업성을 자동 산출합니다")

# ==========================================
# 사이드바
# ==========================================
with st.sidebar:
    st.header("📥 인풋 레이어")

    st.subheader("물리 변수")
    site_area = st.number_input("대지면적 (㎡)", value=12267, step=100)
    far_pct   = st.slider("목표 용적률 (%)", 200, 1500, 1000, step=100)
    far       = far_pct / 100
    total_gfa = site_area * far
    st.caption(f"총 연면적: {total_gfa:,.0f} ㎡")

    st.subheader("건물 형태 (포디움 + 타워)")
    podium_area = st.number_input("포디움 바닥면적 (㎡)", value=9000, step=100)
    tower_area  = st.number_input("타워 1개동 바닥면적 (㎡)", value=800, step=50)
    tower_count = 3  # 타워 고정 3개동

    st.subheader("공시지가 / 철거비")
    land_price   = st.number_input("개별공시지가 (원/㎡)", value=2826000, step=10000)
    demo_price   = st.number_input("철거비 (원/㎡, 대지기준)", value=106500, step=1000)

    st.subheader("공사비 단가")
    st.caption("타워 층수에 따라 고층 할증 자동 반영")
    st.info("주거: 국토부 기본형건축비 2,292,000원 × 고층할증 × 충남보정(0.98)\n상업·커뮤니티: 복합청사 3,734,000원 × 1.04 × 0.98")

    st.subheader("PF 구조")
    eq_ratio   = st.slider("자기자본 비율 (%)", 10, 50, 30, step=5)
    loan_rate  = st.slider("대출 금리 (%)", 3.0, 8.0, 5.0, step=0.5)
    loan_tenor = st.slider("대출 상환 기간 (년)", 5, 20, 15, step=1)

    st.subheader("환경 변수")
    vac_local  = st.slider("지역 상권 공실률 (%)", 0.0, 60.0, 21.6, step=0.1)
    node_count = st.slider("반경 1km 내 기존 Node 수", 0, 20, 19, step=1)
    deficit_comm = st.number_input("커뮤니티 월 적자 (원/㎡)", value=16667, step=100)
    alpha = st.select_slider(
        "커뮤니티 1,000㎡당 공실률 감소 (α)",
        options=[0.0, 0.5, 1.0, 1.5], value=1.0,
        format_func=lambda x: f"{x}%p"
    )

    st.markdown("---")
    st.subheader("📅 연도별 임대료/공실률")
    st.markdown("**주거**")
    rent_res_1  = st.number_input("주거 임대료 (원/㎡·월)", value=15000, step=500)
    vac_res_1   = st.slider("초기 공실률 1년차 (%)", 0, 40, 15)
    vac_res_2   = st.slider("안정화 공실률 2~5년차 (%)", 0, 30, 8)
    vac_res_3   = st.slider("성숙기 공실률 6년차~ (%)", 0, 20, 5)
    opex_res    = st.number_input("주거 운영비 (원/㎡·월)", value=1600, step=100)

    st.markdown("**상업**")
    rent_com    = st.number_input("상업 임대료 (원/㎡·월)", value=40000, step=1000)
    vac_com_raw = st.slider("상업 공실률 (%)", 0, 50, 15)
    opex_com    = st.number_input("상업 운영비 (원/㎡·월)", value=3000, step=100)

    st.markdown("**NPV**")
    discount_rate = st.slider("할인율 (실질, %)", 3.0, 10.0, 6.0, step=0.5)
    analysis_yrs  = st.slider("분석 기간 (년)", 10, 30, 20)

# ==========================================
# 계산 함수
# ==========================================
def get_com_cap(vac):
    if vac < 5:    return 18.0
    elif vac < 15: return 15.0
    elif vac < 25: return 12.0
    elif vac < 35: return 8.0
    else:          return 5.0

def get_mes(nodes):
    if nodes <= 2:  return 8.0
    elif nodes <= 5: return 5.0
    else:            return 3.0

def get_noi_res(rent, vac, opex):
    return rent * (1 - vac/100) - opex

def get_noi_com(rent, vac, opex):
    return rent * (1 - vac/100) - opex

def run_optimizer(com_cap, mes, noi_r, noi_c, deficit, gfa):
    valid_c, csi_vals = [], []
    for c in np.arange(mes, 100 - com_cap, 0.1):
        res = 100.0 - com_cap - c
        r_n = (res/100)*gfa*noi_r
        c_n = (com_cap/100)*gfa*noi_c
        c_d = (c/100)*gfa*deficit
        if c_d <= 0: continue
        csi = (r_n + c_n) / c_d
        if csi >= 2.0:
            valid_c.append(round(c,1))
            csi_vals.append(round(csi,3))
    return valid_c, csi_vals

def find_elbow(valid_c, csi_vals):
    if len(valid_c) < 3: return 0
    p1 = np.array([valid_c[0],  csi_vals[0],  0.0])
    p2 = np.array([valid_c[-1], csi_vals[-1], 0.0])
    dists = []
    for i in range(len(valid_c)):
        p3 = np.array([valid_c[i], csi_vals[i], 0.0])
        d  = np.abs(np.cross(p2-p1, p3-p1)[2]) / (np.linalg.norm(p2-p1)+1e-10)
        dists.append(d)
    return int(np.argmax(dists))

def calc_irr(cashflows, guess=0.05):
    # 복수의 초기값으로 시도
    for g in [0.05, 0.10, 0.01, -0.05, 0.20]:
        try:
            r = g
            for _ in range(500):
                try:
                    npv  = sum(cf/((1+r)**t) for t,cf in enumerate(cashflows))
                    dnpv = sum(-t*cf/((1+r)**(t+1)) for t,cf in enumerate(cashflows))
                except:
                    break
                if abs(dnpv) < 1e-10: break
                rn = r - npv/dnpv
                if not (-2 < rn < 10): break  # 발산 방지
                if abs(rn-r) < 1e-8: r=rn; break
                r = rn
            if -1 < r < 5:  # 합리적 범위 (-100% ~ 500%)
                return r
        except:
            continue
    return float('nan')

# 고층 할증 함수
def get_height_surcharge(floors):
    if floors <= 5:    return 1.01
    elif floors <= 10: return 1.03
    elif floors <= 15: return 1.04
    elif floors <= 20: return 1.05
    elif floors <= 25: return 1.06
    elif floors <= 30: return 1.07
    else:              return 1.07 + ((floors - 30) // 5) * 0.01

# ==========================================
# 최적화 실행
# ==========================================
noi_res_unit = get_noi_res(rent_res_1, vac_res_3, opex_res)
noi_com_unit = get_noi_com(rent_com, vac_com_raw, opex_com)
com_cap_base = get_com_cap(vac_local)
mes          = get_mes(node_count)

comm_guess = mes
valid_c, csi_vals = [], []
for _ in range(20):
    adj_vac = max(0, vac_local - (comm_guess/1000)*alpha*100)
    com_cap = get_com_cap(adj_vac)
    valid_c, csi_vals = run_optimizer(com_cap, mes, noi_res_unit, noi_com_unit, deficit_comm, total_gfa)
    if not valid_c: break
    idx = find_elbow(valid_c, csi_vals)
    new_guess = valid_c[idx]
    if abs(new_guess - comm_guess) < 0.2: comm_guess = new_guess; break
    comm_guess = new_guess

if not valid_c:
    st.error("❌ CSI ≥ 2.0을 만족하는 커뮤니티 비율이 없습니다. 인풋값을 조정하세요.")
    st.stop()

idx      = find_elbow(valid_c, csi_vals)
opt_comm = valid_c[idx]
opt_csi  = csi_vals[idx]
opt_com  = com_cap
opt_res  = round(100.0 - opt_com - opt_comm, 1)
csi_upper= valid_c[-1]
adj_vac_final = max(0, vac_local - (opt_comm/1000)*alpha*100)

# 층수
# 층수 (포디움 + 타워 구조)
area_com_tot  = (opt_com /100) * total_gfa
area_comm_tot = (opt_comm/100) * total_gfa
area_res_tot  = (opt_res /100) * total_gfa
floors_com    = max(1, round(area_com_tot  / podium_area))
floors_comm   = max(1, round(area_comm_tot / podium_area))
floors_res    = max(1, round(area_res_tot  / (tower_area * tower_count)))
total_floors_int = floors_com + floors_comm + floors_res
# CAPEX
# 타워 층수 기반 고층 할증 자동 반영
surcharge        = get_height_surcharge(floors_res)
capex_res_unit   = 2292000 * surcharge * 0.98   # 기본단가 × 고층할증 × 충남보정
capex_com_unit   = 3734000 * 1.04 * 0.98        # 복합청사 기준 (포디움 고정)

capex_res_total  = (opt_res /100)*total_gfa * capex_res_unit
capex_com_total  = (opt_com /100)*total_gfa * capex_com_unit
capex_comm_total = (opt_comm/100)*total_gfa * capex_com_unit
capex_demo       = site_area * demo_price
capex_land       = site_area * land_price
total_capex      = capex_res_total + capex_com_total + capex_comm_total + capex_demo + capex_land

equity = total_capex * eq_ratio/100
debt   = total_capex * (1 - eq_ratio/100)
lr     = loan_rate/100
af     = (lr*((1+lr)**loan_tenor))/(((1+lr)**loan_tenor)-1) if lr > 0 else 1/loan_tenor
annual_ds = debt * af

# 연도별 CF
cf_list = [-equity]
noi_list, ds_list, net_cf_list, cum_cf_list = [], [], [], []
cum = -equity
payback = None
for y in range(1, analysis_yrs+1):
    vac_r = vac_res_1 if y==1 else (vac_res_2 if y<=5 else vac_res_3)
    noi_r = get_noi_res(rent_res_1, vac_r, opex_res)
    noi_c = get_noi_com(rent_com, vac_com_raw, opex_com)
    annual_noi = ((opt_res/100)*total_gfa*noi_r + (opt_com/100)*total_gfa*noi_c
                  - (opt_comm/100)*total_gfa*deficit_comm)*12
    ds  = annual_ds if y <= loan_tenor else 0
    net = annual_noi - ds
    cum += net
    noi_list.append(annual_noi/1e8)
    ds_list.append(ds/1e8)
    net_cf_list.append(net/1e8)
    cum_cf_list.append(cum/1e8)
    cf_list.append(net)
    if payback is None and cum >= 0: payback = y

# 성숙기 NOI
ann_res = (opt_res/100)*total_gfa*noi_res_unit*12/1e8
ann_com = (opt_com/100)*total_gfa*noi_com_unit*12/1e8
ann_def = (opt_comm/100)*total_gfa*deficit_comm*12/1e8
ann_noi = ann_res + ann_com - ann_def

npv_val = sum(cf/(1+discount_rate/100)**t for t,cf in enumerate(cf_list)) / 1e8
irr_val = calc_irr(cf_list) * 100

feasible = ann_noi > 0 and opt_csi >= 2.0

# ==========================================
# 메인 화면
# ==========================================
# 상단 KPI
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("주거", f"{opt_res}%", f"{floors_res}층")
c2.metric("상업", f"{opt_com}%", f"{floors_com}층")
c3.metric("커뮤니티", f"{opt_comm}%", f"{floors_comm}층")
c4.metric("총 CAPEX", f"{total_capex/1e8:.0f}억")
c5.metric(f"{analysis_yrs}년 NPV", f"{npv_val:+.0f}억")
if np.isnan(irr_val):
    c6.metric("IRR", "계산불가", "NPV 음수 구간")
else:
    c6.metric("IRR", f"{irr_val:.1f}%", "≥ 할인율 ✅" if irr_val >= discount_rate else "< 할인율 ❌")

st.markdown("---")

# 탭 구성
tab1, tab2, tab3 = st.tabs(["📊 최적화 결과", "💰 현금흐름(CF)", "⚙️ 상세 검증"])

# ─── 탭1: 최적화 결과 ───
with tab1:
    left, right = st.columns([1.3, 1])

    with left:
        st.header("CSI 곡선 & 파레토 최적점")
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.plot(valid_c, csi_vals, color='#0f3460', linewidth=2.5, label='CSI curve')
        ax.plot([valid_c[0],valid_c[-1]],[csi_vals[0],csi_vals[-1]],'k--',alpha=0.3,linewidth=1,label='Reference line')
        ax.plot(opt_comm, opt_csi, 'o', color='#e94560', markersize=12, zorder=5,
                label=f'파레토 최적점 ({opt_comm}%, CSI {opt_csi:.1f}x)')
        ax.axhline(y=2.0, color='#e94560', linestyle='-', linewidth=1.5, alpha=0.7, label='CSI=2.0 부도선')
        ax.axvline(x=mes, color='#2ecc71', linestyle='--', linewidth=1.2, alpha=0.8, label=f'MES 하한 ({mes}%)')
        ax.axvline(x=csi_upper, color='#f39c12', linestyle='--', linewidth=1.2, alpha=0.8, label=f'CSI 상한 ({csi_upper}%)')
        ax.fill_betweenx([2.0, max(csi_vals)*1.05], mes, csi_upper, alpha=0.06, color='#2ecc71', label='생존 구간')
        ax.set_xlabel('커뮤니티 비율 (%)')
        ax.set_ylabel('교차보조 지수 (CSI)')
        ax.legend(fontsize=8, loc='upper right')
        ax.grid(True, linestyle='--', alpha=0.4)
        ax.set_facecolor('#fafafa')
        fig.patch.set_facecolor('white')
        plt.tight_layout()
        st.pyplot(fig); plt.close()

        # 연도별 NOI 테이블
        st.header("연도별 NOI 구성")
        rows = []
        for label, vac_r in [("1년차", vac_res_1),("2~5년차",vac_res_2),("6년차~",vac_res_3)]:
            nr = get_noi_res(rent_res_1, vac_r, opex_res)
            ra = (opt_res/100)*total_gfa*nr*12/1e8
            ca = (opt_com/100)*total_gfa*noi_com_unit*12/1e8
            da = (opt_comm/100)*total_gfa*deficit_comm*12/1e8
            rows.append({"연차":label,"주거공실":f"{vac_r}%",
                         "주거NOI":f"+{ra:.1f}억","상업NOI":f"+{ca:.1f}억",
                         "커뮤니티적자":f"-{da:.1f}억","통합NOI":f"+{ra+ca-da:.1f}억"})
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with right:
        st.header("건물 형태 시각화")

        fig2, ax2 = plt.subplots(figsize=(6, 8))
        ax2.set_xlim(0, 10)
        ax2.set_ylim(0, (floors_res + floors_com + floors_comm) * 1.15)
        ax2.set_facecolor('#f0f4f8')
        fig2.patch.set_facecolor('white')
        ax2.axis('off')

        # 등축 투영 설정값
        dx = 1.2   # 깊이 오프셋 x
        dy = 0.5   # 깊이 오프셋 y

        def draw_box(ax, x, y, w, h, d, color, label=None, fontsize=9):
            """등축 투영 박스 그리기"""
            # 앞면
            front = plt.Polygon([[x,y],[x+w,y],[x+w,y+h],[x,y+h]],
                                  closed=True, facecolor=color, edgecolor='white', linewidth=0.8, alpha=0.95)
            # 윗면
            top   = plt.Polygon([[x,y+h],[x+w,y+h],[x+w+d,y+h+dy],[x+d,y+h+dy]],
                                  closed=True, facecolor=color, edgecolor='white', linewidth=0.8, alpha=0.75)
            # 옆면
            side  = plt.Polygon([[x+w,y],[x+w+d,y+dy],[x+w+d,y+h+dy],[x+w,y+h]],
                                  closed=True, facecolor=color, edgecolor='white', linewidth=0.8, alpha=0.60)
            for patch in [front, top, side]:
                ax.add_patch(patch)
            if label:
                ax.text(x+w/2, y+h/2, label, ha='center', va='center',
                        color='white', fontsize=fontsize, fontweight='bold', zorder=10)

        # 포디움 (상업)
        pod_h_com  = floors_com
        pod_h_comm = floors_comm
        pod_w      = 7.0
        pod_x      = 1.5

        # 상업 포디움
        draw_box(ax2, pod_x, 0, pod_w, pod_h_com, dx,
                 '#4a9aba', f'상업\n{floors_com}층\n({opt_com:.0f}%)', fontsize=10)

        # 커뮤니티 포디움
        draw_box(ax2, pod_x, pod_h_com, pod_w, pod_h_comm, dx,
                 '#2ecc71', f'커뮤니티\n{floors_comm}층\n({opt_comm:.0f}%)', fontsize=10)

        pod_top = pod_h_com + pod_h_comm

        # 타워 3개 (주거)
        tower_w   = 1.6
        tower_gap = 0.4
        tower_h   = floors_res
        tower_xs  = [pod_x + 0.3,
                     pod_x + tower_w + tower_gap + 0.3,
                     pod_x + (tower_w + tower_gap)*2 + 0.3]

        for i, tx in enumerate(tower_xs):
            label = f'주거\n{floors_res}층' if i==1 else None
            draw_box(ax2, tx, pod_top, tower_w, tower_h, dx*0.5,
                     '#0f3460', label, fontsize=9)

        # 범례 텍스트
        ax2.text(5, (floors_res+pod_top)*1.08,
                 f'포디움 {pod_h_com+pod_h_comm}층 + 타워 {floors_res}층 × 3개동',
                 ha='center', va='center', fontsize=10, color='#333',
                 fontweight='bold')

        plt.tight_layout()
        st.pyplot(fig2); plt.close()

        st.caption(f"포디움: 상업 {floors_com}층 + 커뮤니티 {floors_comm}층 | 타워 3개동 × {floors_res}층")

        # CAPEX 구성
        st.header("CAPEX 구성")
        capex_items = {
            "주거동": capex_res_total/1e8,
            "상업동": capex_com_total/1e8,
            "커뮤니티동": capex_comm_total/1e8,
            "철거비": capex_demo/1e8,
            "토지비": capex_land/1e8,
        }
        fig3, ax3 = plt.subplots(figsize=(5, 3))
        colors_c = ['#0f3460','#4a9aba','#2ecc71','#e94560','#f39c12']
        bars = ax3.barh(list(capex_items.keys()), list(capex_items.values()),
                        color=colors_c, edgecolor='white')
        for bar, val in zip(bars, capex_items.values()):
            ax3.text(bar.get_width()+5, bar.get_y()+bar.get_height()/2,
                     f'{val:.0f}억', va='center', fontsize=9)
        ax3.set_xlabel('금액 (억원)')
        ax3.set_title(f'총 CAPEX: {total_capex/1e8:.0f}억원 (주거 고층할증 {surcharge:.2f}배)', fontweight='bold')
        ax3.set_facecolor('#fafafa'); fig3.patch.set_facecolor('white')
        ax3.spines['top'].set_visible(False); ax3.spines['right'].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig3); plt.close()

# ─── 탭2: 현금흐름 ───
with tab2:
    st.header("연도별 현금흐름 (CF)")

    years_list = list(range(1, analysis_yrs+1))

    fig4, (ax4a, ax4b) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # 상단: NOI / 대출상환 / 순CF 막대
    width = 0.3
    x = np.array(years_list)
    ax4a.bar(x - width, noi_list, width, color='#0f3460', alpha=0.8, label='연간 NOI')
    ax4a.bar(x,        [-d for d in ds_list], width, color='#e94560', alpha=0.8, label='대출 상환')
    ax4a.bar(x + width, net_cf_list, width, color='#2ecc71', alpha=0.8, label='순 CF')
    ax4a.axhline(0, color='black', linewidth=0.8)
    ax4a.set_ylabel('금액 (억원)')
    ax4a.set_title('연도별 현금흐름', fontweight='bold')
    ax4a.legend(fontsize=9)
    ax4a.grid(True, linestyle='--', alpha=0.3)
    ax4a.set_facecolor('#fafafa')

    # 하단: 누적 CF
    colors_cum = ['#e94560' if v < 0 else '#2ecc71' for v in cum_cf_list]
    ax4b.bar(x, cum_cf_list, color=colors_cum, alpha=0.7)
    ax4b.plot(x, cum_cf_list, 'o-', color='#0f3460', linewidth=1.5, markersize=4)
    ax4b.axhline(0, color='black', linewidth=1.2, linestyle='--')
    if payback:
        ax4b.axvline(payback, color='#f39c12', linewidth=2,
                     linestyle='--', label=f'투자 회수 {payback}년차')
        ax4b.legend(fontsize=9)
    ax4b.set_xlabel('연도')
    ax4b.set_ylabel('누적 CF (억원)')
    ax4b.set_title('누적 현금흐름 (손익분기점)', fontweight='bold')
    ax4b.grid(True, linestyle='--', alpha=0.3)
    ax4b.set_facecolor('#fafafa')
    ax4b.set_xticks(x)

    fig4.patch.set_facecolor('white')
    plt.tight_layout()
    st.pyplot(fig4); plt.close()

    # CF 테이블
    st.header("연도별 CF 상세")
    cf_rows = []
    for i, y in enumerate(years_list):
        cf_rows.append({
            "연도": f"{y}년차",
            "연간NOI": f"+{noi_list[i]:.1f}억",
            "대출상환": f"-{ds_list[i]:.1f}억",
            "순CF": f"{net_cf_list[i]:+.1f}억",
            "누적CF": f"{cum_cf_list[i]:+.1f}억",
        })
    st.dataframe(cf_rows, use_container_width=True, hide_index=True)

    # 재무 요약
    st.markdown("---")
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("총 CAPEX",   f"{total_capex/1e8:.0f}억원")
    m2.metric("자기자본",    f"{equity/1e8:.0f}억원", f"{eq_ratio}%")
    m3.metric("투자 회수",   f"{payback}년차" if payback else "20년 초과")
    if np.isnan(irr_val):
        m4.metric("IRR", "계산불가", "NPV 음수 구간")
    else:
        m4.metric("IRR", f"{irr_val:.1f}%", f"할인율 {discount_rate}% {'✅' if irr_val>=discount_rate else '❌'}")

# ─── 탭3: 상세 검증 ───
with tab3:
    st.header("알고리즘 판정")
    checks = [
        ("MES 하한", f"커뮤니티 {opt_comm}% ≥ {mes}%", opt_comm >= mes),
        ("CSI 방어", f"CSI {opt_csi:.1f}배 ≥ 2.0", opt_csi >= 2.0),
        ("NOI 양수", f"연간 +{ann_noi:.1f}억원", ann_noi > 0),
        ("NPV 양수", f"{analysis_yrs}년 {npv_val:+.0f}억원", npv_val > 0),
        ("IRR", f"{'계산불가' if np.isnan(irr_val) else f'{irr_val:.1f}%'} vs 할인율 {discount_rate}%", not np.isnan(irr_val) and irr_val >= discount_rate),
    ]
    for name, detail, ok in checks:
        icon = "✅" if ok else "❌"
        st.markdown(f"{icon} **{name}** — {detail}")

    if feasible and npv_val > 0:
        st.success("✅ 사업성 확인 — 지자체 보조금 없이 영구 자생 가능")
    else:
        st.error("❌ 조건 미충족 — 인풋 조정 필요")

    st.markdown("---")
    st.header("알고리즘 경로")
    st.markdown(f"""
| 단계 | 값 |
|------|---|
| 지역 공실률 | {vac_local}% |
| 상업 Cap (원본) | {com_cap_base}% |
| 커뮤니티 보정 후 공실률 | {adj_vac_final:.1f}% |
| 상업 Cap (보정 후) | {opt_com}% |
| MES 하한 | {mes}% |
| CSI 상한 | {csi_upper}% |
| 파레토 최적점 | {opt_comm}% |
| α | {alpha}%p/1,000㎡ |
""")
