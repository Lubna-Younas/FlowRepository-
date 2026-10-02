from pathlib import Path
import importlib.util
import json
import numpy as np
import pandas as pd
import pytest
from flowio import create_fcs
from flowworkbench.core import analyze, validated_config, inspect_fcs, gate_masks, binomial_interval, time_qc, compare_groups

ROOT=Path(__file__).resolve().parents[1]


def fcs(path, values, names=("A","B"),metadata=None):
    with path.open("wb") as handle:
        create_fcs(handle,np.asarray(values,dtype="float32").ravel().tolist(),list(names),metadata_dict=metadata)
    return path


def test_processing_declarations():
    with pytest.raises(ValueError,match="Already transformed"):
        validated_config(dict(signal_state="transformed"))
    with pytest.raises(ValueError,match="Spectral analysis"):
        validated_config(dict(instrument="s8",signal_state="raw_conventional"))
    with pytest.raises(ValueError,match="positive"):
        validated_config(dict(cofactor=-1))
    with pytest.raises(ValueError,match="Unknown"):
        validated_config(dict(silent_typo=True))


def test_exact_intervals_include_zero_uncertainty():
    low,high=binomial_interval(0,100000)
    assert low==0 and 0<high<.00005
    assert binomial_interval(0,0)==(None,None)
    assert binomial_interval(100,100)[1]==1


def test_unreviewed_gates_rejected_and_hierarchy_keeps_parent():
    x=np.array([[0,0],[1,2],[2,3],[3,4]],float)
    with pytest.raises(ValueError,match="reviewed"):
        gate_masks(x,["A","B"],[dict(name="gate",bounds={"A":[0,2]})],np.ones(4,bool))
    gates=[dict(name="parent",reviewed=True,bounds={"A":[0,2]}),dict(name="child",parent="parent",reviewed=True,bounds={"B":[1,None]})]
    masks=gate_masks(x,["A","B"],gates,np.ones(4,bool))
    assert masks["child"].tolist()==[False,True,False,False]


def test_time_flags_are_not_event_removal():
    x=np.ones((1000,2));x[:,1]=np.arange(1000);x[400:500,0]=1000
    bins,flags=time_qc(x,["A","Time"],[0],validated_config(dict(qc_bin_events=100)))
    assert flags[400:500].all() and not flags[:100].any()
    assert bins.flagged.sum()>=1


def test_time_reset_at_bin_boundary_is_not_missed():
    x=np.ones((1000,2));x[:,1]=np.arange(1000);x[500:,1]-=500
    _,flags=time_qc(x,["A","Time"],[0],validated_config(dict(qc_bin_events=100)))
    assert flags[500:600].all()


def test_negative_values_and_rare_counts_survive(tmp_path):
    x=np.column_stack([np.r_[np.full(997,-100.),[5000,5000,5000]],np.ones(1000)])
    path=fcs(tmp_path/"rare.fcs",x)
    config=dict(signal_state="compensated",channels=["A","B"],clusters=0,
        gates=[dict(name="rare",reviewed=True,bounds={"A":[4000,None]})],fit_events_per_sample=10,plot_events_per_sample=10)
    summary=analyze([path],tmp_path/"out",config)
    counts=pd.read_csv(tmp_path/"out/tables/event_counts.csv")
    table=pd.read_csv(tmp_path/"out/tables/population_frequencies.csv")
    assert counts.eligible.iloc[0]==1000
    assert table.loc[table.population=="rare","count"].iloc[0]==3
    assert summary["status"]=="REVIEW_REQUIRED"
    assert (tmp_path/"out/figures/event_counts.svg").exists()


def test_no_double_compensation_and_no_silent_nonfinite(tmp_path):
    path=fcs(tmp_path/"comp.fcs",[[100,20],[120,30],[np.nan,1]],metadata={"spillover":"2,A,B,1,0.1,0,1"})
    for state in ["compensated","raw_conventional"]:
        config=dict(signal_state=state,channels=["A","B"],transform="none",clusters=0,
                    gates=[dict(name="below15",reviewed=True,bounds={"B":[None,15]})])
        out=tmp_path/state;analyze([path],out,config)
        freq=pd.read_csv(out/"tables/population_frequencies.csv")
        assert freq.loc[freq.population=="below15","count"].iloc[0]==(1 if state=="raw_conventional" else 0)
        events=pd.read_csv(out/"events/sample_001.csv.gz")
        assert events.event_index_0.tolist()==[0,1,2]
        assert events.finite.tolist()==[True,True,False]


def test_channel_order_uses_numeric_fcs_order(tmp_path):
    names=[f"X{i}" for i in range(12)]
    path=fcs(tmp_path/"many.fcs",np.arange(24).reshape(2,12),names)
    assert inspect_fcs(path)["channels"]==names


def test_bad_files_and_s8_version_are_explicit(tmp_path):
    path=tmp_path/"s8.fcs";path.write_bytes(b"FCS3.2"+b" "*100)
    with pytest.raises(ValueError,match="3.2"): inspect_fcs(path)
    bad=ROOT/"data/raw/flowkit/data/noncompliant/data_start_offset_discrepancy_example.fcs"
    if bad.exists():
        with pytest.raises(Exception,match="discrepancy"): inspect_fcs(bad)


