from __future__ import annotations
import io
import json
from pathlib import Path
import tempfile
import zipfile

import pandas as pd
import streamlit as st
import yaml

from flowworkbench.core import analyze, inspect_fcs, validated_config
from flowworkbench.palettes import PALETTES, get_palette
from flowworkbench.report import recolor_report

st.set_page_config(page_title="Flow Workbench", page_icon="◌", layout="wide", initial_sidebar_state="expanded")
if "pending_navigation" in st.session_state:
    st.session_state["navigation"] = st.session_state.pop("pending_navigation")


def navigate(page, demo=None):
    st.session_state["navigation"] = page
    if demo is not None:
        st.session_state["input_mode"] = "Example data" if demo else "My FCS files"


def use_synthetic_settings(channels):
    st.session_state["own_instrument"] = "generic"
    st.session_state["own_signal_state"] = "synthetic"
    st.session_state["own_markers"] = [ch for ch in ["MarkerA", "MarkerB"] if ch in channels]
    st.session_state["own_discovery"] = True
    st.session_state["own_clusters"] = 2


def make_zip(directory):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(directory.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(directory))
    return buffer.getvalue()


def save_uploads(uploads, directory):
    paths = []
    for upload in uploads:
        name = Path(upload.name.replace("\\", "/")).name
        path = directory / name
        if path in paths:
            raise ValueError("Two files have the same name. Give each sample a unique filename first.")
        path.write_bytes(upload.getvalue())
        paths.append(path)
    return paths


def remember_result(output, summary, config, label):
    return {
        "summary": summary, "zip": make_zip(output), "palette": config.get("palette", "soft"),
        "config": config, "input_label": label,
        "counts": pd.read_csv(output / "tables/event_counts.csv"),
        "frequencies": pd.read_csv(output / "tables/population_frequencies.csv"),
        "figures": {p.name: p.read_text() for p in sorted((output / "figures").glob("*.svg"))},
    }


def repaint_result(result, palette):
    # Only the app's own result archive is accepted, never an uploaded ZIP.
    with tempfile.TemporaryDirectory(prefix="flow-colors-") as temporary:
        output = Path(temporary)
        with zipfile.ZipFile(io.BytesIO(result["zip"])) as archive:
            for member in archive.infolist():
                if not (output / member.filename).resolve().is_relative_to(output.resolve()):
                    raise ValueError("Unsafe path in result archive")
            archive.extractall(output)
        config = recolor_report(output, palette)
        return remember_result(output, result["summary"], config, result.get("input_label", "Previous run"))


with st.sidebar:
    st.caption("FLOW WORKBENCH")
    st.radio("Where would you like to go?", ["Start here", "Analyze", "Results", "FlowJo gates"], key="navigation")
    st.divider()
    palette = st.selectbox("Color scheme", list(PALETTES), format_func=lambda key: PALETTES[key]["name"], key="palette_choice")
    style = get_palette(palette)
    swatches = "".join(f'<span title="{color}" style="display:inline-block;width:22px;height:22px;border:1px solid #56616b;border-radius:5px;background:{color};margin:2px"></span>' for color in style["colors"])
    st.markdown(f'<div aria-label="Selected palette colors">{swatches}</div>', unsafe_allow_html=True)
    st.caption(style["description"])
    st.caption("Screen accents change immediately. On Results, apply the scheme to saved figures and downloads without rerunning the analysis.")
    with st.expander("What do these words mean?"):
        st.write("**Event:** one recorded measurement; not necessarily one live cell.")
        st.write("**Marker:** a measured biological signal, for example CD3 or CD4.")
        st.write("**Unmixed:** fluorescence signals already separated by spectral analysis software.")
        st.write("**Gate:** a rule that selects events, similar to a gate in FlowJo.")
        st.write("**Cluster:** events grouped by similar marker signals; the cell type still needs review.")
        st.write("**QC:** quality checks on the file and acquisition.")
    st.caption("Local processing · Research prototype")

