**You may contact me by email at qcfrag@gmail.com**

## 📘 Summary
R-TFT is a real-time method for detecting and tracking resonance in arbitrary n-body systems by projecting angular velocity vectors onto fractional resonance templates. This enables detection of non-integer locking behaviors, applicable from planetary orbits to quantum systems.

To handle noise and systemic drift, the method uses:
- Dynamic background subtraction (inner vs outer system projections)
- Adaptive outer statistics update (variance spikes, perturbations)
- Sector-based updates for spatial heterogeneity
- This results in sharp, noise-resilient detection of resonance onset, collapse, and transitions into chaos.

## ⚙️ Simple Explanation
- Snapshot the System: Capture two time slices of the system (e.g. orbital bodies).
- Track the Motion: Compare positions over time to compute phase velocities.
- Use Two Boxes: Define an inner box (target) and outer box (noise field).
- Subtract Noise: Remove shared background motion using differential projection.
- Reveal True Path: What remains is a clean, resonance-aligned trajectory.

## 🔬 Simulation Validation
- SNR gain: +15.3 dB under noisy, drifting background
- Lock accuracy: >90% reduction in false positives vs FFT
- Adaptation: Adjusts to noise in ≤ 3 steps
- Performance: Constant time per frame (O(1)) → real-time capable

## 📊 Performance Comparison

| Feature / Metric                    | Traditional (FFT / STFT) | R-TFT (This Work)          |
|------------------------------------|---------------------------|----------------------------|
| **Detection Latency**              | Moderate–High             | ✅ Immediate (≤1 frame)    |
| **False Positive Rate (High Noise)**| ~12%                      | ✅ < 1%                    |
| **Noise Adaptation**               | None / Static             | ✅ Dynamic (≤3 steps)      |
| **Signal-to-Noise Ratio (SNR)**    | ~0–1.5 dB                 | ✅ 15.3 dB                 |
| **Supports Non-Integer Locking (P)**| ❌                        | ✅ Yes                     |
| **Computational Complexity**       | O(n log n)                | ✅ O(1) per step           |
| **Real-Time System Deployment**    | Poor (batch)              | ✅ Excellent (live-ready)  |

## R-TFT_Complete.pdf

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15872338.svg)](https://doi.org/10.5281/zenodo.15872338)

- Contain the full published paper.
  
## r_tft.py

- Core Python implementation of the R-TFT algorithm
- Includes real-time fractional resonance metric
- Lightweight: only requires NumPy
- Ready for plug-in to any orbital, neural, or quantum system

## R_TFT_Multi_Vector.pdf

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15877517.svg)](https://doi.org/10.5281/zenodo.15877517)

- Extends the R-TFT framework to support multi-vector resonance tracking
- Captures simultaneous phase locks across multiple resonance templates
- Enables detection of nested, overlapping, or mixed-domain resonances
- Demonstrates cross-domain pattern recognition in physics, neural, and chaotic systems
- Includes visual benchmarks and mathematical justification

## R_TFT_Dimensionality_Detection_Experiment.pdf

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.15857168.svg)](https://doi.org/10.5281/zenodo.15857168)

- Experimental demonstration of R-TFT’s ability to detect emergent structure
- Shows golden ratio resonance behavior from a chaotic attractor
- Useful for understanding multi-dimensional applications

## deepseek_analysis_log.txt

- Contain validation of R-TFT across physics, quantum, neural, and chaos domains. 
- This log contains symbolic validation of the R-TFT framework across physics, quantum, neural, and dynamical domains using DeepSeek-Math.
- Results reflect alignment between theoretical predictions and symbolic inference across quantum, orbital, and neural systems.

## license.txt

- Resonance Ethics License (REL-1.0)  
