import numpy as np, pandas as pd, os, random
from datetime import datetime, timedelta
rng = np.random.default_rng(42); random.seed(42)
OUT = "/home/claude/vajra_data"
TODAY = datetime(2026,10,11)

# ---------- 1. bases / depots ----------
bases = pd.DataFrame([
 ("BASE01","Air Force Station Ambala","Haryana",3,2),
 ("BASE02","Air Force Station Pune","Maharashtra",2,2),
 ("BASE03","Air Force Station Jodhpur","Rajasthan",3,1),
 ("BASE04","Air Force Station Tezpur","Assam",2,1),
 ("BASE05","Air Force Station Bengaluru (BRD)","Karnataka",4,3)],
 columns=["base_id","base_name","state","daily_maintenance_slots","hangar_bays"])
bases.to_csv(f"{OUT}/bases_maintenance_agencies.csv", index=False)

# ---------- 2. fleet ----------
types = [("Transport-A","Twin-turbofan",2),("Fighter-B","Twin-turbofan",2),("Trainer-C","Single-turbofan",1),("Heli-D","Twin-turboshaft",2)]
fleet, engines = [], []
n_air = 24
eid = 1
for i in range(1, n_air+1):
    t = types[(i-1) % 4]
    base = bases.base_id[rng.integers(0,5)]
    fh = int(rng.integers(1500, 9000))
    tail = f"VJ-{100+i}"
    fleet.append(dict(aircraft_id=tail, aircraft_type=t[0], engine_config=t[1], num_engines=t[2], base_id=base,
        commission_year=int(rng.integers(2008,2022)), total_flight_hours=fh,
        mission_role=random.choice(["Transport","Combat","Training","Surveillance"]),
        last_inspection_date=(TODAY-timedelta(days=int(rng.integers(5,120)))).date()))
    for p in range(t[2]):
        engines.append(dict(engine_id=f"ENG-{eid:03d}", aircraft_id=tail, position=p+1, engine_model="TF-"+("30" if t[0]!="Heli-D" else "TS-20"),
            install_date=(TODAY-timedelta(days=int(rng.integers(200,1800)))).date(),
            cycles_since_new=int(rng.integers(300,3000)), hours_since_overhaul=int(rng.integers(100,1800))))
        eid += 1
fleet = pd.DataFrame(fleet); engines = pd.DataFrame(engines)
fleet.to_csv(f"{OUT}/fleet_aircraft.csv", index=False)
engines.to_csv(f"{OUT}/engines.csv", index=False)
n_eng = len(engines)

# ---------- 3. training data (C-MAPSS style, run-to-failure) ----------
sensor_names = ["T24_lpc_outlet_temp","T30_hpc_outlet_temp","T50_lpt_outlet_temp","P30_hpc_outlet_pressure",
 "Nf_fan_speed","Nc_core_speed","Ps30_static_pressure","phi_fuel_flow_ratio","NRf_corr_fan_speed",
 "NRc_corr_core_speed","BPR_bypass_ratio","htBleed","W31_hpt_coolant_bleed","W32_lpt_coolant_bleed","vibration_mm_s"]
base_val = [642,1590,1408,554,2388,9050,47.5,521,2388,8140,8.4,393,39,23.4,2.0]
# sign/magnitude of drift at end-of-life
drift = [+2.5,+30,+45,-1.5,+0.05,+25,+1.2,-2.0,+0.07,+30,+0.15,+8,-1.5,-0.9,+4.5]
noise = [0.4,5,6,0.1,0.05,8,0.12,0.3,0.05,10,0.03,1.2,0.15,0.1,0.15]
rows=[]
for e in range(1,61):  # 60 training engines
    life = int(rng.integers(150,320))
    onset = int(life*rng.uniform(0.35,0.55))
    for c in range(1,life+1):
        s = max(0,(c-onset)/(life-onset))**1.8   # degradation 0..1
        alt = random.choice([0,10000,20000,25000,35000,42000]); mach=random.choice([0,0.25,0.62,0.7,0.84])
        tra = random.choice([60,80,100])
        r = dict(engine_id=f"TRN-{e:03d}", cycle=c, altitude_ft=alt, mach=mach, throttle_resolver_angle=tra)
        for k,(n,b,d,nz) in enumerate(zip(sensor_names,base_val,drift,noise)):
            r[n]=round(b + d*s + rng.normal(0,nz),3)
        r["rul_true"]=life-c
        r["rul_capped_125"]=min(125,life-c)
        rows.append(r)
train = pd.DataFrame(rows)
train.to_csv(f"{OUT}/train_sensor_run_to_failure.csv", index=False)

