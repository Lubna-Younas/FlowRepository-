"""Panel-specific Random Forest benchmark with explicitly disjoint subject splits.

Not wired into the app. Real labels need independent expert review and compatible
signal processing. Synthetic results test the harness, not biological accuracy.
"""
import argparse
import json
from pathlib import Path
import platform

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score, balanced_accuracy_score
from flowworkbench.core import sha256, write_json


def validate_splits(frame,splits,features):
    required={"subject_id","sample_id","label","panel_id"}
    if not required.issubset(frame) or not {"subject_id","split"}.issubset(splits):
        raise ValueError("Events require subject_id,sample_id,label,panel_id; splits require subject_id,split")
    if frame[list(required)].isna().any().any() or frame[list(required)].astype(str).eq("").any().any():
        raise ValueError("Missing identifiers or labels")
    if frame.panel_id.nunique()!=1: raise ValueError("Train one compatible panel at a time")
    if len(set(features))!=len(features) or set(features)&required or not set(features).issubset(frame):
        raise ValueError("Features must be unique measured signals, excluding labels and identifiers")
    if splits.subject_id.duplicated().any() or set(splits.subject_id)!=set(frame.subject_id):
        raise ValueError("Exactly one split per subject is required; no unmatched or overlapping subjects")
    if frame.groupby("sample_id").subject_id.nunique().max()!=1:
        raise ValueError("A sample cannot belong to multiple subjects")
    if set(splits.split)!={"train","validation","test"}:
        raise ValueError("Specify train, validation, and test splits")
    if (splits.groupby("split").size()<2).any(): raise ValueError("Require at least two independent subjects in every split; more are needed for credible validation")
    if not np.isfinite(frame[features].to_numpy(dtype=float)).all(): raise ValueError("Nonfinite features must be resolved before training")
    return frame.merge(splits,on="subject_id",validate="many_to_one")


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--events",required=True,type=Path);p.add_argument("--split",required=True,type=Path)
    p.add_argument("--features",nargs="+",required=True);p.add_argument("--output",required=True,type=Path)
    p.add_argument("--synthetic",action="store_true");p.add_argument("--seed",type=int,default=42)
    args=p.parse_args()
    if args.output.exists() and any(args.output.iterdir()): raise ValueError("Output must be empty")
    if args.events.stat().st_size>500*1024**2: raise ValueError("Prototype training input limited to 500 MiB; use a streaming adapter for larger studies")
    frame=validate_splits(pd.read_csv(args.events),pd.read_csv(args.split),args.features)
    train=frame[frame.split=="train"]
    # Class cap per training subject keeps rare training labels and bounds resources.
    fit=pd.concat([g.sample(n=min(len(g),2000),random_state=args.seed) for _,g in train.groupby(["subject_id","label"])])
    model=RandomForestClassifier(n_estimators=200,max_depth=18,min_samples_leaf=2,class_weight="balanced_subsample",random_state=args.seed,n_jobs=2)
    model.fit(fit[args.features],fit.label)
    args.output.mkdir(parents=True,exist_ok=True)
    joblib.dump(model,args.output/"model.joblib")
    labels=sorted(frame.label.unique());results={};subject_results=[]
    for split in ["validation","test"]:
        subset=frame[frame.split==split].copy()
        pred=model.predict(subset[args.features]);prob=model.predict_proba(subset[args.features]).max(axis=1)
        results[split]=dict(macro_f1=float(f1_score(subset.label,pred,labels=labels,average="macro",zero_division=0)),
            balanced_accuracy=float(balanced_accuracy_score(subset.label,pred)),
            per_class=classification_report(subset.label,pred,labels=labels,output_dict=True,zero_division=0),
            confusion_matrix=confusion_matrix(subset.label,pred,labels=labels).tolist(),labels=labels,
            unknown_labels=sorted(set(subset.label)-set(model.classes_)),
            below_fixed_0p6_confidence_fraction=float(np.mean(prob<.6)))
        subset["prediction"]=pred;subset["max_vote_fraction_uncalibrated"]=prob
        subset[["subject_id","sample_id","label","prediction","max_vote_fraction_uncalibrated"]].to_csv(args.output/f"{split}_predictions.csv.gz",index=False)
        for sid,g in subset.groupby("subject_id"):
            subject_results.append(dict(subject_id=sid,split=split,events=len(g),macro_f1=float(f1_score(g.label,g.prediction,labels=labels,average="macro",zero_division=0))))
    pd.DataFrame(subject_results).to_csv(args.output/"subject_metrics.csv",index=False)
    write_json(args.output/"metrics.json",results)
    card=dict(status="SYNTHETIC_HARNESS_TEST_ONLY" if args.synthetic else "EXPERIMENTAL_UNVALIDATED",
              dataset_sha256=sha256(args.events),split_sha256=sha256(args.split),model_sha256=sha256(args.output/"model.joblib"),
              python=platform.python_version(),sklearn=__import__('sklearn').__version__,features=args.features,
              panel_id=str(frame.panel_id.iloc[0]),random_seed=args.seed,fit_events=len(fit),total_events=len(frame),
              subjects=frame.groupby('split').subject_id.unique().apply(list).to_dict(),
              preprocessing="Input must already have compatible compensation/unmixing/transformation; no normalization is fitted here",
              selection="Fixed architecture; no tuning on test subjects; training cap 2000 events per class per subject",
              limitations=["No evidence of Aurora/S8 transfer", "Expert label uncertainty is not modeled", "Vote fractions are not calibrated probabilities", "Do not deserialize untrusted joblib models", "Synthetic performance is not biological accuracy"],metrics=results)
    write_json(args.output/"model_card.json",card)
    print(json.dumps({"status":card["status"],"fit_events":len(fit),"test_macro_f1":results["test"]["macro_f1"]},indent=2))


if __name__=="__main__": main()
