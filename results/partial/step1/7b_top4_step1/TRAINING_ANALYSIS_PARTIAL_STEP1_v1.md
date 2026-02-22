# Training Analysis: Partial Step 1 (v1)

## 1. Executive Summary
The first Partial Fine-Tuning run (unfreezing last 4 layers) shows that full-weight updates are **significantly less efficient** for knowledge absorption than LoRA on the Gemma-7B model. While LoRA reached **86% accuracy** at Epoch 3, the Partial run only reached **68.6%**. Furthermore, unfreezing the backbone weights caused extreme destabilization of the model's pre-trained state, as evidenced by an initial `eval_loss` of **13.85**.

## 2. Partial vs. LoRA Comparison (at Epoch 3.0)

| Metric | LoRA (`test4_7b_r64`) | Partial (Top 4 Layers) | Difference |
| :--- | :--- | :--- | :--- |
| **Train Loss** | ~0.80 | 1.28 | ❌ Partial is slower |
| **Mean Token Accuracy** | **86.0%** | **68.6%** | ❌ -17.4% Accuracy |
| **Eval Loss (QA)** | 4.09 | **9.39** | ❌ Severe Destabilization |
| **Grad Norm (Peak)** | ~2.5 | **155.0** | ⚠️ Highly Unstable |

## 3. Critical Observations

### 1. The "Destabilization" Effect
In Step 1, we expect `eval_loss` (QA pairs) to rise as the model specializes in raw text. However, a jump to **13.85** is extreme. This indicates that modifying the actual weights of the top 4 layers is "breaking" the model's ability to process instructions much faster than LoRA adapters do. 

### 2. Knowledge Distribution
The fact that accuracy is much lower (**68% vs 86%**) suggests that D&D rule knowledge is not effectively captured by only updating the last 4 layers of the model. LoRA targets all linear modules across *all* 28 layers of the model, which seems essential for deep domain adaptation.

### 3. Gradient Instability
The `grad_norm` spike to **155** at Step 40 is a major red flag. It suggests that the learning rate (`2e-5`) might be too high for unfreezing the backbone weights, or that the "Raw Text" samples are creating conflicting gradients in the top-level layers.

## 4. Success Rubric Assessment
*   [x] **Train Loss:** < 1.5 (Actual: 1.28)
*   [ ] **Peak Accuracy:** > 70% (Actual: 68.6% - **FAIL**)
*   [x] **Trend Stability:** Steady, but with high grad spikes.

**Verdict:** **NOT READY FOR STEP 2.** The model has absorbed significantly less knowledge than the LoRA version and has suffered more damage to its base weights.

## 5. How to Improve Partial Fine-Tuning

If you want to continue with the Partial approach instead of LoRA, consider these changes:

1.  **Unfreeze More Layers:** Unfreezing only 4 layers is too narrow. Try unfreezing the **top 12 layers** (`--num-layers 12`) to allow knowledge to be stored deeper in the model.
2.  **Lower Learning Rate:** To fix the `grad_norm` spikes and the massive `eval_loss`, drop the LR to **`1e-5`** or **`5e-6`**.
3.  **Unfreeze Embeddings:** Use the `--unfreeze-embeddings` flag. Domain adaptation often requires updating the vocabulary weights to handle specific terms (like "Ability Score Modifier" or "Proficiency Bonus") more effectively.
4.  **Use a Linear Scheduler:** `cosine` might be decaying the LR too quickly for partial weights. A `linear` or `constant` scheduler might allow for more thorough updates.

## 6. Recommendation
**Return to LoRA.** The `test4_7b_r64` run is objectively superior in every metric. Partial fine-tuning is generally used when you have a massive dataset and want to fundamentally change the model's internal world-model. For D&D rules, LoRA's ability to "patch" knowledge across the entire network is much more effective.
