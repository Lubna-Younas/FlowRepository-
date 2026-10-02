from __future__ import annotations
from html import escape
import json
from pathlib import Path
from datetime import datetime, timezone
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from .palettes import get_palette

SHAPES = ["o", "^", "s", "D", "P", "v", "X", "<"]


def render_report(out, summary, config, samples, frequencies, counts, save_plot_inputs=True):
    out = Path(out)
    style = get_palette(config.get("palette", "soft"))
    colors = style["colors"]
    if save_plot_inputs:
        # Display subsets only; recoloring never refits a model or changes event tables.
        (out/"metadata/report_samples.json").write_text(json.dumps([{k:s[k] for k in ["id", "name"]} for s in samples]))
        np.savez_compressed(out/"metadata/report_plot_data.npz", **{
            f'{s["id"]}_{key}': s[key] for s in samples for key in ["plot_labels", "plot_values", "embedding"]})
    plt.rcParams.update({"svg.fonttype": "none", "pdf.fonttype": 42, "font.size": 10,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "axes.labelcolor": "#233540", "text.color": "#233540", "figure.facecolor": "white"})
    figures=[]
    def save(fig, name, caption):
        fig.tight_layout()
        for extension in ("svg", "pdf"):
            fig.savefig(out/f"figures/{name}.{extension}", bbox_inches="tight")
        plt.close(fig)
        figures.append((name, caption))
    fig, ax=plt.subplots(figsize=(9,4))
    positions=np.arange(len(samples))
    ax.bar(positions-.18, counts.total, width=.36, color=colors[0], edgecolor="#3F4D56", label="Recorded")
    ax.bar(positions+.18, counts.eligible, width=.36, color=colors[1], edgecolor="#3F4D56", hatch="//", label="Eligible")
    ax.set_xticks(positions, counts.event_table); ax.set_ylabel("Events"); ax.legend(); ax.set_title("Event retention")
    save(fig,"event_counts","All recorded events and the denominator used for analysis. Sample IDs are mapped to filenames below.")
    for sample in samples:
        bins=sample["bins"]
        fig, axes=plt.subplots(2,1,figsize=(9,5),sharex=True)
        axes[0].plot(bins.start_event_0, bins.median_first_marker, color=style["accent"], marker="o", ms=3)
        axes[0].set_ylabel("Bin median\n(signal scale)")
        axes[0].set_title(sample["name"] + " — " + config["channels"][0], fontsize=10)
        axes[1].plot(bins.start_event_0, bins.events_per_time_unit, color=style["accent"], marker="s", ms=3)
        axes[1].set_ylabel("Events / time unit"); axes[1].set_xlabel("Original event index (zero based)")
        for row in bins.itertuples():
            if row.flagged:
                for axis in axes: axis.axvspan(row.start_event_0,row.stop_event_exclusive,color=colors[1],alpha=.4,hatch="//")
        save(fig,sample["id"]+"_qc","Hatched intervals require review and are retained. These heuristic flags are not PeacoQC. Time units are instrument-scaled, not assumed seconds.")
        coords=sample["embedding"]
        if len(coords):
            fig, ax=plt.subplots(figsize=(8,5))
            if coords.shape[1]==1: coords=np.column_stack([coords[:,0],np.zeros(len(coords))])
            for label in np.unique(sample["plot_labels"]):
                mask=sample["plot_labels"]==label
                name=f"Cluster {label+1}" if label>=0 else "Eligible events"
                ax.scatter(coords[mask,0],coords[mask,1],s=7,alpha=.65,c=colors[max(label,0)%8],marker=SHAPES[max(label,0)%8],label=name,linewidths=.15,edgecolors="#3F4D56")
            if config["clusters"]<=12: ax.legend(fontsize=8,markerscale=2,bbox_to_anchor=(1.02,1),loc="upper left")
            ax.set(xlabel="PC 1",ylabel="PC 2",title=sample["id"]+" · shared PCA (display subset)")
            save(fig,sample["id"]+"_pca","PCA is a display, not evidence of cell types. Clusters are assigned in transformed marker space. Colors repeat above eight clusters; use tables and labels.")
        if len(sample["plot_values"]):
            fig,ax=plt.subplots(figsize=(9,4))
            for j,channel in enumerate(config["channels"][:8]):
                ax.hist(sample["plot_values"][:,j],bins=60,histtype="step",color=colors[j],linewidth=1.8,label=channel,linestyle=["-","--",":","-."][j%4])
            ax.set(xlabel=f"{config['transform']} signal",ylabel="Displayed events",title=sample["id"]+" · marker distributions")
            ax.legend(fontsize=7,bbox_to_anchor=(1.02,1),loc="upper left")
            save(fig,sample["id"]+"_markers","First eight selected channels. Negative compensated/unmixed values are retained. Full-panel statistics are in exported tables.")
    populations=frequencies.loc[frequencies.population.str.startswith("Cluster ")]
    if len(populations):
        pivot=populations.pivot(index="sample",columns="population",values="fraction").reindex([s["name"] for s in samples]).fillna(0)
        fig,ax=plt.subplots(figsize=(max(7, len(pivot.columns)*.5),max(3,len(samples)*.6)))
        im=ax.imshow(pivot.to_numpy(),cmap=style["heatmap"],vmin=0,vmax=max(float(pivot.max().max()),.01),aspect="auto")
        ax.set_xticks(range(len(pivot.columns)),pivot.columns,rotation=45,ha="right")
        ax.set_yticks(range(len(samples)),[s["id"] for s in samples])
        fig.colorbar(im,ax=ax,label="Fraction of analysis parent")
        ax.set_title("Cluster frequencies · all eligible events")
        save(fig,"cluster_frequencies","A shared clustering model makes IDs consistent within this run. This is not batch normalization; compare only compatible panels and reviewed acquisition conditions.")
    # Scalar and tabular text is escaped, including untrusted FCS file names.
    cards="".join(f'<article><h3>{escape(name.replace("_"," "))}</h3><img src="figures/{name}.svg" alt="{escape(caption)}"><p>{escape(caption)}</p><a href="figures/{name}.svg">SVG</a> · <a href="figures/{name}.pdf">PDF</a></article>' for name,caption in figures)
    warnings="".join(f'<li><strong>{escape(w["sample"])}</strong>: {escape(w["message"])}</li>' for w in summary["warnings"])
    stages="".join(f'<tr><th>{escape(k.replace("_"," "))}</th><td>{escape(str(v))}</td></tr>' for k,v in summary["stages"].items())
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Flow Workbench analysis report</title>
<style>body{{font:16px/1.65 system-ui,sans-serif;color:#233540;background:#fafbfc;margin:0}}main{{max-width:1100px;margin:auto;padding:40px 28px}}h1{{font-size:38px;line-height:1.15}}h2{{margin-top:36px}}.eyebrow{{color:#386d8a;letter-spacing:.1em;font-size:13px}}.status{{background:#f4eadb;padding:14px 20px;border-radius:8px}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;border-bottom:1px solid #d5dfe4;padding:9px;overflow-wrap:anywhere}}th{{background:#eaf1f4}}.table{{overflow-x:auto}}article{{background:white;padding:20px;margin:25px 0;border:1px solid #dce4e8;border-radius:12px}}img{{width:100%;max-height:560px;object-fit:contain}}a{{color:#285d79}}li{{margin:8px 0}}@media print{{body{{background:white}}article{{break-inside:avoid}}}}</style>
<style>body{{background:{style['background']}}}th{{background:{style['surface']}}}a,.eyebrow{{color:{style['accent']}}}</style>
<main><p class="eyebrow">FLOW WORKBENCH · RESEARCH PROTOTYPE {__import__('flowworkbench').__version__}</p><h1>Your flow cytometry results</h1>
<p>{summary['samples']} samples · {summary['events']:,} recorded events · seed {config['seed']}</p>
<p>Color scheme: {escape(style['name'])}. Colors affect presentation only; counts and assignments are unchanged.</p>
<p class="status"><strong>REVIEW REQUIRED.</strong> Exploratory output. No validated biological annotation. Review controls, gates, and acquisition flags before interpreting populations.</p>
<h2>What ran</h2><table>{stages}</table><h2>Event accounting</h2><div class="table">{counts.to_html(index=False,escape=True,border=0)}</div>
<h2>Review notes</h2><ul>{warnings}</ul><h2>Figures</h2>{cards}
<h2>Population frequencies</h2><p>Intervals describe event-counting uncertainty only. Zero observed cells do not establish absence. Counts below {config['rare_event_warning']} are flagged; this is a review threshold, not a validated limit of detection.</p><div class="table">{frequencies.head(100).to_html(index=False,escape=True,border=0,float_format=lambda x:f'{x:.5f}')}</div><p>First 100 rows shown. <a href="tables/population_frequencies.csv">Download complete CSV</a>.</p>
<h2>Reproducibility</h2><p><a href="metadata/config.json">Configuration</a> · <a href="metadata/inputs.json">Input checksums</a> · <a href="metadata/versions.json">Software versions</a> · <a href="summary.json">Run summary</a></p>
<p>Event exports preserve original zero-based indices, QC flags, eligibility, and gate membership. Cluster −1 means unassigned; it is never a biological population. Counts use every eligible event. All figures are editable SVG and PDF; this report is HTML and may be printed to PDF.</p></main></html>'''
    (out/"report.html").write_text(html,encoding="utf-8")


def recolor_report(directory, palette):
    """Regenerate display/export assets using stored plot data, with no reanalysis."""
    get_palette(palette)
    out=Path(directory)
    if not (out/"metadata/report_plot_data.npz").exists():
        raise ValueError("This older report has no saved plot data. Run the analysis once with the updated app to enable recoloring.")
    config=json.loads((out/"metadata/config.json").read_text())
    previous=config.get("palette", "soft")
    config["palette"]=palette
    summary=json.loads((out/"summary.json").read_text())
    samples=json.loads((out/"metadata/report_samples.json").read_text())
    with np.load(out/"metadata/report_plot_data.npz", allow_pickle=False) as arrays:
        for sample in samples:
            for key in ["plot_labels", "plot_values", "embedding"]:
                sample[key]=arrays[f'{sample["id"]}_{key}']
            sample["bins"]=pd.read_csv(out/f'tables/{sample["id"]}_acquisition_qc.csv')
    counts=pd.read_csv(out/"tables/event_counts.csv")
    frequencies=pd.read_csv(out/"tables/population_frequencies.csv")
    render_report(out, summary, config, samples, frequencies, counts, save_plot_inputs=False)
    (out/"metadata/config.json").write_text(json.dumps(config,indent=2))
    history=out/"metadata/presentation_history.json"
    changes=json.loads(history.read_text()) if history.exists() else []
    changes.append(dict(previous_palette=previous,palette=palette,changed_utc=datetime.now(timezone.utc).isoformat(),analysis_recomputed=False))
    history.write_text(json.dumps(changes,indent=2))
    return config
