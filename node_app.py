import streamlit as st
import numpy as np
import matplotlib.pyplot as plt
import platform
from matplotlib import rcParams

if platform.system() == "Windows":
    plt.rcParams["font.family"] = "Malgun Gothic"
elif platform.system() == "Darwin":
    plt.rcParams["font.family"] = "AppleGothic"
else:
    plt.rcParams["font.family"] = "DejaVu Sans"
rcParams["axes.unicode_minus"] = False

st.set_page_config(page_title="결절점 자동 최적화 모델", page_icon="🏢", layout="wide")
st.markdown("""
<style>
h1{color:#1a1a2e;font-size:1.8rem!important}
h2{color:#16213e;font-size:1.2rem!important;border-bottom:2px solid #0f3460;padding-bottom:4px}
</style>""", unsafe_allow_html=True)

st.title("🏢 결절점(Node) 자동 최적화 모델")
st.caption("전국 범용 버전 — 지역 데이터 입력 시 최적 주·상·커 비율 및 사업성 자동 산출")

# ==========================================
# 사이드바
# ==========================================
with st.sidebar:
    st.header("📥 인풋 레이어")

    st.subheader("물리 변수")
    site_area = st.number_input("대지면적 (㎡)", value=12267, step=100)
    far_pct   = st.slider("목표 용적률 (%)", 200, 1500, 1000, step=100)
    total_gfa = site_area * far_pct / 100
    st.caption(f"총 연면적: {total_gfa:,.0f} ㎡")

    st.subheader("건물 형태 (포디움 + 타워)")
    podium_area = st.number_input("포디움 바닥면적 (㎡)", value=8500, step=100)
    tower_area  = st.number_input("타워 1개동 바닥면적 (㎡)", value=800, step=50)
    tower_count = 3

    st.subheader("공사비 단가 (원/㎡)")
    st.caption("고층할증·지역보정 적용 후 단가")
    capex_res_base  = st.number_input("주거동", value=2335142, step=10000)
    capex_com_base  = st.number_input("상업동", value=3806595, step=10000)
    capex_comm_base = st.number_input("커뮤니티동", value=3806595, step=10000)
    st.caption("커뮤니티 건설비를 0으로 입력하면 시(市) 부담으로 처리")

    st.subheader("공시지가 / 철거비")
    land_price = st.number_input("개별공시지가 (원/㎡)", value=2826000, step=10000)
    demo_price = st.number_input("철거비 (원/㎡)", value=106500, step=1000)

    st.subheader("PF 구조")
    eq_ratio      = st.slider("자기자본 비율 (%)", 10, 50, 30, step=5)
    hug_pct       = st.slider("HUG 융자 비율 (주거 건설비 중 %)", 0, 100, 80, step=5)
    loan_rate_hug = st.slider("HUG 금리 (%)", 1.0, 3.0, 2.0, step=0.5)
    loan_rate_pf  = st.slider("민간PF 금리 (%)", 3.0, 8.0, 5.0, step=0.5)
    loan_tenor    = st.slider("대출 상환 기간 (년)", 5, 20, 15, step=1)
    const_period  = st.slider("공사 기간 (년)", 1, 4, 2, step=1)

    st.subheader("환경 변수")
    vac_local  = st.slider("지역 상권 공실률 (%)", 0.0, 60.0, 21.6, step=0.1)
    node_count = st.slider("반경 1km 내 기존 Node 수", 0, 3, 1, step=1)

    st.subheader("지역 인구 데이터")
    total_pop  = st.number_input("행정동 총 인구 (명)", value=28795, step=100)
    solo_hh    = st.number_input("1인가구 수 (가구)", value=7140, step=100)
    existing_lib   = st.slider("기존 도서관 수 (반경 1km)", 0, 5, 0)
    existing_sport = st.slider("기존 체육시설 수 (반경 1km)", 0, 5, 1)

    st.markdown("---")
    st.subheader("📅 연도별 임대료/공실률")
    st.markdown("**주거**")
    rent_res   = st.number_input("주거 임대료 (원/㎡·월)", value=15000, step=500)
    vac_res_1  = st.slider("초기 공실률 1년차 (%)", 0, 40, 15)
    vac_res_2  = st.slider("안정화 공실률 2~5년차 (%)", 0, 30, 8)
    vac_res_3  = st.slider("성숙기 공실률 6년차~ (%)", 0, 20, 5)
    opex_res   = st.number_input("주거 운영비 (원/㎡·월)", value=1600, step=100)

    st.markdown("**상업**")
    rent_com   = st.number_input("상업 임대료 (원/㎡·월)", value=40000, step=1000)
    vac_com    = st.slider("상업 공실률 (%)", 0, 50, 15)
    opex_com   = st.number_input("상업 운영비 (원/㎡·월)", value=3000, step=100)
    comm_mgmt  = st.number_input("커뮤니티 공용관리비 (원/㎡·월)", value=1600, step=100)

    st.markdown("**NPV**")
    discount_rate = st.slider("할인율 (실질, %)", 3.0, 10.0, 7.0, step=0.5)
    analysis_yrs  = st.slider("분석 기간 (년)", 10, 30, 20)

    st.markdown("---")
    st.subheader("🏦 리츠(REITs) 구조")
    use_reits     = st.checkbox("리츠 구조 적용", value=False)
    fund_eq_ratio = st.slider("기금 출자 비율 (%)", 10, 50, 35, step=5)
    fund_div_rate = st.slider("기금 배당률 (%)", 1.0, 5.0, 3.0, step=0.5)
    soc_ratio     = st.slider("생활SOC 지원 비율 (%커뮤니티)", 0, 100, 75, step=5)

    st.markdown("---")
    if st.button("📋 현재 설정값 내보내기"):
        st.code(f"""# 현재 설정값 (기본값으로 붙여넣기용)
site_area      = {site_area}
far_pct        = {far_pct}
podium_area    = {podium_area}
tower_area     = {tower_area}
capex_res_base = {capex_res_base}
capex_com_base = {capex_com_base}
capex_comm_base= {capex_comm_base}
land_price     = {land_price}
demo_price     = {demo_price}
eq_ratio       = {eq_ratio}
hug_pct        = {hug_pct}
loan_rate_hug  = {loan_rate_hug}
loan_rate_pf   = {loan_rate_pf}
loan_tenor     = {loan_tenor}
const_period   = {const_period}
vac_local      = {vac_local}
node_count     = {node_count}
total_pop      = {total_pop}
solo_hh        = {solo_hh}
existing_lib   = {existing_lib}
existing_sport = {existing_sport}
rent_res       = {rent_res}
vac_res_1      = {vac_res_1}
vac_res_2      = {vac_res_2}
vac_res_3      = {vac_res_3}
opex_res       = {opex_res}
rent_com       = {rent_com}
vac_com        = {vac_com}
opex_com       = {opex_com}
comm_mgmt      = {comm_mgmt}
discount_rate  = {discount_rate}
analysis_yrs   = {analysis_yrs}""", language="python")

