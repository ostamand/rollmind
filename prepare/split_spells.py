import os
import re

def split_spells(input_file, output_dir):
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    os.makedirs(output_dir, exist_ok=True)

    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split by the "### " header
    # We use a lookahead to keep the delimiter in the split
    spells = re.split(r'\n(?=### )', content)
    
    # Handle the case where the first spell doesn't have a leading newline
    if not spells[0].startswith('### '):
        # Check if the very first characters are ###
        if content.startswith('### '):
            # The split worked, but the first element is already correct
            pass
        else:
            # First element might be preamble, skip it
            spells = spells[1:]

    count = 0
    for spell_text in spells:
        spell_text = spell_text.strip()
        if not spell_text.startswith('### '):
            continue
            
        # Extract the name from the first line
        first_line = spell_text.split('\n')[0]
        spell_name = first_line.replace('###', '').strip()
        
        # Sanitize filename
        safe_name = "".join([c for c in spell_name if c.isalnum() or c in (' ', '-', '_')]).strip()
        if not safe_name:
            continue
            
        file_path = os.path.join(output_dir, f"{safe_name}.md")
        
        with open(file_path, 'w', encoding='utf-8') as f_out:
            f_out.write(spell_text)
        
        count += 1

    print(f"Successfully split {count} spells into {output_dir}")

if __name__ == "__main__":
    split_spells("data/spells.txt", "data/spells")
