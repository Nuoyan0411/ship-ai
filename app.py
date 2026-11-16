import streamlit as st
from openai import OpenAI

client = OpenAI(
    api_key="sk-ws-H.YYEIMIX.5L1z.MEUCIQDuFuVRNBR8hiQAl7hFKWWZsvyNbiYJj7FVIH1kesz7gAIgMOr8EifT7zgW5ovnqYXqCOJa-9c4SwBv1aHWX10kGAI",
    base_url="https://ws-6jnunfa680cv3mzb.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
)
st.title("船舶故障诊断助手")

if "messages" not in st.session_state:
    st.session_state.messages = []

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