st.markdown(f'''<style>
.stApp{{background:{style['background']};color:#233540}}
.block-container{{max-width:1180px;padding-top:3.5rem}}
h1{{letter-spacing:-.03em}} h1,h2,h3,p,label{{color:#233540}}
[data-testid="stSidebar"]{{background:{style['surface']}}}
[data-testid="stMetric"]{{background:{style['surface']};padding:16px;border-radius:12px}}
[data-testid="stMetricValue"]{{font-size:1.25rem!important}}
[data-testid="stBaseButton-primary"]{{background:{style['accent']};border-color:{style['accent']};color:white}}
[data-testid="stBaseButton-primary"] p{{color:white}}
button{{border-radius:9px!important}} .step-number{{color:{style['accent']};font-weight:700;font-size:13px;letter-spacing:.06em}}
.step-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:12px 0 24px}}
.step-card{{background:white;border:1px solid #D5DFE4;border-radius:12px;padding:16px}}
.step-card p{{margin:0}} .step-card .step-number{{margin-bottom:8px;letter-spacing:0}}
</style>''', unsafe_allow_html=True)
route = st.session_state["navigation"]

if route == "Start here":
    st.caption("A GUIDED START")
    st.title("Let’s walk through your first analysis")
    st.write("Start with the public example. It is already on this workstation, so you can learn the workflow before using your own files.")
    steps = [
        ("1 · Choose files", "Try the example or select FCS files from one panel."),
        ("2 · Choose markers", "Tell the app which biological signals to compare."),
        ("3 · Run the analysis", "The app checks acquisition and summarizes the events."),
        ("4 · Review & download", "Read quality notes, inspect figures, then save your report."),
    ]
    cards = "".join(f'<div class="step-card"><p class="step-number">{title}</p><p>{text}</p></div>' for title, text in steps)
    st.markdown(f'<div class="step-grid">{cards}</div>', unsafe_allow_html=True)
    a, b = st.columns(2)
    a.button("Try the example", type="primary", on_click=navigate, args=("Analyze", True), width="stretch")
    b.button("Use my own FCS files", on_click=navigate, args=("Analyze", False), width="stretch")
    st.subheader("What you will get")
    st.write("A readable report, quality-check plots, population summaries, and editable SVG/PDF figures. Changing a color scheme changes their appearance, not the results.")
    with st.expander("How does this fit with our FlowJo workflow?", expanded=True):
        st.write("For a new exploratory analysis, use **Analyze**. To inspect existing gates, use **FlowJo gates** with a saved workspace and its matching FCS files. These are separate workflows; importing a workspace does not automatically add those gates to the exploratory analysis.")
        st.write("For Aurora, use verified unmixed FCS exports. For S8, native FCS 3.2 is not supported yet; a verified supported export is needed. Keep FlowJo as the comparison reference while we validate your panel.")
    with st.expander("What this version does automatically"):
        st.write("Checks FCS metadata; accounts for invalid numeric values; flags acquisition changes; applies the selected transformation; optionally groups events by marker similarity; counts eligible events; creates plots and a report.")
        st.write("It does not yet automatically identify your biological cell types, remove all debris/dead cells/doublets, or normalize batches. Saved expert-reviewed gates can be supplied under advanced settings.")

