#!/usr/bin/env python3
"""Build and verify a public, content-addressed DLT history evidence bundle."""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def canonical(obj) -> bytes:
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")

def build(snapshot: Path, audit_path: Path, output: Path) -> dict:
    snapshot=snapshot.resolve(); audit_path=audit_path.resolve(); output=output.resolve()
    audit=json.loads(audit_path.read_text(encoding="utf-8"))
    if audit.get("status")!="PASS" or audit.get("errors") or audit.get("warnings"):
        raise SystemExit("FAIL-CLOSED: audit must be PASS with empty errors and warnings")
    if audit.get("continuity_status")!="VERIFIED_AGAINST_OFFICIAL_CALENDAR":
        raise SystemExit("FAIL-CLOSED: official calendar continuity is not verified")
    attestation=next(snapshot.rglob("*calendar*attestation*.json"),None)
    if attestation is None:
        # Accept the explicitly declared conventional filename only.
        attestation=snapshot/"calendar_attestation.json"
    if not attestation.is_file():
        raise SystemExit("FAIL-CLOSED: calendar attestation JSON is not present in snapshot")
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Refusing to overwrite a non-empty evidence output directory")
    output.mkdir(parents=True,exist_ok=True)
    copied=[]
    for src in sorted(snapshot.rglob("*")):
        if src.is_file():
            rel=src.relative_to(snapshot)
            dst=output/"snapshot"/rel
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(src,dst)
            copied.append(dst)
    audit_dst=output/"audit_report.json"
    shutil.copyfile(audit_path,audit_dst); copied.append(audit_dst)
    files=[]
    for p in sorted(copied):
        files.append({"path":p.relative_to(output).as_posix(),"bytes":p.stat().st_size,"sha256":sha(p)})
    manifest={
      "schema":"DLT-PI-200-HISTORY-EVIDENCE-v1",
      "status":"AUDITED_PUBLIC_EVIDENCE_BUNDLE",
      "source_snapshot_completed_at_utc":audit.get("snapshot_completed_at_utc"),
      "draw_count":audit.get("draw_count"),
      "first_draw_id":audit.get("first_draw_id"),
      "last_draw_id":audit.get("last_draw_id"),
      "history_csv_sha256":audit.get("csv_sha256_computed"),
      "raw_page_count":audit.get("raw_page_count"),
      "calendar_attestation_sha256":audit.get("calendar_attestation_sha256"),
      "calendar_source_document_sha256":audit.get("calendar_source_document_sha256"),
      "audit_report_sha256":sha(audit_dst),
      "files":files,
      "limitations":[
        "snapshot_retrieved_at_utc is a snapshot-completion availability proxy, not original publication time",
        "calendar attestation transcription is human-verified; the auditor validates hashes and exact ID/date equality but does not parse the source document",
        "Git commit timestamps and OpenTimestamps proofs establish anchoring, not lottery predictiveness or source truth"
      ]
    }
    raw=canonical(manifest)
    (output/"evidence_manifest.json").write_bytes(raw+b"\n")
    (output/"evidence_manifest.sha256").write_text(hashlib.sha256(raw).hexdigest()+"  evidence_manifest.json\n",encoding="ascii")
    return {"status":"BUILT","manifest_sha256":hashlib.sha256(raw).hexdigest(),"files":len(files),"draw_count":manifest["draw_count"]}

def verify(bundle: Path) -> dict:
    manifest_path=bundle/"evidence_manifest.json"
    manifest=json.loads(manifest_path.read_text(encoding="utf-8"))
    errors=[]
    for item in manifest.get("files",[]):
        p=bundle/item["path"]
        if not p.is_file(): errors.append("missing:"+item["path"]); continue
        if p.stat().st_size!=item["bytes"] or sha(p)!=item["sha256"]: errors.append("hash_or_size:"+item["path"])
    raw=canonical(manifest)
    digest=hashlib.sha256(raw).hexdigest()
    expected=(bundle/"evidence_manifest.sha256").read_text(encoding="ascii").split()[0]
    if digest!=expected: errors.append("manifest_hash_mismatch")
    return {"status":"FAIL" if errors else "PASS","manifest_sha256":digest,"errors":errors}

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="cmd",required=True)
    b=sub.add_parser("build"); b.add_argument("--snapshot-dir",required=True); b.add_argument("--audit-report",required=True); b.add_argument("--output-dir",required=True)
    v=sub.add_parser("verify"); v.add_argument("--bundle-dir",required=True)
    a=ap.parse_args()
    result=build(Path(a.snapshot_dir),Path(a.audit_report),Path(a.output_dir)) if a.cmd=="build" else verify(Path(a.bundle_dir))
    print(json.dumps(result,ensure_ascii=False,indent=2))
    if result["status"] not in ("BUILT","PASS"): raise SystemExit(1)
if __name__=="__main__": main()
