from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it")
messages = [
    {"role": "user", "content": "What is 2+2?"},
    {"role": "assistant", "content": "It is 4."}
]
chat_prompt = tokenizer.apply_chat_template(messages, tokenize=False)
print(f"Chat Template Output: {repr(chat_prompt)}")
