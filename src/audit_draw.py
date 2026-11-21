#!/usr/bin/env python3
"""Auditable post-draw evaluation for China Super Lotto. Python stdlib only."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

FRONT_RANGE=set(range(1,36)); BACK_RANGE=set(range(1,13))

def validate_zone(nums, expected, allowed, label):
    if not isinstance(nums,list) or len(nums)!=expected or any(type(n) is not int for n in nums) or len(set(nums))!=expected or not set(nums)<=allowed:
        raise ValueError(f'{label} must contain {expected} distinct valid integers')

def tier(fh,bh):
    # Tier mapping only; cash payout is deliberately not inferred from tier.
    if (fh,bh)==(5,2): return 1
    if (fh,bh)==(5,1): return 2
    if (fh,bh) in {(5,0),(4,2)}: return 3
    if (fh,bh)==(4,1): return 4
    if (fh,bh) in {(4,0),(3,2)}: return 5
    if (fh,bh) in {(3,1),(2,2)}: return 6
    if (fh,bh) in {(3,0),(1,2),(2,1),(0,2)}: return 7
    return None

def evaluate(data):
    draw=data['draw']; validate_zone(draw['front'],5,FRONT_RANGE,'draw.front'); validate_zone(draw['back'],2,BACK_RANGE,'draw.back')
    df,db=set(draw['front']),set(draw['back']); models=data['tickets']
    if not isinstance(models,dict) or not models: raise ValueError('tickets must map model IDs to non-empty ticket arrays')
    rows=[]; summaries={}
    all_budgets=[]
    for model, tickets in models.items():
        if not isinstance(tickets,list) or not tickets: raise ValueError(f'{model}: ticket list is empty')
        all_budgets.append(len(tickets)); seen=set(); hits=[]
        for idx,t in enumerate(tickets,1):
            validate_zone(t.get('front'),5,FRONT_RANGE,f'{model}[{idx}].front')
            validate_zone(t.get('back'),2,BACK_RANGE,f'{model}[{idx}].back')
            key=(tuple(sorted(t['front'])),tuple(sorted(t['back'])))
            if key in seen: raise ValueError(f'{model}: duplicate ticket at row {idx}')
            seen.add(key)
            fh=len(set(t['front'])&df); bh=len(set(t['back'])&db); prize_tier=tier(fh,bh)
            rows.append({'model':model,'ticket':idx,'front_hits':fh,'back_hits':bh,'prize_tier':prize_tier})
            hits.append((fh,bh,prize_tier))
        n=len(hits)
        summaries[model]={
            'ticket_count':n,
            'front_hits_total':sum(x[0] for x in hits),
            'front_hits_per_ticket':sum(x[0] for x in hits)/n,
            'back_hits_total':sum(x[1] for x in hits),
            'back_hits_per_ticket':sum(x[1] for x in hits)/n,
            'prize_ticket_count':sum(x[2] is not None for x in hits),
            'prize_tier_counts':{str(k):sum(x[2]==k for x in hits) for k in range(1,8)},
        }
    if len(set(all_budgets))!=1:
        summaries['_warning']='Unequal ticket budgets: do not compare raw prize counts without normalization.'
    payload=json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    return {'schema':'dlt-draw-audit-v1','draw_id':data.get('draw_id'),'draw_date':data.get('draw_date'),
            'source_status':data.get('source_status','UNVERIFIED_USER_SUPPLIED'),
            'source_url':data.get('source_url'),'input_sha256':hashlib.sha256(payload).hexdigest(),
            'draw':draw,'model_summaries':summaries,'ticket_rows':rows,
            'theoretical_per_ticket_baseline':{'front_hits':5/7,'back_hits':1/3},
            'inference_warning':'A single draw is descriptive only; no model ranking or predictive-edge claim is justified.'}

def main():
    ap=argparse.ArgumentParser(description=__doc__); ap.add_argument('input'); ap.add_argument('-o','--output')
    a=ap.parse_args(); data=json.loads(Path(a.input).read_text(encoding='utf-8')); result=evaluate(data)
    out=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output: Path(a.output).write_text(out+'\n',encoding='utf-8')
    else: print(out)
if __name__=='__main__': main()
