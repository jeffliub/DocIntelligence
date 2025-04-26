import streamlit as st
import google.generativeai as genai
import snowflake.connector
import pandas as pd
import os
import tempfile

# 设置 Gemini API Key 和 model
genai.configure(api_key=st.secrets["general"]["geminiKey"])
model = genai.GenerativeModel('gemini-1.5-pro-latest') 

# Snowflake 连接
@st.cache_resource
def get_connection():
    return snowflake.connector.connect(
        user=st.secrets["home"]["user"],
        private_key=st.secrets["home"]["private_key"],
        account=st.secrets["home"]["account"],
        warehouse=st.secrets["home"]["warehouse"],
        database=st.secrets["home"]["database"],
        schema=st.secrets["home"]["schema"],
        role=st.secrets["home"]["role"],
    )

@st.cache_data(ttl=600)
def load_data_from_snowflake(_conn, query):
    cursor = _conn.cursor()
    try:
        cursor.execute(query)
        df = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
        if 'ISSUED_DATE' in df.columns:
            df['ISSUED_DATE'] = pd.to_datetime(df['ISSUED_DATE'])
        if 'TOTAL_AMOUNT' in df.columns:
            df['TOTAL_AMOUNT'] = pd.to_numeric(df['TOTAL_AMOUNT'])
        return df
    except Exception as e:
        st.error(f"Data loading failed: {e}")
        return pd.DataFrame()
    finally:
        cursor.close()

def upload_file_to_snowflake(_conn, file_path, stage_name="demo_stage", sub_path=None):
    """
    将文件上传到 Snowflake 内部命名阶段。

    Args:
        conn: Snowflake 连接对象。
        file_path (str): 要上传的文件的本地路径。
        stage_name (str): Snowflake 阶段的名称。
        sub_path (str, 可选): 阶段内的子路径（如果需要）。
    """
    cursor = _conn.cursor()
    try:
        # 构建阶段路径
        stage_path = f"@{stage_name}"
        if sub_path:
            stage_path = f"{stage_path}/{sub_path}"

        # 使用 put 命令上传文件
        put_command = f"PUT file://{file_path} {stage_path} AUTO_COMPRESS=FALSE"
        print(f"The command to upload the file: {put_command}")
        cursor.execute(put_command)
        st.success(f"The file [{os.path.basename(file_path)}] has uploaded to {stage_path}")

    except Exception as e:
        st.error(f"File uploading to Snowflake failed: {e}")
    finally:
        cursor.close()


conn = get_connection()
sql_query = """
SELECT CLIENT_NAME, CLIENT_ADDRESS, INVOICE_NO, TOTAL_AMOUNT, ISSUED_DATE, DUE_DATE, OCR_SCORE, CREATED_AT from documents
"""
df = load_data_from_snowflake(conn, sql_query)
print(df.info())
years = df['ISSUED_DATE'].dt.year.unique().tolist()
years.sort(reverse=True)
print(years)
selected_year = st.selectbox("Please choose year", years, index=0)
if selected_year:
    sql_query = f"""
    SELECT CLIENT_NAME, CLIENT_ADDRESS, INVOICE_NO, TOTAL_AMOUNT, ISSUED_DATE, DUE_DATE, OCR_SCORE, CREATED_AT from documents
    WHERE EXTRACT(YEAR FROM ISSUED_DATE) = {selected_year}
    """
    selected_year_df = load_data_from_snowflake(conn, sql_query)
    current_total_amount = selected_year_df['TOTAL_AMOUNT'].sum()
    current_total_transactions = selected_year_df.shape[0]
    current_average_amount = selected_year_df['TOTAL_AMOUNT'].mean() if current_total_transactions > 0 else 0
    st.subheader(f"{selected_year} KPI")

    col1, col2, col3 = st.columns(3)

    previous_year = selected_year - 1
    sql_query = f"""
    SELECT CLIENT_NAME, CLIENT_ADDRESS, INVOICE_NO, TOTAL_AMOUNT, ISSUED_DATE, DUE_DATE, OCR_SCORE, CREATED_AT from documents
    WHERE EXTRACT(YEAR FROM ISSUED_DATE) = {previous_year}
    """
    previous_year_df = load_data_from_snowflake(conn, sql_query)
    previous_total_amount = previous_year_df['TOTAL_AMOUNT'].sum()

    amount_delta = None
    if previous_total_amount > 0:
        amount_delta = (current_total_amount - previous_total_amount) / previous_total_amount

    with col1:
        st.metric(label="Total Amount",
              value=f"${current_total_amount:,.2f}",
              delta=f"{amount_delta:.2%}" if amount_delta is not None else None)

    with col2:
        st.metric(label="Total invoices", value=f"{current_total_transactions:,}")

    with col3:
        st.metric(label="Average Amount per invoice", value=f"${current_average_amount:,.2f}")

    # 添加年度总金额趋势图
    # st.subheader("年度总金额趋势")

    # yearly_amount = df.groupby(df['ISSUED_DATE'].dt.year)['TOTAL_AMOUNT'].sum().reset_index()
    # yearly_amount = yearly_amount.rename(columns={'ISSUED_DATE': '年份', 'TOTAL_AMOUNT': '总金额'})  # Simplified

    # st.line_chart(yearly_amount.set_index('年份'))


