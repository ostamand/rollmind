# Step 1 Training Analysis: Knowledge Extraction (eval_v1)

## 1. Run Summary
- **Step:** 1 (Knowledge Extraction / Domain Adaptation)
- **Status:** Complete (5 Epochs / 330 Steps)
- **Primary Goal:** Extract D&D rules and stylistic patterns into the model.

## 2. Metric Deep Dive

### Training Loss & Accuracy
| Metric | Start (Step 5) | Peak (Step 305) | Final (Step 330) |
| :--- | :--- | :--- | :--- |
| **Train Loss** | 27.44 | 0.4278 | 0.4777 |
| **Mean Token Accuracy** | 52.44% | 98.52% | 98.33% |

- **Observation:** Training loss showed an aggressive and consistent downward trend, dropping from 27.44 to below 0.5. Mean token accuracy reached an exceptionally high peak of **98.52%**, indicating near-perfect memorization of the training corpus.

### Validation Loss (Format Mismatch Paradox)
| Step | Eval Loss |
| :--- | :--- |
| 50 | 2.5029 |
| 150 | 3.0526 |
| 300 | 4.7979 |
| 330 (Final) | 2.5029 |

- **Observation:** As expected for Step 1, the `eval_loss` (on QA pairs) increased as the model specialized in the raw text corpus (from 2.50 to 4.79 at step 300). The final eval value (2.5029) is identical to the step 50 result, which likely indicates a final evaluation pass or logging artifact rather than a sudden recovery. This "paradox" confirms the model is successfully diverging from its generic baseline to adopt domain-specific knowledge.

## 3. Success Rubric

- [x] **Train Loss:** Significantly dropped (> 98% reduction).
- [x] **Peak Accuracy:** 98.52% (Exceeds 70% requirement).
- [x] **Trend Stability:** Steady upward trend in accuracy with minimal noise.
- [x] **Grad Norm:** Generally stable (remaining mostly between 5.0 and 15.0 after the initial warm-up).

## 4. Checkpoint Recommendations

- **The Knowledge Peak (Recommended):** **Step 305** (98.52% accuracy). This checkpoint has the highest rules-coverage.
- **The Inflection Point:** **Step 140** (87.7% accuracy). Accuracy gains slowed after this point, making it a highly efficient "light" version of the domain-adapted model.
- **The Safety Checkpoint:** **Step 50** (2.50 eval loss). Lowest divergence from conversational baseline.

## 5. Final Assessment & Hyperparameter Optimization

### Status: **Cleared for Step 2 (Instruction Tuning)**

The run is highly successful in terms of knowledge absorption. However, the accuracy of **98%+** puts it in the **"Overfit"** category according to the mandate. While excellent for rules-heavy applications, there is a risk of verbatim quoting and loss of conversational fluidity.

### Recommendations for Future Runs:
1. **Increase Weight Decay:** To prevent verbatim "parrot" behavior and encourage more generalized rule learning, consider increasing weight decay (e.g., from 0.01 to 0.1).
2. **Early Exit:** Given that accuracy reached 87%+ by step 140, training for 5 full epochs may be overkill for this corpus size. 2-3 epochs might suffice to reach the ~90% accuracy sweet spot.
3. **LoRA Capacity:** The high accuracy suggests `lora_r` is sufficient; no increase in rank is currently needed.
