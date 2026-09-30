#!/usr/bin/env python3
"""Calculate added-mass T/S estimates and optional sealed-box alignments."""

from __future__ import annotations

import argparse
import json
import math
from statistics import mean


def parse_pair(value: str) -> tuple[float, float]:
    try:
        free, added = (float(x.strip()) for x in value.split(",", 1))
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError("pair must be FREE_FS,ADDED_FS") from exc
    if free <= 0 or added <= 0 or added >= free:
        raise argparse.ArgumentTypeError("frequencies must satisfy FREE_FS > ADDED_FS > 0")
    return free, added


def parse_volumes(value: str) -> list[float]:
    try:
        volumes = [float(x.strip()) for x in value.split(",") if x.strip()]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("volumes must be comma-separated litres") from exc
    if not volumes or any(v <= 0 for v in volumes):
        raise argparse.ArgumentTypeError("all volumes must be positive")
    return volumes


def calculate_pair(
    fs: float,
    fs_added: float,
    mass_g: float,
    sd_cm2: float,
    rho: float,
    sound_speed: float,
    re_ohm: float | None,
    qes: float | None,
) -> dict[str, float]:
    mass_kg = mass_g / 1000.0
    sd_m2 = sd_cm2 / 10000.0
    mms_kg = mass_kg / ((fs / fs_added) ** 2 - 1.0)
    cms_m_per_n = 1.0 / ((2.0 * math.pi * fs) ** 2 * mms_kg)
    vas_l = rho * sound_speed**2 * sd_m2**2 * cms_m_per_n * 1000.0
    result = {
        "fs_free_hz": fs,
        "fs_added_hz": fs_added,
        "frequency_drop_percent": (1.0 - fs_added / fs) * 100.0,
        "mms_g": mms_kg * 1000.0,
        "cms_mm_per_n": cms_m_per_n * 1000.0,
        "vas_l": vas_l,
    }
    if re_ohm is not None and qes is not None:
        result["bl_tm"] = math.sqrt(2.0 * math.pi * fs * mms_kg * re_ohm / qes)
    return result


def sealed_alignment(vb_l: float, fs: float, qts: float, vas_l: float) -> dict[str, float]:
    ratio = math.sqrt(1.0 + vas_l / vb_l)
    qtc = qts * ratio
    fc = fs * ratio
    b = 2.0 - 1.0 / qtc**2
    y = (-b + math.sqrt(b * b + 4.0)) / 2.0
    f3 = fc * math.sqrt(y)

    peak_db = -999.0
    peak_hz = 0.0
    for step in range(1, 10001):
        frequency = fc * (0.05 + step * 0.0005)
        x = frequency / fc
        magnitude = x * x / math.sqrt((1.0 - x * x) ** 2 + (x / qtc) ** 2)
        db = 20.0 * math.log10(magnitude)
        if db > peak_db:
            peak_db = db
            peak_hz = frequency
    return {
        "net_volume_l": vb_l,
        "qtc": qtc,
        "fc_hz": fc,
        "f3_hz": f3,
        "peak_db": max(0.0, peak_db),
        "peak_hz": peak_hz,
    }


def rounded(value):
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, list):
        return [rounded(x) for x in value]
    if isinstance(value, dict):
        return {key: rounded(val) for key, val in value.items()}
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pair",
        action="append",
        required=True,
        type=parse_pair,
        help="FREE_FS,ADDED_FS in Hz; repeat for multiple runs",
    )
    parser.add_argument("--mass-g", required=True, type=float, help="total added mass in grams")
    area = parser.add_mutually_exclusive_group(required=True)
    area.add_argument("--sd-cm2", type=float, help="effective piston area in cm^2")
    area.add_argument("--dd-mm", type=float, help="effective piston diameter in mm")
    parser.add_argument("--re", type=float, help="DC resistance in ohms")
    parser.add_argument("--qes", type=float, help="electrical Q")
    parser.add_argument("--qts", type=float, help="total Q for sealed-box estimates")
    parser.add_argument("--volumes", type=parse_volumes, help="comma-separated sealed net volumes in litres")
    parser.add_argument("--rho", type=float, default=1.204, help="air density kg/m^3")
    parser.add_argument("--sound-speed", type=float, default=343.2, help="sound speed m/s")
    args = parser.parse_args()

    if args.mass_g <= 0:
        parser.error("--mass-g must be positive")
    if (args.re is None) != (args.qes is None):
        parser.error("--re and --qes must be supplied together")
    if args.volumes and args.qts is None:
        parser.error("--qts is required when --volumes is used")

    sd_cm2 = args.sd_cm2
    if sd_cm2 is None:
        if args.dd_mm <= 0:
            parser.error("--dd-mm must be positive")
        sd_cm2 = math.pi * (args.dd_mm / 10.0) ** 2 / 4.0
    if sd_cm2 <= 0:
        parser.error("effective area must be positive")

    runs = [
        calculate_pair(fs, fsa, args.mass_g, sd_cm2, args.rho, args.sound_speed, args.re, args.qes)
        for fs, fsa in args.pair
    ]
    averages = {key: mean(run[key] for run in runs) for key in runs[0]}
    result = {
        "inputs": {
            "added_mass_g": args.mass_g,
            "sd_cm2": sd_cm2,
            "rho_kg_m3": args.rho,
            "sound_speed_m_s": args.sound_speed,
        },
        "runs": runs,
        "averages": averages,
    }
    if args.volumes:
        result["sealed_alignments"] = [
            sealed_alignment(vb, averages["fs_free_hz"], args.qts, averages["vas_l"])
            for vb in args.volumes
        ]
    print(json.dumps(rounded(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
