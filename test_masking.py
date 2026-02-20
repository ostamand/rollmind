from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("google/gemma-2b-it")

question = "What is 2+2?"
answer = "It is 4."

prompt = f"""<start_of_turn>user
{question}<end_of_turn>
<start_of_turn>model
"""
completion = f"{answer}<end_of_turn>"

prompt_ids = tokenizer(text=prompt)["input_ids"]
prompt_completion_ids = tokenizer(text=prompt + completion)["input_ids"]

print(f"Prompt IDs: {prompt_ids}")
print(f"Prompt+Completion IDs: {prompt_completion_ids}")

if prompt_completion_ids[:len(prompt_ids)] == prompt_ids:
    print("Match successful!")
else:
    print("Mismatch!")
    print(f"Start of combined: {prompt_completion_ids[:len(prompt_ids)]}")
