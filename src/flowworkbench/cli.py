from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys
import yaml
from .core import analyze, inspect_fcs


def main():
    p=argparse.ArgumentParser(prog="flow-workbench",description="Traceable local flow cytometry research prototype")
    sub=p.add_subparsers(dest="command",required=True)
    inspect=sub.add_parser("inspect",help="Read FCS header/metadata without transforming data")
    inspect.add_argument("files",nargs="+")
    run=sub.add_parser("run",help="Run configured QC, gates, exploration and report")
    run.add_argument("files",nargs="+"); run.add_argument("--config",required=True,type=Path)
    run.add_argument("--output",required=True,type=Path); run.add_argument("--sample-sheet",type=Path)
    flowjo=sub.add_parser("flowjo",help="Reconstruct supported gates from a FlowJo v10 WSP")
    flowjo.add_argument("workspace",type=Path);flowjo.add_argument("--fcs-dir",required=True,type=Path);flowjo.add_argument("--output",required=True,type=Path)
    sub.add_parser("gui",help="Launch browser UI on this workstation")
    args=p.parse_args()
    try:
        if args.command=="inspect":
            result=[]
            for path in args.files:
                try: result.append({"status":"METADATA_READABLE",**inspect_fcs(path)})
                except Exception as e: result.append(dict(file=Path(path).name,status="FAIL",error=str(e)))
            print(json.dumps(result,indent=2))
            return int(any(r['status']=='FAIL' for r in result))
        if args.command=="run":
            result=analyze(args.files,args.output,yaml.safe_load(args.config.read_text()),args.sample_sheet)
            print(f"Report: {(args.output/'report.html').resolve()}\nStatus: {result['status']}")
        elif args.command=="flowjo":
            from .flowjo import import_workspace
            r=import_workspace(args.workspace,args.fcs_dir,args.output)
            print(f"Reconstructed {len(r['samples'])} samples. Review {args.output/'workspace_import.json'}")
        else:
            return subprocess.call([sys.executable,"-m","streamlit","run",str(Path(__file__).with_name("app.py")),"--server.address=127.0.0.1","--browser.gatherUsageStats=false"])
    except Exception as e:
        print(f"Analysis stopped: {e}",file=sys.stderr)
        return 1
    return 0


if __name__=="__main__": raise SystemExit(main())
