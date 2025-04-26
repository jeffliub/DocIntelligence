import google.generativeai as genai

genai.configure(api_key="your-api-key")

# for m in genai.list_models():
#     print(f"{m.name} (supports generation: {'generateContent' in m.supported_generation_methods})")


model = genai.GenerativeModel('gemini-1.5-pro-latest') 

question ="""
你是一个SQL专家，帮助将自然语言转成SQL查询。以下是数据库结构：
表1：documents(DOC_ID, CLIENT_NAME, CLIENT_ADDRESS, INVOICE_NO, TOTAL_AMOUNT, ISSUED_DATE, DUE_DATE, OCR_SCORE, CREATED_AT)
表2：document_items(ITEM_ID, DOC_ID, ITEM_NAME, UNIT_PRICE)
DOC_ID 是两表的主外键连接字段。
问题：请给我所有客户的名字和地址。
请只返回SQL查询，不要解释。
"""
# print(len(question))
response = model.generate_content(question)

print(response.text)