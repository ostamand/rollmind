---
license: apache-2.0
library_name: transformers
tags:
- dnd
- rpg
- gemma
- tabletop
- roleplaying
- gemma3
- fine-tuned
datasets:
- custom-dnd-phb-2024
language:
- en
metrics:
- perplexity
pipeline_tag: text-generation
---

# 🔮 RollMind: The 2024 D&D Rules Engine

**RollMind** is a specialized, domain-expert Large Language Model fine-tuned specifically on the **2024 D&D Player's Handbook**. 

While generic models often hallucinate rules or mix up editions (confusing 2014 rules with 2024 revisions), RollMind is ground-truth aligned with the latest mechanics—from **Weapon Masteries** and **Heroic Inspiration** to the new **Crafting** and **Exhaustion** rules.

## ✨ Why RollMind?

- **🛡️ Character-Aware Reasoning**: RollMind doesn't just give generic advice. By injecting your **Character Profile** (Class, Level, Stats) into the prompt, the model calculates *your* specific Spell Save DCs and Attack Bonuses. Ask "I cast Fireball!" and it knows your DC is 15 because you're a Level 5 Wizard.
- **🎲 Functional Dice System**: LLMs are notorious for "hallucinating" dice results. RollMind solves this by outputting `[ROLL]8d6[/ROLL]` tags. This allows your application to intercept the tag and perform a **true cryptographic roll**, ensuring mechanical fairness and excitement.
- **⚔️ 2024 Rule Mastery**: No more arguing about whether a Grappled creature can move or how the new "Hide" action works. RollMind knows the 2024 RAW (Rules as Written).
- **🧠 Dual-Phase Training**: 
  1. **Domain Adaptation**: Continued pre-training on 100% of the PHB 2024 text for deep rule retention.
  2. **Instruction Alignment**: Fine-tuned on thousands of synthetic combat scenarios and Q&A pairs generated via Vertex AI.

## 🚀 Usage (With Character Context)

To get the most out of RollMind, prepend your character's stats to your prompt:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

model_id = "YOUR_USERNAME/RollMind-v1-gemma3-12b"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype=torch.bfloat16, device_map="auto")

# 1. Define your character profile
profile = "Character Profile: Wizard Level 5. Stats: INT 18 (+4), Spell DC 15. "
user_input = "I cast Fireball at the group of goblins!"

# 2. Combine and template
prompt = f"<start_of_turn>user\n{profile}{user_input}<end_of_turn>\n<start_of_turn>model\n"

inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=512)

print(tokenizer.decode(outputs[0], skip_special_tokens=True))
# Expected Output: "...The targets must make a DC 15 Dexterity save or take [ROLL]8d6[/ROLL] fire damage."
```

## 🛠️ The Training Journey: A Two-Step Approach

RollMind was forged through a specialized multi-stage pipeline designed to transition a general-purpose LLM into a precise D&D rules engine.

### Step 1: Domain Adaptation (Continued Pre-training)
Before learning how to "chat," the model first had to "read." We processed the entire 2024 Player's Handbook into **semantic chunks** of ~3000 characters, carefully preserving header hierarchies to maintain context. The model underwent continued pre-training on 100% of this corpus, ensuring it internalizes the **Rules as Written (RAW)** at a fundamental level.

### Step 2: Instruction Alignment (SFT)
To transform raw knowledge into a helpful assistant, we generated a massive, high-fidelity synthetic dataset using **Vertex AI (Gemini 3 Flash Preview)**. Our pipeline included:

*   **🧠 Contextual QA**: For every PHB chunk, we generated 5-7 complex QA pairs. Each pair was prepended with a randomized **Character Profile** (e.g., "Level 5 Wizard with 18 INT"), teaching the model to calculate DCs and bonuses dynamically based on the user's stats.
*   **🎲 Functional Roll Synthesis**: We built a dedicated pipeline to generate thousands of examples of the `[ROLL]` tag system. This included complex **Upcasting logic** (e.g., casting *Fireball* at 5th level) and **Cantrip Scaling** (e.g., *Eldritch Blast* at level 11).
*   **🎭 Scenario-Based Training**: We simulated real-world table scenarios—from "Leveling Up" and "Multiclassing" to "Complex Combat Conditions" (Grappled, Prone, Incapacitated)—ensuring the model understands the *flow* of a game.
*   **🛡️ Refusal & Guardrails**: RollMind is trained to be an expert, not a generalist. It includes a "Refusal" dataset that teaches it to decline general knowledge questions (e.g., "How do I cook pasta?") and rule-impossible actions (e.g., "I cast *Fireball* as a Level 1 Cleric").

The final dataset was aggregated using **stratified sampling** to ensure a perfect balance between core rules, tactical combat, and functional rolling behavior.