# test set: 20 engines truncated before failure
trows=[]; truth=[]
for e in range(1,21):
    life = int(rng.integers(150,320)); onset=int(life*rng.uniform(0.35,0.55))
    cut = int(rng.integers(int(life*0.4), life-5))
    for c in range(1,cut+1):
        s=max(0,(c-onset)/(life-onset))**1.8
        r=dict(engine_id=f"TST-{e:03d}",cycle=c,altitude_ft=random.choice([0,10000,20000,35000]),mach=random.choice([0,0.25,0.62,0.84]),throttle_resolver_angle=random.choice([60,80,100]))
        for n,b,d,nz in zip(sensor_names,base_val,drift,noise): r[n]=round(b+d*s+rng.normal(0,nz),3)
        trows.append(r)
    truth.append(dict(engine_id=f"TST-{e:03d}",rul_true=life-cut))
pd.DataFrame(trows).to_csv(f"{OUT}/test_sensor_truncated.csv",index=False)
pd.DataFrame(truth).to_csv(f"{OUT}/test_rul_ground_truth.csv",index=False)

# ---------- 4. fleet current state: health, RUL ----------
state=[]
profiles = rng.choice(["healthy","watch","critical"], size=n_eng, p=[0.75,0.17,0.08])
for (_,en),pf in zip(engines.iterrows(),profiles):
    if pf=="healthy": hs=rng.uniform(72,98); rul=int(rng.integers(90,250)); an=rng.uniform(0.02,0.30)
    elif pf=="watch": hs=rng.uniform(42,69); rul=int(rng.integers(30,90)); an=rng.uniform(0.40,0.65)
    else: hs=rng.uniform(8,38); rul=int(rng.integers(2,25)); an=rng.uniform(0.72,0.97)
    state.append(dict(engine_id=en.engine_id, aircraft_id=en.aircraft_id, health_score=round(hs,1),
        status="Healthy" if hs>=70 else ("Watch" if hs>=40 else "Critical"),
        predicted_rul_cycles=rul, anomaly_score=round(an,3),
        failure_risk_7d=round(min(0.99,max(0.01,(1-hs/100)**1.5)),3), last_updated=TODAY.strftime("%Y-%m-%d %H:%M")))
state=pd.DataFrame(state); state.to_csv(f"{OUT}/engine_health_status.csv",index=False)

# ---------- 5. component health ----------
comps=["Fan","Compressor","Combustion Chamber","Turbine","Shaft"]
ch=[]
for _,s in state.iterrows():
    worst=random.choice(comps)
    for c in comps:
        h=s.health_score+rng.normal(0,5)
        if c==worst: h-=rng.uniform(5,25)
        h=float(np.clip(h,2,100))
        ch.append(dict(engine_id=s.engine_id,component=c,health_score=round(h,1),
          colour="Green" if h>=70 else ("Yellow" if h>=40 else "Red"),
          shap_contribution=round((100-h)/100*rng.uniform(0.5,1.2),3)))
pd.DataFrame(ch).to_csv(f"{OUT}/component_health.csv",index=False)

# ---------- 6. live stream (60 min, 1 reading / 10 s subset => every 30s) ----------
live=[]
t0=TODAY.replace(hour=9,minute=0)
for _,s in state.iterrows():
    if s.engine_id not in list(state.sort_values("health_score").engine_id[:4])+list(state.engine_id[:2]): continue
    sev = (100-s.health_score)/100
    for k in range(120):
        ts=t0+timedelta(seconds=30*k); ramp=(k/120)
        live.append(dict(timestamp=ts.strftime("%Y-%m-%d %H:%M:%S"),engine_id=s.engine_id,
          temp_c=round(480+60*sev*ramp+rng.normal(0,3),2), pressure_kpa=round(100+25*sev*ramp+rng.normal(0,1.5),2),
          vibration_mm_s=round(2+5*sev*ramp**2+rng.normal(0,0.15),3), fan_rpm=round(9000+rng.normal(0,30),0),
          oil_pressure_psi=round(55-8*sev*ramp+rng.normal(0,0.6),2), egt_c=round(620+70*sev*ramp+rng.normal(0,4),1)))
pd.DataFrame(live).to_csv(f"{OUT}/live_stream_simulation.csv",index=False)

# ---------- 7. maintenance records ----------
mtypes=[("Scheduled Inspection",8,"Routine"),("Borescope Inspection",12,"Routine"),("Oil System Service",6,"Routine"),
 ("Fan Blade Replacement",48,"Unscheduled"),("Compressor Wash",10,"Routine"),("Turbine Blade Repair",72,"Unscheduled"),
 ("Sensor Replacement",5,"Unscheduled"),("Bearing Replacement",60,"Unscheduled"),("Major Overhaul",300,"Scheduled")]
mr=[]
for i in range(1,451):
    en=engines.iloc[rng.integers(0,n_eng)]; m=random.choice(mtypes)
    d=TODAY-timedelta(days=int(rng.integers(1,900)))
    mr.append(dict(record_id=f"MR-{i:05d}",engine_id=en.engine_id,aircraft_id=en.aircraft_id,date=d.date(),
      maintenance_type=m[0],category=m[2],downtime_hours=int(m[1]*rng.uniform(0.7,1.5)),
      technician_id=f"TECH-{rng.integers(1,40):03d}",base_id=fleet.base_id[fleet.aircraft_id==en.aircraft_id].iloc[0],
      fault_found=random.choice(["None","Wear","Crack","Leak","Sensor drift","Foreign object damage"]) if m[2]!="Routine" else random.choice(["None","None","Wear"]),
      cost_inr_lakh=round(rng.uniform(0.2,4)*(m[1]/10+1),2)))
