import os
from dotenv import load_dotenv
from openai import OpenAI, APIStatusError

load_dotenv()

def main():
    client = OpenAI(
        api_key=os.getenv("NVIDIA_API_KEY"),
        base_url=os.getenv("NVIDIA_BASE_URL")
    )

    model = os.getenv("NVIDIA_MODEL")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "Answer directly and concisely. Do not include internal reasoning."
            },
            {
                "role": "user",
                "content": "Explain RAG in three simple sentences."
            }
        ],
        temperature=0.3,
        max_tokens=4096,
        reasoning_effort="low"
    )

    message = response.choices[0].message

    print("\nNVIDIA API SUCCESS")
    print("Answer:", message.content)
    print("Finish reason:", response.choices[0].finish_reason)
    print("Usage:", response.usage)


if __name__ == "__main__":
    main()
