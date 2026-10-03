# Older NHIS reported diabetes type and public mortality: source checkpoint

Before treating a reported diagnosis as a lasting model state, Demeter needs to check how that answer relates to later recorded outcomes. This checkpoint identifies a possible mortality check and the source definitions needed to make it reproducible. It does not establish that a diagnosis label is a biological state.

This is a used-source documentary appraisal. No participant files were requested, no records were projected, and no mortality or prevalence estimates were calculated. Raw producer documents and original acquisition receipts remain fetch-only in ignored research outputs; only this authored account and its [sanitized metadata receipt](validation/nhis-older-reported-type-mortality-source-checkpoint-v1.json) are archived in the repository. This does not admit a clinical model input. All five scientific gates remain false.

## Why this is a useful next step

A future source-specific check could ask whether a model reproduces assumed all-cause mortality through **December 31, 2019** across adults' literal baseline reported diabetes-type groups in the **2016 survey**. This is a fixed calendar endpoint with unequal elapsed follow-up, not a common elapsed horizon or an annual clinical hazard. Keeping 2017 separate is initially clearer; 2018 cannot supply the explicit type question. This could advance predictive validation of a mortality observation mechanism, while leaving causal state mortality, biological type truth, undiagnosed T2D and dietary effects unresolved.

## Survey definitions that change the design

