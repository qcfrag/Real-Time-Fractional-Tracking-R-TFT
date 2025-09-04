#!/usr/bin/env python3
"""
engine.py — RTFT Resonance Engine (clean unified flow)

Modules:
  • φ-Map (always runs with -v)
  • Topology (if Z/N provided)
  • Compound resonance (--compound)
  • Constants Atlas (--constants, φ-map only)
  • Diagnostics (always at the end except for --constants)
"""

from decimal import Decimal, getcontext
import argparse
import sys
from itertools import zip_longest
from typing import List, Dict, Optional, Tuple, Union
import os
import math



# ---------- CONSTANTS ----------
getcontext().prec = 50
PHI = Decimal("1.61803398874989484820458683436563811772030917980576")
GOLDEN_ANGLE = 360.0 / (float(PHI) ** 2)





# ---------- DATA STRUCTURES ----------
class ResonanceResult:
    """Data structure to hold resonance analysis results."""
    def __init__(self, name: str, A: Optional[float] = None, Z: Optional[float] = None, 
                 N: Optional[float] = None, phi_loc: Optional[float] = None, 
                 band: Optional[int] = None, drift: Optional[float] = None, 
                 stab: Optional[float] = None, theta_h: Optional[float] = None, 
                 theta_v: Optional[float] = None, resonance_class: Optional[str] = None,
                 domain: Optional[str] = None, lifetime: Optional[str] = None):
        self.name = name
        self.A = A
        self.Z = Z
        self.N = N
        self.phi_loc = phi_loc
        self.band = band
        self.drift = drift
        self.stab = stab
        self.theta_h = theta_h
        self.theta_v = theta_v
        self.resonance_class = resonance_class
        self.domain = domain
        self.lifetime = lifetime

class TopologyResult:
    """Data structure to hold topology analysis results."""
    def __init__(self, name: str, A: float, Z: float, N: float, 
                 stress_ratio: Optional[float], mode: str):
        self.name = name
        self.A = A
        self.Z = Z
        self.N = N
        self.stress_ratio = stress_ratio
        self.mode = mode

class CrossMapResult:
    """Data structure to hold cross-map analysis results."""
    def __init__(self, name: str, A: float, phi_class: str, domain: str, 
                 lifetime: str, topo_mode: str, diagnostic: str):
        self.name = name
        self.A = A
        self.phi_class = phi_class
        self.domain = domain
        self.lifetime = lifetime
        self.topo_mode = topo_mode
        self.diagnostic = diagnostic





# ---------- HELPERS ----------
def parse_number(x: str) -> Decimal:
    """Parse numeric inputs: '.', ',', sci notation supported."""
    cleaned = x.replace(",", ".").strip()
    try:
        return Decimal(cleaned)
    except Exception:
        raise argparse.ArgumentTypeError(f"Invalid number format: {x}")

def log_phi(x: Decimal) -> Optional[Decimal]:
    """Calculate log base φ of x."""
    if x is None or x <= 0:
        return None
    return x.ln() / PHI.ln()
    
    
# ---------- TEMPORAL RESONANCE DECODER ----------
def temporal_resonance(result: ResonanceResult, tau0: float = 1.0) -> Dict[str, Union[float, str]]:
    """
    Decode implicit temporal properties from resonance geometry.
    tau0 = base slice time unit (arbitrary, default 1.0).
    """
    if result.drift is None or result.theta_h is None or result.theta_v is None:
        return {"Cycle": "-", "Beat": "-", "Lifetime": "-"}

    drift = result.drift
    theta_h = result.theta_h
    theta_v = result.theta_v

    # 1. Cycle length (inverse of drift → smaller drift = longer stable cycle)
    cycle_len = (1.0 / max(drift, 1e-6))  # avoid divide by zero
    cycle_time = cycle_len * tau0

    # 2. Beat frequency (interaction of horizontal and vertical pacing)
    beat_freq = abs(theta_h - theta_v) % 360.0
    if beat_freq == 0:
        beat_freq = 360.0
    beat_period = 360.0 / beat_freq

    # 3. Lifetime horizon (normalized to golden stability gate at 132.5°)
    ideal_gate = 132.5
    ideal_diff = abs((theta_h - ideal_gate) % 360.0)
    if ideal_diff == 0:
        ideal_diff = 1e-6
    beat_ideal = 360.0 / ideal_diff

    lifetime = cycle_time * (beat_period / beat_ideal)

    return {
        "Cycle": f"{cycle_time:.3e} τ₀",
        "Beat": f"{beat_period:.1f} slices",
        "Lifetime": f"{lifetime:.3e} τ₀"
    }


