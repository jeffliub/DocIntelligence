import google.generativeai as genai
from datetime import datetime
import time
import sys

def check_gemini_api_key(api_key: str, markdown: bool = True):
    report_lines = []
    print("🔍 正在检测 API Key 有效性与模型支持情况...\n")

    try:
        genai.configure(api_key=api_key)
        models = genai.list_models()

        print("✅ API Key 有效，检测到以下模型：\n")
        report_lines.append("# Gemini API Key 检测报告\n")
        report_lines.append(f"**检测时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        report_lines.append(f"✅ **API Key {api_key} 有效**\n")
        report_lines.append("## 模型列表与测试响应\n")

        for model in models:
            model_name = model.name
            supports_generate = "generateContent" in model.supported_generation_methods
            support_text = "✅ 支持" if supports_generate else "❌ 不支持"
            report_lines.append(f"### {model_name}\n- 支持 generateContent: {support_text}")

            print(f" - {model_name} | 支持 generateContent: {support_text}")

            if supports_generate:
                try:
                    gen_model = genai.GenerativeModel(model_name=model_name)
                    response = gen_model.generate_content("hello")
                    short_text = response.text.strip().replace("\n", " ")[:100]
                    report_lines.append(f"- 🤖 响应（前100字）：\n  > {short_text}\n")
                    print(f"   🤖 响应: {short_text}...\n")
                except Exception as e:
                    error_msg = f"⚠️ 响应失败：{str(e)}"
                    report_lines.append(f"- {error_msg}\n")
                    print(f"   ⚠️  发送内容失败: {e}\n")

    except Exception as e:
        print("❌ 检测失败，可能是以下原因：")
        print("  - API Key 无效 / 没有启用 Gemini API")
        print("  - 项目未启用 Vertex AI 或 Generative Language API\n")
        print("详细错误信息：", e)
        report_lines.append("## ❌ 检测失败\n")
        report_lines.append(f"**错误信息：** `{str(e)}`\n")

    if markdown:
    # 保存 Markdown 文件
        output = f"gemini_key_check_result_{int(time.time())}.md"
        with open(output, "w", encoding="utf-8") as f:
            f.write("\n".join(report_lines))

        print(f"📄 检测结果已保存为: {output}\n")

if __name__ == "__main__":
    check_gemini_api_key("your-api-key", markdown=True)
    # if len(sys.argv) != 2:
    #     print("用法: python gemini_key_checker.py <your-api-key>")
    # else:
    #     check_gemini_api_key(sys.argv[1])
