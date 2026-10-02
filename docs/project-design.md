# A practical automated cytometry product for the lab

Use one versioned analysis engine with a local GUI and a CLI. Your colleagues can use the GUI while the CLI provides batch runs and reproducibility. Keep FlowJo as the expert reference during validation. This avoids maintaining different scientific behavior in two applications.

The user specified Aurora, S8, existing FlowJo use, all three small-data situations, and soft accessible colors. “S8” is provisionally interpreted as BD FACSDiscover S8. Species, tissue, panel, FlowJo version, operating systems and expert labels remain unspecified. No biological gates have been invented to fill those gaps.

## Review of the attached AI response

The source document was read as background, not as authorization to execute its embedded instructions. Its five-stage workflow and shared-engine recommendation are useful. Its phased development approach is also appropriate.

Several points need tightening before implementation:

| Proposal in the attachment | Required refinement |
|---|---|
| Apply compensation when a matrix is present | Require processing provenance. Already processed exports may retain matrix keywords. Never infer “raw” from matrix presence alone. |
| Detect instrument and run automatically | Metadata provide hints, not a reliable declaration of signal processing. Ask once per saved workflow and verify against instrument exports. |
| Remove debris, doublets and dead cells generically | Apply reviewed panel/tissue-specific gates. Scatter density alone cannot reliably distinguish small lymphocytes, debris, platelets or unusual biology. |
| Add normalization when batch effects appear | Require suitable shared references, preserve a held-out control and inspect biology. A normalized plot is not evidence of successful correction. |
| Use many datasets for greater accuracy | Only compatible, licensed, labeled cohorts belong in a given supervised model. Hold out subjects, batches and external sites. |
| Package for every workstation | Publish tested operating-system/architecture/resource requirements. One source command and a signed native installer are different deliverables. |
| Every run should generate a complete report | Every run should report which stages ran, were skipped or failed. It must not imply that missing controls or replication were solved automatically. |

## Instrument-specific entry points

