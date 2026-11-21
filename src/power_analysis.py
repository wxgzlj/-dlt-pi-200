#!/usr/bin/env python3
"""Parametric Monte Carlo power planning for DLT-PI-200; not a backtest."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, math, platform, random
from pathlib import Path

N, T, K, NNUM = 200, 10, 5, 35
NTEST, ALPHA, MDE, SEED = 4, 0.05, 0.10, 2026112101
EFFECTS = (0.0, 0.05, 0.10, 0.15, 0.20)
COMB = math.comb(NNUM, K)


def current_source_hash():
    digest=hashlib.sha256()
    for path in sorted(Path("src").glob("*.py")):
        digest.update(path.name.encode("utf-8")+b"\0"+path.read_bytes())
    return digest.hexdigest()


def validate_covariance_panel(panel):
    if panel.get("status")!="COMPUTED_FROM_FIXED_PORTFOLIOS_UNDER_UNIFORM_DRAW_NULL":
        raise ValueError("portfolio covariance input is not a verified computed panel")
    if panel.get("draw_count")!=N:
        raise ValueError("portfolio covariance panel must contain exactly 200 draws")
    if panel.get("paired_difference_models")!=["A","B1","B2","C"]:
        raise ValueError("portfolio covariance model order must be A,B1,B2,C")
    if not panel.get("parameters_sha256"):
        raise ValueError("portfolio covariance panel is missing the frozen parameter hash")
    provenance=panel.get("frozen_provenance")
    required=("code_sha256","analysis_plan_sha256","pi_source_sha256",
              "historical_snapshot_sha256","history_audit_sha256",
              "history_snapshot_completed_at_utc","historical_draw_count","game_rules_id")
    if not isinstance(provenance,dict) or any(not provenance.get(k) for k in required):
        raise ValueError("portfolio covariance panel is missing frozen provenance")
    if provenance["code_sha256"]!=current_source_hash():
        raise ValueError("portfolio panel code hash does not match current frozen src/ tree")
    prereg=Path("PREREGISTRATION.md")
    if prereg.exists() and provenance["analysis_plan_sha256"]!=hashlib.sha256(prereg.read_bytes()).hexdigest():
        raise ValueError("portfolio panel analysis-plan hash does not match current PREREGISTRATION.md")
    matrix=panel.get("average_per_draw_paired_difference_covariance")
    cholesky_psd(matrix)
    return matrix


def ticket_var():
    p = K / NNUM
    return K * p * (1-p) * ((NNUM-K)/(NNUM-1))


def paired_sd():
    portfolio_var = ticket_var()/T * (1-T/COMB)
    return math.sqrt(2*portfolio_var)


def betacf(a, b, x):
    it, eps, tiny = 200, 3e-14, 1e-300
    qab, qap, qam = a+b, a+1, a-1
    c, d = 1.0, 1-qab*x/qap
    if abs(d)<tiny: d=tiny
    d=1/d
    h=d
    for m in range(1,it+1):
        m2=2*m
        aa=m*(b-m)*x/((qam+m2)*(a+m2))
        d=1+aa*d
        if abs(d)<tiny: d=tiny
        c=1+aa/c
        if abs(c)<tiny: c=tiny
        d=1/d
        h*=d*c
        aa=-(a+m)*(qab+m)*x/((a+m2)*(qap+m2))
        d=1+aa*d
        if abs(d)<tiny: d=tiny
        c=1+aa/c
        if abs(c)<tiny: c=tiny
        d=1/d
        delta=d*c
        h*=delta
        if abs(delta-1)<eps: break
    return h


def ibeta(a,b,x):
    if x<=0: return 0.0
    if x>=1: return 1.0
    bt=math.exp(math.lgamma(a+b)-math.lgamma(a)-math.lgamma(b)+a*math.log(x)+b*math.log1p(-x))
    if x<(a+1)/(a+b+2): return bt*betacf(a,b,x)/a
    return 1-bt*betacf(b,a,1-x)/b


def t_p(t,df):
    return ibeta(df/2,0.5,df/(df+t*t))


def holm(pvals):
    order=sorted(range(len(pvals)),key=lambda i:(pvals[i],i))
    out=set()
    for rank,i in enumerate(order):
        if pvals[i] <= ALPHA/(len(order)-rank): out.add(i)
        else: break
    return out


def wilson(p,n):
    z=1.96; z2=z*z; den=1+z2/n
    center=(p+z2/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z2/(4*n*n))/den
    return [max(0,center-half),min(1,center+half)]


def mcse(p,n):
    q=(p*n+0.5)/(n+1)
    return math.sqrt(q*(1-q)/n)


def cholesky_psd(matrix):
    n=len(matrix)
    if n==0 or any(len(row)!=n for row in matrix):
        raise ValueError("covariance matrix must be non-empty and square")
    lower=[[0.0]*n for _ in range(n)]
    for i in range(n):
        for j in range(i+1):
            if not math.isclose(matrix[i][j],matrix[j][i],rel_tol=1e-9,abs_tol=1e-12):
                raise ValueError("covariance matrix must be symmetric")
            value=matrix[i][j]-sum(lower[i][k]*lower[j][k] for k in range(j))
            if i==j:
                if value < -1e-10:
                    raise ValueError("covariance matrix is not positive semidefinite")
                lower[i][j]=math.sqrt(max(value,0.0))
            elif lower[j][j] > 1e-12:
                lower[i][j]=value/lower[j][j]
            elif abs(value)>1e-8:
                raise ValueError("singular covariance matrix failed PSD factorization")
    return lower


def simulate_covariance(reps,effect,sd_mult,seed,covariance,target_index=0,target_model="A"):
    """Multivariate-t power simulation from a supplied draw-level covariance matrix.

    The average per-draw covariance is treated as the common covariance for
    the 200 draw-level observations. Bartlett's Wishart construction preserves
    the supplied cross-comparison dependence. Draw-to-draw heteroskedasticity
    is approximated by the average covariance.
    """
    rng=random.Random(seed); df=N-1; p=NTEST
    scaled=[[float(covariance[i][j])*sd_mult*sd_mult for j in range(p)] for i in range(p)]
    lower=cholesky_psd(scaled)
    anyrej=target=0
    for _ in range(reps):
        z=[rng.gauss(0,1) for _ in range(p)]
        means=[sum(lower[i][k]*z[k] for k in range(i+1))/math.sqrt(N) for i in range(p)]
        a=[[0.0]*p for _ in range(p)]
        for i in range(p):
            a[i][i]=math.sqrt(rng.gammavariate((df-i)/2,2))
            for j in range(i):
                a[i][j]=rng.gauss(0,1)
        b=[[sum(lower[i][k]*a[k][j] for k in range(j,i+1)) for j in range(i+1)] for i in range(p)]
        ps=[]
        for i in range(p):
            ss=sum(value*value for value in b[i])
            sample_var=ss/df
            shift=effect if i==target_index else 0.0
            if sample_var<=1e-15:
                stat=math.inf if shift>0 else (-math.inf if shift<0 else 0.0)
            else:
                stat=(means[i]+shift)/math.sqrt(sample_var/N)
            ps.append(t_p(stat,df))
        rejected=holm(ps)
        anyrej += bool(rejected)
        target += target_index in rejected
    family=anyrej/reps; power=target/reps
    return {
        "effect":effect,"sd_multiplier":sd_mult,"simulations":reps,
        "target_comparison":f"{target_model}_vs_D",
        "target_power":power,"target_power_mcse":mcse(power,reps),
        "target_power_mc_95_wilson":wilson(power,reps),
        "family_rejection_rate":family,"family_rejection_mcse":mcse(family,reps),
        "family_rejection_mc_95_wilson":wilson(family,reps)
    }


def simulate(reps,effect,sd_mult,seed,target_index=0,target_model="A"):
    rng=random.Random(seed); df=N-1
    delta=effect*math.sqrt(N)/(paired_sd()*sd_mult)
    anyrej=target=0
    for _ in range(reps):
        dmean=rng.gauss(0,1)
        dss=rng.gammavariate(df/2,2)
        ps=[]
        for j in range(NTEST):
            mmean=rng.gauss(0,1)
            z=(mmean-dmean)/math.sqrt(2)+(delta if j==target_index else 0)
            mss=rng.gammavariate(df/2,2)
            cross=rng.gauss(0,1)
            diffss=(mss+dss-2*math.sqrt(dss)*cross)/2
            stat=z/math.sqrt(max(diffss,1e-15)/df)
            ps.append(t_p(stat,df))
        rejected=holm(ps)
        anyrej += bool(rejected)
        target += target_index in rejected
    family=anyrej/reps; power=target/reps
    return {
        "effect":effect,"sd_multiplier":sd_mult,"simulations":reps,
        "target_comparison":f"{target_model}_vs_D",
        "target_power":power,"target_power_mcse":mcse(power,reps),
        "target_power_mc_95_wilson":wilson(power,reps),
        "family_rejection_rate":family,"family_rejection_mcse":mcse(family,reps),
        "family_rejection_mc_95_wilson":wilson(family,reps)
    }


def report(reps,seed,covariance=None,target_model="A",covariance_source="REFERENCE_ANALYTIC"):
    target_index=("A","B1","B2","C").index(target_model)
    if covariance is None:
        run=lambda reps,e,m,s: simulate(reps,e,m,s,target_index,target_model)
        variance=paired_sd()**2
        recorded_covariance=[[variance if i==j else variance/2 for j in range(NTEST)] for i in range(NTEST)]
        joint_description="reference model: candidate-minus-D tests share one D component; candidate residuals are mutually independent"
        covariance_limitation="actual A/B1/B2 shared-pi dependence and C portfolio exposure are not calibrated"
    else:
        run=lambda reps,e,m,s: simulate_covariance(reps,e,m,s,covariance,target_index,target_model)
        recorded_covariance=covariance
        joint_description="supplied 4x4 fixed-portfolio covariance matrix captures cross-model overlap and shared-control dependence"
        covariance_limitation="uses average per-draw covariance as a common covariance; draw-to-draw heteroskedasticity is approximated"
    curve=[run(reps,e,1.0,seed+i*100003) for i,e in enumerate(EFFECTS)]
    stress=[run(reps,MDE,m,seed+900001+i*100003) for i,m in enumerate((1.25,1.5,2.0))]
    return {
        "experiment_id":"DLT-PI-200",
        "analysis_type":"PARAMETRIC_MONTE_CARLO_POWER_PLANNING_NOT_BACKTEST",
        "generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z"),
        "runtime":{"python":platform.python_version(),"implementation":platform.python_implementation(),
                   "prng":"random.Random MT19937","base_seed":seed},
        "covariance_source":covariance_source,
        "portfolio_paired_difference_covariance_matrix":recorded_covariance,
        "target_model":target_model,
        "design":{"draws":N,"tickets_per_model_per_draw":T,
                  "endpoint":"draw-level mean front hits per ticket",
                  "comparisons":["A-D","B1-D","B2-D","C-D"],
                  "multiplicity":"Holm step-down; two-sided family alpha 0.05",
                  "mde":MDE,"target_power":0.80},
        "null_reference":{
            "ticket_mean":K*K/NNUM,"ticket_variance":ticket_var(),
            "front_ticket_combinations":COMB,
            "portfolio_mean_variance":ticket_var()/T*(1-T/COMB),
            "paired_difference_sd":paired_sd(),
            "assumption":"candidate and D each behave as independent uniform portfolios of 10 distinct front tickets"},
        "alternative":{
            "type":"draw-level location shift, one candidate shifted; other three null",
            "warning":"statistical power scenario only; not a physical lottery mechanism or predictive evidence",
            "joint_dependence":joint_description,
            "limitation":covariance_limitation},
        "null_fwer_check":curve[0],"power_curve":curve,"noise_inflation_sensitivity":stress,
        "conclusion":(
            "PRELIMINARY_ONLY; actual frozen portfolio exposure covariance is not supplied"
            if covariance is None else
            "PRELIMINARY_PANEL_COVARIANCE_ESTIMATE; final test freeze and heteroskedasticity/normality validation remain pending"
        )
    }


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--simulations",type=int,default=100000)
    ap.add_argument("--seed",type=int,default=SEED)
    ap.add_argument("--output",default="results/power_analysis_preliminary.json")
    ap.add_argument("--power-plan",default="POWER_ANALYSIS_PLAN.md")
    ap.add_argument("--portfolio-covariance",help="200-payload output from portfolio_covariance.py")
    ap.add_argument("--target-model",choices=("A","B1","B2","C"),default="A")
    ap.add_argument("--preregistration-commit",default="d64002531a9a6661c533cb47acdc48d8a89e2ead")
    ap.add_argument("--allow-small-run",action="store_true")
    a=ap.parse_args()
    if a.simulations<100000 and not a.allow_small_run: ap.error("at least 100,000 simulations per scenario required")
    covariance=None
    covariance_source="REFERENCE_ANALYTIC"
    if a.portfolio_covariance:
        panel=json.loads(Path(a.portfolio_covariance).read_text(encoding="utf-8"))
        try:
            covariance=validate_covariance_panel(panel)
        except Exception as exc:
            ap.error(str(exc))
        covariance_source=hashlib.sha256(Path(a.portfolio_covariance).read_bytes()).hexdigest()
    out=report(a.simulations,a.seed,covariance,a.target_model,covariance_source)
    out["provenance"]={
        "source_code_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "power_plan_sha256":hashlib.sha256(Path(a.power_plan).read_bytes()).hexdigest(),
        "preregistration_commit":a.preregistration_commit,
        "portfolio_covariance_sha256":covariance_source if a.portfolio_covariance else None}
    p=Path(a.output); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    mde=next(x["target_power"] for x in out["power_curve"] if x["effect"]==MDE)
    highnoise=next(x["target_power"] for x in out["noise_inflation_sensitivity"] if x["sd_multiplier"]==1.5)
    print(json.dumps({"status":"PRELIMINARY_POWER_REPORT_CREATED","output":str(p),
                      "simulations_per_scenario":a.simulations,"paired_sd":paired_sd(),
                      "mde_power":mde,"power_at_1_5x_noise":highnoise},indent=2))


if __name__=="__main__":
    main()
