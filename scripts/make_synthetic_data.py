"""Synthetic stress fixtures. These are NOT biological or instrument validation."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
from flowio import create_fcs

ROOT=Path(__file__).resolve().parents[1]


def main():
    output=ROOT/"data/synthetic";output.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(20261001)
    names=["FSC-A","SSC-A","FSC-H","MarkerA","MarkerB","LiveDead","Time"]
    catalog=[]
    for name,n,rare in [("clean_two_populations",12000,.02),("single_population",3000,0),
                        ("rare_0p1_percent",100000,.001),("low_events",50,.02),("drift_and_nonfinite",10000,.02),
                        ("zero_events",0,0)]:
        x=np.zeros((n,len(names)),dtype=float)
        x[:,0]=rng.normal(60000,4000,n);x[:,1]=rng.normal(20000,2000,n);x[:,2]=x[:,0]*.92
        x[:,3:5]=rng.normal(100,30,(n,2));x[:,5]=rng.normal(50,10,n);x[:,6]=np.arange(n)*.01
        # Fixed integer counts make rare-event survival testable.
        labels=np.zeros(n,dtype=int);ids=rng.choice(n,size=int(n*rare),replace=False);labels[ids]=1
        x[ids,3]=rng.normal(7000,200,len(ids));x[ids,4]=rng.normal(6000,200,len(ids))
        if name=="drift_and_nonfinite":
            x[3000:4000,3]+=4000;x[0,3]=np.nan;x[1,4]=np.inf;x[2,3]=-120
        path=output/f"{name}.fcs"
        with path.open("wb") as f:
            create_fcs(f,x.astype('float32').ravel().tolist(),names,opt_channel_names=["Scatter","Scatter","Scatter","Synthetic A","Synthetic B","Viability proxy","Time"],metadata_dict={"cyt":"SYNTHETIC_NOT_AN_INSTRUMENT","timestep":"1"})
        pd.DataFrame(dict(event_index_0=np.arange(n),synthetic_class=labels)).to_csv(output/f"{name}_truth.csv",index=False)
        catalog.append(dict(file=path.name,events=n,rare_events=int(labels.sum()),synthetic=True))
    # Independent simulated subjects exercise split isolation; do not claim lab accuracy.
    tables=[];splits=[]
    for subject in range(12):
        n=1800;labels=rng.choice(3,size=n,p=[.75,.24,.01])
        centers=np.array([[0,0],[4,4],[8,-1]])
        values=centers[labels]+rng.normal(0,.85,(n,2))+rng.normal(0,.25,2)
        sid=f"synthetic_subject_{subject:02d}"
        frame=pd.DataFrame(values,columns=["MarkerA","MarkerB"])
        frame["subject_id"]=sid;frame["sample_id"]=sid+"_sample";frame["label"]=[f"synthetic_class_{x}" for x in labels]
        frame["panel_id"]="synthetic_panel_v1";tables.append(frame)
        splits.append(dict(subject_id=sid,split="train" if subject<6 else "validation" if subject<9 else "test"))
    pd.concat(tables).to_csv(output/"training_events.csv",index=False)
    pd.DataFrame(splits).to_csv(output/"subject_split.csv",index=False)
    (output/"manifest.json").write_text(json.dumps(catalog,indent=2))
    print(f"Wrote {len(catalog)} FCS stress fixtures and a synthetic training cohort to {output}")


if __name__=="__main__": main()