elif route == "Analyze":
    st.caption("PREPARE YOUR RUN")
    st.title("Analyze FCS files")
    mode = st.radio("Which files would you like to use?", ["Example data", "My FCS files"], horizontal=True, key="input_mode")
    demo = mode == "Example data"
    st.caption("Example data → Run example analysis. My FCS files → upload your files, confirm their settings, then Run analysis.")
    st.subheader("1 · Choose your files")
    uploads = []
    if demo:
        st.info("The example contains 3 public conventional-flow samples. CD3, CD4 and CD8 are selected, and the processing settings are filled in. You can keep them for your first run.")
    else:
        uploads = st.file_uploader("Select FCS files", type="fcs", accept_multiple_files=True)
        st.caption("Use samples from the same panel and processing state. Keep control tubes out of biological comparisons.")
    with tempfile.TemporaryDirectory(prefix="flowworkbench-") as temporary:
        tmp = Path(temporary)
        inputs = tmp / "inputs"
        inputs.mkdir()
        try:
            paths = sorted((Path.cwd() / "data/raw/flowkit/data/8_color_data_set/fcs_files").glob("*.fcs")) if demo else save_uploads(uploads, inputs)
        except ValueError as exc:
            paths = []
            st.error(str(exc))
        if demo and not paths:
            st.error("The example has not been downloaded. From the project folder, run .venv/bin/python scripts/download_data.py, then reload.")
        metadata = []
        for path in paths:
            try:
                metadata.append(inspect_fcs(path))
            except Exception as exc:
                st.error(f"{path.name}: {exc}")
        if paths and len(metadata) == len(paths):
            st.dataframe(pd.DataFrame([{"File": m["file"], "Recorded events": m["events"], "Measured channels": m["parameters"]} for m in metadata]), hide_index=True, width="stretch")
            empty_files = [m["file"] for m in metadata if m["events"] == 0]
            if empty_files:
                st.error("These files contain zero recorded events: " + ", ".join(empty_files) + ". Remove them from this upload selection before running. No files are skipped automatically.")
            synthetic_fixture = all(m["instrument"] == "SYNTHETIC_NOT_AN_INSTRUMENT" for m in metadata)
            if synthetic_fixture and not demo:
                st.info("These files identify themselves as our synthetic software tests, not Aurora/S8 measurements. The shortcut below selects Synthetic test data, MarkerA and MarkerB, and 2 exploratory groups. The empty zero_events.fcs fixture is intended to test rejection and cannot be included in a completed analysis.")
                st.button("Use synthetic test settings", on_click=use_synthetic_settings, args=(metadata[0]["channels"],))
            st.subheader("2 · Confirm the export and select markers")
            if demo:
                instrument, state = "generic", "raw_conventional"
                st.caption("Example preset: conventional flow · apply the file’s spillover matrix once · arcsinh scale · 6 exploratory clusters.")
            else:
                instrument = st.selectbox("Which instrument produced these files?", ["aurora", "s8", "generic", "cytof"], format_func=lambda x: {"aurora": "Cytek Aurora", "s8": "BD FACSDiscover S8", "generic": "Other / conventional flow", "cytof": "Mass cytometry"}[x], key="own_instrument")
                states = ["unknown", "unmixed", "transformed"] if instrument in {"aurora", "s8"} else ["unknown", "compensated", "raw_conventional", "unmixed", "transformed", "synthetic"]
                if st.session_state.get("own_signal_state") not in states:
                    st.session_state["own_signal_state"] = "unknown"
                state = st.selectbox("How were these files exported?", states, format_func=lambda x: {"unknown": "I’m not sure yet", "unmixed": "Already unmixed by spectral analysis software", "compensated": "Already compensated", "raw_conventional": "Raw conventional signals with a verified spillover matrix", "transformed": "Already transformed for display/analysis", "synthetic": "Synthetic test data"}[x], help="The app cannot safely infer this from the filename. Check the instrument export or ask the operator.", key="own_signal_state")
                if state == "unknown":
                    st.info("You can inspect the files now. Before running, confirm their export status with the instrument operator; this prevents applying signal correction twice.")
                if instrument == "s8":
                    st.caption("S8: use one verified unmixed fluorescence channel set. Raw detectors and imaging parameters must not be mixed into marker clustering. Native FCS 3.2 remains unsupported.")
            common = [ch for ch in metadata[0]["channels"] if all(ch in m["channels"] for m in metadata)]
            marker_map = dict(zip(metadata[0]["channels"], metadata[0]["markers"]))
            demo_channels = ["CD3 APC-H7 FLR-A", "CD4 PE-Cy7 FLR-A", "CD8 PerCP-Cy55 FLR-A"]
            default = [ch for ch in demo_channels if ch in common] if demo else []
            channels = st.multiselect("Which markers should be compared?", common, default=default, format_func=lambda ch: f"{marker_map[ch]} · {ch}" if marker_map[ch] else ch, key="demo_markers" if demo else "own_markers")
            st.caption("Choose phenotype markers such as CD3, CD4 or CD8. Leave Time, scatter (FSC/SSC), imaging and viability out of exploratory marker clustering. A viability gate is a separate step.")
            discovery = st.checkbox("Explore groups of similar events (clustering)", value=demo, key="demo_discovery" if demo else "own_discovery")
            clusters = st.number_input("How many exploratory groups?", min_value=1, max_value=40, value=6, help="This is a setting you choose, not an estimate of the true number of cell types.", key="demo_clusters" if demo else "own_clusters") if discovery else 0
            if discovery:
                st.caption("Cluster 1, Cluster 2, etc. are provisional groups. Review marker expression before assigning cell-type names.")
            with st.expander("Advanced settings · optional"):
                st.caption("Keep these values for the example. For your lab panel, use settings agreed with your FlowJo reference analysis.")
                transform_options = ["none"] if state == "transformed" else ["arcsinh", "logicle", "none"]
                transform = st.selectbox("Signal scale (transformation)", transform_options, help="Rescales signal values for analysis and plotting. This is not batch normalization.")
                cofactor = st.number_input("Arcsinh cofactor", min_value=.01, value=150.0)
                a, b, c = st.columns(3)
                log_t = a.number_input("Logicle T", min_value=1.0, value=262144.0)
                log_w = b.number_input("Logicle W", min_value=0.0, value=.5)
                log_m = c.number_input("Logicle M", min_value=.1, value=4.5)
                seed = st.number_input("Random seed", min_value=0, max_value=2**32-1, value=42, help="Fixes the random choices so you can reproduce the run.")
                fit_events = st.number_input("Events used to fit groups, per sample", min_value=100, max_value=100000, value=20000, step=100)
                st.caption("Counts use all eligible events. Only model fitting and plots use a subset; rare groups can still be missed during discovery.")
                gate_yaml = st.text_area("Expert-reviewed gates (YAML list)", value="[]", help="Leave [] for the example. Gates use signal units before the selected transformation; see the project guide.")
                parent = st.text_input("Population to analyze (parent gate)", value="all")
                sample_sheet = st.file_uploader("Optional sample metadata CSV", type="csv", help="Columns: sample, subject_id, condition, batch. Needed for supported biological-group comparisons.")
            config = dict(instrument=instrument, signal_state=state, channels=channels, transform=transform, cofactor=cofactor,
                          clusters=int(clusters), seed=int(seed), fit_events_per_sample=int(fit_events), analysis_parent=parent,
                          logicle_t=log_t, logicle_w=log_w, logicle_m=log_m, palette=palette)
            issue = None
            try:
                config["gates"] = yaml.safe_load(gate_yaml)
                validated_config(config)
            except (ValueError, TypeError, yaml.YAMLError) as exc:
                issue = str(exc)
            st.subheader("3 · Run your analysis")
            st.write(f"**{len(paths)} samples · {len(channels)} selected markers · {int(clusters)} exploratory groups · {style['name']}**")
            st.caption("For this first run: check acquisition quality and explore marker patterns. Automatic biological labels and batch normalization are not included.")
            if issue:
                st.error(issue)
            blockers = []
            if empty_files:
                blockers.append("Remove the zero-event file(s) from the upload selection: " + ", ".join(empty_files))
            if state == "unknown":
                blockers.append("Confirm how the files were exported in step 2; 'I’m not sure yet' keeps Run analysis disabled.")
            if not channels:
                blockers.append("Select at least one marker in step 2.")
            if issue:
                blockers.append("Correct the settings error shown above.")
            if blockers:
                st.warning("Before you can run:\n\n" + "\n".join(f"- {item}" for item in blockers))
            else:
                st.success("Ready to run. Review the selected files and settings, then use the button below.")
            st.download_button("Save settings for this run", yaml.safe_dump(config), "analysis_config.yaml", "text/yaml", disabled=issue is not None)
            if st.button("Run example analysis" if demo else "Run analysis", type="primary", disabled=bool(blockers), key="run_analysis"):
                try:
                    sheet = None
                    if sample_sheet:
                        sheet = tmp / "sample_sheet.csv"
                        sheet.write_bytes(sample_sheet.getvalue())
                    output = tmp / "results"
                    with st.spinner("Checking files, comparing events and preparing your report…"):
                        summary = analyze(paths, output, config, sheet)
                        st.session_state["result"] = remember_result(output, summary, config, "Public example" if demo else "Your FCS files")
                    st.session_state["pending_navigation"] = "Results"
                    st.rerun()
                except Exception as exc:
                    st.error(f"The run stopped: {exc}")
                    st.caption("Any earlier completed result remains on Results; it is not the output of this failed attempt.")
        else:
            st.subheader("2 · Confirm the export and select markers")
            st.caption("These settings appear after all selected FCS files can be read.")
            st.subheader("3 · Run your analysis")
            if not demo and not uploads:
                st.info("First upload your FCS files in step 1. Then confirm their export status and select markers in step 2 to enable Run analysis. To practice without uploading, select Example data above.")
            else:
                st.warning("Resolve the file errors shown above before running. No files are skipped automatically.")
            st.button("Run example analysis" if demo else "Run analysis", type="primary", disabled=True, key="run_analysis")

