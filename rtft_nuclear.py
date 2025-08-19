#!/usr/bin/env python3
"""
rtft_core_ref.py — Minimal, paper-faithful RTFT core (Decimal precision)
----------------------------------------------------------------------
What it does (single goal):
- Computes Dim(A), Cφ, Aφ, Tφ, Sφ (Rclean=1) with high precision.
- Prints the paper's half-life *estimator* τ_est (Eq. 9) — no empirical fit.
- Guesses (Z,N) from a smooth stability-valley proxy if Z is not provided.

Design choices:
- Decimal(prec=80) for all internal math (stable, reproducible).
- Only one optional input: a list/range of A. If omitted, prints a demo panel.
- Output is rounded for readability, but calculations are high-precision.
"""

from decimal import Decimal, getcontext
import math
import sys

# -------------------- Precision & constants --------------------
getcontext().prec = 80

PHI  = (Decimal(1) + Decimal(5).sqrt()) / Decimal(2)
LN_PHI = PHI.ln()

TAU0 = Decimal("1.6e-3")          # seconds (paper Eq. 11)
SEC_PER_YEAR = Decimal("31557600")
PHI_INV = Decimal(1) / PHI

# -------------------- Core functions (paper) --------------------
def dim(A: Decimal) -> Decimal:
    """Dim(A) = ln(A) / ln(φ)"""
    return A.ln() / LN_PHI

def c_phi(A: Decimal) -> Decimal:
    """Cφ(A) = |Dim(A) - Round(Dim(A))|, clamped to [0, 0.5]."""
    d = dim(A)
    # nearest-integer with bankers rounding (harmless here)
    nearest = d.to_integral_value()
    c = (d - nearest).copy_abs()
    if c > Decimal("0.5"):
        c = Decimal("0.5")
    return c

def _pow_frac(x: Decimal, p_num: int, p_den: int) -> Decimal:
    """x**(p_num/p_den), x>0, using Decimal ln/exp."""
    return ((Decimal(p_num) / Decimal(p_den)) * x.ln()).exp()

def z0_valley(A: Decimal) -> Decimal:
    """Smooth stability-valley proxy for Z (no data tables)."""
    A_2_3 = _pow_frac(A, 2, 3)
    return A / (Decimal(2) + Decimal("0.015") * A_2_3)

def guess_ZN(A: Decimal):
    Z = z0_valley(A)
    N = A - Z
    return Z, N

def A_phi(A: Decimal, Z: Decimal, N: Decimal) -> Decimal:
    """Asymmetry penalty with φ-convex weight: (1 - |Z-N|/A)^(φ-1)"""
    if A <= 0:
        return Decimal(0)
    frac = Decimal(1) - (Z - N).copy_abs() / A
    if frac < 0: frac = Decimal(0)
    if frac > 1: frac = Decimal(1)
    return frac ** (PHI - Decimal(1))

def T_phi(A: Decimal) -> Decimal:
    """Unified threshold: (1 - Cφ)^2 * Aφ * Rclean, with Rclean=1."""
    c = c_phi(A)
    Z, N = guess_ZN(A)
    return ((Decimal(1) - c) ** 2) * A_phi(A, Z, N) * Decimal(1)

def S_phi(A: Decimal) -> Decimal:
    """Unified stability score: (1 - Cφ)^φ * (Tφ)^(φ - 1)."""
    c = c_phi(A)
    T = T_phi(A)
    return ((Decimal(1) - c) ** PHI) * (T ** (PHI - Decimal(1)))

def tau_est_seconds(A: Decimal) -> Decimal:
    """
    Paper's Eq. (9) half-life *estimator* (seconds).
    τ = τ0 · φ^{-Dim(A)} · (1-Cφ)^2 · e^{-5Cφ} · φ^{-(A mod 2)}
    """
    c = c_phi(A)
    d = dim(A)
    exp_term = (-Decimal(5) * c).exp()
    parity = PHI ** (-(int(A) % 2))
    return TAU0 * (PHI ** (-d)) * ((Decimal(1) - c) ** 2) * exp_term * parity

def theta_emit_deg(A: Decimal) -> Decimal:
    """Eq. (16): θ = θφ*(1 - Cφ) + θanti*Cφ"""
    theta_phi = Decimal("360") * (PHI ** Decimal(-2))               # ~137.5°
    theta_anti = Decimal("360") * (Decimal(1) - (PHI ** Decimal(-2)))  # ~222.5°
    c = c_phi(A)
    return theta_phi * (Decimal(1) - c) + theta_anti * c

def band_from_S(S: Decimal) -> str:
    if S >= Decimal("0.75"):
        return "Golden"
    if S >= PHI_INV:  # ~0.618
        return "Meta-Stable"
    return "Decay-Prone"

# -------------------- Pretty printing --------------------
def fmt_f(x: Decimal, places: int = 6) -> str:
    # show with fixed decimals (no scientific) up to requested places
    q = Decimal(1).scaleb(-places)  # 10^-places
    return str(x.quantize(q))

def fmt_sci(x: Decimal, places: int = 6) -> str:
    # scientific string with given places
    if x.is_infinite():
        return "Infinity"
    # Convert via float for formatting only (safe for display); math stays Decimal.
    return f"{float(x):.{places}e}"

def print_panel(As):
    print("\nRTFT Core (paper-faithful) — no empirical fit")
    print("================================================")
    print("{:<6} {:>10} {:>10} {:>14} {:>10} {:>12}".format(
        "A", "Dim(A)", "Cφ", "Sφ", "Band", "τ_est (y)"
    ))
    print("-" * 70)
    for A_int in As:
        A = Decimal(A_int)
        S = S_phi(A)
        band = band_from_S(S)
        tau_y = tau_est_seconds(A) / SEC_PER_YEAR
        print(f"{A_int:<6d} {fmt_f(dim(A),3):>10} {fmt_f(c_phi(A),6):>10} {fmt_f(S,6):>14} {band:>10} {fmt_sci(tau_y,6):>12}")

# -------------------- CLI-lite --------------------
def parse_As(argv):
    if len(argv) <= 1:
        return None  # means: use demo
    # Accept space-separated ints, or a single "start:end"
    toks = argv[1:]
    out = []
    for t in toks:
        if ":" in t:
            a, b = t.split(":", 1)
            a, b = int(a), int(b)
            if a <= b:
                out.extend(range(a, b+1))
            else:
                out.extend(range(b, a+1))
        else:
            out.append(int(t))
    return sorted(set(out))

def main():
    As = parse_As(sys.argv)
    if As is None:
        # Demo set
        As = list(range(1, 236))
        print_panel(As)
        print("\nVerification:")
        for (a, name) in [(3, "H-3"), (4, "He-4"), (50, "V-50"), (235, "U-235")]:
            A = Decimal(a)
            S = S_phi(A)
            band = band_from_S(S)
            tau_y = tau_est_seconds(A) / SEC_PER_YEAR
            print(f"{name:>6}:  Sφ={float(S):.6f}  Band={band:12s}  t1/2={fmt_sci(tau_y)} years")
    else:
        print_panel(As)

if __name__ == "__main__":
    main()