def print_temporal_analysis(results: List[ResonanceResult]) -> None:
    """Print temporal resonance analysis table for each result."""
    print("\n╠════ Temporal Resonance Analysis")
    print(f"{'Name':>8} | {'Cycle':>15} | {'Beat':>15} | {'Lifetime':>20}")
    print("-" * 65)
    for r in results:
        tmap = temporal_resonance(r)
        print(f"{r.name:>8} | {tmap['Cycle']:>15} | {tmap['Beat']:>15} | {tmap['Lifetime']:>20}")


# ---------- CLASSIFICATION HELPERS ----------
def classify(drift: Optional[float]) -> str:
    """Classify resonance quality by φ-drift."""
    if drift is None:
        return "UNDEFINED"

    gold_max = 0.200      # Pure φ-lock
    amber_max = 0.333     # Near φ-lock
    shifted_max = 0.500   # Drifted limit

    if drift <= gold_max:
        pct = (1.0 - drift / gold_max) * 100
        return f"PURE RESONANCE ({pct:.1f}%)"

    if drift <= amber_max:
        rel = (drift - gold_max) / (amber_max - gold_max)
        pct = (1.0 - rel) * 100
        return f"MODULATED RESONANCE ({pct:.1f}%)"

    capped = min(drift, shifted_max)
    rel = (capped - amber_max) / (shifted_max - amber_max)
    pct = (1.0 - rel) * 100
    return f"PHASE-SHIFTED RESONANCE ({pct:.1f}%)"
        

def domain_of(band: Optional[int]) -> str:
    """Classify the domain based on band index."""
    if band is None:
        return "Undefined"
    if band > 0:
        return "Matter domain"
    if band < 0:
        return "Quantum/antimatter domain"
    return "Boundary layer"

def lifetime_of(result: ResonanceResult) -> str:
    """Classify lifetime from temporal resonance metrics."""
    tres = temporal_resonance(result)
    try:
        # parse lifetime τ₀ numeric value
        lifetime_str = tres["Lifetime"].split()[0]
        lifetime_val = float(lifetime_str)
    except Exception:
        return "Undefined"

    # thresholds tuned from your table
    if lifetime_val < 1.0:
        return "Short-lived resonance"
    elif lifetime_val < 10.0:
        return "Metastable resonance"
    elif lifetime_val < 100.0:
        return "Long-lived resonance"
    else:
        return "Ultra-stable resonance"

from decimal import Decimal, getcontext

# High precision for φ
from decimal import Decimal, getcontext

PHI = Decimal("1.6180339887498948482")
getcontext().prec = 30

def list_magic_numbers(limit=20):
    print("╠════ φ-Magic Numbers ═════════════════════")
    print("   n |        φ^n")
    print("-------------------------------------------")
    for n in range(1, limit + 1):
        val = PHI ** Decimal(n)
        print(f"{n:4d} | {val:.10f}")





