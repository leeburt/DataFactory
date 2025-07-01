from openai import OpenAI
import os

model2_api= os.getenv("OPENAI_API_URL")
model2_key= os.getenv("OPENAI_API_KEY")
model2_model= "o4-mini"


## openai接口的测试代码
client = OpenAI(
    base_url=model2_api,
    api_key=model2_key,)

response = client.chat.completions.create(
    model=model2_model,
    messages=[
        {"role": "user", "content": "What is the capital of the moon?"}
    ]
)

print(response)