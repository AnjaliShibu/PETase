#!/usr/bin/env python3
"""
STEP 9 - Prototyping & Home-Scale Deployment Protocol (fixed, standalone)

Fixes vs. the original notebook cell
  * The garbled line `conversion = 100.0 * (1.0np.exp(...))` is now valid:
        conversion = 100 * (1 - exp(-k * t * T/55))
  * Predicted Tm is no longer forced to >= 61.2 by `max(61.2, ...)`.
    Tm is an INPUT (from your ESM-2 / stability model) and the report states
    the real margin between Tm and the reactor set-point.
  * Works standalone (no dependency on variables from earlier notebook cells);
    inside the notebook you can still pass your own values.
  * Writes the same files the phone app reads: FASTA, CSV log, JSON config.

Usage
    python petase_step9.py                       # defaults (Mutant-v4, 60 C, 24 h)
    python petase_step9.py --tm 58 --temp 55     # custom
    python petase_step9.py --outdir ../samples
"""
import argparse
import csv
import json
import math
import os

import numpy as np

# ----------------------------------------------------------------------------
# Constants (same as the phone app: index.html -> MODEL block)
# ----------------------------------------------------------------------------
K0 = 0.045            # base rate constant (1/h) from the notebook
T_REF = 55.0          # reference temperature for the T/T_ref scaling
X_CAP = 95.2          # max conversion cap (%)
PET_UNIT = 192.17     # g/mol repeat unit of PET
TPA_MW = 166.13       # terephthalic acid, g/mol
WT_SEQ = "NTPMSVSDKLIVLGAHEDGV"      # 20-aa demo fragment (NOT the full enzyme)
MUT_SEQ = "NTPAAASRDLIVGGAHEDGV"     # 20-aa demo fragment (NOT the full enzyme)


def stability_factor(temp_c: float, tm_c: float) -> float:
    """1.0 below Tm, smooth exponential loss of activity above Tm."""
    return 1.0 if temp_c <= tm_c else math.exp(-(temp_c - tm_c) / 3.0)


def stir_factor(rpm: float) -> float:
    """Mass-transfer assumption: saturates at >= 200 RPM."""
    return min(1.0, math.sqrt(max(rpm, 0) / 200.0))


def rate_constant(temp_c, tm_c, activity=1.0, rpm=250):
    return K0 * (temp_c / T_REF) * activity * stir_factor(rpm) * stability_factor(temp_c, tm_c)


def conversion(t_h, temp_c, tm_c, activity=1.0, rpm=250):
    k = rate_constant(temp_c, tm_c, activity, rpm)
    return min(100.0 * (1.0 - math.exp(-k * t_h)), X_CAP)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seq", default=MUT_SEQ)
    ap.add_argument("--tm", type=float, default=61.2, help="predicted Tm (C) from your model")
    ap.add_argument("--dg", type=float, default=-8.3, help="binding dG (kcal/mol) from your model")
    ap.add_argument("--rmsf", type=float, default=1.09, help="avg RMSF (A) from your MD/model")
    ap.add_argument("--temp", type=float, default=60.0, help="reactor set-point (C)")
    ap.add_argument("--hours", type=int, default=24)
    ap.add_argument("--load", type=float, default=50.0, help="PET load g/L")
    ap.add_argument("--volume", type=float, default=1.0, help="reactor volume L")
    ap.add_argument("--rpm", type=float, default=250)
    ap.add_argument("--activity", type=float, default=1.0)
    ap.add_argument("--outdir", default=".")
    a = ap.parse_args()

    print("STEP 9: Prototyping & Home-Scale Deployment Protocol")
    print("\n[9.1] Expression construct")
    print("  Host:      Pichia pastoris (X-33)")
    print("  Promoter:  AOX1 (methanol inducible)")
    print(f"  Construct: {len(a.seq)} aa (codon-optimise for host before ordering)")

    print("\n[9.2] Home-scale stir-reactor simulation")
    time_points = np.arange(0, a.hours + 1, 4)
    conv = [round(conversion(t, a.temp, a.tm, a.activity, a.rpm), 2) for t in time_points]
    margin = a.tm - a.temp
    final = conv[-1]
    tpa_g = a.load * a.volume * final / 100.0 * TPA_MW / PET_UNIT
    k = rate_constant(a.temp, a.tm, a.activity, a.rpm)
    t_half = math.log(2) / k if k > 0 else float("inf")
    print(f"  Set-point {a.temp:.1f} C | Tm {a.tm:.1f} C | margin {margin:+.1f} C")
    print(f"  PET load {a.load} g/L x {a.volume} L | stir {a.rpm:.0f} RPM")
    for t, c in zip(time_points, conv):
        print(f"    t={int(t):>2d} h  conversion={c:6.2f} %")
    print(f"  Half-conversion time: {t_half:.1f} h | TPA released: {tpa_g:.2f} g")

    print("\n" + "=" * 65)
    print(" PETASE MUTANT: PIPELINE TELEMETRY REPORT (simulation)")
    print("=" * 65)
    print(f" Sequence (demo fragment):   {a.seq}")
    print(f" Tm (input from model):      {a.tm:.2f} C")
    print(f" Tm - set-point margin:      {margin:+.2f} C" + ("  (thin!)" if margin < 3 else ""))
    print(f" Binding dG (input):         {a.dg} kcal/mol")
    print(f" Avg RMSF (input):           {a.rmsf} A")
    print(f" {a.hours} h conversion (sim):      {final}%")
    print(" Status: simulation only - needs wet-lab validation before any claim")
    print("=" * 65)

    os.makedirs(a.outdir, exist_ok=True)
    with open(os.path.join(a.outdir, "sample_reactor_log.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["hour", "temp_c", "conversion_pct", "tpa_g", "stir_rpm"])
        for h in range(0, a.hours + 1):
            c = round(conversion(h, a.temp, a.tm, a.activity, a.rpm), 2)
            w.writerow([h, a.temp, c, round(a.load * a.volume * c / 100 * TPA_MW / PET_UNIT, 3), a.rpm])
    cfg = {
        "device": "petase-reactor-01",
        "mutant": "AI Mutant-v4",
        "sequence": a.seq,
        "tm_c": a.tm,
        "setpoint_c": a.temp,
        "heater": True,
        "stir_rpm": a.rpm,
        "pet_load_g_per_l": a.load,
        "volume_l": a.volume,
        "dg_kcal_mol": a.dg,
        "rmsf_angstrom": a.rmsf,
        "sim_conversion_pct": final,
    }
    with open(os.path.join(a.outdir, "sample_reactor_config.json"), "w") as f:
        json.dump(cfg, f, indent=2)
    with open(os.path.join(a.outdir, "sample_sequences.fasta"), "w") as f:
        f.write(f">IsPETase_wildtype_fragment | demo 20-aa\n{WT_SEQ}\n")
        f.write(f">AI_Mutant_v4 | Tm={a.tm}C | demo 20-aa\n{a.seq}\n")
        f.write(">Mutant_v5_candidate | demo 20-aa\nNTPAAASRDLIVGGAHEDGV\n".replace("NTPAAASRDLIVGGAHEDGV", "NTPAASSRDLIVGGAHEDGV"))
    print(f"\nWrote samples to {os.path.abspath(a.outdir)}")


if __name__ == "__main__":
    main()
