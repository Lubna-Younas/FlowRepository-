# Data quality and small-data behavior

“Good” and “bad” are assay-dependent. A file can be technically readable but unsuitable for a particular biological comparison. A rare population, negative signal after unmixing, or unusual disease phenotype is not automatically poor quality. Keep three separate decisions: file validity, technical quality, and fitness for the biological question.

## Experimental and acquisition record

Define biological units, inclusion criteria, expected effect and population endpoints before analysis. Balance/randomize acquisition across conditions where possible. Track technical versus biological replicates, operator, run order, instrument settings/QC, sample transport/storage, processing delay, viability, tissue digestion, staining protocol, fixation/permeabilization, reagent lots and panel version. Record counts, volume or counting-bead information if absolute counts are an endpoint.

Include unstained controls, appropriate single-stain references, compensation/unmixing controls matched to the workflow, and relevant FMO/positive/negative biological controls. FMO controls help with boundary placement; they do not replace spectral single-stain references or quantify all nonspecific binding. Spectral references must be appropriate for the fluorochrome, sample preparation and autofluorescence strategy. For between-run normalization, acquire matched reference material and keep independent controls for evaluation. See the [flow cytometry guidelines](https://eprints.whiterose.ac.uk/id/eprint/184275/).

## Failure matrix

| Situation | Correct response | Prototype status |
|---|---|---|
| Truncated/corrupt FCS, offset disagreement | Fail with a diagnostic; never silently repair the source | Strict parser rejects tested offset fixtures |
| FCS 3.2 / multiple datasets per file | Validate an adapter or export each dataset using a supported verified workflow | Explicitly blocked |
| Different integer/float widths or byte order | Use an established parser; test edge cases separately | FlowIO used; current fixture set does not cover every encoding |
| Duplicate/missing detector names | Request an explicit mapping; do not collapse columns | Blocked |
| Missing marker labels | Show channels and require panel review | Warning; no biological annotation |
| Inconsistent panel/marker mapping | Separate runs or use validated mapping rules | Selected missing channels or inconsistent marker labels block pooling |
| Raw spectral detectors | Unmix with validated matched references/instrument workflow | Not implemented |
| Matrix retained in already processed FCS | Record processing state; avoid double compensation | Explicit signal-state control |
| Unmixed/compensated negative signals | Retain and use appropriate transformations | Retained; tested |
| Already transformed export | Avoid a second transformation and wrong gate scale | Requires transform none |
| NaN or infinity | Quantify and preserve affected event IDs; stop if unusable | Excluded from eligibility across recorded parameters, with exported flags |
| Upper-range pileup / clipping | Flag; review detector range, gain and event acquisition | Simple declared-range warning; not a full detector saturation model |
| Drift, clogs, bubbles, time reversal/gaps | Show trends and event accounting; review affected intervals | Median/rate heuristic flags retained; not validated artifact detection |
| No time channel | Report which acquisition checks cannot run | Acquisition-order trend only |
| Too few events for bin QC | Avoid a false PASS | Explicit warning; drift check requires five bins |
| Doublets/debris/dead cells | Use tissue and panel-specific reviewed gates; inspect plots | Configured gates only; no generic classifier |
| No viability dye or singlet dimensions | Mark cleanup unavailable; do not infer live/singlet identity confidently | No automatic substitution |
| High autofluorescence / tandem degradation / spreading | Review references and controls; do not erase tails automatically | Requires expert/instrument review |
| Incompatible batch or sample preparation | Separate analysis or fit a justified design | No automatic normalization; multi-batch hypothesis tests withheld |
| Zero-event file | Reject analysis; keep source for parser tests | Blocked |
| Zero-event gated population | Export zero with a defined parent and uncertainty; do not label absent | Supported; no denominator gives undefined frequency |
| Very large/high-dimensional file | Bound resources and use chunked processing | Explicit event/file limits; chunked ingestion not yet implemented |
| Failed step | Preserve diagnostics and partial output; never show a completed result | CLI/GUI stop; see run status metadata |

Filenames are not reliable evidence of “raw,” “clean,” “unmixed,” or cell type. Store declared state and source processing history. Raw files are immutable; event indices are zero based and trace back to original order. Gate rules apply to the declared signal scale before the selected display transformation. Independent transforms may make identical-looking gate coordinates mean different biological thresholds.

## Few populations

Start with marker distributions and validated gates. For one or two populations, a fixed high k will split them into artificial subclusters. Leave clustering off by default and consider whether discovery adds value. Do not force UMAP/t-SNE on very small datasets or treat separated islands as ground truth. Evaluate selected k, seeds, marker choices and sample contributions. The present KMeans baseline accepts k=0 and never names clusters biologically.

## Rare populations

Rare cells need enough acquired parent events, specific markers, appropriate negative controls and explicit limits of blank/detection/quantification. A universal “100 events” threshold is not an assay validation. The prototype uses it only as a review flag.

For an idealized population fraction p and N independent sampled events, the expected count is Np and the probability of seeing at least one is 1−(1−p)^N. At p=0.01% and N=10,000, the expected count is 1 and the chance of observing any is about 63.2%; a subsample can easily miss the population. Rough Poisson counting variation is 1/√k: 25 events imply about 20% relative counting uncertainty, 100 about 10%, before gating and preparation uncertainty. These are counting arguments, not guaranteed assay sensitivity. See [rare-event validation considerations](https://pubmed.ncbi.nlm.nih.gov/32940947/).

Fit models on a bounded training subset if necessary, but apply gates/models and count on the full eligible dataset. Preserve rare training labels; never remove low-density tails solely for being unusual. Low event rates, contamination and spillover artifacts can mimic rare cells, so full-file retention alone does not establish specificity. Report counts and parent denominators together, use per-class precision/recall and absolute false-positive counts, and inspect events near gate boundaries. Zero observed events should receive an interval/upper bound rather than an “absent” label.

The synthetic rare fixture contains 100 known proxy events in 100,000 events. It checks count retention only; it does not mimic all spectral artifacts, real rare-cell biology or a validated detection limit.

## Few biological samples

A million cells from one donor is still one biological replicate. Do not use cell-level tests to manufacture sample size. With n=1 or n=2 per group, prioritize descriptive summaries, QC and experimental planning. With small n, display all donor values and effect sizes and avoid strong conclusions from unstable p-values.

The prototype pools technical-replicate counts within subject and uses subject frequencies for its limited unpaired tests. It requires at least three independent subjects per group, exactly two conditions and one batch. This is an operational guard, not a claim that n=3 provides adequate power. Paired/repeated subjects, multi-batch studies and more complex designs are currently descriptive only. Extend using pre-specified paired tests, mixed models or suitable abundance models with multiplicity control and power planning.

Absolute cell counts require a validated counting-bead/volume workflow. Frequencies are compositional: one population changing alters others’ fractions. Marker medians must include the scale and background/transform context; transformed medians should not be mislabeled raw MFI.

## Accessibility and review

Use pale backgrounds, dark text, muted blues/ochres/purples and redundant shapes/hatching. Use sequential perceptually ordered maps for intensities, neutral centered diverging maps only where a meaningful zero exists, and direct labels. Never rely on red versus green. Large cluster counts require small multiples or labeled tables; the prototype repeats colors above eight clusters and calls that out. Export SVG text and PDF fonts as editable vectors, and inspect labels in grayscale and common color-vision deficiency simulations before publication.
