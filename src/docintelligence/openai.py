from openai import OpenAI

client = OpenAI(
    # This is the default and can be omitted
    api_key="sk-proj-yours",
)

response = client.responses.create(
    model="gpt-4o",
    instructions="You are a coding assistant that talks like a pirate.",
    input="How do I check if a Python object is an instance of a class?",
)

print(response.output_text)