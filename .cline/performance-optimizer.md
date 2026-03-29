---
name: performance-optimizer
description: 実行速度、メモリ（VRAM）使用量、リアルタイム性の観点からコードを最適化します。
---

# performance-optimizer

## Usage
- Jetson環境での推論速度を向上させたいとき。
- 100Hzなどの高頻度データ処理（UDPバイナリ等）の遅延を抑えたいとき。
- マルチGPU環境でのVRAMオフロードを最適化したいとき。

## Steps
1. **ボトルネックの特定**: 計算量 (O-notation) とメモリ確保の頻度を確認します。
2. **メモリ効率化**: 配列の事前確保 (Pre-allocation)、C++での `std::move` 活用、C#での `Span<T>` 導入を検討します。
3. **並列処理の最適化**: SIMD命令の活用や、マルチスレッド（Task/Thread）のロック競合を最小化します。
4. **ハードウェア特化**: NVIDIA環境であれば CUDA/TensorRT への適合性を、組み込みであればキャッシュフレンドリーな構造を提案します。
