from transformers import AutoTokenizer

model_id = "google/gemma-2b-it"
tokenizer = AutoTokenizer.from_pretrained(model_id)

text = """<start_of_turn>user
Hello<end_of_turn>
<start_of_turn>model
Hi<end_of_turn>"""
tokens = tokenizer.encode(text, add_special_tokens=False)
decoded_tokens = [tokenizer.decode([t]) for t in tokens]

print(f"Tokens: {tokens}")
print(f"Decoded: {decoded_tokens}")

for token in ["<start_of_turn>", "<end_of_turn>", "<bos>", "<eos>"]:
    token_id = tokenizer.convert_tokens_to_ids(token)
    print(f"Token {token}: ID {token_id}")
