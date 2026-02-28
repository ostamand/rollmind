import json
import random
import os
import argparse
from prepare.utils import generate_random_profile

def generate_simple_rolls(num_samples=1000):
    dice_types = [4, 6, 8, 10, 12, 20, 100]
    questions = [
        "Roll {dice}",
        "Can you roll {dice}?",
        "I need a {dice} roll.",
        "Roll me a {dice}",
        "Please roll {dice}",
        "Give me a {dice} roll",
        "Roll {count}d{sides}",
        "Roll {count}d{sides}+{mod}",
        "Roll {count}d{sides}-{mod}",
        "Can you roll {count}d{sides}?",
        "I attack! Roll {count}d{sides}+{mod}",
        "Damage roll: {count}d{sides}",
        "Roll for initiative! {count}d{sides}+{mod}"
    ]

    responses = [
        "Rolling: [ROLL]{dice_str}[/ROLL]",
        "You got: [ROLL]{dice_str}[/ROLL]",
        "Result: [ROLL]{dice_str}[/ROLL]",
        "The dice show: [ROLL]{dice_str}[/ROLL]",
        "Here is your roll: [ROLL]{dice_str}[/ROLL]",
        "Sure! [ROLL]{dice_str}[/ROLL]",
        "Coming right up: [ROLL]{dice_str}[/ROLL]"
    ]

    samples = []
    for _ in range(num_samples):
        count = random.randint(1, 10)
        sides = random.choice(dice_types)
        mod = random.randint(1, 10)
        use_mod = random.random() > 0.3
        
        if use_mod:
            op = random.choice(["+", "-"])
            dice_str = f"{count}d{sides}{op}{mod}"
        else:
            dice_str = f"{count}d{sides}"
            
        q_template = random.choice(questions)
        r_template = random.choice(responses)
        
        # Simple placeholder replacement
        q = q_template.replace("{dice}", dice_str).replace("{count}", str(count)).replace("{sides}", str(sides)).replace("{mod}", str(mod))
        r = r_template.replace("{dice_str}", dice_str)
        
        # Generate a random profile
        profile = generate_random_profile()

        # Apply Gemma template using proper escaping
        full_text = f"<start_of_turn>user\n{profile}\n\n{q}<end_of_turn>\n<start_of_turn>model\n{r}<end_of_turn>"
        samples.append({"text": full_text})

    return samples

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic dice roll training data.")
    parser.add_argument("--output", type=str, default="data/step2/_A100_simple_rolls.jsonl", help="Path to the output JSONL file")
    parser.add_argument("--num_samples", type=int, default=1000, help="Number of samples to generate")
    args = parser.parse_args()

    # Ensure output directory exists
    output_dir = os.path.dirname(args.output)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    samples = generate_simple_rolls(args.num_samples)
    
    with open(args.output, 'w', encoding='utf-8') as f:
        for sample in samples:
            f.write(json.dumps(sample) + "\n")
            
    print(f"Generated {len(samples)} samples to {args.output}")

if __name__ == "__main__":
    main()
