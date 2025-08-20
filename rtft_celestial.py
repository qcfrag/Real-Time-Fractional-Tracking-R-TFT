# rtft_celestial.py — RTFT φ‑lattice table for Solar System (no pandas, no CSV)
"""
Real‑Time Fractional Tracking (R‑TFT) φ‑lattice table for the Solar System.

This prints a neat table with columns:
  Planet | AU | s | k | |e| | R

Zero dependencies (only stdlib). No CSV is written.

Windows quickstart (copy/paste):
  cd /d G:\RTFT2.0\py
  py rtft_celestial.py
  py rtft_celestial.py --auto-c
  py rtft_celestial.py --anchor Earth --target-s -0.9878
  py rtft_celestial.py --c 0.9878
  py rtft_celestial.py --pluto

Notes:
- --auto-c finds a fold shift c that minimizes total |e| across all planets (L1 fit).
- --anchor <Planet> --target-s <value> sets c so that the chosen planet’s stepcode s equals target-s.
- --c lets you set c manually (overrides --auto-c if both provided).
- X0 is the zero-scale (default 1.0 AU).

RTFT definitions (φ-only):
  s_raw = log_φ(AU / X0)
  s     = s_raw − c
  k     = round(s)
  e     = s − k         -> |e| ∈ [0, 0.5]
  K(Δ)  = φ^{-abs(Δ)}
  P_w   = K(|e|),  P_b = K(1−|e|),  R = P_w / (P_w + P_b)
"""

import math, argparse, sys

phi = (1 + 5**0.5) / 2  # golden ratio

BODIES = [
    ("Mercury", 0.38709893),
    ("Venus",   0.72333199),
    ("Earth",   1.00000011),
    ("Mars",    1.52366231),
    ("Jupiter", 5.20336301),
    ("Saturn",  9.53707032),
    ("Uranus", 19.19126393),
    ("Neptune", 30.06896348),
    # ("Pluto",  39.482),
]

def log_phi(x: float) -> float:
    return math.log(x) / math.log(phi)

def rtft_cols(x: float, X0: float, c: float):
    """Return (s, k, |e|, R) for scalar x (e.g., AU)."""
    s_raw = log_phi(x / X0)
    s = s_raw - c
    k = int(round(s))
    e = s - k
    eabs = abs(e)
    Pw = phi ** (-eabs)
    Pb = phi ** (-(1.0 - eabs))
    R  = Pw / (Pw + Pb)
    return s, k, eabs, R

def base_s_values(X0: float):
    return [(name, log_phi(au / X0)) for name, au in BODIES]

def total_abs_e(c: float, s_vals):
    """Objective: minimize sum |e| with e = (s_raw - c) - round(s_raw - c)."""
    tot = 0.0
    for _, s in s_vals:
        e = (s - c) - round(s - c)
        tot += abs(e)
    return tot

def fit_c_L1(X0: float):
    """Grid search c in [0,1): coarse then fine (L1 minimization of total |e|)."""
    s_vals = base_s_values(X0)
    best_c, best_val = 0.0, 1e9
    # coarse sweep
    for i in range(1000):
        c = i / 1000.0
        val = total_abs_e(c, s_vals)
        if val < best_val:
            best_c, best_val = c, val
    # fine sweep around best
    lo = max(0.0, best_c - 0.02); hi = min(1.0, best_c + 0.02)
    steps = 8000
    for j in range(steps + 1):
        c = lo + j * (hi - lo) / steps
        val = total_abs_e(c, s_vals)
        if val < best_val:
            best_c, best_val = c, val
    return best_c

def anchor_c(X0: float, planet: str, target_s: float):
    """Choose c so that chosen planet has s == target_s."""
    s_vals = dict(base_s_values(X0))
    if planet not in s_vals:
        sys.exit(f"Unknown planet '{planet}'. Choices: {[n for n,_ in BODIES]}")
    s_raw = s_vals[planet]
    return s_raw - target_s  # s = s_raw - c  =>  c = s_raw - target_s

def main():
    epilog = (
        "Examples (Windows):\n"
        "  cd /d G:\\RTFT2.0\\py\n"
        "  py rtft_celestial.py\n"
        "  py rtft_celestial.py --auto-c\n"
        "  py rtft_celestial.py --anchor Earth --target-s -0.9878\n"
        "  py rtft_celestial.py --c 0.9878\n"
        "  py rtft_celestial.py --pluto\n"
    )
    ap = argparse.ArgumentParser(
        description="RTFT φ‑lattice table for Solar System — prints table only (no CSV).",
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--x0", type=float, default=1.0, help="zero‑scale X0 (default: 1.0 AU)")
    ap.add_argument("--c",  type=float, default=None, help="fold shift c (default: None)")
    ap.add_argument("--auto-c", action="store_true", help="fit c to minimize sum |e| (L1) over all bodies")
    ap.add_argument("--anchor", default=None, help="anchor planet name (e.g., Earth) to set its s to --target-s")
    ap.add_argument("--target-s", type=float, default=-0.9878, help="target s for --anchor (default: -0.9878)")
    ap.add_argument("--pluto", action="store_true", help="include Pluto")
    args = ap.parse_args()

    bodies = list(BODIES)
    if args.pluto:
        bodies.append(("Pluto", 39.482))

    # choose c
    if args.anchor:
        c = anchor_c(args.x0, args.anchor, args.target_s)
        mode = f"anchor:{args.anchor}, target s={args.target_s}"
    elif args.auto_c:
        c = fit_c_L1(args.x0)
        mode = "auto-c (L1)"
    elif args.c is not None:
        c = float(args.c)
        mode = "manual c"
    else:
        c = 0.0
        mode = "default c=0.0"

    # build rows and print
    rows = []
    for name, au in bodies:
        s, k, eabs, R = rtft_cols(au, args.x0, c)
        rows.append((name, au, s, k, eabs, R))

    print(f"X0={args.x0}, c={c:.6f}  [{mode}]")
    print(f"{'Planet':<9} {'AU':>10} {'s':>11} {'k':>3} {'|e|':>10} {'R':>9}")
    for name, au, s, k, eabs, R in rows:
        print(f"{name:<9} {au:10.6f} {s:11.6f} {k:3d} {eabs:10.6f} {R:9.6f}")

if __name__ == "__main__":
    main()
