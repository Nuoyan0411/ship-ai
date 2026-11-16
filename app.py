import streamlit as st
import io
import csv
from datetime import datetime

# ======================
# 页面配置
# ======================
st.set_page_config(
    page_title="船舶主机诊断助手",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

    # --- 机型选择 ---
    st.subheader("🔧 机型设置")
    selected_model = st.sidebar.radio(
        "当前主机型号：",
        ["通用", "MAN B&W MC", "Wärtsilä X-DF", "WinGD X-DF"],
        index=0
    )

    st.markdown("---")

    # --- 一键导出 Excel ---
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
        df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='黑烟排查表')
            wb = writer.book
            ws = writer.sheets['黑烟排查表']

            header_font = Font(name='Microsoft YaHei', bold=True, size=11, color='FFFFFF')
            header_fill = PatternFill(start_color='2C3E50', end_color='2C3E50', fill_type='solid')
            align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
            align_left = Alignment(horizontal='left', vertical='center', wrap_text=True)
            border = Border(
                left=Side(style='thin'), right=Side(style='thin'),
                top=Side(style='thin'), bottom=Side(style='thin')
            )

            for col_num, column_title in enumerate(df.columns, 1):
                cell = ws.cell(row=1, column=col_num)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = align_center
                cell.border = border

            for row_num in range(2, len(df) + 2):
                for col_num, column_title in enumerate(df.columns, 1):
                    cell = ws.cell(row=row_num, column=col_num)
                    cell.alignment = align_left if column_title in ["检查方法与要点", "标准值 / 判据", "工具/仪表要求", "风险提示 & 处置建议"] else align_center
                    cell.border = border

            for column in ws.columns:
                max_length = 0
                column_letter = get_column_letter(column[0].column)
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                ws.column_dimensions[column_letter].width = adjusted_width

            ws.freeze_panes = 'A2'

        output.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"主机黑烟排查表_{timestamp}.xlsx"

        st.success("✅ Excel 已生成！点击下方按钮下载。")
        st.download_button(
            label="⬇️ 下载 Excel",
            data=output,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key="download_excel"
        )

    st.markdown("---")
    st.caption("💡 提示：本表依据 MAN B&W / WinGD / Wärtsilä 主流主机维护规范编制，实际使用请以船级社及设备厂商最新手册为准。")

# ======================
# 主内容区：对话
# ======================
st.title("🚢 船舶主机智能诊断助手")

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

    # 调用 AI
    with st.chat_message("assistant"):
        response = st.write_stream(
            st.session_state.client.chat.completions.create(
                model="gpt-4o",
                messages=messages_for_ai,
                stream=True
            )
        )
    st.session_state.messages.append({"role": "assistant", "content": response})