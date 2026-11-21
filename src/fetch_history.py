#!/usr/bin/env python3
"""Fetch all available Super Lotto draws from the official Sports Lottery API.

The API snapshot retrieval time is recorded as published_at_utc for every row.
This is deliberately conservative: a snapshot can only be used for forecasts
whose cutoff is later than the snapshot retrieval time. Never backdate rows.
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
    return {"draw_id":issue,"draw_date":date,"published_at_utc":snapshot_time,
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
    out=Path(args.output_dir); rawdir=out/"raw"; rawdir.mkdir(parents=True,exist_ok=True)
    snapshot_time=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
    rows=[]; seen=set(); page_hashes=[]; page=1
    while True:
        obj,raw,url=fetch_page(page,args.page_size,args.timeout)
        (rawdir/f"page_{page:04d}.json").write_bytes(raw)
        page_hashes.append({"page":page,"url":url,"sha256":sha(raw),"bytes":len(raw)})
        records=obj.get("value",{}).get("list",[])
        if not records:
            break
        for item in records:
            row=normalize(item,snapshot_time)
            if row["draw_id"] in seen:
                raise RuntimeError(f"duplicate issue across API pages: {row['draw_id']}")
            seen.add(row["draw_id"]); rows.append(row)
        if len(records)<args.page_size:
            break
        page+=1
        time.sleep(args.delay)
    if not rows:
        raise RuntimeError("official API returned no draw records")
    rows.sort(key=lambda r:r["draw_id"])
    csv_path=out/"history_snapshot.csv"
    with csv_path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=["draw_id","draw_date","published_at_utc","front","back"])
        w.writeheader(); w.writerows(rows)
    raw_bundle=json.dumps({"source":"official_sporttery_api","snapshot_time_utc":snapshot_time,
                           "page_hashes":page_hashes},ensure_ascii=False,sort_keys=True,indent=2).encode()
    manifest={"source":"official_sporttery_api","endpoint":API,"gameNo":"85",
              "snapshot_time_utc":snapshot_time,"draw_count":len(rows),
              "first_draw_id":rows[0]["draw_id"],"last_draw_id":rows[-1]["draw_id"],
              "csv_sha256":sha(csv_path.read_bytes()),"pages":page_hashes,
              "publication_time_policy":"snapshot retrieval time assigned to every row; conservative and never backdated"}
    (out/"manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