def test_cross_sample_model_counts_full_files(tmp_path):
    rng=np.random.default_rng(9);paths=[]
    for name in ["a","b"]:
        x=np.vstack([rng.normal(0,.1,(200,2)),rng.normal(8,.1,(50,2))])
        paths.append(fcs(tmp_path/f"{name}.fcs",x))
    c=dict(signal_state="synthetic",channels=["A","B"],transform="none",clusters=2,fit_events_per_sample=100,plot_events_per_sample=5)
    for name in ["one","two"]: analyze(paths,tmp_path/name,c)
    for sid in ["sample_001","sample_002"]:
        a=pd.read_csv(tmp_path/f"one/events/{sid}.csv.gz");b=pd.read_csv(tmp_path/f"two/events/{sid}.csv.gz")
        assert a.cluster_id_0.equals(b.cluster_id_0)
        assert (a.cluster_id_0>=0).sum()==250
    freq=pd.read_csv(tmp_path/"one/tables/population_frequencies.csv")
    assert freq[freq.population.str.startswith("Cluster")].groupby("sample")["count"].sum().tolist()==[250,250]


def test_no_overwrite_or_unknown_signal_state(tmp_path):
    p=fcs(tmp_path/"a.fcs",[[1,2]])
    with pytest.raises(ValueError,match="unknown"):
        analyze([p],tmp_path/"out",dict(channels=["A","B"]))
    out=tmp_path/"existing";out.mkdir();(out/"keep").write_text("retained")
    with pytest.raises(ValueError,match="never overwritten"):
        analyze([p],out,dict(channels=["A","B"],signal_state="synthetic"))
    assert (out/"keep").read_text()=="retained"
    assert json.loads((tmp_path/"out/run_failure.json").read_text())["status"]=="FAILED"


def test_empty_files_and_mixed_panels_are_blocked(tmp_path):
    empty=fcs(tmp_path/"empty.fcs",np.empty((0,2)))
    with pytest.raises(ValueError,match="zero events"):
        analyze([empty],tmp_path/"empty_result",dict(channels=["A","B"],signal_state="synthetic"))
    a=fcs(tmp_path/"a.fcs",[[1,2]])
    b=fcs(tmp_path/"b.fcs",[[1,2]],names=["A","C"])
    with pytest.raises(ValueError,match="mixed panels"):
        analyze([a,b],tmp_path/"mixed_result",dict(channels=["A","B"],signal_state="synthetic"))


def test_small_n_and_paired_data_do_not_create_p_values(tmp_path):
    (tmp_path/"metadata").mkdir();(tmp_path/"tables").mkdir()
    f=pd.DataFrame([dict(sample=f"s{i}",population="rare",count=i,denominator=100,fraction=i/100) for i in range(4)])
    meta=pd.DataFrame(dict(sample=[f"s{i}" for i in range(4)],subject_id=[f"d{i}" for i in range(4)],condition=["A","A","B","B"],batch=["1"]*4))
    path=tmp_path/"sample_sheet.csv";meta.to_csv(path,index=False)
    assert "fewer than 3" in compare_groups(f,path,tmp_path)
    meta.subject_id=["d1","d2","d1","d2"];meta.to_csv(path,index=False)
    assert "paired" in compare_groups(f,path,tmp_path)
    assert not (tmp_path/"tables/exploratory_group_tests.csv").exists()


def test_training_rejects_subject_leakage():
    spec=importlib.util.spec_from_file_location("baseline",ROOT/"scripts/train_baseline.py")
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    f=pd.DataFrame(dict(subject_id=["d1"],sample_id=["s1"],label=["rare"],panel_id=["one"],A=[2.]))
    split=pd.DataFrame(dict(subject_id=["d1","d1"],split=["train","test"]))
    with pytest.raises(ValueError,match="one split"):
        module.validate_splits(f,split,["A"])


def test_recoloring_preserves_analysis_and_all_schemes_export(tmp_path):
    from html import unescape
    from flowworkbench.report import recolor_report
    from flowworkbench.palettes import PALETTES
    path=fcs(tmp_path/"sample.fcs",np.random.default_rng(17).normal(size=(300,2)))
    out=tmp_path/"report"
    analyze([path],out,dict(signal_state="synthetic",channels=["A","B"],clusters=2,plot_events_per_sample=100))
    protected=[p for p in out.rglob("*") if p.is_file() and p.suffix not in {".svg",".pdf",".html"} and p.name!="config.json"]
    original={p:p.read_bytes() for p in protected}
    for key, palette in PALETTES.items():
        config=recolor_report(out,key)
        assert config["palette"]==key
        assert palette["name"] in unescape((out/"report.html").read_text(encoding="utf-8"))
        assert palette["colors"][0].lower() in (out/"figures/event_counts.svg").read_text(encoding="utf-8").lower()
        assert (out/"figures/event_counts.pdf").read_bytes().startswith(b"%PDF")
        assert all(p.read_bytes()==contents for p,contents in original.items())
    assert all(not change["analysis_recomputed"] for change in json.loads((out/"metadata/presentation_history.json").read_text()))
    with pytest.raises(ValueError,match="palette"):
        validated_config(dict(palette="unrecognized"))
