#!/usr/bin/env python3
"""Generate a reproducible decimal prefix of pi using Chudnovsky binary splitting.

Standard-library only. Output contains digits after the decimal point, with no
leading '3'. The requested digit count is explicit and recorded by the caller.
"""
from __future__ import annotations
import argparse
import sys
from math import isqrt
from pathlib import Path

C3_OVER_24 = 640320**3 // 24
KNOWN_PREFIX = "14159265358979323846264338327950288419716939937510"


def binary_split(a: int, b: int) -> tuple[int, int, int]:
    if b - a == 1:
        if a == 0:
            return 1, 1, 13591409
        p = (6*a - 5) * (2*a - 1) * (6*a - 1)
        q = a*a*a*C3_OVER_24
        t = p * (13591409 + 545140134*a)
        if a & 1:
            t = -t
        return p, q, t
    m = (a+b)//2
    p1, q1, t1 = binary_split(a, m)
    p2, q2, t2 = binary_split(m, b)
    return p1*p2, q1*q2, t1*q2 + p1*t2


def pi_fraction_digits(count: int) -> str:
    if count < 50:
        raise ValueError("at least 50 digits are required for prefix verification")
    guard = 20
    precision = count + guard
    terms = precision // 14 + 2
    p, q, t = binary_split(0, terms)
    scale = 10**precision
    sqrt_scaled = isqrt(10005 * scale * scale)
    scaled_pi = (426880 * sqrt_scaled * q) // t
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(0)
    s = str(scaled_pi).zfill(precision + 1)
    out = s[1:1+count]
    if not out.startswith(KNOWN_PREFIX):
        raise RuntimeError("computed pi prefix failed independent known-prefix check")
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--digits", type=int, default=600_000)
    ap.add_argument("--output", default="data/pi_digits_600000.txt")
    args = ap.parse_args()
    digits = pi_fraction_digits(args.digits)
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(digits + "\n", encoding="ascii")
    import hashlib
    print(f"digits={len(digits)}")
    print(f"sha256={hashlib.sha256(digits.encode('ascii')).hexdigest()}")
    print(f"output={path}")


if __name__ == "__main__":
    main()
