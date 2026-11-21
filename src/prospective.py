#!/usr/bin/env python3
"""Commit–reveal ledger for prospective lottery forecasts. Python stdlib only."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, secrets, sys
from pathlib import Path

ROOT = Path.cwd()
LEDGER = ROOT / "ledger" / "events.jsonl"
VAULT = ROOT / "private" / "prospective-vault"

def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
def sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def now(): return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def parse_utc(value):
    parsed=dt.datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if parsed.tzinfo is None: raise ValueError("timestamp must include Z or explicit UTC offset")
    return parsed.astimezone(dt.timezone.utc)

def validate_seed_provenance(obj, cutoff_utc):
    required=("created_at_utc","root_seed_hex","root_seed_commitment_sha256","seed_anchor")
    missing=[key for key in required if key not in obj]
    if missing: raise ValueError("forecast payload missing seed provenance: "+", ".join(missing))
    try: root=bytes.fromhex(obj["root_seed_hex"])
    except Exception: raise ValueError("root_seed_hex is not valid hexadecimal")
    if len(root)!=32: raise ValueError("root seed must be exactly 32 bytes")
    root_hash=sha(root)
    if obj["root_seed_commitment_sha256"]!=root_hash:
        raise ValueError("root seed does not match its public commitment hash")
    anchor=obj["seed_anchor"]
    if not isinstance(anchor,dict): raise ValueError("seed_anchor must be an object")
    if anchor.get("seed_commitment_sha256")!=root_hash:
        raise ValueError("seed anchor does not bind the forecast root seed")
    if not anchor.get("anchor_url"): raise ValueError("seed anchor URL is missing")
    commit_sha=str(anchor.get("anchor_commit_sha",""))
    if len(commit_sha)!=40 or any(c not in "0123456789abcdefABCDEF" for c in commit_sha):
        raise ValueError("seed anchor must contain the full 40-character commit SHA")
    anchor_time=parse_utc(anchor.get("anchored_at_utc",""))
    created_time=parse_utc(obj["created_at_utc"])
    if anchor_time>=created_time: raise ValueError("seed commitment must be anchored before forecast generation")
    if created_time>=cutoff_utc: raise ValueError("forecast payload was created at or after the draw cutoff")
    if anchor_time>=cutoff_utc: raise ValueError("seed commitment was not anchored before the draw cutoff")

def read_ledger():
    if not LEDGER.exists(): return []
    out=[]
    for n,line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip(): continue
        try: out.append(json.loads(line))
        except Exception as e: raise ValueError(f"ledger line {n} is invalid JSON: {e}")
    return out
def head_hash(records): return records[-1]["record_hash"] if records else "0"*64
def append_record(record):
    records=read_ledger()
    record={**record,"prev_hash":head_hash(records)}
    record["record_hash"]=sha(canonical(record))
    LEDGER.parent.mkdir(parents=True,exist_ok=True)
    fd=os.open(LEDGER,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    try: os.write(fd,(canonical(record).decode()+"\n").encode()); os.fsync(fd)
    finally: os.close(fd)
    return record

def cmd_commit(args):
    p=Path(args.payload).resolve()
    obj=json.loads(p.read_text(encoding="utf-8"))
    required=["experiment_id","draw_id","created_at_utc","scheduled_cutoff_utc","game_rules_id","models","tickets","code_sha256","analysis_plan_sha256","primary_endpoint","root_seed_hex","root_seed_commitment_sha256","seed_anchor"]
    missing=[k for k in required if k not in obj]
    if missing: raise ValueError("payload missing required keys: "+", ".join(missing))
    exp,draw=str(obj["experiment_id"]),str(obj["draw_id"])
    # Enforce the declared UTC cutoff; naive timestamps are rejected.
    cutoff_text=str(obj["scheduled_cutoff_utc"]).replace("Z", "+00:00")
    cutoff=dt.datetime.fromisoformat(cutoff_text)
    if cutoff.tzinfo is None: raise ValueError("scheduled_cutoff_utc must include Z or an explicit UTC offset")
    cutoff_utc=cutoff.astimezone(dt.timezone.utc)
    validate_seed_provenance(obj, cutoff_utc)
    if dt.datetime.now(dt.timezone.utc) >= cutoff_utc:
        raise ValueError("forecast cutoff has passed; this record cannot enter the confirmatory cohort")
    # Defense in depth: enforce the seed ceremony at the ledger boundary too.
    seed_hex=obj.get("root_seed_hex")
    seed_hash=obj.get("root_seed_commitment_sha256")
    anchor=obj.get("seed_anchor")
    if not isinstance(seed_hex,str) or len(seed_hex)!=64:
        raise ValueError("payload must include the 32-byte root_seed_hex")
    try:
        seed_bytes=bytes.fromhex(seed_hex)
    except ValueError:
        raise ValueError("root_seed_hex is not valid hexadecimal")
    if len(seed_bytes)!=32 or sha(seed_bytes)!=seed_hash:
        raise ValueError("root seed does not match root_seed_commitment_sha256")
    if not isinstance(anchor,dict):
        raise ValueError("payload must include the pre-draw seed_anchor attestation")
    if anchor.get("seed_commitment_sha256")!=seed_hash:
        raise ValueError("seed anchor does not bind the committed root seed")
    if not anchor.get("anchor_url") or not anchor.get("anchor_commit_sha"):
        raise ValueError("seed anchor URL and full commit SHA are required")
    anchor_text=str(anchor.get("anchored_at_utc","")).replace("Z","+00:00")
    try:
        anchor_time=dt.datetime.fromisoformat(anchor_text)
    except ValueError:
        raise ValueError("seed anchor timestamp is invalid")
    if anchor_time.tzinfo is None or anchor_time.astimezone(dt.timezone.utc)>=cutoff_utc:
        raise ValueError("seed anchor must be timezone-aware and strictly before forecast cutoff")
    created_text=str(obj.get("created_at_utc","")).replace("Z","+00:00")
    try:
        created_time=dt.datetime.fromisoformat(created_text)
    except ValueError:
        raise ValueError("forecast created_at_utc is missing or invalid")
    if created_time.tzinfo is None or created_time.astimezone(dt.timezone.utc)>=cutoff_utc:
        raise ValueError("forecast creation timestamp must be timezone-aware and before cutoff")
    if created_time.astimezone(dt.timezone.utc)<anchor_time.astimezone(dt.timezone.utc):
        raise ValueError("forecast was created before the seed commitment anchor")
    if obj.get("draw_id")!=draw or obj.get("experiment_id")!=exp:
        raise ValueError("payload experiment/draw identifiers are inconsistent")
    # Validate the complete registered portfolio: same ticket budget and valid, unique DLT combinations.
    models=obj["models"]
    if models != ["A", "B1", "B2", "C", "D"]:
        raise ValueError("DLT-PI-200 requires the frozen model order A,B1,B2,C,D")
    tickets=obj["tickets"]
    if not isinstance(tickets,dict) or set(tickets.keys())!=set(str(x) for x in models):
        raise ValueError("tickets must contain exactly one list for every registered model")
    budgets=[]
    for model_id in models:
        rows=tickets[str(model_id)]
        if not isinstance(rows,list) or len(rows) != 10: raise ValueError(f"model {model_id} must contain exactly 10 tickets")
        budgets.append(len(rows)); seen=set()
        for ticket in rows:
            f=ticket.get("front",[]); b=ticket.get("back",[])
            if len(f)!=5 or len(set(f))!=5 or any(type(v) is not int or not 1<=v<=35 for v in f):
                raise ValueError(f"model {model_id} has an invalid front zone")
            if len(b)!=2 or len(set(b))!=2 or any(type(v) is not int or not 1<=v<=12 for v in b):
                raise ValueError(f"model {model_id} has an invalid back zone")
            key=(tuple(sorted(f)),tuple(sorted(b)))
            if key in seen: raise ValueError(f"model {model_id} contains a duplicate ticket")
            seen.add(key)
    if len(set(budgets))!=1: raise ValueError("all registered models must have the same ticket budget")
    records=read_ledger()
    if any(r.get("type")=="commit" and r.get("experiment_id")==exp and r.get("draw_id")==draw for r in records):
        raise ValueError("commit already exists for this experiment/draw; never overwrite it")
    nonce=secrets.token_hex(32)
    payload_bytes=canonical(obj)
    commitment=sha(payload_bytes+bytes.fromhex(nonce))
    VAULT.mkdir(mode=0o700,parents=True,exist_ok=True)
    stem=f"{exp}__{draw}".replace("/","_")
    sealed=VAULT/(stem+".sealed.json")
    secret=VAULT/(stem+".nonce")
    # Exclusive creation prevents accidental overwrite.
    with sealed.open("xb") as f: f.write(payload_bytes); f.flush(); os.fsync(f.fileno())
    with secret.open("x",encoding="ascii") as f: f.write(nonce); f.flush(); os.fsync(f.fileno())
    try: os.chmod(sealed,0o400); os.chmod(secret,0o400)
    except OSError: pass
    rec=append_record({"type":"commit","timestamp_utc":now(),"experiment_id":exp,"draw_id":draw,
      "scheduled_cutoff_utc":obj["scheduled_cutoff_utc"],"commitment_sha256":commitment,
      "payload_sha256":sha(payload_bytes),"sealed_payload":str(sealed.relative_to(ROOT)),
      "nonce_file":str(secret.relative_to(ROOT))})
    print(json.dumps({"status":"COMMITTED","commitment_sha256":commitment,"record_hash":rec["record_hash"],
      "ledger_head":rec["record_hash"],"external_anchor_required":True,
      "instruction":"Publish experiment_id, draw_id, commitment_sha256 and ledger_head to an independently timestamped public append-only location before scheduled_cutoff_utc."},ensure_ascii=False,indent=2))

def cmd_reveal(args):
    records=read_ledger(); commits=[r for r in records if r.get("type")=="commit" and r.get("experiment_id")==args.experiment_id and r.get("draw_id")==args.draw_id]
    if len(commits)!=1: raise ValueError("expected exactly one matching commit")
    c=commits[0]
    if any(r.get("type")=="reveal" and r.get("commit_record_hash")==c["record_hash"] for r in records): raise ValueError("this commitment has already been revealed")
    sealed=ROOT/c["sealed_payload"]; secret=ROOT/c["nonce_file"]
    payload_bytes=sealed.read_bytes(); nonce=bytes.fromhex(secret.read_text(encoding="ascii").strip())
    if sha(payload_bytes)!=c["payload_sha256"] or sha(payload_bytes+nonce)!=c["commitment_sha256"]:
        raise ValueError("commitment verification failed; do not publish this reveal")
    payload=json.loads(payload_bytes)
    result_path=Path(args.result).resolve(); result=json.loads(result_path.read_text(encoding="utf-8"))
    if not all(k in result for k in ("official_source_url","retrieved_at_utc","raw_source_sha256","front","back","result_status")):
        raise ValueError("result JSON must include official_source_url, retrieved_at_utc, raw_source_sha256, front, back, result_status")
    rec=append_record({"type":"reveal","timestamp_utc":now(),"experiment_id":args.experiment_id,"draw_id":args.draw_id,
      "commit_record_hash":c["record_hash"],"commitment_sha256":c["commitment_sha256"],"nonce":nonce.hex(),
      "payload":payload,"official_result":result,"result_file_sha256":sha(result_path.read_bytes())})
    print(json.dumps({"status":"REVEALED_AND_VERIFIED","commitment_sha256":c["commitment_sha256"],"record_hash":rec["record_hash"],"ledger_head":rec["record_hash"]},ensure_ascii=False,indent=2))

def cmd_verify(_args):
    records=read_ledger(); prev="0"*64; seen_commit=set(); seen_reveal=set(); issues=[]; counts={"commit":0,"reveal":0}
    for i,r in enumerate(records,1):
        body={k:v for k,v in r.items() if k!="record_hash"}
        if r.get("prev_hash")!=prev: issues.append(f"line {i}: previous hash mismatch")
        expected=sha(canonical(body))
        if r.get("record_hash")!=expected: issues.append(f"line {i}: record hash mismatch")
        prev=r.get("record_hash","")
        typ=r.get("type"); counts[typ]=counts.get(typ,0)+1
        if typ=="commit":
            key=(r.get("experiment_id"),r.get("draw_id"))
            if key in seen_commit: issues.append(f"line {i}: duplicate commit {key}")
            seen_commit.add(key)
            revealed = any(x.get("type")=="reveal" and x.get("commit_record_hash")==r.get("record_hash") for x in records)
            try:
                pb=(ROOT/r["sealed_payload"]).read_bytes(); nonce=bytes.fromhex((ROOT/r["nonce_file"]).read_text().strip())
                if sha(pb)!=r["payload_sha256"]: issues.append(f"line {i}: sealed payload hash mismatch")
                if sha(pb+nonce)!=r["commitment_sha256"]: issues.append(f"line {i}: commitment mismatch")
            except Exception as e:
                # Public clones do not possess the private pre-reveal vault.
                # Once revealed, the public payload+nonce are verified below.
                if not revealed:
                    pass
        elif typ=="reveal":
            ch=r.get("commit_record_hash")
            if ch in seen_reveal: issues.append(f"line {i}: duplicate reveal for commit {ch}")
            seen_reveal.add(ch)
            if sha(canonical(r.get("payload"))+bytes.fromhex(r.get("nonce","")))!=r.get("commitment_sha256"):
                issues.append(f"line {i}: revealed payload does not match commitment")
            if not any(x.get("type")=="commit" and x.get("record_hash")==ch and x.get("commitment_sha256")==r.get("commitment_sha256") for x in records[:i-1]):
                issues.append(f"line {i}: reveal has no preceding matching commit")
        else: issues.append(f"line {i}: unknown record type {typ}")
    pending=[f"{e}/{d}" for e,d in seen_commit if not any(r.get("type")=="reveal" and r.get("commit_record_hash")==c.get("record_hash") for c in records if c.get("type")=="commit" and (c.get("experiment_id"),c.get("draw_id"))==(e,d) for r in records)]
    print(json.dumps({"status":"PASS_LOCAL_INTEGRITY" if not issues else "FAIL","records":len(records),"counts":counts,
      "ledger_head":prev,"pending_reveals":sorted(pending),"issues":issues,
      "external_anchor_check":"NOT PERFORMED: compare ledger_head and each commitment with the independently timestamped public anchor."},ensure_ascii=False,indent=2))
    if issues: sys.exit(2)

def main():
    ap=argparse.ArgumentParser(description=__doc__); sub=ap.add_subparsers(dest="cmd",required=True)
    p=sub.add_parser("commit");p.add_argument("payload");p.set_defaults(fn=cmd_commit)
    p=sub.add_parser("reveal");p.add_argument("experiment_id");p.add_argument("draw_id");p.add_argument("result");p.set_defaults(fn=cmd_reveal)
    p=sub.add_parser("verify");p.set_defaults(fn=cmd_verify)
    a=ap.parse_args()
    try:a.fn(a)
    except Exception as e: print(f"ERROR: {e}",file=sys.stderr);sys.exit(2)
if __name__=="__main__": main()
