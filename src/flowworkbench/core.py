from __future__ import annotations

import hashlib
import importlib.metadata
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import flowio
import numpy as np
import pandas as pd
from scipy.stats import beta, mannwhitneyu

from . import __version__
from .palettes import get_palette


DEFAULTS = dict(
    instrument="generic", signal_state="unknown", channels=[], transform="arcsinh",
    cofactor=150.0, logicle_t=262144.0, logicle_w=0.5, logicle_m=4.5,
    clusters=0, seed=42, fit_events_per_sample=20000, plot_events_per_sample=4000,
    max_events_per_sample=1000000, max_total_events=2000000,
    max_file_mb=200, low_event_warning=1000, rare_event_warning=100,
    qc_bin_events=500, qc_mad_threshold=6.0, gates=[], analysis_parent="all", palette="soft",
)
STATES = {"unknown", "raw_conventional", "compensated", "unmixed", "transformed", "synthetic"}


def sha256(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def validated_config(config=None):
    config = config or {}
    extra = set(config) - set(DEFAULTS)
    if extra:
        raise ValueError(f"Unknown configuration keys: {sorted(extra)}")
    c = {**DEFAULTS, **config}
    get_palette(c["palette"])
    if c["signal_state"] not in STATES:
        raise ValueError("Choose an explicit signal_state")
    if c["instrument"] not in {"generic", "aurora", "s8", "cytof"}:
        raise ValueError("instrument must be generic, aurora, s8, or cytof")
    if c["instrument"] in {"aurora", "s8"} and c["signal_state"] not in {"unknown", "unmixed", "transformed"}:
        raise ValueError("Spectral analysis requires verified unmixed (or already transformed) channels; raw spectral unmixing is not implemented")
    if c["transform"] not in {"none", "arcsinh", "logicle"}:
        raise ValueError("transform must be none, arcsinh, or logicle")
    if c["signal_state"] == "transformed" and c["transform"] != "none":
        raise ValueError("Already transformed data require transform: none")
    for key in ["cofactor", "logicle_t", "logicle_m", "qc_mad_threshold", "max_file_mb"]:
        if not isinstance(c[key], (int, float)) or not np.isfinite(c[key]) or c[key] <= 0:
            raise ValueError(f"{key} must be finite and positive")
    if not 0 <= c["logicle_w"] <= c["logicle_m"] / 2:
        raise ValueError("logicle_w must be between 0 and logicle_m / 2")
    for key in ["fit_events_per_sample", "plot_events_per_sample", "max_events_per_sample", "max_total_events", "low_event_warning", "rare_event_warning", "qc_bin_events"]:
        if type(c[key]) is not int or c[key] < 1:
            raise ValueError(f"{key} must be a positive integer")
    if type(c["seed"]) is not int or not 0 <= c["seed"] < 2**32:
        raise ValueError("seed must be an integer in [0, 2**32)")
    if type(c["clusters"]) is not int or not 0 <= c["clusters"] <= 40:
        raise ValueError("clusters must be an integer from 0 (off) to 40")
    if not isinstance(c["channels"], list) or not all(isinstance(x, str) for x in c["channels"]) or len(set(c["channels"])) != len(c["channels"]):
        raise ValueError("channels must be a list of unique detector names")
    if not isinstance(c["gates"], list):
        raise ValueError("gates must be a list")
    return c


def inspect_fcs(path, max_mb=200):
    path = Path(path)
    if path.stat().st_size > max_mb * 1024**2:
        raise ValueError(f"{path.name}: exceeds {max_mb} MiB per-file limit")
    with path.open("rb") as f:
        version = f.read(6).decode("ascii", errors="replace")
    if version not in {"FCS2.0", "FCS3.0", "FCS3.1"}:
        raise ValueError(f"{version}: parser support verified only for FCS 2.0/3.0/3.1. Native S8 FCS 3.2 requires a separately validated adapter or verified FCS 3.1 export; do not rename the header.")
    f = flowio.FlowData(str(path), only_text=True)  # strict offsets; no silent repair
    channel_metadata = [f.channels[i + 1] for i in range(f.channel_count)]
    channels = [item.get("pnn", "") for item in channel_metadata]
    if not all(channels) or len(set(channels)) != len(channels):
        raise ValueError("Missing or duplicate detector names; resolve explicitly before analysis")
    if int(f.text.get("nextdata", 0)) != 0:
        raise ValueError("Multi-dataset FCS is not supported; export each dataset separately")
    return dict(file=path.name, version=version, events=f.event_count, parameters=f.channel_count,
                datatype=f.text.get("datatype"), instrument=f.text.get("cyt", "unknown"),
                channels=channels, markers=[item.get("pns", "").strip() for item in channel_metadata],
                ranges=[float(item.get("pnr", 0)) for item in channel_metadata],
                has_spillover=bool(f.text.get("spillover") or f.text.get("spill")))


def binomial_interval(k, n, alpha=0.05):
    """Exact Clopper–Pearson interval: event counting uncertainty, not donor variation."""
    if n == 0:
        return None, None
    return (0.0 if k == 0 else float(beta.ppf(alpha/2, k, n-k+1)),
            1.0 if k == n else float(beta.ppf(1-alpha/2, k+1, n-k)))


def time_qc(events, channel_names, selected, config):
    """Conservative exploratory flags; never remove a rare event just for extremeness."""
    size = config["qc_bin_events"]
    positions = np.arange(0, len(events), size)
    if not len(positions):
        return pd.DataFrame(), np.zeros(0, dtype=bool)
    finite = np.isfinite(events[:, selected]).all(axis=1)
    medians = []
    for start in positions:
        good = finite[start:start+size]
        block = events[start:start+size, selected][good]
        medians.append(np.median(block, axis=0) if len(block) else np.full(len(selected), np.nan))
    medians = np.asarray(medians)
    valid_bins = np.isfinite(medians).all(axis=1)
    flags = np.zeros(len(positions), dtype=bool)
    reasons = [""] * len(positions)
    if valid_bins.sum() >= 5:
        center = np.median(medians[valid_bins], axis=0)
        mad = np.median(np.abs(medians[valid_bins] - center), axis=0)
        # A small absolute/relative floor prevents numerical noise at zero MAD.
        denom = np.maximum(1.4826*mad, 1e-8 + np.abs(center)*1e-6)
        scores = np.abs(medians-center)/denom
        flags |= np.any(scores > config["qc_mad_threshold"], axis=1)
        for i in np.flatnonzero(flags):
            reasons[i] = "signal median shift; review acquisition"
    time_indices = [i for i, n in enumerate(channel_names) if n.casefold() == "time"]
    if time_indices:
        all_times = events[:, time_indices[0]]
        resets = np.flatnonzero(np.diff(all_times) < 0) + 1
        for event in resets:
            i = int(event // size)
            flags[i] = True
            reasons[i] += "; acquisition time reversal"
    rows = []
    rates = []
    for i, start in enumerate(positions):
        end = min(start+size, len(events))
        row = dict(start_event_0=int(start), stop_event_exclusive=int(end), events=end-start,
                   median_first_marker=float(medians[i, 0]) if valid_bins[i] else None)
        rate = np.nan
        if time_indices:
            t = events[start:end, time_indices[0]]
            if not np.isfinite(t).all() or (np.diff(t) < 0).any():
                flags[i] = True
                reasons[i] += "; nonfinite or nonmonotonic time"
            elif len(t) > 1 and t[-1] > t[0]:
                rate = (len(t)-1)/(t[-1]-t[0])
        rates.append(rate)
        rows.append(row)
    rates = np.array(rates)
    valid_rates = np.isfinite(rates) & (rates > 0)
    if valid_rates.sum() >= 5:
        lr = np.log(rates[valid_rates]); mid = np.median(lr)
        spread = max(1.4826*np.median(np.abs(lr-mid)), 0.1)
        for i in np.flatnonzero(valid_rates):
            if abs(np.log(rates[i])-mid) > config["qc_mad_threshold"]*spread:
                flags[i] = True; reasons[i] += "; event rate change"
    event_flags = np.zeros(len(events), dtype=bool)
    for i, row in enumerate(rows):
        row.update(flagged=bool(flags[i]), reason=reasons[i].strip("; "),
                   events_per_time_unit=float(rates[i]) if np.isfinite(rates[i]) else None)
        if flags[i]:
            event_flags[row["start_event_0"]:row["stop_event_exclusive"]] = True
    return pd.DataFrame(rows), event_flags


def gate_masks(events, names, gates, finite):
    """Ordered, user-reviewed rectangular or polygon gates in signal space.

    Signal space means after declared compensation, before visualization transform.
    For already transformed inputs, it is their supplied scale.
    """
    from matplotlib.path import Path as PolygonPath
    masks = {"all": finite.copy()}
    for gate in gates:
        name = gate.get("name", "")
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,49}", name) or name in masks:
            raise ValueError("Gate names must be unique, start with a letter, and use letters/numbers/_/-")
        if gate.get("reviewed") is not True:
            raise ValueError(f"Gate {name} requires reviewed: true after checking controls and scale")
        parent = gate.get("parent", "all")
        if parent not in masks:
            raise ValueError(f"Gate {name}: unknown or out-of-order parent {parent}")
        mask = masks[parent].copy()
        if gate.get("type", "rectangle") == "rectangle":
            bounds = gate.get("bounds", {})
            if not bounds:
                raise ValueError(f"Gate {name}: bounds required")
            for channel, bounds_pair in bounds.items():
                if channel not in names or len(bounds_pair) != 2:
                    raise ValueError(f"Invalid bounds/channel in {name}")
                low, high = bounds_pair
                if any(v is not None and not np.isfinite(v) for v in (low, high)):
                    raise ValueError("Gate bounds must be finite or null")
                if low is not None and high is not None and low >= high:
                    raise ValueError("Gate lower bound must be less than upper bound")
                values = events[:, names.index(channel)]
                mask &= np.isfinite(values)
                if low is not None: mask &= values >= low
                if high is not None: mask &= values < high
        elif gate.get("type") == "polygon":
            dims = gate.get("channels", [])
            vertices = np.asarray(gate.get("vertices", []), dtype=float)
            if len(dims) != 2 or any(x not in names for x in dims) or vertices.ndim != 2 or vertices.shape[1] != 2 or len(vertices) < 3 or not np.isfinite(vertices).all():
                raise ValueError(f"Invalid polygon {name}")
            xy = events[:, [names.index(x) for x in dims]]
            mask &= np.isfinite(xy).all(axis=1) & PolygonPath(vertices).contains_points(xy)
        else:
            raise ValueError(f"Unsupported gate type in {name}")
        masks[name] = mask
    return masks


def analyze(paths, output, config=None, sample_sheet=None):
    out = Path(output)
    may_write = not out.exists() or not any(out.iterdir())
    try:
        return _analyze(paths, output, config, sample_sheet)
    except Exception as exc:
        if may_write:
            out.mkdir(parents=True, exist_ok=True)
            write_json(out/"run_failure.json", dict(status="FAILED", error=str(exc), partial_outputs=True))
        raise


def _analyze(paths, output, config=None, sample_sheet=None):
    """One engine for CLI and GUI. Refuse ambiguous biology; preserve event IDs."""
    c = validated_config(config)
    paths = sorted([Path(p).resolve() for p in paths], key=lambda p: p.name)
    if not paths or len({p.name for p in paths}) != len(paths):
        raise ValueError("Provide FCS files with unique basenames")
    if not c["channels"]:
        raise ValueError("Select analysis channels explicitly after inspecting the FCS files")
    if c["signal_state"] == "unknown":
        raise ValueError("Signal processing status unknown: inspection is allowed, analysis requires a declaration")
    inspections = [inspect_fcs(p, c["max_file_mb"]) for p in paths]
    if sum(m["events"] for m in inspections) > c["max_total_events"]:
        raise ValueError("Run exceeds max_total_events; use a smaller batch or an explicitly sized workstation configuration")
    for m in inspections:
        if m["events"] == 0 or m["events"] > c["max_events_per_sample"]:
            raise ValueError(f"{m['file']}: zero events or exceeds max_events_per_sample")
        if set(c["channels"]) - set(m["channels"]):
            raise ValueError(f"{m['file']}: selected channels missing; mixed panels require separate runs")
    marker_maps = [dict(zip(m["channels"], m["markers"])) for m in inspections]
    if any([mapping[x] for x in c["channels"]] != [marker_maps[0][x] for x in c["channels"]] for mapping in marker_maps):
        raise ValueError("Selected channels have inconsistent marker labels across samples; resolve panel mapping before pooling")
    out = Path(output)
    if out.exists() and any(out.iterdir()):
        raise ValueError("Output directory must be empty; existing results are never overwritten")
    out.mkdir(parents=True, exist_ok=True)
    for name in ["figures", "tables", "metadata", "events"]: (out/name).mkdir()
    write_json(out/"metadata/config.json", c)
    write_json(out/"metadata/inputs.json", [{**m, "sha256": sha256(p)} for m, p in zip(inspections, paths)])
    versions = {p: importlib.metadata.version(p) for p in ["flowkit", "flowio", "flowutils", "numpy", "pandas", "scipy", "scikit-learn", "matplotlib"]}
    write_json(out/"metadata/versions.json", {"flow-workbench": __version__, **versions})
    write_json(out/"metadata/source_checksums.json", {p.name: sha256(p) for p in sorted(Path(__file__).parent.glob("*.py"))})
    import flowkit as fk
    from sklearn.cluster import MiniBatchKMeans
    from sklearn.decomposition import PCA
    from .report import render_report
    rng = np.random.default_rng(c["seed"])
    samples, warnings, frequencies, medians = [], [], [], []
    for index, (path, meta) in enumerate(zip(paths, inspections)):
        sid = f"sample_{index+1:03d}"
        s = fk.Sample(str(path))
        events = s.get_events(source="raw").copy()
        names = meta["channels"]
        compensation = "not applied; declared " + c["signal_state"]
        if c["signal_state"] == "raw_conventional":
            spill = s.metadata.get("spillover") or s.metadata.get("spill")
            if not spill:
                raise ValueError(f"{path.name}: raw conventional file lacks a spillover matrix; supply a verified compensated export")
            s.apply_compensation(spill)
            events = s.get_events(source="comp").copy()
            compensation = "FCS spillover applied once to declared raw conventional signals"
        selected = [names.index(x) for x in c["channels"]]
        finite = np.isfinite(events).all(axis=1)
        bins, flags = time_qc(events, names, selected, c)
        bins.to_csv(out/f"tables/{sid}_acquisition_qc.csv", index=False)
        masks = gate_masks(events, names, c["gates"], finite)
        if c["analysis_parent"] not in masks:
            raise ValueError("analysis_parent is not an available gate")
        eligible = masks[c["analysis_parent"]]
        values = events[:, selected].copy()
        if c["transform"] == "arcsinh": values = np.arcsinh(values/c["cofactor"])
        elif c["transform"] == "logicle":
            from flowutils.transforms import logicle
            values[finite] = logicle(values[finite], list(range(len(selected))), t=c["logicle_t"], w=c["logicle_w"], m=c["logicle_m"], a=0)
        if not np.isfinite(values[eligible]).all():
            raise ValueError(f"{path.name}: nonfinite values after transformation")
        messages = ["Acquisition QC flags are exploratory and retained; no automatic time/debris/singlet/viability exclusion."]
        if not finite.all(): messages.append(f"Excluded {int((~finite).sum())} nonfinite events; original indices retained in event table.")
        if eligible.sum() < c["low_event_warning"]: messages.append("Low event count: population estimates and discovery may be unstable.")
        if not any(n.casefold() == "time" for n in names): messages.append("Time channel missing: event-rate QC unavailable; signal drift plotted in acquisition order.")
        if len(bins) < 5: messages.append("Fewer than five acquisition bins: robust drift detection unavailable.")
        if flags.any(): messages.append(f"{int(flags.sum())} events lie in flagged acquisition bins; inspect the QC plot.")
        if not c["gates"]: messages.append("No reviewed cleanup or biological gates: denominator includes all finite recorded events.")
        if not all(marker_maps[index][ch] for ch in c["channels"]): messages.append("Some marker annotations are missing; confirm the selected panel manually.")
        saturation = {}
        for j in selected:
            r = meta["ranges"][j]
            if r > 0:
                fraction = float(np.mean(events[finite, j] >= r - 1)) if finite.any() else 0.0
                saturation[names[j]] = fraction
                if fraction > .01: messages.append(f"{names[j]}: >1% at/above declared detector upper range; review clipping.")
        for message in messages: warnings.append(dict(sample=path.name, message=message))
        gate_parents = {g["name"]: g.get("parent", "all") for g in c["gates"]}
        for name, mask in masks.items():
            parent = gate_parents.get(name, "all")
            n = int(masks[parent].sum()); k = int(mask.sum()); lo, hi = binomial_interval(k, n)
            frequencies.append(dict(sample=path.name, population=name, parent=parent, count=k, denominator=n,
                                    fraction=k/n if n else None, ci_low=lo, ci_high=hi,
                                    low_count=k < c["rare_event_warning"], method="reviewed gate" if name != "all" else "finite events"))
        fit_ids = rng.choice(np.flatnonzero(eligible), size=min(int(eligible.sum()), c["fit_events_per_sample"]), replace=False)
        plot_ids = rng.choice(np.flatnonzero(eligible), size=min(int(eligible.sum()), c["plot_events_per_sample"]), replace=False)
        samples.append(dict(id=sid, name=path.name, values=values, eligible=eligible, finite=finite,
                            masks=masks, qc_flags=flags, bins=bins, fit_ids=fit_ids, plot_ids=plot_ids,
                            total=len(events), compensation=compensation, saturation=saturation))
    pooled = np.vstack([s["values"][s["fit_ids"]] for s in samples])
    k = c["clusters"]
    model = None
    if k:
        if len(pooled) < max(k*10, 50) or len(np.unique(pooled, axis=0)) < k:
            raise ValueError("Too few events or distinct signals for requested clusters; choose clusters: 0 or fewer clusters")
        model = MiniBatchKMeans(n_clusters=k, random_state=c["seed"], n_init=10, batch_size=4096)
        model.fit(pooled)
        write_json(out/"metadata/exploratory_model.json", dict(method="MiniBatchKMeans", centers=model.cluster_centers_.tolist(),
                   channels=c["channels"], seed=c["seed"], training_events=len(pooled), biological_annotation=False,
                   warning="Exploratory shared clusters; chosen k does not estimate the true number of cell types"))
    pca = PCA(n_components=min(2, len(c["channels"]), len(pooled))) if len(pooled) > 1 and np.any(np.std(pooled, axis=0) > 0) else None
    if pca is not None: pca.fit(pooled)
    for s in samples:
        labels = np.full(s["total"], -1, dtype=int)
        if model is not None:
            eligible_ids = np.flatnonzero(s["eligible"])
            for offset in range(0, len(eligible_ids), 50000):
                ids = eligible_ids[offset:offset+50000]
                labels[ids] = model.predict(s["values"][ids])
            for cluster in range(k):
                mask = labels == cluster; n=int(s["eligible"].sum()); count=int(mask.sum())
                lo, hi = binomial_interval(count, n)
                frequencies.append(dict(sample=s["name"], population=f"Cluster {cluster+1}", parent=c["analysis_parent"], count=count,
                                        denominator=n, fraction=count/n if n else None, ci_low=lo, ci_high=hi,
                                        low_count=count < c["rare_event_warning"], method="exploratory clustering"))
                for j, channel in enumerate(c["channels"]):
                    medians.append(dict(sample=s["name"], population=f"Cluster {cluster+1}", channel=channel,
                                        median=float(np.median(s["values"][mask, j])) if count else None, scale=c["transform"]))
        events_table = pd.DataFrame(dict(event_index_0=np.arange(s["total"]), finite=s["finite"],
            acquisition_qc_flag=s["qc_flags"], eligible=s["eligible"], cluster_id_0=labels))
        for name, mask in s["masks"].items(): events_table[f"gate_{name}"] = mask
        events_table.to_csv(out/f"events/{s['id']}.csv.gz", index=False)
        s["plot_labels"] = labels[s["plot_ids"]]
        s["plot_values"] = s["values"][s["plot_ids"]]
        s["embedding"] = pca.transform(s["plot_values"]) if pca is not None and len(s["plot_ids"]) else np.empty((0, 2))
        np.save(out/f"metadata/{s['id']}_fit_event_indices.npy", s["fit_ids"])
        np.save(out/f"metadata/{s['id']}_plot_event_indices.npy", s["plot_ids"])
    freq = pd.DataFrame(frequencies)
    freq.to_csv(out/"tables/population_frequencies.csv", index=False)
    pd.DataFrame(medians, columns=["sample", "population", "channel", "median", "scale"]).to_csv(out/"tables/marker_medians.csv", index=False)
    counts = pd.DataFrame([dict(sample=s["name"], event_table=s["id"], total=s["total"], finite=int(s["finite"].sum()), eligible=int(s["eligible"].sum()), qc_flagged_retained=int(s["qc_flags"].sum()), fit_events=len(s["fit_ids"]), plotted_events=len(s["plot_ids"]), compensation=s["compensation"]) for s in samples])
    counts.to_csv(out/"tables/event_counts.csv", index=False)
    comparison_note = compare_groups(freq, sample_sheet, out)
    summary = dict(version=__version__, created_utc=datetime.now(timezone.utc).isoformat(), samples=len(samples),
                   events=sum(s["total"] for s in samples), status="REVIEW_REQUIRED", warnings=warnings,
                   stages=dict(compensation=c["signal_state"], acquisition_qc="exploratory flags only", biological_cleanup="reviewed configuration gates" if c["gates"] else "not performed",
                   normalization="not performed; matched reference controls required", discovery=f"shared MiniBatchKMeans, k={k}" if k else "off", statistics=comparison_note),
                   counting_intervals="95% exact binomial; event sampling only, not between-donor uncertainty",
                   limitations=["No clinical validation", "No trained cell-type annotation", "No FlowSOM, PeacoQC, CytoNorm, UMAP or raw spectral unmixing in this prototype", "Population estimates use all eligible events; only model fitting and plotting are subsampled"])
    write_json(out/"summary.json", summary)
    render_report(out, summary, c, samples, freq, counts)
    return summary


def compare_groups(frequencies, sample_sheet, out):
    """Bounded exploratory unpaired test. Never treats cells as replicates."""
    if sample_sheet is None: return "descriptive only; no sample metadata supplied"
    metadata = pd.read_csv(sample_sheet, dtype=str, keep_default_na=False)
    required = {"sample", "subject_id", "condition", "batch"}
    if not required.issubset(metadata) or metadata[list(required)].eq("").any().any():
        raise ValueError("Sample sheet requires nonempty sample, subject_id, condition, batch")
    if metadata["sample"].duplicated().any() or set(metadata["sample"]) != set(frequencies["sample"]):
        raise ValueError("Sample sheet must contain exactly one row per input sample")
    if "role" in metadata and not metadata["role"].eq("biological").all():
        raise ValueError("Control tubes must not enter biological comparisons; include only role=biological samples")
    if "panel_id" in metadata and (metadata["panel_id"].eq("").any() or metadata["panel_id"].nunique() != 1):
        raise ValueError("Sample sheet must specify one compatible panel per run")
    metadata.to_csv(out/"metadata/sample_sheet.csv", index=False)
    if metadata["condition"].nunique() != 2: return "descriptive only; this prototype tests exactly two groups"
    if metadata.groupby("subject_id")["condition"].nunique().max() > 1:
        return "descriptive only; repeated/paired subjects require a paired or mixed-effects model"
    if metadata["batch"].nunique() > 1:
        return "descriptive only; multi-batch inference requires a validated batch-aware design"
    merged = frequencies.merge(metadata, on="sample", validate="many_to_one")
    # Technical replicates: pool counts within subject, then compare subject frequencies.
    grouped = merged.groupby(["population", "subject_id", "condition"], as_index=False)[["count", "denominator"]].sum()
    grouped["fraction"] = grouped["count"] / grouped["denominator"].replace(0, np.nan)
    grouped.to_csv(out/"tables/subject_frequencies.csv", index=False)
    conditions = sorted(metadata["condition"].unique())
    rows=[]
    for population, frame in grouped.groupby("population"):
        if population == "all": continue
        a, b = [frame.loc[frame.condition == g, "fraction"].dropna().to_numpy() for g in conditions]
        if min(len(a), len(b)) < 3: continue
        p=float(mannwhitneyu(a,b,alternative="two-sided",method="auto").pvalue)
        rows.append(dict(population=population, condition_a=conditions[0], condition_b=conditions[1],
                         n_subjects_a=len(a), n_subjects_b=len(b), median_difference_b_minus_a=float(np.median(b)-np.median(a)), p_value=p))
    if not rows: return "descriptive only; fewer than 3 independent subjects/group or no eligible populations"
    tests=pd.DataFrame(rows); p=tests.p_value.to_numpy(); order=np.argsort(p)
    adjusted=np.minimum.accumulate((p[order]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]
    q=np.empty(len(p)); q[order]=np.minimum(adjusted,1); tests["q_value_bh"]=q
    tests.to_csv(out/"tables/exploratory_group_tests.csv",index=False)
    return "exploratory unpaired subject-level Mann–Whitney tests with BH correction; small n and post-discovery tests need caution"