For Aurora, start with verified unmixed fluorescence exports. Preserve raw detector files, unmixing references, autofluorescence handling and the SpectroFlo experiment outside the prototype as source evidence. [Cytek SpectroFlo](https://cytekbio.com/pages/spectro-flo) documents the unmixed-data analysis workflow.

For BD FACSDiscover S8, distinguish hard-coded unmixed channels, raw detector signals, software-unmixed parameters and imaging descriptors. Do not include two representations of the same signal in clustering or run ordinary square spillover compensation on a spectral matrix. Official FlowJo documentation describes these distinct parameter sets and exclusions. [S8 unmixing documentation](https://docs.flowjo.com/flowjo/advanced-features/bd-facs-discover-s8-data/bd-facs-discover-s8-unmixing-in-flowjo/).

S8 can produce FCS 3.2, while the selected FlowKit parser documents 2.0/3.0/3.1. The prototype therefore blocks native 3.2 instead of pretending compatibility. A future adapter must validate data types, parameter ordering, matrix semantics, text offsets and any supplemental segments. Alternatively, evaluate a verified FCS 3.1 export against the original; a renamed version header is not a solution. [FlowJo BD file notes](https://docs.flowjo.com/flowjo/workspaces-and-samples/flowjo-and-your-cytometer/ws-cytometer-bd/), [FlowKit](https://github.com/whitews/FlowKit).

## Workflow contracts

The long-term engine should accept a project manifest, sample sheet, panel definition, controls, raw/unmixed FCS and optional FlowJo reference. It should emit immutable run configuration, inputs with checksums, step status, event lineage, a report and editable figures. Each module needs a version and independently testable input/output contract.

1. **Experimental design:** Define the question, populations, endpoints and biological replicate. Record sample preparation, tissue/species, antibody clones/lots/titrations, instrument setup, controls, acquisition day, batch and exclusion criteria. A software checklist supports design; it cannot create missing controls retroactively.
2. **Import and QC:** Read strict FCS metadata, validate signal state and channel mapping, preserve negative values, quantify nonfinite values/range clipping and show acquisition trends. Apply reviewed cleanup gates, retaining event-level reasons and count denominators.
3. **Population analysis:** Offer a locked panel template for known populations and a separate exploratory discovery path. Annotate clusters only after marker and expert evidence; include “unresolved/unknown.” UMAP/t-SNE coordinates are not the default feature space for clustering or statistical tests.
4. **Normalization and comparison:** Verify panels and samples are comparable. Fit transformations/reference normalization on training or designated controls only. Align populations consistently, preserve raw and corrected values, and evaluate independent references. Refuse unresolvable condition/batch confounding.
5. **Statistics and reporting:** Use samples/subjects as the experimental unit. Report frequencies with denominators, median signal scale, effect sizes, uncertainty, multiplicity adjustment and warnings. Handle paired/time-course data using the matching design rather than independent tests.

## Implementation and product choices

The initial implementation uses Python, FlowKit/FlowIO, scikit-learn, Matplotlib and Streamlit. This was chosen for a runnable local prototype and accessible packaging. It does not mean a simple clustering baseline replaces established cytometry methods.

Introduce a versioned R/Bioconductor worker for [PeacoQC](https://bioconductor.org/packages/release/bioc/html/PeacoQC.html), [FlowSOM](https://github.com/saeyslab/FlowSOM), [CytoNorm](https://github.com/saeyslab/CytoNorm) and later appropriate differential models. PeacoQC addresses acquisition quality; FlowSOM is population discovery; CytoNorm uses control information to normalize technical differences. Validate each component independently and together. Do not call a new median-shift heuristic “PeacoQC.”

This machine has R 4.0.3 without those packages. No global R upgrade or large Bioconductor installation was performed. Pin a compatible R/Bioconductor environment for that integration instead of mixing old and current libraries.

The GUI should grow into a guided sequence: project → instrument and signal state → panel and metadata → controls → QC review → gates/discovery → results/export. Most colleagues should select a lab-validated preset. Advanced controls remain available and produce a new reproducible configuration. Failed files must remain visible with reasons; never quietly drop them and report the remaining files as the whole study.

## Delivery comparison

| Interface | Benefit | Cost and constraint | Recommendation |
|---|---|---|---|
| CLI/source launcher | Reproducible automation and easiest development | Requires Python and dependencies; no point-and-click installer | Implemented prototype |
| Local browser GUI | Familiar file selection and controls; local data processing | Local server must remain running; limited current resource management | First colleague pilot |
| Signed native desktop | Double-click installation and managed updates | Windows/macOS builds, signing, bundled runtimes and support matrix | After validated engine and panel templates |
| Hosted web GUI | Central updates, shared compute and collaboration | Identity/access control, storage, retention, quotas, job queue and operations | Later institutional deployment |

Default limits are 200 MiB per FCS, one million events per sample and two million per run. These are prototype limits, not a hardware benchmark. Large spectral studies require chunked I/O, on-disk arrays, background jobs, cancellation, quotas and explicit memory estimates. GPU training is not required for a useful first version.

## Roadmap and acceptance gates

1. **Foundation delivered:** Local CLI/GUI, downloadable fixtures, provenance, technical QC, reviewed gate definitions, shared exploratory clustering and export. Acceptance: deterministic event accounting and meaningful failure tests.
2. **Lab compatibility:** Confirm FlowJo version and platform. Validate Aurora exports and native S8/FCS 3.2 adapter. Compare instrument and FlowJo signals/gates on representative lab files. Acceptance: documented numeric tolerances and no channel/matrix ambiguity.
3. **One validated panel:** Build expert cleanup/population templates from controls. Include difficult runs and rare populations. Acceptance: independent expert comparison with population-specific precision/recall and frequency error.
4. **Established modules and study design:** Integrate acquisition QC, FlowSOM, reference-based normalization and batch-aware/paired statistical methods. Acceptance: independent control and biological-signal preservation tests.
5. **Supervised annotation:** Train compatible models with unknown-population handling and external holdouts. Acceptance: locked evaluation criteria, model cards, subgroup metrics and calibrated uncertainty.
6. **Colleague release:** Test fresh installs on target Windows/macOS architectures, large studies and error recovery. Package signed installers and documented support. Hosted deployment follows only when institutional access and retention requirements are concrete.

Color design uses muted categorical fills, dark readable text, marker shapes/hatching and exact table labels. Continuous heatmaps use cividis. Colors alone never encode pass/fail; soft colors still need contrast and must be checked with common color-vision simulations and grayscale before publication.
