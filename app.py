


import streamlit as st
import io
import csv
import re

from datetime import datetime

DEFAULT_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_MODEL = "qwen-plus"


def generate_diagnosis(user_input: str, model_type: str) -> str:
    """离线规则诊断：基于关键词匹配主机故障"""
    # 安全类型转换，防止非字符串输入报错
    text = str(user_input).lower()

    rules = [
        {
            "keywords": ["黑烟", "冒烟", "排烟"],
            "response": (
                "🔍 **可能原因分析（主机冒黑烟）**\n\n"
                "1. **燃油系统问题**\n"
                "   - 喷油器雾化不良或滴漏 → 检查启阀压力，清洗或更换喷油器\n"
                "   - 燃油粘度过高 → 核对 HFO 加热温度（应 ≥130℃）\n"
                "2. **进气系统问题**\n"
                "   - 扫气压力不足 → 检查增压器、空冷器是否脏堵\n"
                "⚠️ **建议排查顺序**：喷油器 → 燃油粘度 → 扫气压力"
            ),
        },
        {
            "keywords": ["排气温度", "排温高"],
            "response": (
                "🔍 **可能原因分析（排气温度偏高）**\n\n"
                "1. **单缸排温高** → 检查该缸喷油器或排气阀\n"
                "2. **各缸排温普遍偏高** → 检查增压器效率、空冷器脏堵\n"
                "⚠️ **建议**：先对比各缸温差，若单缸温差 >30℃ 则重点排查该缸。"
            ),
        },
        {
            "keywords": ["启动", "起动"],
            "response": (
                "🔍 **可能原因分析（主机启动困难）**\n\n"
                "1. **启动空气系统** → 压力不足（应 ≥2.5 MPa）\n"
                "2. **燃油系统** → 燃油未切换到位或管路有空气\n"
                "⚠️ **建议**：先确认空气瓶压力，再听诊启动阀有无漏气声。"
            ),
        },
        {
            "keywords": ["滑油压力", "油压低"],
            "response": (
                "🔍 **可能原因分析（滑油压力偏低）**\n\n"
                "1. **油位不足** → 检查循环柜油位，及时补油\n"
                "2. **滑油滤器脏堵** → 切换备用滤器并清洗\n"
                "3. **滑油泵故障** → 检查泵体磨损、安全阀设定\n"
                "⚠️ **建议**：压力低于报警值应立即降速，低于停机值必须停车检查。"
            ),
        },
        {
            "keywords": ["冷却水", "水温高", "淡水温度"],
            "response": (
                "🔍 **可能原因分析（冷却水温度偏高）**\n\n"
                "1. **淡水膨胀柜水位低** → 补水并查漏点\n"
                "2. **海水管路堵塞** → 检查海水滤器、海底阀\n"
                "3. **淡水冷却器效率下降** → 开盖清洗管束\n"
                "⚠️ **建议**：水温持续升高时先降负荷，避免缸套过热变形。"
            ),
        },
        {
            "keywords": ["振动", "抖动", "异常震动"],
            "response": (
                "🔍 **可能原因分析（主机振动异常）**\n\n"
                "1. **轴系对中不良** → 检查轴承间隙、曲轴拐挡差\n"
                "2. **某缸燃烧不均** → 对比各缸爆发压力与排温\n"
                "3. **地脚螺栓松动** → 检查机架固定螺栓\n"
                "⚠️ **建议**：振动突然加剧应立即降速，排查曲轴、轴承状态。"
            ),
        },
        {
            "keywords": ["喘振", "增压器异响"],
            "response": (
                "🔍 **可能原因分析（增压器喘振）**\n\n"
                "1. **空冷器脏堵** → 扫气阻力增大，需清洗\n"
                "2. **排气系统背压过高** → 检查锅炉烟道挡板、废气旁通阀\n"
                "3. **负荷突变** → 避免快速加车\n"
                "⚠️ **建议**：喘振时立即降负荷，手动打开放气阀，检查压气机叶轮状态。"
            ),
        },
        {
            "keywords": ["扫气箱", "着火", "扫气高温"],
            "response": (
                "🔍 **可能原因分析（扫气箱着火）**\n\n"
                "1. **活塞环磨损/断裂** → 燃气下窜至扫气箱\n"
                "2. **喷油器漏油** → 未燃燃油积聚扫气箱\n"
                "3. **扫气温度过高** → 空冷器冷却不足\n"
                "⚠️ **建议**：发现扫气温度骤升立即降速，必要时停车，使用蒸汽/CO₂灭火，严禁立即打开道门。"
            ),
        },
        {
            "keywords": ["漏油", "燃油泄漏"],
            "response": (
                "🔍 **可能原因分析（燃油泄漏）**\n\n"
                "1. **高压油管破裂** → 检查管路老化、接头松动\n"
                "2. **喷油器密封失效** → 更换O型圈或整套喷油器\n"
                "3. **燃油泵填料函磨损** → 检查泵体密封\n"
                "⚠️ **建议**：发现漏油立即隔离泄漏点，清理现场，注意防火防爆。"
            ),
        },
        {
            "keywords": ["缸套", "磨损", "拉缸"],
            "response": (
                "🔍 **可能原因分析（缸套磨损/拉缸）**\n\n"
                "1. **润滑不足** → 检查气缸油注油器是否正常工作\n"
                "2. **冷却不良** → 缸套水温过高导致油膜破坏\n"
                "3. **燃烧不良** → 积碳加剧磨料磨损\n"
                "⚠️ **建议**：滑油中出现大量金属屑或缸套水温度异常升高时，立即降速并准备吊缸检查。"
            ),
        },
    ]

    for rule in rules:
        if any(kw in text for kw in rule["keywords"]):
            return rule["response"]

    return (
        "🔍 **未匹配到具体故障模式**\n"
        "请尝试描述：主机冒黑烟、排气温度高、启动困难、滑油压力低、振动异常等。"
    )


