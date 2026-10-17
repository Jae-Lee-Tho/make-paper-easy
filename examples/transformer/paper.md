# Attention Is All You Need (arXiv:1706.03762v7) — extracted notes

> Partial extract. This environment could not download the PDF, and the arXiv HTML page only allows its tables and figures to be reproduced, so this file holds the facts and tables the figures and summary use. Running make-paper-easy in Claude Code on your own computer downloads the PDF and writes the full text here.

Vaswani et al., Google Brain / Google Research, NIPS 2017. Source: https://arxiv.org/abs/1706.03762

## Key facts used in the summary
- The Transformer drops recurrence and convolutions and is based solely on attention.
- WMT 2014 English-to-German: big model 28.4 BLEU, more than 2.0 BLEU above the best previous models, including ensembles (Sec. 6.1).
- WMT 2014 English-to-French: single big model 41.8 BLEU after 3.5 days on eight GPUs.
- Base model: N = 6, d_model = 512, d_ff = 2048, h = 8, d_k = d_v = 64, P_drop = 0.1, ε_ls = 0.1; 100,000 steps, about 12 hours on one machine with 8 NVIDIA P100 GPUs (Sec. 5.2).
- Big model: 300,000 steps, 3.5 days on 8 P100 GPUs. P_drop = 0.1 for EN-FR.
- Optimizer: Adam, learning-rate warmup for 4000 steps then decay; residual dropout 0.1; label smoothing 0.1.
- Also applied to English constituency parsing.

## Equations
- Scaled dot-product attention (Eq. 1): Attention(Q, K, V) = softmax(QKᵀ / √d_k) V
- Position-wise feed-forward network (Eq. 2): FFN(x) = max(0, xW₁ + b₁)W₂ + b₂
- Positional encoding (Sec. 3.5): PE(pos, 2i) = sin(pos / 10000^(2i/d_model)), PE(pos, 2i+1) = cos(pos / 10000^(2i/d_model))

## Table 1: per-layer complexity, sequential operations, maximum path length
| Layer type | Complexity per layer | Sequential ops | Max path length |
|---|---|---|---|
| Self-Attention | O(n²·d) | O(1) | O(1) |
| Recurrent | O(n·d²) | O(n) | O(n) |
| Convolutional | O(k·n·d²) | O(1) | O(log_k(n)) |
| Self-Attention (restricted) | O(r·n·d) | O(1) | O(n/r) |

## Table 2: BLEU on newstest2014 and training cost (FLOPs)
| Model | EN-DE | EN-FR | Cost EN-DE | Cost EN-FR |
|---|---|---|---|---|
| ByteNet | 23.75 | | | |
| Deep-Att + PosUnk | | 39.2 | | 1.0·10²⁰ |
| GNMT + RL | 24.6 | 39.92 | 2.3·10¹⁹ | 1.4·10²⁰ |
| ConvS2S | 25.16 | 40.46 | 9.6·10¹⁸ | 1.5·10²⁰ |
| MoE | 26.03 | 40.56 | 2.0·10¹⁹ | 1.2·10²⁰ |
| Deep-Att + PosUnk Ensemble | | 40.4 | | 8.0·10²⁰ |
| GNMT + RL Ensemble | 26.30 | 41.16 | 1.8·10²⁰ | 1.1·10²¹ |
| ConvS2S Ensemble | 26.36 | 41.29 | 7.7·10¹⁹ | 1.2·10²¹ |
| Transformer (base model) | 27.3 | 38.1 | 3.3·10¹⁸ | |
| Transformer (big) | 28.4 | 41.8 | 2.3·10¹⁹ | |