# ==========================================
# 계산 함수
# ==========================================
def get_com_cap(vac):
    if vac < 5:    return 18.0
    elif vac < 15: return 15.0
    elif vac < 25: return 12.0
    elif vac < 35: return 8.0
    else:          return 5.0

def calc_comm_ratio(pop, solo, lib_exist, sport_exist, gfa):
    lib_need   = max(0, pop/20000 - lib_exist) * 264
    sport_need = max(0, pop/10000 - sport_exist) * 400
    solo_need  = solo * 0.5
    total_need = lib_need + sport_need + solo_need
    return total_need / gfa * 100, total_need, lib_need, sport_need, solo_need

def get_height_surcharge(floors):
    if floors <= 5:    return 1.01
    elif floors <= 10: return 1.03
    elif floors <= 15: return 1.04
    elif floors <= 20: return 1.05
    elif floors <= 25: return 1.06
    elif floors <= 30: return 1.07
    else:              return 1.07 + ((floors-30)//5)*0.01

def calc_irr(cashflows, guess=0.05):
    for g in [0.05, 0.10, 0.01, -0.05, 0.20]:
        try:
            r = g
            for _ in range(500):
                pv  = sum(cf/((1+r)**t) for t,cf in enumerate(cashflows))
                dpv = sum(-t*cf/((1+r)**(t+1)) for t,cf in enumerate(cashflows))
                if abs(dpv) < 1e-10: break
                rn = r - pv/dpv
                if not (-2 < rn < 10): break
                if abs(rn-r) < 1e-8: r=rn; break
                r = rn
            if -1 < r < 5: return r
        except: continue
    return float('nan')

# ==========================================
# Step 1: 커뮤니티 비율 (법적 기준)
# ==========================================
opt_comm_raw, comm_area_need, lib_need, sport_need, solo_need = \
    calc_comm_ratio(total_pop, solo_hh, existing_lib, existing_sport, total_gfa)
opt_comm = max(3.0, round(opt_comm_raw, 1))

# Step 2: 상업 Cap
opt_com = get_com_cap(vac_local)

# Step 3: 주거
opt_res = round(100.0 - opt_com - opt_comm, 1)
if opt_res < 0:
    opt_comm = round(100.0 - opt_com - 10, 1)
    opt_res  = 10.0

# 면적
area_res  = opt_res /100 * total_gfa
area_com  = opt_com /100 * total_gfa
area_comm = opt_comm/100 * total_gfa

# 층수
floors_com   = max(1, round(area_com  / podium_area))
floors_comm  = max(1, round(area_comm / podium_area))
floors_res   = max(1, round(area_res  / (tower_area * tower_count)))
total_floors = floors_com + floors_comm + floors_res

# CAPEX
surcharge       = get_height_surcharge(floors_res)
capex_res_total = area_res * capex_res_base
capex_com_total = area_com * capex_com_base
capex_comm_total= area_comm * capex_comm_base
capex_demo_total= site_area * demo_price
capex_land_total= site_area * land_price
total_capex     = capex_res_total + capex_com_total + capex_comm_total + capex_land_total + capex_demo_total

# 자금 조달
deposit_res   = rent_res * 12 * area_res
deposit_com   = 555232   * area_com
total_deposit = deposit_res + deposit_com

# 생활SOC 보조금
soc_grant_amt  = capex_comm_total * soc_ratio / 100
net_capex_adj  = total_capex - soc_grant_amt

if use_reits:
    # 리츠 구조
    fund_equity_amt = net_capex_adj * fund_eq_ratio/100
    private_eq_amt  = net_capex_adj * (eq_ratio/100 - fund_eq_ratio/100)
    private_eq_amt  = max(private_eq_amt, net_capex_adj * 0.10)
    pf_loan_amt     = net_capex_adj - fund_equity_amt - private_eq_amt
    pf_after_amt    = max(0, pf_loan_amt - total_deposit)
    lr_reits        = loan_rate_pf/100
    af_reits        = (lr_reits*(1+lr_reits)**loan_tenor)/((1+lr_reits)**loan_tenor-1)
    annual_ds_reits = pf_after_amt * af_reits
    annual_fund_div = fund_equity_amt * fund_div_rate/100
    equity          = private_eq_amt
    debt_initial    = pf_loan_amt
    debt_after_refi = pf_after_amt
    annual_ds       = annual_ds_reits
    blended_rate    = lr_reits
else:
    # 일반 PF 구조
    soc_grant_amt  = 0  # 리츠 아닐 때 SOC 별도 처리
    fund_equity_amt = 0
    annual_fund_div = 0

if not use_reits:
    hug_amount      = capex_res_total * hug_pct/100
    equity          = total_capex * eq_ratio/100
    debt_initial    = max(0, total_capex*(1-eq_ratio/100))
    hug_ratio       = hug_amount / total_capex
    blended_rate    = loan_rate_hug/100*hug_ratio + loan_rate_pf/100*(1-hug_ratio)
    lr              = blended_rate
    debt_after_refi = max(0, debt_initial - total_deposit)
    af_refi         = (lr*(1+lr)**loan_tenor)/((1+lr)**loan_tenor-1) if lr>0 else 1/loan_tenor
    annual_ds       = debt_after_refi * af_refi
    annual_fund_div = 0
    fund_equity_amt = 0
    soc_grant_amt   = 0
else:
    debt_after_refi = debt_after_refi
    lr              = blended_rate

# NOI
def get_noi(vac_r):
    nr = rent_res*(1-vac_r/100) - opex_res
    nc = rent_com*(1-vac_com/100) - opex_com
    cc = comm_mgmt * area_comm * 12
    return (area_res*nr + area_com*nc)*12 - cc

# CF (공사기간 + 준공시점 보증금 조기상환 반영)
# 보증금은 준공 첫해 현금 유입 + PF 원금 조기상환으로 처리
# 0년차: 자기자본 투입
initial_cf = -equity
cf_list    = [initial_cf]
noi_list, ds_list, net_list, cum_list = [], [], [], []
cum     = initial_cf
payback = None

for y in range(1, analysis_yrs+1):
    if y <= const_period:
        # 공사중: NOI 없음, 초기대출 이자
        noi = 0
        ds  = debt_initial * lr

    elif y == const_period + 1:
        # 준공 첫해: NOI + 보증금 수령 + 잔여대출 기준 원리금
        op_y  = 1
        vac_r = vac_res_1
        noi   = get_noi(vac_r)
        ds    = annual_ds
        net   = noi - ds - annual_fund_div + total_deposit
        cum  += net
        noi_list.append(noi/1e8)
        ds_list.append(ds/1e8)
        net_list.append(net/1e8)
        cum_list.append(cum/1e8)
        cf_list.append(net)
        if payback is None and cum >= 0: payback = y
        continue

    else:
        op_y  = y - const_period
        vac_r = vac_res_1 if op_y==1 else (vac_res_2 if op_y<=5 else vac_res_3)
        noi   = get_noi(vac_r)
        ds    = annual_ds if y <= loan_tenor + const_period else 0

    net  = noi - ds - annual_fund_div
    cum += net
    noi_list.append(noi/1e8)
    ds_list.append(ds/1e8)
    net_list.append(net/1e8)
    cum_list.append(cum/1e8)
    cf_list.append(net)
    if payback is None and cum >= 0: payback = y

npv_val = sum(cf/(1+discount_rate/100)**t for t,cf in enumerate(cf_list))/1e8
irr_val = calc_irr(cf_list)*100

ann_noi = get_noi(vac_res_3)/1e8
funding_gap = max(0, -npv_val)

# ==========================================
# 메인 화면
# ==========================================
c1,c2,c3,c4,c5,c6 = st.columns(6)
c1.metric("주거", f"{opt_res}%", f"{floors_res}층")
c2.metric("상업", f"{opt_com}%", f"{floors_com}층")
c3.metric("커뮤니티", f"{opt_comm}%", f"{floors_comm}층")
c4.metric("총 CAPEX", f"{total_capex/1e8:.0f}억", "리츠 구조 ✅" if use_reits else "일반 PF")
c5.metric(f"{analysis_yrs}년 NPV", f"{npv_val:+.0f}억", f"실투자 {equity/1e8:.0f}억" if use_reits else "")
if np.isnan(irr_val):
    c6.metric("IRR", "계산중", "")
elif irr_val >= discount_rate:
    c6.metric("IRR", f"{irr_val:.1f}%", f"✅ 할인율({discount_rate}%) 상회")
else:
    c6.metric("IRR", f"{irr_val:.1f}%", f"❌ 할인율({discount_rate}%) 미달")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📊 최적화 결과", "💰 현금흐름(CF)", "⚙️ 상세 검증"])

# ─── 탭1 ───
with tab1:
    left, right = st.columns([1.3, 1])

    with left:
        st.header("Step 1: 커뮤니티 비율 (법적 기준)")
        st.markdown(f"""
| 시설 | 근거 | 필요면적 |
|------|------|:-------:|
| 도서관 | 한국도서관기준 2만명당 1개 | **{lib_need:.0f}㎡** |
| 체육시설 | 국민체육진흥법 1만명당 1개 | **{sport_need:.0f}㎡** |
| 1인가구 공용공간 | {solo_hh:,}가구 × 0.5㎡ | **{solo_need:.0f}㎡** |
| **합계** | | **{comm_area_need:.0f}㎡ ({opt_comm_raw:.1f}%)** |
| **채택 비율** | 최소 3% 이상 | **{opt_comm}%** |
""")

        st.header("Step 2~3: 상업 Cap → 주거 확정")
        st.markdown(f"""
| 단계 | 값 | 근거 |
|------|:--:|------|
| 상업 Cap | {opt_com}% | 지역 공실률 {vac_local}% 기반 |
| 주거 | {opt_res}% | 100% - 상업 - 커뮤니티 잔여 |
""")

        # 연도별 NOI
        st.header("연도별 NOI")
        rows = []
        for label, vac_r in [("1년차",vac_res_1),("2~5년차",vac_res_2),("6년차~",vac_res_3)]:
            nr = rent_res*(1-vac_r/100)-opex_res
            nc = rent_com*(1-vac_com/100)-opex_com
            ra = area_res*nr*12/1e8
            ca = area_com*nc*12/1e8
            cc = comm_mgmt*area_comm*12/1e8
            rows.append({"연차":label,"주거공실":f"{vac_r}%",
                         "주거NOI":f"+{ra:.1f}억","상업NOI":f"+{ca:.1f}억",
                         "커뮤니티":f"-{cc:.1f}억","통합NOI":f"+{ra+ca-cc:.1f}억"})
        st.dataframe(rows, use_container_width=True, hide_index=True)

    with right:
        st.header("건물 형태")
        fig2, ax2 = plt.subplots(figsize=(4, 7))
        ax2.set_xlim(0,1); ax2.set_ylim(0,(floors_res+floors_com+floors_comm)*1.15)
        ax2.set_facecolor('#f0f4f8'); fig2.patch.set_facecolor('white'); ax2.axis('off')

        dx, dy = 1.2, 0.5
        def draw_box(ax, x, y, w, h, d, color, label=None, fs=9):
            from matplotlib.patches import Polygon as MPoly
            import matplotlib.colors as mc
            rgb = mc.to_rgb(color)
            dark = tuple(max(0,c-0.2) for c in rgb)
            darker = tuple(max(0,c-0.35) for c in rgb)
            front = plt.Polygon([[x,y],[x+w,y],[x+w,y+h],[x,y+h]],
                                  closed=True,facecolor=color,edgecolor='white',lw=0.8,alpha=0.95)
            top   = plt.Polygon([[x,y+h],[x+w,y+h],[x+w+d,y+h+dy],[x+d,y+h+dy]],
                                  closed=True,facecolor=dark,edgecolor='white',lw=0.8,alpha=0.75)
            side  = plt.Polygon([[x+w,y],[x+w+d,y+dy],[x+w+d,y+h+dy],[x+w,y+h]],
                                  closed=True,facecolor=darker,edgecolor='white',lw=0.8,alpha=0.60)
            for p in [front,top,side]: ax.add_patch(p)
            if label and h > 1:
                ax.text(x+w/2,y+h/2,label,ha='center',va='center',
                        color='white',fontsize=fs,fontweight='bold',zorder=10)

        pod_x, pod_w = 1.5, 7.0
        draw_box(ax2,pod_x,0,pod_w,floors_com,dx,'#4a9aba',
                 f'상업\n{floors_com}층\n({opt_com:.0f}%)',10)
        draw_box(ax2,pod_x,floors_com,pod_w,floors_comm,dx,'#2ecc71',
                 f'커뮤니티\n{floors_comm}층\n({opt_comm:.0f}%)',10)
        pod_top = floors_com+floors_comm
        # 타워 3개동 - 포디움 위에 올라가도록
        tw = 1.5
        tgap = 0.35
        txs = [pod_x + 0.2,
               pod_x + tw + tgap + 0.2,
               pod_x + (tw+tgap)*2 + 0.2]
        for i,tx in enumerate(txs):
            lbl = f'주거\n{floors_res}층' if i==1 else None
            draw_box(ax2,tx,pod_top,tw,floors_res,dx*0.4,'#0f3460',lbl,9)

        # 포디움-타워 경계선
        ax2.plot([pod_x-0.1, pod_x+pod_w+dx+0.1],
                 [pod_top, pod_top],
                 color='white', lw=2, zorder=5, linestyle='--')

        ax2.text(5,(floors_res+pod_top)*1.06,
                 f'포디움 {pod_top}층 + 타워 {floors_res}층 × 3동',
                 ha='center',fontsize=9,color='#333',fontweight='bold')
        plt.tight_layout()
        st.pyplot(fig2); plt.close()

        # CAPEX
        st.header("CAPEX 구성")
        capex_items = {"주거동":capex_res_total/1e8,"상업동":capex_com_total/1e8,
                       "커뮤니티동":capex_comm_total/1e8,"철거비":capex_demo_total/1e8,"토지비":capex_land_total/1e8}
        fig3, ax3 = plt.subplots(figsize=(5,3))
        colors_c = ['#0f3460','#4a9aba','#2ecc71','#e94560','#f39c12']
        bars = ax3.barh(list(capex_items.keys()),list(capex_items.values()),color=colors_c,edgecolor='white')
        for bar,val in zip(bars,capex_items.values()):
            ax3.text(bar.get_width()+2,bar.get_y()+bar.get_height()/2,
                     f'{val:.0f}억',va='center',fontsize=9)
        ax3.set_xlabel('금액 (억원)')
        ax3.set_title(f'총 CAPEX: {total_capex/1e8:.0f}억원 (고층할증 {surcharge:.2f}배)',fontweight='bold')
        ax3.set_facecolor('#fafafa'); fig3.patch.set_facecolor('white')
        ax3.spines['top'].set_visible(False); ax3.spines['right'].set_visible(False)
        plt.tight_layout()
        st.pyplot(fig3); plt.close()

# ─── 탭2 ───
with tab2:
    st.header("연도별 현금흐름")
    years_list = list(range(1, analysis_yrs+1))
    fig4, (ax4a,ax4b) = plt.subplots(2,1,figsize=(12,8),sharex=True)
    x = np.array(years_list)
    w = 0.28
    ax4a.bar(x-w, noi_list, w, color='#0f3460', alpha=0.8, label='연간 NOI')
    ax4a.bar(x,   [-d for d in ds_list], w, color='#e94560', alpha=0.8, label='대출 상환')
    ax4a.bar(x+w, net_list, w, color='#2ecc71', alpha=0.8, label='순 CF')
    ax4a.axhline(0,color='black',lw=0.8)
    ax4a.set_ylabel('금액 (억원)'); ax4a.legend(fontsize=9)
    ax4a.grid(True,linestyle='--',alpha=0.3); ax4a.set_facecolor('#fafafa')
    ax4a.set_title('연도별 현금흐름',fontweight='bold')

    colors_cum = ['#e94560' if v<0 else '#2ecc71' for v in cum_list]
    ax4b.bar(x, cum_list, color=colors_cum, alpha=0.7)
    ax4b.plot(x, cum_list, 'o-', color='#0f3460', lw=1.5, markersize=4)
    ax4b.axhline(0,color='black',lw=1.2,linestyle='--')
    if payback:
        ax4b.axvline(payback,color='#f39c12',lw=2,linestyle='--',label=f'투자회수 {payback}년차')
        ax4b.legend(fontsize=9)
    ax4b.set_xlabel('연도'); ax4b.set_ylabel('누적 CF (억원)')
    ax4b.set_title('누적 현금흐름',fontweight='bold')
    ax4b.grid(True,linestyle='--',alpha=0.3); ax4b.set_facecolor('#fafafa')
    ax4b.set_xticks(x)
    fig4.patch.set_facecolor('white')
    plt.tight_layout()
    st.pyplot(fig4); plt.close()

    m1,m2,m3,m4,m5 = st.columns(5)
    m1.metric("총 CAPEX", f"{total_capex/1e8:.0f}억")
    m2.metric("보증금 조기상환", f"{total_deposit/1e8:.0f}억", "준공시점 대출 상환")
    m3.metric("실질 대출", f"{debt_after_refi/1e8:.0f}억", f"초기 {debt_initial/1e8:.0f}억 → 보증금 상환")
    m4.metric("투자 회수", f"{payback}년차" if payback else "초과")
    m5.metric("Funding Gap", f"{funding_gap:.0f}억" if funding_gap>0 else "없음 ✅")

# ─── 탭3 ───
with tab3:
    st.header("자금 조달 구조")
    st.markdown(f"""
| 항목 | 금액 | 금리 | 비고 |
|------|-----:|:----:|------|
| 주거동 건설비 | {capex_res_total/1e8:.0f}억 | {loan_rate_hug}% | HUG 공공지원 민간임대 융자 |
| 상업동 건설비 | {capex_com_total/1e8:.0f}억 | {loan_rate_pf}% | 민간 PF |
| 커뮤니티 건설비 | {capex_comm_total/1e8:.0f}억 | — | 시(市) 부담 시 0 입력 |
| 토지비 + 철거비 | {(capex_land_total+capex_demo_total)/1e8:.0f}억 | {loan_rate_pf}% | 민간 PF |
| 보증금 활용 | -{total_deposit/1e8:.0f}억 | — | 초기 대출 감소 |
| **가중평균 금리** | | **{blended_rate*100:.2f}%** | |
""")

    st.header("알고리즘 판정")
    checks = [
        ("커뮤니티 법적 기준", f"{opt_comm}% (필요 {opt_comm_raw:.1f}%)", opt_comm >= opt_comm_raw),
        ("NOI 양수", f"연간 +{ann_noi:.1f}억", ann_noi > 0),
        (f"{analysis_yrs}년 NPV", f"{npv_val:+.0f}억", npv_val > 0),
        ("IRR vs 할인율", f"{irr_val:.1f}% vs {discount_rate}%" if not np.isnan(irr_val) else "계산불가",
         not np.isnan(irr_val) and irr_val >= discount_rate),
    ]
    for name, detail, ok in checks:
        st.markdown(f"{'✅' if ok else '❌'} **{name}** — {detail}")

    if funding_gap > 0:
        st.warning(f"⚠️ Funding Gap: **{funding_gap:.0f}억원** — 공공기여 최소 필요액")
        st.markdown(f"> 커뮤니티 건설비(시 부담) 외 추가 {funding_gap:.0f}억원의 공공지원 시 사업성 확보")
    else:
        st.success("✅ 추가 공공지원 없이 자생 가능")

    st.header("알고리즘 경로")
    st.markdown(f"""
| 단계 | 내용 | 값 |
|------|------|:--:|
| Step 1 | 도서관 필요면적 | {lib_need:.0f}㎡ |
| Step 1 | 체육시설 필요면적 | {sport_need:.0f}㎡ |
| Step 1 | 1인가구 공용공간 | {solo_need:.0f}㎡ |
| Step 1 | **커뮤니티 비율 확정** | **{opt_comm}%** |
| Step 2 | 상업 Cap (공실률 {vac_local}%) | {opt_com}% |
| Step 3 | **주거 비율 확정** | **{opt_res}%** |
| Step 4 | 가중평균 금리 | {blended_rate*100:.2f}% |
| Step 5 | 보증금 대출 감소 | {total_deposit/1e8:.0f}억 |
""")
