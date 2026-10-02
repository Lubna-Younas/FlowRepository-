# Dataset register and download status

Recorded on 2026-10-01. The working collection contains **28 downloaded files, including 17 FCS, totaling 80.12 MiB**. They come from three public software repositories. This is a diverse fixture collection, not 28 independent biological datasets or donors.

Every file is pinned to an upstream commit, checked against its published Git blob digest and size, and recorded with a SHA-256 checksum. The catalog is `data/catalog/public_fixtures.json`; the local receipt is `data/raw/download_manifest.json`. The software source archive excludes third-party raw data; recipients use the downloader to retrieve the same files.

| Collection | Files downloaded | Purpose | Limitations |
|---|---|---|---|
| [FlowKit](https://github.com/whitews/FlowKit) | FCS examples, 8-color workspace and spillover CSV, simple-gate workspace, README and license | Conventional fluorescence, compensation, gates, FCS 2.0/3.0/3.1, integer and floating-point signals, low event counts, index sorting, malformed offsets | Mix of real and synthetic examples. Subject/control provenance is insufficient for independent model validation. Three 8-color files may share biological source; never invent donor IDs. |
| [PeacoQC](https://github.com/saeyslab/PeacoQC) | 111.fcs, 111_Comp_Trans.fcs, DESCRIPTION and README | Raw versus processed method examples and acquisition-QC development | These are related versions, not independent samples. The processed file must not be compensated/transformed again. No expert artifact truth imported. |
| [FlowSOM](https://github.com/saeyslab/FlowSOM) | 68983.fcs, gating.wsp, gatingResult.csv, DESCRIPTION and README | Mouse immune example with gates and population labels | One sample cannot establish donor generalization or Aurora/S8 transfer. Label agreement is a software fixture check. |

The full DATA-segment audit in `benchmarks/fixture_audit.csv` finds **14 readable files, two expected malformed-offset rejections, and one additional strict rejection**: `test_comp_example.fcs` has an off-by-one DATA offset. Its metadata can be read, but strict event loading rejects it; it was not silently repaired or included in the analysis. The audit records event counts, channel counts, data types and FCS versions. Readability is not a biological QC pass.

The mouse workspace reconstruction was compared with the bundled event labels. Five named populations match event membership exactly. CD4 T-cell membership differs by **5 of 19,225 events** (7,482 reconstructed versus 7,487 reference events). This unresolved discrepancy is recorded in `benchmarks/flowjo_fixture_agreement.csv`; no claim of complete FlowJo parity is made.

Repository licenses and source notices are retained where available. A software repository license does not automatically settle all underlying study/data rights. Before redistribution, commercial reuse or production model training, verify study-level terms and consent restrictions. No license acceptance or account registration was performed during these downloads.

## Synthetic collection

`scripts/make_synthetic_data.py` creates six FCS fixtures with known numeric truth: 12,000 events/two proxies, 3,000 events/one population, 100,000 events/100 rare proxies (0.1%), 50 total events, drift plus NaN/infinity/negative values, and a zero-event file. The last is an expected analysis rejection. These files are marked synthetic in metadata and in the manifest.

The same script creates 21,600 simulated training-table events across 12 simulated subjects and explicit training/validation/test partitions. This only tests the model harness. No simulation is presented as a patient or as empirical evidence of biological accuracy.

## Expansion queue

| Source | Why it matters | Current status |
|---|---|---|
| [FlowCyt](https://github.com/VIPER-GENEVA/FlowCyt-Classification-Benchmark) | Labeled human bone marrow across 30 patients; donor-separated classification development | Repository and instructions reviewed. The publisher-linked UNIGE download endpoint timed out. No FlowCyt patient data downloaded or used for training. |
| [HDCytoData](https://bioconductor.org/packages/release/data/experiment/html/HDCytoData.html) | Curated high-dimensional benchmarks with sample, patient and reference population metadata where available | Catalog reviewed; data not downloaded. Use a compatible pinned R/Bioconductor environment; inspect source cohort and terms before selecting datasets. |
| [Aurora 40-color raw OMIP data FR-FCM-Z2QT](https://flowrepository.org/id/FR-FCM-Z2QT) | Public spectral raw-data compatibility and reference-control development | Source identified, but page retrieval returned 502 in this session. Raw spectral files would still require a validated unmixing workflow. No claim of spectral validation. |
| Your Aurora/S8 lab | Matched panels, instruments, operators, controls and expert FlowJo gates | Not provided. This is the essential external validation set for the intended users. |

FlowRepository's own landing page reports storage-related upload/download problems. This can affect availability; failed retrievals must remain visible rather than substituted with unlabeled or unrelated data. [Repository status](https://flowrepository.org/).

## Coverage still missing

The current set does not establish native S8 FCS 3.2 support, spectral reference validity, imaging-parameter handling, multi-lab panel transfer, real rare-cell sensitivity/specificity, limit of detection/quantification, multi-batch normalization or independent clinical population annotation. Additional priorities are difficult real acquisitions with expert artifact labels, low-dimensional real panels with few populations, enough independent subjects, and matched shared controls across days.

Do not merge different tissues/species or panels to increase the nominal training size. Keep instrument/tissue/panel provenance, de-duplicate source samples, and group all related versions within the same evaluation split. Expand each scientific validation category deliberately.