# 用户输入
st.title("🧾 Invoice Query")
question = st.text_input("Please enter your question (eg: Which customer has the largest amount?)")

if st.button("ASK") and question:
    # 调用 OpenAI 转换为 SQL
    prompt = f"""
你是一个SQL专家，帮助将自然语言转成SQL查询。以下是数据库结构：
表1：documents(DOC_ID, CLIENT_NAME, CLIENT_ADDRESS, INVOICE_NO, TOTAL_AMOUNT, ISSUED_DATE, DUE_DATE, OCR_SCORE, CREATED_AT)
表2：document_items(ITEM_ID, DOC_ID, ITEM_NAME, UNIT_PRICE)
DOC_ID 是两表的主外键连接字段。
问题：{question}
请只返回SQL查询纯文本，不要解释，不要做任何格式化处理。
"""
    print(prompt)
    response = model.generate_content(prompt)

    sql_query = response.text
    print(sql_query)
    st.code(sql_query, language="sql")

    # 执行 SQL 查询
    cursor = conn.cursor()
    try:
        cursor.execute(sql_query)
        df = pd.DataFrame(cursor.fetchall(), columns=[col[0] for col in cursor.description])
        st.dataframe(df)
    except Exception as e:
        st.error(f"Query failed: {e}")

# 文件上传部分
st.header("Upload File to Snowflake")
uploaded_file = st.file_uploader("Please choose the file to upload")
stage_name = "demo_stage"  # st.text_input("Snowflake 阶段名称", "demo_stage")  # 允许用户指定阶段
# sub_path = st.text_input("阶段子路径 (可选)", "")  # 允许用户指定子路径

if st.button("UPLOAD") and uploaded_file is not None:
    # 检查文件是否已上传
    if uploaded_file.size == 0:
        st.error("The uploaded file is empty, please select a valid file.")
    else:    
        original_filename = uploaded_file.name
        safe_filename = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in original_filename)
        # 将上传的文件保存到临时位置
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(safe_filename)[1], prefix=os.path.splitext(safe_filename)[0]) as temp_file:
            temp_file.write(uploaded_file.getbuffer())
            temp_file_path = temp_file.name  # 获取临时文件的路径
            print(f"Temp file path: {temp_file_path}")
            # st.info(f"文件已保存到临时路径：{temp_file_path}")  # 显示临时文件路径

        if conn:
            upload_file_to_snowflake(conn, temp_file_path, stage_name)

        # 清理临时文件
        os.remove(temp_file_path)