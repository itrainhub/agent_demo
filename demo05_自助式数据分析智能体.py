"""
自助式数据分析智能体
@File       demo05_自助式数据分析智能体.py
@Author     小明
@Date       2025/11/21 14:05
@Version    V0.0.1
"""
import json

import streamlit as st
import pandas as pd
from langchain_experimental.agents import create_pandas_dataframe_agent
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

# 提示词前缀
PROMPT_PREFIX = """你是一位数据分析助手，你的回应内容取决于用户的请求内容，请按照下面的步骤处理用户请求：

1. 思考阶段 (Thought) ：先分析用户请求类型（文字回答/表格/图表），并验证数据类型是否匹配。
2. 行动阶段 (Action) ：根据分析结果选择以下严格对应的格式。
   - 纯文字回答: 
     {"answer": "不超过50个字符的明确答案"}

   - 表格数据：  
     {"table":{"columns":["列名1", "列名2", ...], "data":[["第一行值1", "值2", ...], ["第二行值1", "值2", ...]]}}

   - 柱状图 
     {"bar":{"columns": ["A", "B", "C", ...], "data":[35, 42, 29, ...]}}

   - 折线图 
     {"line":{"columns": ["A", "B", "C", ...], "data": [35, 42, 29, ...]}}

3. 格式校验要求
   - 字符串值必须使用英文双引号
   - 数值类型不得添加引号
   - 确保数组闭合无遗漏

4. 关于多种不同格式的数据
   - 如果需要返回生成多种不同格式的数据，将它们合并，如：
     {"answer":"不超过50个字符的明确答案", "bar":{"columns": ["A", "B", "C", ...], "data":[35, 42, 29, ...]}}

   错误案例：{'columns':['Product', 'Sales'], data:[[A001, 200]]}  
   正确案例：{"columns":["product", "sales"], "data":[["A001", 200]]}

注意：除生成的数据本身外，响应输出不要有任何其它无关文本，响应数据的"output"中不要有换行符、制表符以及其他格式符号。

当前用户请求内容："""

# df 变量中暂存读取到的文件数据
df = None

# 模型
model = ChatOpenAI(
    base_url='https://api.deepseek.com/v1',
    api_key=SecretStr('sk-5540161374c74948b64385cdfbc24b62'),
    model='deepseek-reasoner'
)

st.title('自助式数据分析智能体')
file_type = st.radio('文件类型:', ['Excel', 'CSV'], horizontal=True)
ext = 'xlsx' if file_type == 'Excel' else 'csv'
uploaded_file = st.file_uploader('上传文件:', type=ext)
# 根据选择上传的文件，读取文件数据
if uploaded_file:
    if file_type == 'Excel':
        # 将 excel 文件中的表名读取出来
        wb = pd.ExcelFile(uploaded_file)
        sheet_names = wb.sheet_names
        sheet_name = st.radio('选择表:', sheet_names, horizontal=True)
        # 根据选择的表名，读取数据
        df = pd.read_excel(uploaded_file, sheet_name=sheet_name)
    else:
        df = pd.read_csv(uploaded_file)
    # 显示读取到的文件数据
    with st.expander('文件数据详情:'):
        st.dataframe(df)
# 提问框
question = st.text_area('提出问题:', placeholder='请针对选择的数据文件进行提问')
# 提问按钮
btn = st.button('提问')

# 接入大语言模型进行处理
if question and df is not None and btn:
    with st.spinner('思考中...'):
        agent = create_pandas_dataframe_agent(
            llm=model,
            df=df,
            verbose=True,
            max_iterations=10,
            allow_dangerous_code=True,
            agent_executor_kwargs={
                'handle_parsing_errors': True,
            }
        )
        result = agent.invoke({
            'input': PROMPT_PREFIX + question,
        })
    st.markdown(result['output'])
    # TODO: 后续业务处理
    try:
        # 解析响应返回的输出数据，转换为 Python 的 dict 结构数据
        result = json.loads(result['output'])
        if 'answer' in result: # 纯文本回答
            st.markdown('纯文本回答: ' + result['answer'])
        if 'table' in result: # 表格数据的返回
            temp_df = pd.DataFrame(result['table']['data'], columns=result['table']['columns'])
            st.dataframe(temp_df)
        if 'bar' in result: # 柱状图
            data = pd.Series(result['bar']['data'], index=result['bar']['columns'])
            st.bar_chart(data)
        if 'line' in result: # 折线图
            data = pd.Series(result['line']['data'], index=result['line']['columns'])
            st.line_chart(data)
    except:
        st.error('解析数据异常')