# ======================
# 页面配置
# ======================
st.set_page_config(
    page_title=" Ship-AI 船舶主机诊断助手",
    page_icon="⚓️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 注入「深海航海」主题 CSS（仅美化外观，不动任何逻辑）
st.markdown("""
<style>
/* ===================== 深海航海主题 Ship-AI ===================== */
.stApp, [data-testid="stAppViewContainer"] {
    background: radial-gradient(circle at 20% -10%, #14417a 0%, #0b2545 55%, #05121f 100%) !important;
}
[data-testid="stAppViewContainer"] > .main { background: transparent !important; }
header[data-testid="stHeader"] { background: transparent !important; }
html, body, [class*="css"] { color: #dbeafe !important; }

/* 侧边栏：深色玻璃面板 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0a2140 0%, #06162a 100%) !important;
    border-right: 1px solid rgba(56,189,248,.35) !important;
}
[data-testid="stSidebar"] * { color: #e0f2fe !important; }

/* 输入框 / 密码框 */
[data-testid="stTextInput"] input, [data-testid="stTextInput"] [data-baseweb="input"] > div {
    background: rgba(2,20,40,.55) !important;
    border: 1px solid rgba(56,189,248,.4) !important;
    color: #e0f2fe !important;
    border-radius: 10px !important;
}

/* 主按钮：渐变蓝 + 悬停上浮 */
.stButton > button, [data-testid="stDownloadButton"] > button, .stFormSubmitButton > button {
    background: linear-gradient(135deg, #0284c7, #38bdf8) !important;
    border: none !important;
    color: #ffffff !important;
    border-radius: 12px !important;
    padding: .6rem 1.1rem !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 14px rgba(56,189,248,.35) !important;
    transition: transform .18s ease, box-shadow .18s ease !important;
}
.stButton > button:hover, [data-testid="stDownloadButton"] > button:hover {
    transform: translateY(-3px) !important;
    box-shadow: 0 9px 24px rgba(56,189,248,.6) !important;
}

/* 对话输入框 */
[data-testid="stChatInput"] textarea {
    background: rgba(2,20,40,.6) !important;
    border: 1px solid rgba(56,189,248,.5) !important;
    color: #e0f2fe !important;
    border-radius: 14px !important;
}

/* 聊天气泡：毛玻璃卡片 */
[data-testid="stChatMessage"] {
    background: rgba(13,42,74,.55) !important;
    backdrop-filter: blur(6px);
    border: 1px solid rgba(56,189,248,.25) !important;
    border-radius: 16px !important;
    padding: .9rem 1.1rem !important;
    margin-bottom: .8rem !important;
}

/* 提示条 */
[data-testid="stAlert"] { border-radius: 12px !important; }

/* Hero 标题横幅 */
.ship-hero {
    background: linear-gradient(120deg, rgba(2,132,199,.92), rgba(56,189,248,.6));
    border: 1px solid rgba(125,211,252,.5);
    border-radius: 18px;
    padding: 1.4rem 1.6rem;
    box-shadow: 0 10px 30px rgba(2,20,40,.5);
    color: #f0f9ff;
    margin-bottom: 1.1rem;
}
.ship-hero .t { font-size: 2rem; font-weight: 800; letter-spacing: 1px; margin: 0; }
.ship-hero .s { margin: .4rem 0 0; opacity: .92; font-size: 1.05rem; }

/* ============ 动效层（第7轮承诺项，此处补齐） ============ */
/* 1) 对话气泡：上浮淡入进场 */
[data-testid="stChatMessage"] { animation: fadeSlideIn .45s ease-out both; }
@keyframes fadeSlideIn {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}

/* 2) 按钮流光：悬停时一道高光从左扫到右 */
.stButton > button, [data-testid="stDownloadButton"] > button {
    position: relative !important;
    overflow: hidden !important;
}
.stButton > button::before, [data-testid="stDownloadButton"] > button::before {
    content: '' !important;
    position: absolute;
    top: 0; left: -120%;
    width: 60%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.55), transparent);
    transform: skewX(-20deg);
    pointer-events: none;
}
.stButton > button:hover::before, [data-testid="stDownloadButton"] > button:hover::before {
    animation: shineSweep .75s ease-out;
}
@keyframes shineSweep {
    from { left: -120%; }
    to   { left: 160%; }
}

/* 3) Hero 横幅：缓慢流动的光带，纯 CSS 不卡页面 */
.ship-hero { position: relative; overflow: hidden; }
.ship-hero::after {
    content: '';
    position: absolute;
    inset: 0;
    background: linear-gradient(115deg, transparent 40%, rgba(255,255,255,.18) 50%, transparent 60%);
    background-size: 250% 100%;
    animation: heroFlow 6s linear infinite;
    pointer-events: none;
}
@keyframes heroFlow {
    from { background-position: 120% 0; }
    to   { background-position: -120% 0; }
}

/* 4) AI 输出表格的界面美化 */
[data-testid="stMarkdownContainer"] table th {
    background: rgba(2,132,199,.55) !important;
    color: #f0f9ff !important;
}
[data-testid="stMarkdownContainer"] table tr:hover td {
    background: rgba(56,189,248,.10) !important;
}

/* 评委笔记本性能差时自动降级动效，不影响任何功能 */
@media (prefers-reduced-motion: reduce) {
    [data-testid="stChatMessage"], .ship-hero::after,
    .stButton > button:hover::before, [data-testid="stDownloadButton"] > button:hover::before {
        animation: none !important;
    }
}

/* ===== 动效增强：弹入 / 流光 / 呼吸灯 / 表格美化 ===== */
@keyframes shipFadeUp { from { opacity:0; transform:translateY(16px);} to { opacity:1; transform:translateY(0);} }
[data-testid="stChatMessage"] { animation: shipFadeUp .5s ease-out both; }

.stButton > button, [data-testid="stDownloadButton"] > button { position:relative; overflow:hidden; }
@keyframes shipShine { 0%{background-position:-200% 0;} 100%{background-position:200% 0;} }
.stButton > button::after, [data-testid="stDownloadButton"] > button::after {
  content:''; position:absolute; inset:0; pointer-events:none; opacity:0;
  background:linear-gradient(120deg, transparent 30%, rgba(255,255,255,.5) 50%, transparent 70%);
  background-size:200% 100%;
}
.stButton > button:hover::after, [data-testid="stDownloadButton"] > button:hover::after {
  opacity:1; animation: shipShine .9s ease;
}
@keyframes shipPulse { 0%,100%{opacity:.35;} 50%{opacity:1;} }
.ship-thinking { color:#7dd3fc; font-weight:700; animation: shipPulse 1.4s infinite; }

[data-testid="stMarkdownContainer"] table { border-collapse:collapse; width:100%; margin:.4rem 0; }
[data-testid="stMarkdownContainer"] th { background:rgba(2,132,199,.4); color:#f0f9ff; }
[data-testid="stMarkdownContainer"] td { background:rgba(2,20,40,.25); }
[data-testid="stMarkdownContainer"] th, [data-testid="stMarkdownContainer"] td {
  border:1px solid rgba(56,189,248,.45); padding:8px 10px; color:#e0f2fe;
}

</style>
""", unsafe_allow_html=True)

# ======================
# 初始化对话历史
# ======================
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "system",
        "content": (
            "你是船舶轮机员的专业助手，专注船舶主机（船用柴油机）、"
            "辅机、轴系、锅炉的故障诊断。用户说的'主机'指船舶主机，"
            "不是计算机。回答要结合二冲程/四冲程柴油机原理，"
            "给出可能原因、排查步骤和处置建议。"
        )
    }]

