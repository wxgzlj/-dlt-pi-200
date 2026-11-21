#!/usr/bin/env python3
"""Fetch all available Super Lotto draws from the official Sports Lottery API.

The snapshot completion time is recorded as snapshot_retrieved_at_utc for every
row. This is a conservative availability proxy, not the original publication
time. A snapshot is usable only when completion strictly precedes the forecast
cutoff. Page 1 is rechecked to detect pagination drift during retrieval.
"""
from __future__ import annotations
import argparse, csv, datetime as dt, hashlib, json, time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API="https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
HEADERS={"User-Agent":"Mozilla/5.0 (compatible; DLT-PI-200-research/1.0)",
         "Accept":"application/json","Referer":"https://static.sporttery.cn/"}


def sha(b:bytes)->str:
    return hashlib.sha256(b).hexdigest()


def fetch_page(page:int,page_size:int,timeout:int)->tuple[dict,bytes,str]:
    params={"gameNo":"85","provinceId":"0","pageSize":str(page_size),"isVerify":"1","pageNo":str(page)}
    url=API+"?"+urlencode(params)
    req=Request(url,headers=HEADERS)
    with urlopen(req,timeout=timeout) as resp:
        raw=resp.read()
        status=resp.status
    if status!=200:
        raise RuntimeError(f"official API returned HTTP {status} on page {page}")
    obj=json.loads(raw.decode("utf-8"))
    if str(obj.get("errorCode"))!="0":
        raise RuntimeError(f"official API error on page {page}: {obj.get('errorMsg')}")
    return obj,raw,url


def normalize(item:dict,snapshot_time:str)->dict:
    issue=str(item.get("lotteryDrawNum","")).strip()
    date=str(item.get("lotteryDrawTime","")).strip()
    nums=[int(x) for x in str(item.get("lotteryDrawResult","")).split()]
    if not issue or len(nums)!=7:
        raise ValueError(f"malformed official draw record: {item}")
    front,back=sorted(nums[:5]),sorted(nums[5:])
    if len(set(front))!=5 or any(x<1 or x>35 for x in front):
        raise ValueError(f"invalid front zone in official issue {issue}")
    if len(set(back))!=2 or any(x<1 or x>12 for x in back):
        raise ValueError(f"invalid back zone in official issue {issue}")
    if not issue.isdigit():
        raise ValueError(f"non-numeric official issue ID: {issue}")
    dt.date.fromisoformat(date)
    return {"draw_id":issue,"draw_date":date,"snapshot_retrieved_at_utc":snapshot_time,
            "front":" ".join(f"{x:02d}" for x in front),
            "back":" ".join(f"{x:02d}" for x in back)}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-dir",default="data/history_snapshot")
    ap.add_argument("--page-size",type=int,default=100)
    ap.add_argument("--timeout",type=int,default=30)
    ap.add_argument("--delay",type=float,default=0.25)
    args=ap.parse_args()
    if not 1<=args.page_size<=5000 or args.delay<0:
        raise ValueError("invalid page size or delay")
    out=Path(args.output_dir); rawdir=out/"raw"
    existing_raw_pages=list(rawdir.glob("page_*.json")) if rawdir.exists() else []
    if (out/"manifest.json").exists() or (out/"history_snapshot.csv").exists() or (out/"source_bundle.json").exists() or existing_raw_pages:
        raise FileExistsError("snapshot output already exists; choose a new timestamped --output-dir, never overwrite a prior snapshot")
    rawdir.mkdir(parents=True,exist_ok=True)
    retrieval_started=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    items=[]; seen=set(); page_hashes=[]; page=1; first_page_signature=None
    while True:
        obj,raw,url=fetch_page(page,args.page_size,args.timeout)
        (rawdir/f"page_{page:04d}.json").write_bytes(raw)
        page_hashes.append({"page":page,"url":url,"sha256":sha(raw),"bytes":len(raw)})
        records=obj.get("value",{}).get("list",[])
        if page==1:
            signature_rows=[{"issue":str(x.get("lotteryDrawNum","")),"date":str(x.get("lotteryDrawTime","")),"result":str(x.get("lotteryDrawResult",""))} for x in records]
            first_page_signature=sha(json.dumps(signature_rows,sort_keys=True,separators=(",",":")).encode())
        if not records:
            break
        for item in records:
            issue=str(item.get("lotteryDrawNum","")).strip()
            if not issue or issue in seen:
                raise RuntimeError(f"duplicate or empty issue across API pages: {issue}")
            seen.add(issue); items.append(item)
        if len(records)<args.page_size:
            break
        page+=1
        time.sleep(args.delay)
    if not items:
        raise RuntimeError("official API returned no draw records")
    # Recheck page 1 after pagination: a new draw inserted during page-number
    # pagination can shift later pages and silently omit/duplicate records.
    verify_obj,verify_raw,verify_url=fetch_page(1,args.page_size,args.timeout)
    verify_records=verify_obj.get("value",{}).get("list",[])
    verify_signature_rows=[{"issue":str(x.get("lotteryDrawNum","")),"date":str(x.get("lotteryDrawTime","")),"result":str(x.get("lotteryDrawResult",""))} for x in verify_records]
    verify_signature=sha(json.dumps(verify_signature_rows,sort_keys=True,separators=(",",":")).encode())
    if verify_signature!=first_page_signature:
        raise RuntimeError("page 1 changed during pagination; discard this partial snapshot and retry into a new directory")
    snapshot_time=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    rows=[normalize(item,snapshot_time) for item in items]
    rows.sort(key=lambda r:(r["draw_date"],int(r["draw_id"])))
    csv_path=out/"history_snapshot.csv"
    with csv_path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["draw_id","draw_date","snapshot_retrieved_at_utc","front","back"])
        w.writeheader(); w.writerows(rows)
    bundle={"source":"official_sporttery_api","retrieval_started_at_utc":retrieval_started,
            "snapshot_completed_at_utc":snapshot_time,"page_hashes":page_hashes,
            "page_1_stability_check":{"re_fetched":True,"signature_matches":True,"verification_url":verify_url}}
    (out/"source_bundle.json").write_text(json.dumps(bundle,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    manifest={"source":"official_sporttery_api","endpoint":API,"gameNo":"85",
              "retrieval_started_at_utc":retrieval_started,"snapshot_completed_at_utc":snapshot_time,
              "snapshot_time_utc":snapshot_time,"draw_count":len(rows),
              "first_draw_id":rows[0]["draw_id"],"last_draw_id":rows[-1]["draw_id"],
              "first_draw_date":rows[0]["draw_date"],"last_draw_date":rows[-1]["draw_date"],
              "csv_sha256":sha(csv_path.read_bytes()),"pages":page_hashes,
              "page_1_stability_check":{"re_fetched":True,"signature_matches":True},
              "timestamp_policy":"snapshot completion time assigned to every row; this is a conservative availability proxy, not the original publication time"}
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
