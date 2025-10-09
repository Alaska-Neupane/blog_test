from litellm import completion
from django.conf import settings 
from dotenv import load_dotenv
from decouple import config
load_dotenv()
GEMINI_API_KEY = config("GEMINI_API_KEY")
response = completion(
    model="gemini/gemini-flash-lite-latest",  
    messages=[{"role": "user", "content": "Which is the largest country in terms of population?"}],
    config_path="litellm_config.json",
    api_key = GEMINI_API_KEY,
    log_file="litellm_logs.txt"
)

print(response['choices'][0]['message']['content'])
print("Tokens used:", response['usage']['total_tokens'])

