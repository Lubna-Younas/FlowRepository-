"""Reconstruct supported FlowJo v10 gates through FlowKit, separately from QC.

This is interoperability testing, not proof of numerical equivalence to FlowJo.
"""
from pathlib import Path
import warnings
import flowkit as fk
import numpy as np
import pandas as pd
from .core import inspect_fcs, sha256, write_json


def import_workspace(workspace, fcs_dir, output):
    out=Path(output)
    if out.exists() and any(out.iterdir()): raise ValueError("Output must be empty")
    paths=sorted(Path(fcs_dir).glob("*.fcs"))
    if not paths: raise ValueError("No FCS files found")
    for path in paths: inspect_fcs(path)
    out.mkdir(parents=True,exist_ok=True)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        w=fk.Workspace(str(workspace),fcs_samples=[str(p) for p in paths],load_missing_file_data=True,find_fcs_files_from_wsp=False)
        ids=w.get_sample_ids(loaded_only=True)
        if not ids: raise ValueError("No supplied FCS files match this workspace")
        w.analyze_samples(use_mp=False)
        report=w.get_analysis_report()
        report.to_csv(out/"gate_statistics.csv",index=False)
        sample_map=[]
        for i,sid in enumerate(ids):
            sample=w.get_sample(sid)
            gate_ids=w.get_gate_ids(sid)
            table=pd.DataFrame({"event_index_0":np.arange(sample.event_count)})
            for gate_name,gate_path in gate_ids:
                table["/".join([*gate_path,gate_name])]=w.get_gate_membership(sid,gate_name,gate_path=gate_path)
            dest=f"sample_{i+1:03d}_gates.csv.gz"
            table.to_csv(out/dest,index=False)
            sample_map.append(dict(sample_id=sid,file=dest,events=sample.event_count,gates=len(gate_ids)))
    result=dict(workspace=Path(workspace).name,workspace_sha256=sha256(workspace),samples=sample_map,
                input_files=[dict(file=p.name,sha256=sha256(p)) for p in paths],warnings=[str(v.message) for v in caught],
                all_workspace_sample_ids=w.get_sample_ids(loaded_only=False),loaded_sample_ids=ids,
                status="RECONSTRUCTED_REQUIRES_FLOWJO_COMPARISON",
                limitations="Partial FlowJo v10 support only; not certified for FlowJo v11, plugins, derived parameters, S8 spectral matrices or native FCS 3.2. Compare counts and event memberships with native FlowJo exports before accepting gates. Original FCS order is retained; no extra filtering applied.")
    write_json(out/"workspace_import.json",result)
    return result
