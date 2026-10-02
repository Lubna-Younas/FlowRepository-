# Validation and responsible model training

The aim is reliable analysis on the lab's panels, instruments and sample types. Training on every downloadable cytometry file would mix different tasks, markers, tissues, preprocessing and label definitions and can reduce reliability. Public data broaden testing; they do not establish accuracy on Aurora/S8 data without independent lab validation.

## Build a reference corpus

Maintain separate collections for parser conformance, acquisition artifacts, biological gating, batch normalization, annotation/classification and external validation. Identify each study, donor, sample, instrument, panel version, tissue/species, processing state, source license/terms, source checksum, labels and expert confidence. Deduplicate files by checksum and study/sample identity. Processed copies of the same sample are not independent samples; they must stay in the same split.

For your first panel, include representative clean acquisitions, poor acquisitions, negative controls, rare/dim populations, different acquisition days, high and low viability, atypical biology and small sample sizes. Two cytometrists should annotate independently and adjudicate disagreements. Keep ambiguous/unknown labels and quantify agreement rather than pretending one gate is infallible.

FlowJo reference packages should include the version, original FCS, workspace, compensation/unmixing state, transform settings, gate hierarchy, gate coordinates, per-gate counts/frequencies and event-level membership if exportable. Save the exact parent denominator. Validate boundary events and unsupported plugins/derived parameters explicitly. A `.wsp` reconstruction is not independent ground truth until compared to the native output.

## Evaluation partitions

Split whole subjects first, with all time points, technical replicates, gated subsets and processed copies grouped together. Then define training and validation subsets and lock an untouched test set. Include a later acquisition batch and, when available, an external site/instrument test. If there are too few independent subjects, use grouped cross-validation for development and report the uncertainty; do not advertise a random cell split as generalization.

Fit learned transforms, normalizers, feature selection, reference maps and hyperparameters using training/authorized reference material only. No test labels or test-specific model tuning. For batch normalization, an explicitly defined shared-control protocol may use designated technical controls; distinguish that from using test subjects to learn correction. Report performance per donor rather than only a pooled cell-level number dominated by a large sample.

## Baselines before complex models

1. Expert/locked template gating for the supported panel.
2. Established acquisition QC and FlowSOM discovery with expert cluster annotation.
3. A simple supervised baseline such as a class-weighted Random Forest on the compatible panel.
4. More complex models only if independent validation shows an improvement at acceptable cost.

The included training script validates one panel, requires a single explicit split per subject, rejects identifier/label feature leakage, caps training contributions by subject/class, uses a fixed Random Forest configuration, and evaluates untouched validation/test subjects. It saves a model card, source/split/model hashes, per-subject metrics, class reports and predictions. It does not validate control quality, assay compatibility, label correctness or subject identity automatically. The confidence values are uncalibrated vote fractions and must not be presented as diagnostic probabilities.

The harness has been executed on 12 simulated subjects (6 train, 3 validation, 3 test). This establishes that the training and reporting code runs. It provides **no evidence of biological cell-type accuracy** and its model is not used by the analysis app. The real public example fits only an exploratory shared clustering model; it does not train a transferable cell-type classifier.

## Measurements and acceptance

| Layer | Measurements | Required interpretation |
|---|---|---|
| File handling | Parse/reject rate by FCS version/type/instrument; numeric equality; channel ordering | Separate expected rejection fixtures from real corrupt files |
| Compensation/unmixing | Matrix/channel agreement, known-control residuals, equivalence with source software | No double application; no inference from filename alone |
| QC | Expert-annotated artifact sensitivity/specificity, fraction removed, rare-event survival | A cleaner plot alone is not success |
| Gating | Per-population precision/recall/F1, overlap, count/frequency bias, denominator agreement | Rare and dim populations need separate evaluation |
| Annotation | Macro F1, balanced accuracy, per-class PR curves, rare precision/recall, confusion matrix | Overall accuracy can hide failure of rare cells |
| Uncertainty | Calibration, abstention coverage/error, unseen-label detection | “Unknown” is preferable to a confident wrong label |
| Normalization | Independent reference alignment plus preservation of known biological differences | Avoid erasing true condition shifts or creating separation |
| Reproducibility | Seeds, source/software hashes, rerun equality and cross-platform tolerance | Version every behavior-changing component |
| Usability | Fresh install, recoverable failure, report comprehension, parameter errors | Pilot with non-bioinformatician colleagues |
| Performance | Peak RAM, disk, runtime by events × channels, cancellation/restart | State a tested workstation support envelope |

Set numerical acceptance criteria with cytometrists for each endpoint before evaluating the held-out cohort. Thresholds appropriate for common lymphocytes may be unacceptable for a 0.01% population. Include confidence intervals over subjects, subgroup/batch results and all exclusions. Never use a high synthetic score, a successful parser run, or a nice UMAP as a release criterion for biological accuracy.

## Release readiness

Before a lab pilot, establish Aurora/S8 signal and file-format compatibility, one reviewed panel template, a FlowJo parity report, and a target Windows/macOS installation test. Before broad distribution, add larger-file streaming, job persistence/cancellation, error logs, cross-platform CI, signed builds and tested upgrades. Before a hosted service, add institutional authentication, project isolation, storage/retention controls, job quotas and operations. Before any clinical claims, define and perform the relevant assay and software validation; this repository makes none.