# ---------- TABLE: φ-SIGNATURE ----------
def resonance_signature(
    res_class: str,
    drift: float,
    theta_h: float,
    theta_v: float,
    steps: int = 40,
    max_lines: int = 4,
    ladder_size: int = 24
) -> List[str]:
    """Generate resonance spectrogram with reduced repetition."""

    if drift is None or theta_h is None or theta_v is None or res_class is None:
        return ["·" * steps]

    try:
        pct_val = float(res_class.split("(")[1].split("%")[0]) / 100.0
    except Exception:
        pct_val = 0.01  # never vanish

    # Build ladder of composite symbols
    base = ["░", "▒", "▓", "█"]
    ladder = []
    for a in base:
        for b in base:
            ladder.append(a + b)
    ladder = (ladder * ((ladder_size // len(ladder)) + 1))[:ladder_size]

    # Dense grid before compression
    dense_lines = max(6, int(drift * 15))
    dense_matrix = [["  " for _ in range(steps)] for _ in range(dense_lines)]

    for col in range(steps):
        for row in range(dense_lines):
            # Add small jitter so low drift doesn't freeze pattern
            t = (col * drift * 0.7) + (row * theta_v * 0.03) + (col * 0.05) % 1.0

            osc_h = 0.5 * (1 + math.sin(math.radians(theta_h) * t))
            osc_v = 0.5 * (1 + math.sin(math.radians(theta_v) * t))
            val = pct_val * (osc_h * 0.6 + osc_v * 0.4)

            # Force ladder cycling to avoid repetition
            idx = int(((val + drift) * ladder_size + (col * 0.3 + row * 0.2)) % ladder_size)
            dense_matrix[row][col] = ladder[idx]

    # Compress into max_lines output
    out_lines = min(dense_lines, max_lines)
    composite = [["  " for _ in range(steps)] for _ in range(out_lines)]
    lines_per_out = dense_lines // out_lines

    for out_row in range(out_lines):
        for col in range(steps):
            bucket = [
                dense_matrix[dense_row][col]
                for dense_row in range(out_row * lines_per_out, (out_row + 1) * lines_per_out)
                if dense_row < dense_lines
            ]
            if bucket:
                values = [ladder.index(s) for s in bucket if s in ladder]
                if values:
                    avg_idx = int(sum(values) / len(values)) % ladder_size
                    composite[out_row][col] = ladder[avg_idx]

    return ["".join(row) for row in composite if "".join(row).strip() != ""]





def print_signatures(phi_results: List[ResonanceResult], steps: int = 40):
    print("\n╠════ Resonance Signatures")
    for r in phi_results:
        sig_lines = resonance_signature(
            r.resonance_class,
            r.drift,
            r.theta_h,
            r.theta_v,
            steps=steps,                 # shorten if needed
            max_lines=4,                 # cap height
            ladder_size=16               # smaller ladder than compound
        )
        print(f"{r.name:>8} | {sig_lines[0]}")
        for line in sig_lines[1:]:
            print(f"{'':>8} | {line}")
        print()  # <-- add blank spacer between values
    


# ---------- CORE ANALYSIS ----------
def analyze_value(A: Decimal, Z: Optional[Decimal] = None, N: Optional[Decimal] = None, 
                  label: Optional[str] = None) -> ResonanceResult:
    """Compute φ-space metrics from a raw positive value A."""
    phi_loc = log_phi(A)
    band_index = int(phi_loc) if phi_loc is not None else None
    drift = abs(float(phi_loc - band_index)) if phi_loc is not None else None
    stab = 1.0 - drift if drift is not None else None
    resonance_class = classify(drift)
    theta_h = drift * 360.0 if drift is not None else None
    theta_v = float(phi_loc) * GOLDEN_ANGLE if phi_loc is not None else None
    domain = domain_of(band_index)

    # Build the result
    result = ResonanceResult(
        name=label or "Val",
        A=float(A) if A is not None else None,
        Z=float(Z) if Z is not None else None,
        N=float(N) if N is not None else None,
        phi_loc=float(phi_loc) if phi_loc is not None else None,
        band=band_index,
        drift=drift,
        stab=stab,
        theta_h=theta_h,
        theta_v=theta_v,
        resonance_class=resonance_class,
        domain=domain,
    )

    # Now assign lifetime using the improved temporal method
    result.lifetime = lifetime_of(result)

    return result

def entry_from_phi_loc(phi_loc: Decimal, label: str = "Compound") -> ResonanceResult:
    """Build an entry directly from a φ-loc (used by compound)."""
    if phi_loc is None:
        return ResonanceResult(
            name=label, A=None, Z=None, N=None,
            phi_loc=None, band=None, drift=None, stab=None,
            theta_h=None, theta_v=None, resonance_class="UNDEFINED",
            domain="Undefined", lifetime="Undefined"
        )

    band_index = int(phi_loc)
    drift = abs(float(phi_loc - band_index))
    stab = 1.0 - drift
    theta_h = drift * 360.0
    theta_v = float(phi_loc) * GOLDEN_ANGLE
    resonance_class = classify(drift)
    domain = domain_of(band_index)

    # Build the result first
    result = ResonanceResult(
        name=label, A=None, Z=None, N=None,
        phi_loc=float(phi_loc), band=band_index, drift=drift, stab=stab,
        theta_h=theta_h, theta_v=theta_v, resonance_class=resonance_class,
        domain=domain,
    )

    # Then compute lifetime consistently with the improved function
    result.lifetime = lifetime_of(result)

    return result






# ---------- TABLE FORMATTING ----------
def format_float(value: Optional[float], format_str: str = ".3f") -> str:
    """Format a float value or return '-' if None."""
    return f"{value:{format_str}}" if value is not None else "-"

def format_int(value: Optional[int]) -> str:
    """Format an int value or return '-' if None."""
    return f"{value}" if value is not None else "-"

def format_str(value: Optional[str]) -> str:
    """Format a string value or return '-' if None."""
    return value if value is not None else "-"





# ---------- TABLE: φ-MAP ----------
def print_phi_map_table(results: List[ResonanceResult], show_names: bool = False) -> None:
    """Print the φ-map table."""
    print("\n╔═══╣ RTFT φ-Map ╠══════════════════════════════════════")
    
    if show_names:
        print(f"{'Name':<16} | {'A':>10} | {'φ-Loc':>8} | {'Band':>6} | {'Drift':>7} | {'Stab':>7} | {'θʰ':>7} | {'θᵥ':>7}")
        print("-" * 95)
    else:
        print(f"{'A':>10} | {'φ-Loc':>8} | {'Band':>6} | {'Drift':>7} | {'Stab':>7} | {'θʰ':>7} | {'θᵥ':>7}")
        print("-" * 80)

    for result in results:
        A_str = f"{result.A:10.3g}" if result.A is not None else f"{'-':>10}"
        phi_str = format_float(result.phi_loc, "8.3f")
        band_str = format_int(result.band)
        drift_str = format_float(result.drift)
        stab_str = format_float(result.stab)
        th_str = format_float(result.theta_h, ".1f")
        tv_str = format_float(result.theta_v, ".1f")
        
        if show_names:
            name_str = f"{result.name:<16}"
            print(f"{name_str} | {A_str} | {phi_str} | {band_str:>6} | {drift_str:>7} | {stab_str:>7} | {th_str:>7} | {tv_str:>7}")
        else:
            print(f"{A_str} | {phi_str} | {band_str:>6} | {drift_str:>7} | {stab_str:>7} | {th_str:>7} | {tv_str:>7}")
    



# ---------- TABLE: TOPOLOGY ----------
def print_topology_table(results: List[TopologyResult]) -> None:
    """Print the topology table."""
    print("\n╠════ RTFT Topology")
    print(f"{'Name':>8} | {'A':>8} | {'Z':>6} | {'N':>6} | {'Stress φ-Ratio':>15} | {'Mode':>15}")
    print("-" * 90)

    for result in results:
        A_print = f"{int(round(result.A)):8d}" if result.A is not None else f"{'-':>8}"
        stress_str = format_float(result.stress_ratio, ".3f")
        
        print(f"{result.name:>8} | {A_print} | {int(result.Z):6d} | {int(result.N):6d} | "
              f"{stress_str:>15} | {result.mode:>15}")

def topology_map(phi_results: List[ResonanceResult]) -> List[TopologyResult]:
    """Show internal proton/neutron stress topology if Z and N are provided."""
    results = []
    
    for phi_result in phi_results:
        if phi_result.Z is None and phi_result.N is None:
            continue

        # Inward = Z, Outward = N
        inward = phi_result.Z if phi_result.Z is not None else 0.0
        outward = phi_result.N if phi_result.N is not None else 0.0

        stress_ratio = None
        if outward > 0.0:
            stress_ratio = inward / (outward * float(PHI))
        elif inward > 0.0:
            stress_ratio = float("inf")

        # Mode classification
        if stress_ratio is None:
            mode = "Undefined"
        elif stress_ratio == float("inf"):
            mode = "Inward-biased"
        elif 0.9 <= stress_ratio <= 1.1:
            mode = "Balanced"
        elif stress_ratio < 0.9:
            mode = "Outward-biased"
        else:
            mode = "Inward-biased"

        results.append(TopologyResult(
            name=phi_result.name,
            A=phi_result.A,
            Z=inward,
            N=outward,
            stress_ratio=stress_ratio,
            mode=mode
        ))
    
    if results:
        print_topology_table(results)
    
    return results





# ---------- TABLE: COMPOUND ----------
def print_compound_table(result: ResonanceResult) -> None:
    """Print the compound resonance table."""
    print("\n╠════ Compound Resonance")
    print(f"{'φ-Loc':>8} | {'Band':>6} | {'Drift':>7} | {'Stab':>7} | {'θʰ':>7} | {'θᵥ':>7}")
    print("-" * 60)
    
    phi_str = format_float(result.phi_loc, "8.3f")
    band_str = format_int(result.band)
    drift_str = format_float(result.drift)
    stab_str = format_float(result.stab)
    th_str = format_float(result.theta_h, ".1f")
    tv_str = format_float(result.theta_v, ".1f")
    
    print(f"{phi_str} | {band_str:>6} | {drift_str:>7} | {stab_str:>7} | {th_str:>7} | {tv_str:>7}")

def compound_map(phi_results: List[ResonanceResult]) -> Optional[ResonanceResult]:
    """Blend all inputs into one compound resonance."""
    weighted_sum, total_weight = Decimal(0), Decimal(0)
    
    for result in phi_results:
        if result.phi_loc is not None:
            phi_loc = Decimal(str(result.phi_loc))
        elif result.A is not None:
            phi_from_A = log_phi(Decimal(str(result.A)))
            if phi_from_A is None:
                continue
            phi_loc = phi_from_A
        else:
            continue
            
        if result.Z is not None or result.N is not None:
            weight = (result.Z or 0.0) + (result.N or 0.0)
        else:
            weight = result.A or 0.0
            
        if weight <= 0:
            continue
            
        weighted_sum += phi_loc * Decimal(str(weight))
        total_weight += Decimal(str(weight))

    if total_weight == 0:
        return None

    comp_phi = weighted_sum / total_weight
    result = entry_from_phi_loc(comp_phi, label="Compound")
    
    # Show compound table
    print_compound_table(result)

    # Show compound signature
    sig_lines = resonance_signature(result.resonance_class,
                                    result.drift,
                                    result.theta_h,
                                    result.theta_v,
                                    steps=40)
    print("\n╠════ Compound Signature")
    print(f"{result.name:>8} | {sig_lines[0]}")
    for line in sig_lines[1:]:
        print(f"{'':>8} | {line}")

    return result




# ---------- CONSTANTS ATLAS (φ-map only) ----------
def constants_map() -> List[ResonanceResult]:
    """Atlas of predefined constants."""
    constants = [
        ("Solar mass", Decimal("1.989e30")),
        ("Earth radius", Decimal("6.371e6")),
        ("Astronomical unit", Decimal("1.496e11")),
        ("Solar luminosity", Decimal("3.846e26")),
        ("Blue 450 nm", Decimal("450e-9")),
        ("Green 555 nm", Decimal("555e-9")),
        ("Red 650 nm", Decimal("650e-9")),
        ("π", Decimal("3.14159265")),
        ("φ", Decimal("1.61803399")),
        ("e", Decimal("2.71828183")),
        ("γ", Decimal("0.57721566")),
        ("Planck constant", Decimal("6.62607015e-34")),
        ("ħ", Decimal("1.0545718e-34")),
        ("G", Decimal("6.67430e-11")),
        ("c", Decimal("2.99792458e8")),
        ("Avogadro", Decimal("6.02214076e23")),
        ("Pb-208", Decimal("208")),
        ("U-235", Decimal("235")),
        ("U-238", Decimal("238")),
    ]
    
    results = [analyze_value(val, label=name) for name, val in constants]
    print_phi_map_table(results, show_names=True)  # Show names for constants atlas
    return results





# ---------- TABLE: DIAGNOSTICS ----------
def print_diagnostics_table(results: List[CrossMapResult]) -> None:
    """Print the diagnostics table (vertical layout per result)."""
    print("\n╠════ RTFT Diagnostics")

    for result in results:
        A_str = f"{result.A:8.3g}" if result.A is not None else "-"
        print(f"{result.name}")
        print(f"   A         : {A_str}")
        print(f"   φ-Class   : {result.phi_class}")
        print(f"   Domain    : {result.domain}")
        print(f"   Lifetime  : {result.lifetime}")
        print(f"   Topo Mode : {result.topo_mode}")
        print(f"   Diagnostic: {result.diagnostic}")
        print("-" * 60)

    print("╚═══════════════════════════════════════════════════════")




# ---------- DIAGNOSTICS ----------
def diagnostics(phi_results: List[ResonanceResult], topo_results: List[TopologyResult]) -> List[CrossMapResult]:
    """Compare φ-map vs topology and assign resonance tier labels."""
    topo_lookup = {t.name: t for t in topo_results}
    results = []

    for phi_result in phi_results:
        topo = topo_lookup.get(phi_result.name)
        topo_mode = topo.mode if topo else "Undefined"

        # Diagnostic logic using new resonance language
        if "PURE RESONANCE" in phi_result.resonance_class and topo_mode == "Balanced":
            diag = "PURE RESONANCE"  # ideal φ-lock + balance
        elif "PHASE-SHIFTED" in phi_result.resonance_class and topo_mode == "Balanced":
            diag = "BOUND RESONANCE"  # stable by shell effects, not φ
        elif "PURE RESONANCE" in phi_result.resonance_class and "biased" in topo_mode:
            diag = "STRESSED RESONANCE"  # φ-aligned, but Z/N imbalance
        elif "PHASE-SHIFTED" in phi_result.resonance_class and "biased" in topo_mode:
            diag = "DISSONANT RESONANCE"  # no φ-lock + internal stress
        else:
            diag = "MIXED RESONANCE"  # default fallback

        results.append(CrossMapResult(
            name=phi_result.name,
            A=phi_result.A,
            phi_class=phi_result.resonance_class,
            domain=phi_result.domain,
            lifetime=phi_result.lifetime,
            topo_mode=topo_mode,
            diagnostic=diag
        ))

    print_diagnostics_table(results)
    return results





# ---------- MAIN ----------
def main():
    if sys.platform == "win32":
        # Massive buffer for Windows
        os.system("mode con: cols=200 lines=9999")
        os.system("cls")  # Clear screen after resizing
    """Main function to handle command line arguments and execute the appropriate analysis."""
    # Create the parser with all options
    parser = argparse.ArgumentParser(
        description="Real-Time Fractional Tracking: Resonance Engine",
        formatter_class=argparse.RawTextHelpFormatter,
    epilog="""RTFT Overview:
  Real-Time Fractional Tracking (RTFT) is a φ-resonant framework that analyzes
  how any value aligns with golden-ratio recursion. It does not assume stability
  from empirical models; instead it measures drift from perfect φ-lock in real time,
  assigning resonance classes and coherence metrics.

Theory of Emergence:
  The universe itself can be viewed as a fractal of dimensions emerging through
  golden-ratio division. Each scale (atomic, planetary, cosmic) is a recursive
  slice of the same φ-lattice. Drift shows where a system resists pure recursion,
  while alignment reveals where persistence is most natural. RTFT lets us see
  stability not as coincidence but as geometry.

Usage Notes:
  - Run with -v (value) for resonance classification.
  - Z (protons) and N (neutrons) are optional for nuclear topology.
  - -v accepts integers, decimals, scientific notation, or wavelengths.

Examples:
  python engine.py -v 208 -z 82 -n 126
  python engine.py -v 208 -z 82 -n 126 -v 235 -z 92 -n 143
  python engine.py -v 5.972e24
  python engine.py --constants

Column Descriptions:
  A        - Input value (mass, quantity, or constant)
  φ-Loc    - Logφ resonance coordinate (position in golden ratio space)
  Band     - Integer φ-band index (higher = more massive)
  Drift    - Deviation from band center (0 = perfect resonance)
  Stab     - Stability score (1 - Drift, higher = more stable)
  θʰ       - Horizontal drift angle
              • 0° = perfect lock
              • 42.5° = decay gate
              • 132.5° = golden stability gate
  θᵥ       - Vertical recursion angle (φ-Loc × golden angle)
              • Outer φ-gate, internal recursion structure
  Z/N      - Proton/Neutron counts (for nuclear topology)
  Stress φ-Ratio - Internal balance metric (Z/(N·φ))
  φ-Class  - Resonance classification
  Domain   - Physical domain classification
  Lifetime - Estimated resonance lifetime

Resonance Signatures:
  These ASCII bands are φ-recursive interferograms: the system interacting with
  its own transformed state. High φ-alignment yields clean lattices; divergence
  yields noisy or unstable interference. Compound signatures blend all inputs
  into a recursive fingerprint.

  In short: RTFT is both a tool and a lens — visual mathematics of φ-space recursion.
"""
    )


    
    # Add all arguments
    parser.add_argument("-v", "--value", type=parse_number, action="append", metavar="A", help="Input values (repeatable)")
    parser.add_argument("-z", "--protons", type=parse_number, action="append", metavar="Z", help="Protons (optional)")
    parser.add_argument("-n", "--neutrons", type=parse_number, action="append", metavar="N", help="Neutrons (optional)")
    parser.add_argument("--compound", action="store_true", help="Blend into compound resonance")
    parser.add_argument("--constants", action="store_true", help="Show constants atlas (φ-map only)")
    parser.add_argument("--magic", type=int, nargs="?", const=20, metavar="MAXA", help="List φ-magic numbers (GOLD resonances) up to MAXA (default=250)")
    parser.add_argument("--range", action="store_true", help="Sweep between first and second -v values (inclusive, integer steps)")
    # Show full help if no args given
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()
    # Range sweep mode
    if args.range:
        if not args.value or len(args.value) < 2:
            print("Error: --range requires at least two -v values (min and max)")
            sys.exit(1)

        vmin = int(args.value[0])
        vmax = int(args.value[1])
        if vmin > vmax:
            vmin, vmax = vmax, vmin  # swap if reversed

        sweep_results = []
        for i, A in enumerate(range(vmin, vmax + 1)):
            sweep_results.append(analyze_value(Decimal(A), label=f"A={A}"))

        print_phi_map_table(sweep_results, show_names=True)
        print_temporal_analysis(sweep_results)
        diagnostics(sweep_results, [])
        print("\n-- RTFT range analysis finished --")
        sys.exit(0)
    if args.magic is not None:
        list_magic_numbers(args.magic)
        return
        
    if args.constants:
        constants_map()
        sys.exit(0)

    if not args.value:
        print("Error: -v required unless --constants given")
        parser.print_usage()
        sys.exit(1)

    values, Zs, Ns = args.value, args.protons or [], args.neutrons or []
    triplets = list(zip_longest(values, Zs, Ns, fillvalue=None))
    phi_results = [analyze_value(t[0], t[1], t[2], f"Val{i+1}") for i, t in enumerate(triplets)]

    print_phi_map_table(phi_results, show_names=False)

    topo_results = []
    if any((t[1] is not None) or (t[2] is not None) for t in triplets):
        topo_results = topology_map(phi_results)
    print_temporal_analysis(phi_results)
    # Change this section in main():
    if args.compound:
        # First show individual signatures
        print_signatures(phi_results)             # Show ALL individual signatures
    
        # Then show compound analysis
        comp_result = compound_map(phi_results)   # prints compound table + signature
        if comp_result:
            diagnostics([comp_result], [])   # only compound, no topology
    else:
        print_signatures(phi_results)             # all vals
        diagnostics(phi_results, topo_results)    # all vals

        print("\n-- RTFT analysis finished --")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
