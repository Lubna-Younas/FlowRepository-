"""Inventory real public FCS fixtures; expected parser failures remain explicit."""
from pathlib import Path
import json
import pandas as pd
import flowio
from flowworkbench.core import inspect_fcs

root=Path(__file__).resolve().parents[1]
catalog=json.loads((root/"data/catalog/public_fixtures.json").read_text())
rows=[]
for entry in catalog["files"]:
    if not entry["path"].endswith(".fcs"): continue
    path=root/"data/raw"/entry["collection"]/entry["path"]
    row=dict(collection=entry["collection"],file=entry["path"],category=entry["category"])
    try:
        meta=inspect_fcs(path)
        data=flowio.FlowData(str(path))
        if len(data.events) != meta["events"] * meta["parameters"]:
            raise ValueError("DATA length differs from declared event count")
        del data
        row.update(status="READABLE",**{k:v for k,v in meta.items() if k in ["events","parameters","version","datatype","instrument","has_spillover"]})
    except Exception as exc:
        row.update(status="EXPECTED_REJECTION" if entry["category"]=="malformed_fcs_expected_rejection" else "UNEXPECTED_FAILURE",error=str(exc))
    rows.append(row)
out=root/"benchmarks/fixture_audit.csv";pd.DataFrame(rows).to_csv(out,index=False)
print(pd.DataFrame(rows).groupby("status").size().to_string())
print(out)