elif route == "Results":
    st.caption("REVIEW YOUR RUN")
    st.title("Your results, explained")
    if "result" not in st.session_state:
        st.info("No completed analysis in this session yet. Try the example first.")
        st.button("Try the example", type="primary", on_click=navigate, args=("Analyze", True))
    else:
        result = st.session_state["result"]
        current_palette = result.get("palette", "soft")
        st.caption(f"{result.get('input_label', 'Previous run')} · completed {result['summary']['created_utc']} · showing the most recent successful run")
        a, b, c = st.columns(3)
        a.metric("Samples", result["summary"]["samples"])
        b.metric("Recorded events", f"{result['summary']['events']:,}")
        c.metric("Analysis", "Completed")
        st.info("Completed means the calculations finished. Review the quality notes and marker plots before interpreting the biology; it does not mean the samples passed every quality check.")
        if current_palette != palette:
            st.write(f"The report currently uses **{PALETTES[current_palette]['name']}**. You selected **{style['name']}**.")
            if st.button("Apply selected colors to this report", type="primary"):
                try:
                    with st.spinner("Updating figures and downloads; event counts and groups stay unchanged…"):
                        st.session_state["result"] = repaint_result(result, palette)
                    st.rerun()
                except Exception as exc:
                    st.error(str(exc))
        else:
            st.caption(f"Figures and downloads use {style['name']}. Choose a different scheme in the sidebar to recolor them.")
        quality_tab, populations_tab, figures_tab, export_tab = st.tabs(["1 · Quality review", "2 · Populations", "3 · Figures", "4 · Download"])
        with quality_tab:
            st.subheader("Start with the event counts")
            st.write("**Recorded** is everything measured. **Eligible** is what remains after invalid-number checks and any supplied gates. **Flagged** marks acquisition intervals to inspect; those events are retained by this prototype.")
            count_columns = {"sample": "Sample", "total": "Recorded", "eligible": "Eligible", "qc_flagged_retained": "Flagged for review"}
            st.dataframe(result["counts"][list(count_columns)].rename(columns=count_columns), hide_index=True, width="stretch")
            with st.expander("Read the quality notes", expanded=True):
                for warning in result["summary"]["warnings"]:
                    st.write(f"**{warning['sample']}**: {warning['message']}")
            st.caption("A warning is a reason to inspect the sample, not an instruction to delete it. Missing cleanup gates mean eligible events may include debris, dead cells or doublets.")
        with populations_tab:
            st.subheader("How many events are in each group?")
            st.write("A percentage always refers to a parent population. For a run without cleanup gates, the parent is all eligible recorded events. Cluster numbers are not confirmed cell-type names.")
            freq = result["frequencies"].copy()
            freq["Percent of parent"] = (100 * freq["fraction"]).round(3)
            freq["95% lower (%)"] = (100 * freq["ci_low"]).round(3)
            freq["95% upper (%)"] = (100 * freq["ci_high"]).round(3)
            columns = ["sample", "population", "parent", "count", "denominator", "Percent of parent", "95% lower (%)", "95% upper (%)", "low_count"]
            st.dataframe(freq[columns].rename(columns={"sample": "Sample", "population": "Group", "parent": "Parent", "count": "Events in group", "denominator": "Events in parent", "low_count": "Low-count flag"}), hide_index=True, width="stretch")
            st.caption("The interval describes uncertainty from counting events, not variation between donors. A zero count does not prove a population is absent.")
        with figures_tab:
            st.subheader("Choose a plot and read its meaning")
            explanations = {
                "pca": ("Marker-pattern map (PCA)", "Each point is a displayed event. Nearby points have similar patterns in this two-dimensional view. Colors and shapes indicate exploratory groups; separation alone does not identify a cell type."),
                "qc": ("Acquisition quality", "Look for changes during recording. The upper plot shows marker signal; the lower shows acquisition rate. Hatched intervals are flagged for review and have not been automatically removed."),
                "markers": ("Marker distributions", "Each line shows the spread of one selected marker. Values are on the chosen transformed scale; negative values after signal correction can be valid."),
                "event_counts": ("Event retention", "Compare how many events were recorded and how many were eligible for analysis."),
                "cluster_frequencies": ("Group frequencies across samples", "Each square shows a group’s fraction in a sample. Dark/light intensity follows the color bar, and is not a pass/fail score."),
            }
            def describe(filename):
                stem = Path(filename).stem
                key = stem if stem in explanations else stem.rsplit("_", 1)[-1]
                title, explanation = explanations.get(key, (stem, "See the report for details."))
                sample = stem.rsplit("_", 1)[0] if stem.startswith("sample_") else "All samples"
                return f"{title} · {sample}", explanation
            names = list(result["figures"])
            default = next((i for i, name in enumerate(names) if name.endswith("_pca.svg")), 0)
            figure = st.selectbox("Figure", names, index=default, format_func=lambda name: describe(name)[0])
            st.write(describe(figure)[1])
            st.image(result["figures"][figure], width="stretch")
            st.download_button("Download this figure as SVG", result["figures"][figure], figure, "image/svg+xml")
            st.caption("Shapes, labels and line patterns remain in every color scheme. With more than eight groups, colors/shapes repeat; use the labeled tables as well.")
        with export_tab:
            st.subheader("Save the whole analysis")
            st.download_button("Download complete report (ZIP)", result["zip"], "flow_workbench_results.zip", "application/zip", type="primary")
            st.write("**1. Unzip the file. 2. Open report.html. 3. Keep the folders together.**")
            st.write("**figures/** contains editable SVG and PDF plots. **tables/** contains the counts and summaries. **events/** contains original event numbers and labels. **metadata/** records settings, colors and checksums.")
            with st.expander("Exact settings and processing details"):
                st.json(result.get("config", result["summary"]["stages"]))
                st.json(result["summary"]["stages"])
        st.button("Set up another analysis", on_click=navigate, args=("Analyze",))

