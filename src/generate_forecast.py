#!/usr/bin/env python3
"""Create the complete 50-ticket DLT-PI-200 forecast payload.

A/B1/B2 use the same pi digit windows for each draw/ticket; only the declared
digit transform differs. C and D use deterministic SHA-256 counter streams
derived from a per-draw 256-bit root seed. No third-party packages are needed.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, json
from pathlib import Path

EXP_ID = "DLT-PI-200"
MODELS = ["A", "B1", "B2", "C", "D"]
TICKETS_PER_MODEL = 10
WINDOW = 2048
BLOCK = 6
PI_PREFIX = "14159265358979323846264338327950288419716939937510"


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_utc(s: str) -> dt.datetime:
    x = s.replace("Z", "+00:00")
    d = dt.datetime.fromisoformat(x)
    if d.tzinfo is None:
        raise ValueError("timestamp must include Z or explicit UTC offset")
    return d.astimezone(dt.timezone.utc)


class HashStream:
    """Version-independent deterministic stream based on SHA-256 counter blocks."""
    def __init__(self, seed: bytes):
        if len(seed) != 32:
            raise ValueError("seed must be exactly 32 bytes")
        self.seed, self.counter, self.buf = seed, 0, b""

    def _take(self, n: int) -> bytes:
        while len(self.buf) < n:
            self.buf += hashlib.sha256(self.seed + self.counter.to_bytes(8, "big")).digest()
            self.counter += 1
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def randbits(self, k: int) -> int:
        if k < 1:
            return 0
        nbytes = (k + 7)//8
        x = int.from_bytes(self._take(nbytes), "big")
        return x & ((1 << k)-1)

    def randbelow(self, n: int) -> int:
        if n <= 0:
            raise ValueError("n must be positive")
        k = n.bit_length()
        while True:
            x = self.randbits(k)
            if x < n:
                return x


def derive_seed(root: bytes, draw_id: str, model: str) -> bytes:
    return hashlib.sha256(root + (EXP_ID + "|" + draw_id + "|" + model).encode("utf-8")).digest()


def sample_without_replacement(population: list[int], k: int, rng: HashStream) -> list[int]:
    a = list(population)
    for i in range(k):
        j = i + rng.randbelow(len(a)-i)
        a[i], a[j] = a[j], a[i]
    return a[:k]


def weighted_without_replacement(counts: dict[int, int], population_n: int, k: int, rng: HashStream) -> list[int]:
    weights = {i: counts.get(i, 0)+1 for i in range(1, population_n+1)}
    chosen = []
    for _ in range(k):
        total = sum(weights.values())
        r = rng.randbelow(total)
        acc, selected = 0, None
        for number in sorted(weights):
            acc += weights[number]
            if r < acc:
                selected = number
                break
        if selected is None:
            raise RuntimeError("weighted sampler internal error")
        chosen.append(selected)
        del weights[selected]
    return sorted(chosen)


def read_history(path: Path, cutoff: dt.datetime) -> tuple[dict[int,int],dict[int,int],int,str]:
    raw = path.read_bytes()
    front_counts = {i:0 for i in range(1,36)}
    back_counts = {i:0 for i in range(1,13)}
    seen = set()
    latest_publication = None
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        required = {"draw_id","published_at_utc","front","back"}
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("history CSV must contain draw_id,published_at_utc,front,back")
        rows = list(reader)
    for row in rows:
        draw = row["draw_id"].strip()
        if not draw or draw in seen:
            raise ValueError("history contains empty or duplicate draw_id")
        seen.add(draw)
        publication_time = parse_utc(row["published_at_utc"])
        if publication_time >= cutoff:
            raise ValueError(f"history row {draw} was not published strictly before forecast cutoff")
        latest_publication = publication_time if latest_publication is None else max(latest_publication, publication_time)
        front = [int(x) for x in row["front"].replace(",", " ").split()]
        back = [int(x) for x in row["back"].replace(",", " ").split()]
        if len(front)!=5 or len(set(front))!=5 or any(x<1 or x>35 for x in front):
            raise ValueError(f"invalid front numbers in history row {draw}")
        if len(back)!=2 or len(set(back))!=2 or any(x<1 or x>12 for x in back):
            raise ValueError(f"invalid back numbers in history row {draw}")
        for x in front: front_counts[x]+=1
        for x in back: back_counts[x]+=1
    latest_text = latest_publication.isoformat().replace("+00:00", "Z") if latest_publication else None
    return front_counts, back_counts, len(rows), sha(raw), latest_text


def pi_window_start(pi_digits: str, draw_id: str, zone: str) -> int:
    half = len(pi_digits)//2
    total = TICKETS_PER_MODEL*WINDOW
    if half <= total:
        raise ValueError("pi digit file is too short for ten non-overlapping ticket windows per zone")
    digest = hashlib.sha256((EXP_ID+"|"+draw_id+"|"+zone).encode("utf-8")).digest()
    return int.from_bytes(digest, "big") % (half-total+1)


def map_window(window: str, q: int, count: int, transform: str) -> tuple[list[int], list[dict]]:
    if len(window) != WINDOW or not window.isdigit():
        raise ValueError("pi window length/format invalid")
    limit = (10**BLOCK//q)*q
    out, events = [], []
    for pos in range(0, len(window)-BLOCK+1, BLOCK):
        raw = window[pos:pos+BLOCK]
        if transform == "identity":
            mapped_block = raw
        elif transform == "reverse":
            mapped_block = raw[::-1]
        elif transform == "complement9":
            mapped_block = "".join(str(9-int(c)) for c in raw)
        else:
            raise ValueError("unknown pi transform")
        z = int(mapped_block)
        ev = {"window_offset":pos,"raw":raw,"transformed":mapped_block,"accepted":False,"mapped":None,"reason":None}
        if z >= limit:
            ev["reason"] = "rejection_sampling"
        else:
            value = 1 + z % q
            if value in out:
                ev["reason"] = "duplicate_number"
            else:
                out.append(value); ev["accepted"]=True; ev["mapped"]=value
                if len(out)==count:
                    events.append(ev)
                    return sorted(out), events
        events.append(ev)
    raise RuntimeError("pi window exhausted before enough distinct numbers were generated")


def pi_tickets(pi_digits: str, draw_id: str, transform: str) -> list[dict]:
    fs = pi_window_start(pi_digits, draw_id, "FRONT")
    bs = len(pi_digits)//2 + pi_window_start(pi_digits, draw_id, "BACK")
    out = []
    for i in range(TICKETS_PER_MODEL):
        fw = pi_digits[fs+i*WINDOW:fs+(i+1)*WINDOW]
        bw = pi_digits[bs+i*WINDOW:bs+(i+1)*WINDOW]
        front, fe = map_window(fw,35,5,transform)
        back, be = map_window(bw,12,2,transform)
        out.append({"front":front,"back":back,"pi_front_window_start":fs+i*WINDOW,
                    "pi_back_window_start":bs+i*WINDOW,"front_mapping_events":fe,"back_mapping_events":be})
    if len({(tuple(t["front"]),tuple(t["back"])) for t in out}) != TICKETS_PER_MODEL:
        raise RuntimeError("duplicate ticket in pi model portfolio; fail closed")
    return out


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draw-id",required=True)
    ap.add_argument("--cutoff-utc",required=True)
    ap.add_argument("--pi-digits",default="data/pi_digits_600000.txt")
    ap.add_argument("--history",required=True)
    ap.add_argument("--seed-file",required=True,help="private 32-byte hex seed created by seed_ceremony.py")
    ap.add_argument("--seed-commitment",required=True,help="public per-draw seed commitment JSON")
    ap.add_argument("--seed-anchor",required=True,help="independent timestamp attestation JSON for the public commitment")
    ap.add_argument("--analysis-plan",default="PREREGISTRATION.md")
    ap.add_argument("--output",required=True)
    args=ap.parse_args()
    cutoff=parse_utc(args.cutoff_utc)
    pi_path=Path(args.pi_digits); pi_raw=pi_path.read_bytes()
    pi_digits=pi_raw.decode("ascii").strip()
    if not pi_digits.startswith(PI_PREFIX) or not pi_digits.isdigit():
        raise ValueError("pi digit file failed known-prefix or decimal-only validation")
    history_path=Path(args.history)
    fc,bc,n_hist,hist_hash,latest_pub=read_history(history_path,cutoff)
    seed_path=Path(args.seed_file)
    commitment_path=Path(args.seed_commitment)
    anchor_path=Path(args.seed_anchor)
    root=bytes.fromhex(seed_path.read_text(encoding="ascii").strip())
    if len(root)!=32:
        raise ValueError("root seed must be exactly 32 bytes")
    seed_commitment=json.loads(commitment_path.read_text(encoding="utf-8"))
    seed_anchor=json.loads(anchor_path.read_text(encoding="utf-8"))
    seed_hash=sha(root)
    if seed_commitment.get("experiment_id")!=EXP_ID or seed_commitment.get("draw_id")!=args.draw_id:
        raise ValueError("seed commitment does not match this experiment/draw")
    if seed_commitment.get("seed_commitment_sha256")!=seed_hash:
        raise ValueError("private seed does not match the precommitted public seed hash")
    if seed_anchor.get("seed_commitment_sha256")!=seed_hash:
        raise ValueError("external anchor does not bind the same seed commitment")
    anchor_time=parse_utc(seed_anchor.get("anchored_at_utc",""))
    if anchor_time>=cutoff:
        raise ValueError("seed commitment was not externally anchored before cutoff")
    if not seed_anchor.get("anchor_url") or not seed_anchor.get("anchor_commit_sha"):
        raise ValueError("external anchor URL and immutable commit SHA are required")
    tickets={
      "A":pi_tickets(pi_digits,args.draw_id,"identity"),
      "B1":pi_tickets(pi_digits,args.draw_id,"reverse"),
      "B2":pi_tickets(pi_digits,args.draw_id,"complement9"),
      "C":[],
      "D":[]
    }
    for model in ("C","D"):
        rng=HashStream(derive_seed(root,args.draw_id,model))
        rows=[]
        for _ in range(TICKETS_PER_MODEL):
            if model=="C":
                front=weighted_without_replacement(fc,35,5,rng)
                back=weighted_without_replacement(bc,12,2,rng)
            else:
                front=sorted(sample_without_replacement(list(range(1,36)),5,rng))
                back=sorted(sample_without_replacement(list(range(1,13)),2,rng))
            rows.append({"front":front,"back":back})
        if len({(tuple(t["front"]),tuple(t["back"])) for t in rows})!=TICKETS_PER_MODEL:
            raise RuntimeError(f"duplicate ticket in {model}; fail closed")
        tickets[model]=rows
    payload={
      "experiment_id":EXP_ID,"draw_id":args.draw_id,"created_at_utc":dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z"),
      "scheduled_cutoff_utc":args.cutoff_utc,"game_rules_id":"DLT-5x35-2x12-2026-revision",
      "models":MODELS,"tickets_per_model":TICKETS_PER_MODEL,"tickets":tickets,
      "parameters":{"pi_block_length":BLOCK,"pi_window_digits":WINDOW,"pi_window_selection":"SHA256(EXP_ID|draw_id|zone) modulo available half-stream; A/B1/B2 share identical windows",
                    "pi_transforms":{"A":"identity","B1":"reverse each 6-digit block","B2":"digit complement d->9-d"},
                    "rejection_sampling":"q in {35,12}; accept z < floor(10^6/q)*q; map 1+(z mod q)",
                    "C":"integer PPS without replacement; weight=count+1; front/back marginal counts separately",
                    "C_D_PRNG":"SHA-256 counter stream; randbelow by rejection; no floating point"},
      "pi_source_sha256":sha(pi_raw.rstrip(b"\n")),"historical_snapshot_sha256":hist_hash,
      "historical_draw_count":n_hist,"history_latest_publication_utc":latest_pub,
      "root_seed_hex":root.hex(),"root_seed_commitment_sha256":seed_hash,"seed_anchor":seed_anchor,"seed_derivation":"SHA256(root_seed_bytes || UTF8(experiment_id|draw_id|model_id))",
      "primary_endpoint":"per-draw mean front hits per ticket; paired model-vs-D",
      "secondary_endpoint":"per-draw mean back hits per ticket; paired model-vs-D",
      "analysis_plan_sha256":sha(Path(args.analysis_plan).read_bytes())
    }
    code_hash=hashlib.sha256()
    for p in sorted(Path("src").glob("*.py")):
        code_hash.update(p.name.encode()+b"\0"+p.read_bytes())
    payload["code_sha256"]=code_hash.hexdigest()
    Path(args.output).parent.mkdir(parents=True,exist_ok=True)
    Path(args.output).write_bytes(canonical(payload)+b"\n")
    print(json.dumps({"status":"FORECAST_PAYLOAD_CREATED_NOT_COMMITTED","draw_id":args.draw_id,
      "models":{m:len(tickets[m]) for m in MODELS},"payload_sha256":sha(canonical(payload)),
      "pi_source_sha256":payload["pi_source_sha256"],"historical_snapshot_sha256":hist_hash,
      "instruction":"Run prospective.py commit only after validating the payload and before the official cutoff; do not rerun with a replacement seed."},indent=2))


if __name__=="__main__":
    main()