The [official CDC Diabetes Atlas methods](https://usdss.cdc.gov/diabetes/data/socrata/National_Burden_Magnitude_methods.html), Definitions and Limitations under diagnosed type, explicitly state that the type question was omitted in 2018. The exact source sentence is: “This question was included in NHIS beginning in 2016 for all years except 2018.” The successfully acquired original HTML and its receipt are pinned in the companion JSON.

Primary search-rendered [2016 Sample Adult layout](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2016/samadult_layout.pdf), pages 75 and 77, and [2017 layout](https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Dataset_Documentation/NHIS/2017/samadult_layout.pdf), pages 84 and 86, document older fields. DIBEV1 codes 1/2/3/7/8/9 distinguish yes, no, borderline or prediabetes, refusal, not ascertained and don't know. DIBTYPE is asked after DIBEV1=1 and distinguishes reported type 1, type 2, other and unknown answers. DIBPRE2 asks about prior professional information about prediabetes, IFG, IGT, borderline or high blood sugar; its conditional universe must remain distinct from laboratory bands. A future intake must bind the complete literal dictionaries and source blanks. The unchanged 2025 seven-category classifier is not an appropriate older-source decoder.

These older layouts/SAS originals failed ordinary GET with URLError and no HTTP status recorded. Search-rendered documentary text is useful evidence but is **not a reproducible raw byte admission**. Full age, sex, proxy, unknown coding and source syntax remain unresolved here. The [2017 summary](https://ftp.cdc.gov/pub/health_statistics/nchs/dataset_documentation/NHIS/2017/samadult_summary.pdf), page 1, names WTFA_SA, PSTRAT and PPSU; it does not justify importing 2025 fields or older STRAT_P/PSU_P aliases. The 2016 catalog identifies revised weights, so the future source vintage must be explicit.

The [2016 MMWR analysis](https://www.cdc.gov/mmwr/volumes/67/wr/mm6712a2.htm), DOI 10.15585/mmwr.mm6712a2, combines reported type with insulin use and recodes some answers. Its published type estimates are therefore not a literal reported-type benchmark for this proposed check. No type should be inferred from insulin or age, and unknown type must not silently become type 2.

## Mortality, selection, clocks and join

The [current NCHS mortality catalog](https://www.cdc.gov/nchs/linked-data/mortality-files/) publicly covers NHIS 1986–2018 with follow-up through 2019. The later 2022 linkage is restricted; it cannot extend the public older source to the current 2025 sample.

The [May 2022 public-file description](https://www.cdc.gov/nchs/data/datalinkage/public-use-linked-mortality-file-description.pdf), pages 1–2, documents probabilistic linkage: MORTSTAT means assumed alive or assumed deceased. Ineligible missing status does not mean survival. ELIGSTAT distinguishes eligible adults, under-18 records unavailable publicly, and insufficient identifying data. For 2015–2018, only sample adults and children appear in the linkage; other Person-file respondents do not silently become complete follow-up.

Some public follow-up times and causes were substituted for disclosure protection; vital status was not perturbed. NHIS uses DODQTR and DODYEAR with interview-quarter anchoring; NHANES PERMTH_INT/PERMTH_EXM must not be transplanted. The smallest initial endpoint uses final status by calendar end and retains unknown/ineligible/unmatched outcomes explicitly. It does not reconstruct exact death dates, assume complete ascertainment abroad, or turn quarter intervals into annual hazards.

The [public dictionary](https://www.cdc.gov/nchs/data/datalinkage/public-use-linked-mortality-files-data-dictionary.pdf), pages 1, 3 and 4, identifies PUBLICID, the status/clock fields and SA_WGT_NEW. SA_WGT_NEW is the linkage-eligibility-adjusted Sample Adult weight, distinct from annual WTFA_SA and the person-level WGT_NEW unavailable for these years. The DIABETES mortality flag is a death-certificate contributing cause, not baseline diagnosis or type.

The [2019 linkage methods](https://www.cdc.gov/nchs/data/datalinkage/2019ndi-linkage-methods-and-analytic-considerations-508.pdf), page 30, explicitly constructs the 2005–2018 NHIS PUBLICID from SRVY_YR columns 3–6, HHX 7–12, FMX 16–17 and FPX 18–19. A future parser must preserve source key components, leading zeros, missingness, duplicate/alias contradictions and unmatched records privately; no guessed numeric coercion or record collapse. Page 12 recommends eligibility-adjusted weights and explains selection and out-of-country death limitations. Page 15 documents the public May 2022 release; an older restricted-only passage elsewhere does not override this updated section or current catalog.

## Smallest reviewable implementation contract

1. Commit a documentary field crosswalk and source-specific used-source protocol before requesting participant bytes. Resolve original native dictionaries, revised 2016 vintage, file layouts and key grammar; preserve blocked requests honestly.
2. Admit immutable native sources and exact loaded transformation code before record projection. Preserve every source record and distinct linkage/answer/universe dispositions; unknown mortality is never zero.
3. First implement synthetic join/conservation and calendar-end status tests. Reject 2018 typed pooling, 2025 code transplantation, NHANES month fields, unknown-to-type2 recoding and annualization. Preserve full survey design rows with zero domain contributions. Covariance, weight eligibility, singleton treatment, df, intervals and public disclosure require a separate explicit contract, not inherited NHANES defaults.
4. Only a later admitted source diagnostic may compare literal reported types and assumed calendar-end mortality. This is predictive validation, not a causal effect or clinical T2D initializer. No numeric comparator, tolerance or risk ratio is proposed here.

Source use is limited to statistical reporting/analysis; the description page 6 prohibits identity determination and linkage with individually identifiable records. This is not a blanket redistribution permission. A tracked checkpoint should contain only Demeter-authored Markdown plus a sanitized receipt JSON, pin both as supporting artifacts, retain all five false gates and disclose original-byte versus browser-rendered provenance. No producer full text, publication counts, health parameters or participant records belong in that documentation increment.

## Program trace and status

This is an input to [I-01/I-07/I-11/I-12](design/04_MODEL_INPUTS.md) and [F-08/T-05/T-08](design/05_FORMULATION_AND_TESTS.md): source definitions, selection, measurement mapping and uncertainty come before a clinical comparison. The [current phase objective](CODEX_V0_1_OBJECTIVE.md) and [scientific review policy](SCIENTIFIC_REVIEW.md) remain authoritative. It does not close a feedback loop, initialize T2D or authorize an agricultural, economic or dietary effect.

`direct_initialization_allowed`, `clinical_fit_allowed`, `engine_activation_allowed`, `sampling_distribution_assumed` and `scientific_release_ready` are all false. Source admission is separately false. Documentary field codes and dates here describe producer metadata; they are not engine cutoffs or clinical parameters.

The publications and producer documentary content were inspected before this checkpoint was authored. This is used-source design work, not preregistration or independent validation. Original successful bytes and failed-request receipts were preserved; byte-verified mortality documents and browser/search-rendered older survey layouts are explicitly distinct. No scientific result is reported.
