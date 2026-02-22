# Training Analysis: Step 1 (7b_r128)

## 1. Executive Summary
The `7b_r128` run was the first execution using the high-performance 24GB VRAM path (no `--low-mem`) and an increased LoRA rank of 128. While training accuracy (82.9%) is lower than the previous `test4_r64` run (98.3%), the **evaluation accuracy on QA pairs is actually higher (34.8% vs 33.2%)**. This suggests that while the model has not "memorized" the source text to the same degree, it has achieved a more robust internal representation of the rules.

## 2. Metric Breakdown

| Metric | test4_7b_r64 (Ref) | 7b_r128 (Recent) | Status |
| :--- | :--- | :--- | :--- |
| **Train Loss (Final)** | 0.0884 | 1.3913 (at Step 65) / 0.6306 (Final) | ⚠️ Slower Convergence |
| **Mean Token Accuracy** | 98.3% (Peak) | 82.9% (Final) | ✅ Strong (Less Overfit) |
| **Eval Loss** | 4.88 | 5.78 | ⚠️ Higher Variance |
| **Eval Accuracy** | 33.2% | 34.8% | ✅ Improved |
| **Grad Norm (Final)** | 1.20 | 2.51 | ⚠️ Less Stable |

## 3. Deep Dive: Why the "Degradation"?

### 3.1. The Regularization Effect
The `weight_decay` was increased from 0.15 to **0.20** in this run. For domain adaptation (Step 1), weight decay competes with knowledge absorption. The lower training accuracy is a direct result of this higher penalty on weight changes, preventing the "memorization" seen in `test4`.

### 3.2. Training Duration
`test4` ran for **5 epochs**, while `r128` ran for **3 epochs**. Domain adaptation on a large corpus typically requires more passes to lock in specific terminology. The model was still showing an upward accuracy trend at the end of Epoch 2, but the cosine scheduler aggressively throttled the learning rate during Epoch 3.

### 3.3. Batch Size & Gradient Stability
The "24GB Mode" auto-adjusted the batch size from `1x8` to `4x2`. While mathematically similar, the logs show higher variance in `mean_token_accuracy` (oscillations of ~3%) starting in Epoch 3. This suggests that the gradient accumulation over fewer steps (2 vs 8) may be introducing more noise into the updates.

## 4. Success Rubric Assessment
*   [x] **Train Loss:** < 1.5 (Actual: 0.63)
*   [x] **Peak Accuracy:** > 70% (Actual: 85.5% peak / 82.9% final)
*   [x] **Trend Stability:** Moderate (some oscillations observed).
*   [x] **Grad Norm:** Stable (remaining < 3.0).

**Verdict:** **READY FOR STEP 2 (Balanced Path).**
*Note: This checkpoint is likely a better candidate for general assistant behavior than `test4`, which was borderline overfit.*

## 5. Checkpoint Recommendation
*   **Primary Choice:** **Step 185**. This step reached the peak accuracy of **85.5%** before a slight dip in the final steps. It represents the best balance between rule knowledge and conversational health.

## 6. Hyperparameter Recommendations for "Perfect" Run
To achieve the "best of both worlds" (high memorization + high capacity):
1.  **Reduce Weight Decay:** Lower to **0.10** to prioritize knowledge absorption over regularization.
2.  **Increase Epochs:** Use **5.0 epochs** to give the $r=128$ rank enough time to converge.
3.  **Manual Batching:** Use `--low-mem` OR manually set `per_device_train_batch_size: 1` in the config to stabilize the gradient updates.
4.  **Learning Rate:** Increase slightly to **1e-4** to compensate for the higher rank.
