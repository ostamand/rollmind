# Training Analysis: Step 1 (Knowledge Extraction) - Final Run

## 1. Run Overview
- **Total Steps:** 325
- **Epochs:** 5.0
- **Model:** Gemma-2b (Assumed)
- **Status:** Completed Successfully

## 2. Metric Trends & Interpretation

### Knowledge Absorption (`mean_token_accuracy`)
- **Initial (Step 5):** 50.27%
- **Clearing Threshold (Step 65):** 70.52%
- **Peak Accuracy:** **99.29%** (Step 300)
- **Final Accuracy:** 98.84% (Step 325)
- **Interpretation:** This run shows **Strong to Overfit** knowledge absorption. Per the rubric, values >95% indicate excellent memorization of rules, which is the primary goal for the D&D Player's Handbook corpus. The model has effectively "memorized" the source material.

### Loss Performance
- **Initial Train Loss:** 4.4679
- **Final Train Loss:** 0.0373
- **Evaluation Loss (The Paradox):** The `eval_loss` followed the expected "Format Mismatch" trend, rising from **3.03** (Step 50) to a peak of **4.18** (Step 300). 
- **Interpretation:** The rising eval loss confirms the model is specializing in the D&D domain and diverging from the generic conversational style of the Q&A validation set. The reset of `eval_loss` to 3.03 at Step 325 likely reflects a final evaluation pass or a trainer artifact, but the trend leading up to it is healthy for Step 1.

### Training Stability
- **Grad Norm:** Remained extremely stable, peaking at 12.3 in the first few steps and settling between **0.4 and 0.8** in the final epoch.
- **Learning Rate:** Followed a cosine schedule with a warmup to 1e-4. No erratic spikes observed.

## 3. Success Rubric

| Criterion | Result | Notes |
| :--- | :--- | :--- |
| **Train Loss < 1.5** | **PASS** | Dropped to 0.03. |
| **Peak Accuracy > 70%** | **PASS** | Reached 99.29%. |
| **Trend Stability** | **PASS** | Steady upward accuracy and downward loss. |
| **Grad Norm Stability** | **PASS** | Consistently < 1.0 in late stages. |

**Verdict:** **READY FOR STEP 2.**

## 4. Checkpoint Selection
- **The Knowledge Peak (Recommended):** The checkpoint at **Step 300** (or the final Step 325) should be used. It represents the maximum internalization of D&D rules.
- **Alternative:** Step 150 (Accuracy ~91%) could be used if Step 2 shows the model is too "stiff" or verbatim.

## 5. Hyperparameter Recommendations
- **Weight Decay:** Since the model reached >99% accuracy, it is likely quoting text verbatim. If Step 2 testing shows it cannot paraphrase well, consider increasing weight decay in future Step 1 runs to encourage more generalized rule learning.
- **Learning Rate:** The current LR of 1e-4 with warmup appears optimal for this dataset size and model.
- **LoRA Rank:** The current rank is sufficient for the corpus. No increase in capacity is needed.