pd.DataFrame(mr).sort_values("date").to_csv(f"{OUT}/maintenance_history.csv",index=False)

# ---------- 8. spares ----------
parts=[("Fan Blade Set","Fan",6.5,45),("Compressor Rotor","Compressor",18,90),("Combustor Liner","Combustion Chamber",9,60),
 ("Turbine Blade Set","Turbine",14,75),("Main Shaft Bearing","Shaft",4.2,30),("Vibration Sensor","Sensors",0.3,10),
 ("Temp Sensor (EGT)","Sensors",0.25,10),("Fuel Nozzle","Combustion Chamber",1.1,20),("Oil Pump","Lubrication",2.4,25),("Seal Kit","General",0.4,7)]
sp=[]
for b in bases.base_id:
    for j,(nm,comp,cost,lead) in enumerate(parts):
        qty=int(rng.integers(0,6)); 
        sp.append(dict(part_id=f"PRT-{j+1:03d}",part_name=nm,component=comp,base_id=b,qty_in_stock=qty,
          reorder_level=2,lead_time_days=int(lead*rng.uniform(0.8,1.4)),unit_cost_inr_lakh=cost,
          supplier=random.choice(["HAL","BEL","GTRE","Imported OEM"])))
pd.DataFrame(sp).to_csv(f"{OUT}/spares_inventory.csv",index=False)

# ---------- 9. alerts ----------
al=[]
sev_map={"Critical":"High","Watch":"Medium","Healthy":"Low"}
trig=["Vibration > limit","EGT margin low","Low RUL","Anomaly score high","Oil pressure drop","Pressure deviation"]
n=0
for _,s in state[state.status!="Healthy"].iterrows():
    for _ in range(int(rng.integers(1,4))):
        n+=1; ts=TODAY.replace(hour=0,minute=0)-timedelta(minutes=int(rng.integers(0,1440)))
        al.append(dict(alert_id=f"ALT-{n:04d}",timestamp=ts.strftime("%Y-%m-%d %H:%M"),engine_id=s.engine_id,
          aircraft_id=s.aircraft_id,severity=sev_map[s.status],trigger=random.choice(trig),
          anomaly_score=round(min(0.99,s.anomaly_score+rng.normal(0,0.04)),3),rul_cycles=s.predicted_rul_cycles,
          status=random.choice(["Unacknowledged","Acknowledged","In Progress","Resolved"])))
pd.DataFrame(al).sort_values("timestamp",ascending=False).to_csv(f"{OUT}/alerts.csv",index=False)

# ---------- 10. rule engine thresholds ----------
rules=pd.DataFrame([
 ("vibration_mm_s",">",5.0,"Critical","Immediate inspection"),("vibration_mm_s",">",3.5,"Warning","Schedule borescope"),
 ("egt_c",">",720,"Critical","Reduce thrust, inspect turbine"),("egt_c",">",680,"Warning","Monitor trend"),
 ("oil_pressure_psi","<",40,"Critical","Ground aircraft"),("oil_pressure_psi","<",48,"Warning","Check oil system"),
 ("temp_c",">",560,"Critical","Inspect combustor"),("temp_c",">",530,"Warning","Monitor"),
 ("predicted_rul_cycles","<",15,"Critical","Plan replacement"),("predicted_rul_cycles","<",40,"Warning","Order spares")],
 columns=["parameter","operator","threshold","severity","recommended_action"])
rules.to_csv(f"{OUT}/rule_engine_thresholds.csv",index=False)

# ---------- 11. fleet availability history + mission demand ----------
av=[]
for d in range(180,0,-1):
    day=TODAY-timedelta(days=d)
    for b in bases.base_id:
        tot=int((fleet.base_id==b).sum()); 
        if tot==0: continue
        unsched=int(rng.binomial(tot,0.08)); sched=int(rng.binomial(tot,0.10))
        ready=max(0,tot-unsched-sched)
        av.append(dict(date=day.date(),base_id=b,total_aircraft=tot,mission_ready=ready,
           under_scheduled_maintenance=sched,under_unscheduled_maintenance=unsched,availability_pct=round(100*ready/tot,1)))
pd.DataFrame(av).to_csv(f"{OUT}/fleet_availability_history.csv",index=False)
md=[dict(date=(TODAY+timedelta(days=d)).date(),base_id=b,aircraft_required=int(max(1,round((fleet.base_id==b).sum()*rng.uniform(0.55,0.8)))))
    for d in range(0,14) for b in bases.base_id if (fleet.base_id==b).sum()>0]
pd.DataFrame(md).to_csv(f"{OUT}/mission_demand_next14d.csv",index=False)
print("done")
