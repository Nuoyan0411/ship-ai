import streamlit as st
from openai import OpenAI

client = OpenAI(
    api_key="sk-ws-H.YYEIMIX.5L1z.MEUCIQDuFuVRNBR8hiQAl7hFKWWZsvyNbiYJj7FVIH1kesz7gAIgMOr8EifT7zgW5ovnqYXqCOJa-9c4SwBv1aHWX10kGAI",
    base_url="https://ws-6jnunfa680cv3mzb.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
)
st.title("船舶故障诊断助手")

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

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if prompt := st.chat_input("请输入故障现象..."):
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model="qwen-plus",
        messages=st.session_state.messages
    )
    answer = response.choices[0].message.content
    st.chat_message("assistant").write(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})