elif route == "FlowJo gates":
    st.caption("USE YOUR EXISTING WORKSPACE")
    st.title("Inspect your FlowJo gates")
    st.write("Use this route when you already have a saved FlowJo analysis and want to reconstruct its supported gates and counts.")
    st.info("Partial FlowJo v10 support. Compare the output with the original FlowJo analysis. FlowJo v11 and S8 spectral matrix handling have not been validated here.")
    st.write("**1. Select the .wsp workspace. 2. Select its matching original FCS files. 3. Reconstruct the gates.**")
    wsp = st.file_uploader("Saved FlowJo workspace (.wsp)", type="wsp")
    uploads = st.file_uploader("Matching original FCS files", type="fcs", accept_multiple_files=True, key="wsp_fcs")
    st.caption("The workspace describes the gates; it does not contain all the original event data, so both are needed. This route exports gate tables and membership, not the exploratory report.")
    if st.button("Reconstruct supported gates", type="primary", disabled=not wsp or not uploads):
        from flowworkbench.flowjo import import_workspace
        try:
            with tempfile.TemporaryDirectory(prefix="flowjo-review-") as temporary:
                tmp = Path(temporary)
                inputs = tmp / "fcs"
                inputs.mkdir()
                save_uploads(uploads, inputs)
                workspace = tmp / "workspace.wsp"
                workspace.write_bytes(wsp.getvalue())
                output = tmp / "output"
                with st.spinner("Reconstructing workspace gates…"):
                    summary = import_workspace(workspace, inputs, output)
                    st.session_state["wsp_result"] = {"zip": make_zip(output), "summary": summary, "table": pd.read_csv(output / "gate_statistics.csv")}
        except Exception as exc:
            st.error(f"Workspace import stopped: {exc}")
    if "wsp_result" in st.session_state:
        result = st.session_state["wsp_result"]
        st.download_button("Download reconstructed gate tables", result["zip"], "flowjo_gate_reconstruction.zip", "application/zip")
        st.dataframe(result["table"], hide_index=True, width="stretch")
        with st.expander("Import notes and sample matching"):
            st.json(result["summary"])