# ======================
# 侧边栏
# ======================
with st.sidebar:
    st.title("⚙️ 主机诊断工具")
    st.markdown("---")
    # --- AI 设置 ---
    st.subheader("🤖 AI 设置")
    api_key = st.text_input(
        "API Key（阿里云百炼，sk- 开头）",
        type="password",
        help="把你百炼控制台生成的 Key 整串粘贴进来，开头是 sk-，前后不要有空格。"
    )
    base_url = st.text_input(
        "接口地址（一般不用改）",
        value=DEFAULT_BASE_URL,
        help="默认国内版地址。若你的 Key 是国际版/新加坡站建的，改成 https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    )
    model_name = st.text_input(
        "模型名",
        value=DEFAULT_MODEL,
        help="百炼支持的模型，如 qwen-plus / qwen-flash / qwen-turbo"
    )

    if api_key:
        cfg_sig = (api_key, base_url)
        if "client" not in st.session_state or st.session_state.get("_cfg") != cfg_sig:
            try:
                from openai import OpenAI
                # ★核心修复：这里必须同时告诉它 Key 和「去哪里连」(base_url)，缺一不可
                st.session_state.client = OpenAI(api_key=api_key, base_url=base_url)
                st.session_state["_cfg"] = cfg_sig
                st.success("✅ 客户端已就绪，在线 AI 可用")
            except Exception as e:
                st.error(f"初始化失败：{e}")
    else:
        st.info("未填写 API Key，将使用离线规则诊断")

    st.markdown("---")
    # --- 机型选择 ---
    st.subheader("🔧 机型设置")
    selected_model = st.radio(
        "当前主机型号：",
        ["通用", "MAN B&W MC", "Wärtsilä X-DF", "WinGD X-DF"],
        index=0
    )

    st.markdown("---")

    # --- 一键导出排查表 (CSV版，安全无拦截) ---
    st.subheader("📥 一键导出排查表")
    if st.button("生成并下载", type="primary", use_container_width=True):
        data = {
            "序号": list(range(1, 11)),
            "检查项目": [
                "扫气箱状态", "燃油粘度与温度", "喷油器启阀压力（抽查）",
                "气阀间隙（重点排气阀）", "增压器状态", "扫气压力建立速度",
                "各缸排气温度均衡性", "启动空气压力衰减",
                "黑烟持续时间与形态", "曲柄箱滑油状态"
            ],
            "检查方法与要点": [
                "打开扫气箱道门，目视检查：有无油渍、积碳、残留火苗；手摸温度是否异常升高",
                "查燃油日志+现场核对：重油（HFO）进机粘度/温度；轻油（MDO）是否切换到位",
                "随机拆检1–2缸喷油器（优先怀疑缸），在试验台上校验启阀压力",
                "盘车至TDC后，用塞尺测量排气阀冷态间隙（按说明书冷态值）",
                "手动转动增压器涡轮端（停机状态），听有无异响；查压气机叶轮是否碰擦、叶片是否变形",
                "观察集控屏扫气压力表：从0升至额定值70%所需时间",
                "启动后30秒，用红外测温仪逐缸测量排气支管温度（避开热辐射干扰）",
                "观察启动空气瓶压力下降速率（启动一次压降应≤0.3MPa）",
                "记录：黑烟是否在转速达20%额定转速后仍持续？是否伴随'噗噗'漏气声？",
                "启动后运行2分钟，停机立即取样检查滑油：颜色、气味、有无乳化/金属屑"
            ],
            "标准值 / 判据": [
                "内壁干燥清洁；无油泥堆积；温度 ≤ 环境温度+10℃",
                "HFO：粘度 12–15 cSt @ 50℃；温度 ≥ 130℃（依粘度曲线）\nMDO：≤ 5 cSt，温度 ≥ 40℃",
                "MAN：350±10 bar；WinGD：380±10 bar；Wärtsilä 31：320±5 bar（查手册）",
                "MAN MC：0.60–0.70 mm；WinGD X72：0.55–0.65 mm；Wärtsilä 31：0.45–0.55 mm",
                "自由旋转无卡滞、无金属摩擦声；叶轮无裂纹/变形",
                "≥ 额定值的70%，且在启动后 15秒内达到",
                "各缸温差 ≤ 30℃（冷态启动允许≤50℃，但持续超差即异常）",
                "单次启动压降 ≤ 0.3 MPa（如初始3.0MPa→结束≥2.7MPa）",
                "正常：冷机启动黑烟 ≤ 20秒，随转速上升迅速变淡\n异常：＞30秒不减/单缸持续冒烟",
                "清澈琥珀色，无刺激酸味，无水珠/泡沫，滤网无大量银色金属屑"
            ],
            "工具/仪表要求": [
                "手电筒、红外测温仪（可选）",
                "粘度计（台架）、温度计、燃油加热器控制面板",
                "喷油器试验台、压力表、密封垫片",
                "塞尺（0.02–1.00mm）、盘车机、拐挡表",
                "手电筒、听音棒、安全手套",
                "集控台压力表、秒表",
                "红外测温仪（精度±2℃）、防护面罩",
                "空气瓶压力表、秒表",
                "秒表、听音棒、目视（白天/强光下）",
                "取样瓶、滤纸、放大镜、pH试纸（可选）"
            ],
            "风险提示 & 处置建议": [
                "⚠️ 发现油迹/焦糊味→立即清理并查漏油源（活塞环/扫气泵密封）；着火痕迹须报公司并做气密试验",
                "❌ 粘度过高→开启蒸汽加热器旁通阀，延长预热时间；严禁强行启动！",
                "✅ 启阀压力偏低→更换弹簧或整套喷油器；针阀卡滞→超声波清洗或更换",
                "❌ 间隙＜下限→排气阀关闭不严→压缩不良；＞上限→启闭延迟→影响换气；调整后必须复测并记录",
                "⚠️ 卡滞或异响→禁止启动！联系厂家评估轴承/转子状态",
                "❌ 建立缓慢→查空冷器脏堵、增压器喘振、扫气管泄漏；启动中勿强行加负荷！",
                "✅ 单缸低温+黑烟→该缸喷油器/气阀/活塞环故障；高温+黑烟→可能后燃严重，查喷油定时",
                "❌ 衰减过快→查启动阀漏气、气缸启动阀卡死、主启动阀内漏；需做气密试验",
                "⚠️ 持续黑烟+漏气声→立即停机吊缸；仅短暂黑烟（≤15s）且暖机后消失→属可接受冷态燃烧恶化",
                "❌ 乳化→查缸套漏水；银色细屑→活塞环/缸套早期磨损；黑色油泥→氧化严重，需换油并查冷却系统"
            ]
        }

        # 把字典转成行，保留原来的列顺序
        headers = [
            "序号",
            "检查项目",
            "检查方法与要点",
            "标准值 / 判据",
            "工具/仪表要求",
            "风险提示 & 处置建议",
        ]
        rows = list(zip(*[data[k] for k in headers]))

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(headers)
        writer.writerows(rows)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"主机黑烟排查表_{timestamp}.csv"

        st.success("✅ 排查表已生成！点击下方按钮下载（可用 Excel 直接打开）。")
        st.download_button(
            label="⬇️ 下载排查表 (.csv)",
            data=output.getvalue(),
            file_name=filename,
            mime="text/csv",
            use_container_width=True,
            key="download_csv",
        )

    st.markdown("---")
    st.caption(
        "💡 提示：本表依据 MAN B&W / WinGD / Wärtsilä 主流主机维护规范编制，实际使用请以船级社及设备厂商最新手册为准。"
    )

# ======================
# 主内容区：对话
# ======================
st.markdown(
    """
    <div class="ship-hero">
        <div class="t">⚓️ 船舶主机智能诊断助手</div>
        <div class="s">🛠️ 在线大模型 + 离线规则双引擎 · 为轮机员提供专业故障诊断</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 显示历史消息（跳过 system）
for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入
if prompt := st.chat_input("描述主机故障现象，例如：主机启动时冒黑烟"):
    # 显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 构建发送给 AI 的消息（加入机型信息）
    messages_for_ai = []
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            # 把机型信息追加到系统提示词
            enhanced_system = msg["content"] + f"\n用户当前机型为：{selected_model}，请根据机型调整回答。"
            messages_for_ai.append({"role": "system", "content": enhanced_system})
        else:
            messages_for_ai.append(msg)

    # 调用 AI（双模式：在线流式 / 离线兜底）
    # 1. 优先尝试在线 AI 流式输出
    if api_key and "client" in st.session_state:
        def generate_stream(messages_for_ai, user_prompt, m_type, m_name):
            full = ""
            degraded = False
            try:
                stream = st.session_state.client.chat.completions.create(
                    model=m_name,
                    messages=messages_for_ai,
                    stream=True
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        full += delta
                        yield delta
            except Exception as e:
                # 把真正的报错打印到终端，也显示到页面上，方便排查
                print(f"【真正的报错是】: {e}")
                st.session_state["_last_error"] = str(e)
                degraded = True

            if degraded and not full:
                st.error("⚠️ 在线 AI 调用失败，已自动切换至离线规则诊断模式。")
                st.caption(f"（技术细节：{st.session_state.get('_last_error', '')}）")
                # 在线失败后安全降级为离线规则
                full = generate_diagnosis(user_prompt, m_type)
                yield full

            # 统一在流结束后写入历史，避免重复记录
            if full:
                st.session_state.messages.append({"role": "assistant", "content": full})

        with st.chat_message("assistant"):
            st.write_stream(generate_stream(messages_for_ai, prompt, selected_model, model_name))

    # 2. 未填写 Key 时，直接输出离线规则
    else:
        response = generate_diagnosis(prompt, selected_model)
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# 【侧边栏专业信息显示】
with st.sidebar:
    st.markdown("# ⚓️ 系统信息")
    st.divider()

    st.markdown("### 🛠️ 技术栈")
    st.success("Streamlit 前端框架")
    st.success("OpenAI 智能诊断引擎")
    st.success("轮机工程领域知识库")

    st.divider()
    st.markdown("### 💡 使用指南")
    st.markdown(
        "1. 离线模式：使用关键词匹配排查常见故障。\n"
        "2. 在线模式：在侧边栏填好 API Key，直接描述故障现象，AI 将结合大模型给出深度分析与建议。\n"
        "3. 建议优先使用【导出排查表】功能留存记录。"
    )
    st.divider()
    st.caption(f"当前系统时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")

# 【对话记录导出功能 · 增强版：表格可导出 / 可直接转 PPT】
def _clean_for_export(text):
    """清洗 AI 回复里可能残留的 HTML 标签，保证导出的 md 干净、转 PPT 不乱码"""
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r"<[^>]+>", "", text).strip()

def _extract_md_tables(text):
    """从一段文本里抽出所有 markdown 表格，返回 [表, 表...]，每个表是原始行列表"""
    lines = str(text).splitlines()
    tables, buf = [], []
    for ln in lines:
        s = ln.strip()
        if s.startswith("|") and s.count("|") >= 2:
            buf.append(s)
        else:
            if len(buf) >= 2:
                tables.append(buf)
            buf = []
    if len(buf) >= 2:
        tables.append(buf)
    return tables

def _md_table_to_rows(md_lines):
    """把 markdown 表格行解析成二维列表，跳过 |---| 分隔行"""
    rows = []
    for ln in md_lines:
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        is_div = (
            all(re.fullmatch(r":?-{2,}:?", c) for c in cells)
            and any("-" in c for c in cells)
        )
        if is_div:
            continue
        rows.append(cells)
    return rows

st.divider()
st.subheader("📝 导出本次对话记录")

ts = datetime.now().strftime("%Y%m%d_%H%M")

# —— Markdown 版：表格原生保留，可直接拖进 Gamma / WPS AI / MindShow 一键生成 PPT ——
md_text = "# Ship-AI 轮机故障诊断记录\n\n"
md_text += f"> 主机机型：{selected_model}    导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n---\n\n"
has_chat = False
for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    has_chat = True
    who = "👤 用户" if msg["role"] == "user" else "🤖 助手"
    md_text += f"### {who}\n\n{_clean_for_export(msg['content'])}\n\n"
if not has_chat:
    md_text += "_暂无对话记录。_\n"

# —— 纯文本版 ——
plain = "Ship-AI 轮机故障诊断记录\n" + "=" * 30 + "\n\n"
for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    who = "用户" if msg["role"] == "user" else "助手"
    plain += f"[{who}]: {_clean_for_export(msg['content'])}\n\n"
if not has_chat:
    plain += "暂无对话记录。\n"
plain += f"\n导出时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

c1, c2 = st.columns(2)
with c1:
    st.download_button(
        "📊 下载对话记录 (.md · 含表格 · 可转PPT)",
        data=md_text,
        file_name=f"Ship-AI_Diagnosis_{ts}.md",
        mime="text/markdown;charset=utf-8",
        use_container_width=True,
    )
with c2:
    st.download_button(
        "📄 下载对话记录 (.txt 纯文本)",
        data=plain.encode("utf-8-sig"),
        file_name=f"Ship-AI_Diagnosis_{ts}.txt",
        mime="text/plain;charset=utf-8",
        use_container_width=True,
    )

# —— 单独把对话里出现的表格抽出来导出成 CSV（Excel 直接打开 / 贴进 PPT）——
_all_tables = []
for msg in st.session_state.messages:
    if msg["role"] == "system":
        continue
    for t in _extract_md_tables(msg["content"]):
        _all_tables.append(t)

if _all_tables:
    st.caption(f"🔎 检测到对话中含 {len(_all_tables)} 个表格，可单独导出为 Excel 可打开的 CSV：")
    csv_out = io.StringIO()
    writer = csv.writer(csv_out)
    for ti, tbl in enumerate(_all_tables, 1):
        writer.writerow([f"—— 表格 {ti} ——"])
        writer.writerow([])
        for row in _md_table_to_rows(tbl):
            writer.writerow(row)
        writer.writerow([])
    # ★ 关键修复：必须写入 UTF-8 BOM（utf-8-sig），否则中文 Windows 的 Excel
    #    会按 GBK 解码，双击打开就是一片乱码。这是上一版乱码的唯一原因。
    st.download_button(
        "📥 下载对话中的全部表格 (.csv)",
        data=csv_out.getvalue().encode("utf-8-sig"),
        file_name=f"Ship-AI_Tables_{ts}.csv",
        mime="text/csv;charset=utf-8",
        use_container_width=True,
    )
    # —— 追加：同样的表格再导出一份真 .xlsx（二进制格式，不存在任何编码问题）——
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill
        from openpyxl.utils import get_column_letter

        wb = Workbook()
        ws = wb.active
        ws.title = "诊断表格"
        _title_font = Font(bold=True, color="FFFFFF")
        _title_fill = PatternFill("solid", fgColor="0284C7")

        r = 1
        for ti, tbl in enumerate(_all_tables, 1):
            ws.cell(row=r, column=1, value=f"表格 {ti}")
            ws.cell(row=r, column=1).font = _title_font
            ws.cell(row=r, column=1).fill = _title_fill
            r += 1
            rows_parsed = _md_table_to_rows(tbl)
            for ci, row in enumerate(rows_parsed):
                for cj, val in enumerate(row, start=1):
                    cell = ws.cell(row=r, column=cj, value=val)
                    cell.alignment = Alignment(vertical="center", wrap_text=True)
                    if ci == 0:
                        cell.font = _title_font
                        cell.fill = _title_fill
                r += 1
            r += 1
        # 自适应列宽（中文按2倍宽度估算）
        for col in range(1, ws.max_column + 1):
            width = 10
            for row in range(1, ws.max_row + 1):
                v = ws.cell(row=row, column=col).value
                if v:
                    w = sum(2 if ord(ch) > 127 else 1 for ch in str(v))
                    width = max(width, min(w + 2, 60))
            ws.column_dimensions[get_column_letter(col)].width = width

        xlsx_buffer = io.BytesIO()
        wb.save(xlsx_buffer)
        st.download_button(
            "📗 下载对话中的全部表格 (.xlsx · Excel零乱码)",
            data=xlsx_buffer.getvalue(),
            file_name=f"Ship-AI_Tables_{ts}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
        st.caption("✅ 已加 UTF-8 BOM，Excel 双击直接打开即可；.xlsx 为二进制格式，任何机器都不会乱码。")
    except Exception as _e:
        st.caption(f"（.xlsx 导出需要 openpyxl，当前不可用：{_e}。CSV 仍可正常打开。）")
        st.caption("✅ CSV 已加 UTF-8 BOM，Excel 双击直接打开不会乱码。")
else:
    st.caption("（当前对话中暂未检测到表格。提问时加一句「用表格列出排查项」，AI 输出表格后这里会自动出现 CSV / xlsx 下载按钮。）")
