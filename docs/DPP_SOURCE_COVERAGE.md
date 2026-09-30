# DPP source coverage before clinical fitting

Assessment: September 30, 2026. This is a review of public documentation for
[#57](https://github.com/Crusonia/Demeter/issues/57) and
[#58](https://github.com/Crusonia/Demeter/issues/58), prepared after the documents
and published results were inspected. It is neither preregistration nor an
independent clinical evaluation. No participant records were acquired or
requested, and no clinical thresholds, transition rates or dietary effects are
introduced.

**Decision:** the inspected public DPP documents describe useful observations,
but do not supply the observations needed to fit Demeter's clinical transitions.
The [repository catalog](https://repository.niddk.nih.gov/study/38) describes
participant data as available for request. Public access to blank forms and
dictionaries does not make those records an unrestricted download. DPP remains
a documentation and source-specific benchmark route under the maintainer's
public-source choice.

The [observation contract](CLINICAL_OBSERVATION_CONTRACT.md) defines the full
requirements; the [preservation adapter](DPP_OBSERVATION_ADAPTER.md) implements
strict normalized objects and synthetic diagnostics. This matrix feeds the health
parts of Q-03/RM-04 → P-02 → I-01/I-05/I-07/I-11/I-12 → F-04/F-08 →
T-01/T-05/T-06/T-08 in the [design registers](design/README.md). It does not
activate the payer, agriculture or business parts of those premises.

## How to read the matrix

Documented presence means a form or dictionary names a field. Documented meaning
means its question or source definition was inspected. **Actual coverage is not
acquired for every row**: a blank form cannot tell us which participants have
complete, comparable measurements. Fit readiness additionally requires compatible
observations, verified timing, an identifiable likelihood and joint uncertainty.
Passing a document checksum establishes none of those scientific conditions.

For example, a participant can report taking medication since the previous visit,
have low glucose at this visit, and still have an earlier diabetes diagnosis.
Those observations do not establish untreated remission or its start date.
Similarly, an appointment missed without a glucose test is not an observation of
healthy glycemia. The model must preserve those distinctions before estimating a
flow between states.

Source labels below refer to the exact snapshots in the
[coverage receipts](validation/dpp-coverage-source-receipts.json). Page numbers
are PDF pages unless a printed/physical distinction is stated.

| Label | Public primary document |
| --- | --- |
| R2008 | [February 2008 release documentation](https://repository.niddk.nih.gov/media/studies/dpp/Documents/Documentation%20for%20full%20scale%20DPP%20data%20release.pdf) |
| DD9 | [V9 data dictionary](https://repository.niddk.nih.gov/public/study_document/DPP_V9/DPP_Data_Dictionary_V9.pdf) |
| RM9 | [V9 archive roadmap](https://repository.niddk.nih.gov/public/study_document/DPP_V9/DPP_Roadmap_V9.pdf) |
| LAB9 | [Laboratory contents](https://repository.niddk.nih.gov/public/study_document/DPP_V9/Data/DPP_Data_2008/Non-Form_Data/Data%20Dictionary/LAB.pdf) |
| S01 / S03 | [Eligibility](https://repository.niddk.nih.gov/public/study_document/DPP_V9/Forms/S01.pdf) / [screening inventory](https://repository.niddk.nih.gov/public/study_document/DPP_V9/Forms/S03.pdf) |
| Q08 | [Interval medical history](https://repository.niddk.nih.gov/public/study_document/DPP_V9/Forms/Q08.pdf) |
| F02 / F03 | [Major follow-up](https://repository.niddk.nih.gov/public/study_document/DPP_V9/Forms/F02.pdf) / [interim inventory](https://repository.niddk.nih.gov/public/study_document/DPP_V9/Forms/F03.pdf) |
| F04 / F05 / F05C | [Missed visit](https://repository.niddk.nih.gov/public/study_document/DPP_V9/Forms/F04.pdf) / [adherence interview](https://repository.niddk.nih.gov/public/study_document/DPP_V9/Forms/F05.pdf) / [adherence codes](https://repository.niddk.nih.gov/public/study_document/DPP_V9/Forms/F05_Med_Adhere_Codes.pdf) |
| P4.5 | [Protocol version 4.5, November 6, 2001](https://dppos.bsc.gwu.edu/documents/1124073/1127212/DPPPROTOCOL.PDF/807eddd1-d9bf-497d-89f0-5de15fc43d79) |

## Observations and their limits

| Required observation | Verified field and primary locator | Supported meaning and remaining gap |
| --- | --- | --- |
| Link observations and visits | `RELEASE_ID`, `VISIT`, `DAYSRAND`; R2008 p11, DD9 form/assay listings | Release identifier, nominal visit and days relative to randomization. Screening days may be negative. These do not establish a unique diagnostic trigger/confirmation pairing. |
| Baseline selection and population | `AGEGROUP`, `SEX`, `RACE_ETH`, `BMICAT`, `BMIGROUP`, `ASSIGN`; R2008 pp5–6,24 | Grouped demographics/body size and assigned arm. Dates and centers are removed; only the final eligible screening sequence is retained. Exact age, geography and original-report selection cannot be reconstructed from these labels. |
| Prior diagnosis and medication | `SCDIAB`, `SCHYMED`; S01 p5 Part III/F.1, DD9 p55 | Eligibility questions about physician diagnosis supported by other clinical data and prior hypoglycemic medication with a gestational-diabetes exception. They do not supply complete lifetime history or a verified diabetes type. |
| New history during follow-up | `IHDIAB`; Q08 p2 Part II/D.5, DD9 p45 | Doctor-told diagnosis in the preceding year. It supplies neither baseline/lifetime history nor an exact date or type, and does not independently document laboratory confirmation. |
| Distinct glycemic assays | `G000`, `G030`, `G120`, `HBA1`; R2008 pp16–17, LAB9 p1, DD9 p23 | Separate fasting/challenge glucose and HbA1c measurements. Some baseline fasting values are recoded. Assays cannot be interchanged, and numerical categories require separately sourced clinical definitions. |
| Screening test conditions/problems | `SOFAST`, `SORESL`, `SOFAIL`, `SODRKT`, `SO30MT`, `SO2HRT`; S03 p6, DD9 pp56–57 | Screening collection, completion/problem reasons and within-visit clocks. They do not certify follow-up refusal, missing-confirmation reasons or every laboratory time encoding. |
| Trigger and diagnostic confirmation | `VISIT=CON/POV`; R2008 pp8,11; P4.5 §5.5.1 printed 5-6 / physical 51; LAB9 p1, DD9 p23 | A confirmation visit may confirm or fail to confirm; POV follows confirmation. No dedicated trigger/confirmation pair identifier or positive-confirmation flag was verified in the inspected laboratory listing. A CON label is not a diagnosis. |
| Diagnosis during the source follow-up | `DIABF`; R2008 p25, DD9 p9 | Source diagnosis indicator computed from glucose results. It is not lifetime history, current glycemia, type classification or a latent state. |
| Event/censoring time | `DIABT`, `DIABV`; R2008 pp8,25, DD9 p9 | Native years to diagnosis visit for cases or final glucose visit for noncases, and a grouped interval. Year denominator, rounding, interval-boundary rules and an unequivocal trigger-versus-confirmation date remain unresolved. |
| Separate later protocol endpoint | `FASTHYPF`, `FASTHYPV`, `FASTHYPT`; R2008 pp4,25–26 | Separate fasting-hyperglycemia endpoint summaries related to protocol medication stopping. They cannot replace DIABF or document every actual treatment change. |
| Missed scheduled visit | `JMCONT`, `JMRSN`, `JMINACT`, `JMEOS`, `JMVSTWK`, `JMVSTTY`; F04 p1/B.2–7, DD9 p15; R2008 p13 | Contact indicator, conditional reason, inactive follow-up status and scheduled occasion. Missed interim visits are excluded. Inactive status does not establish permanent loss or death; the contact indicator has no exact contact date. |
| Excluded calendar dates | Gray `JMVSTDT`, `MAVSTDT`, `IVSTDT`; F04/F05/Q08 p1/B.1; absent from DD9 pp15–16,45–46 | Printed calendar-date questions are excluded from the release. `DAYSRAND` is separate; it must not automatically be interpreted as the last contact or medication cessation day. |
| Adherence interview | `MAVSTTY`, `MAVSTWK`, `MAHOW`, `MAHELD`, `MAPROB`, `MAPLAN`, `MAINTEN`, `MARELI` and supplemental responses; F05 pp1–2, DD9 p16, F05C pp1–2 | Conditional interview about coded medication since the previous visit, strategies and barriers. Codes can indicate stopping/deviation, but do not establish exact cessation or continuous exposure. Absence of the form is not zero medication. |
| Inter-visit coded medication use/dose | `AMTAKM`, `AMDOSE`; F02 p5/H.1; `JITAKMT`, `JIDOSE`; F03 p3/F.1; DD9 pp13–14 | Any use since the last visit and conditional nominal protocol dose. They do not supply daily consumption, cumulative dose or dated dose changes. Coded medication includes masked active/placebo assignment; a medication label does not prove active drug ingestion. |
| Adherence and dispensing observations | `AMCOMPM`, `AMDAYSM`, `AMNOMET`; F02 p5/H.1–2; `JICOMPM`, `JIDAYSM`, `JINOMET`; F03 p3/F.1–2 | Staff exposure categories distinguish pill-container nonreturn; their exact lookback/person-day denominator is not specified by the question. Participant pill-days estimates concern the most recent typical week, not the whole inter-visit interval. A not-dispensed checkbox is not a cessation date; absence or missing coding cannot be inferred from that option alone. |
| Current concomitant prescriptions | `AMRXDQ`, dictionary description columns `AMRXDAM` through `AMRXDJM`; F02 p6/I.1, DD9 p13 | Current prescription snapshot, excluding coded medication. No start/stop dates, adherence or duration; route columns are excluded. Visual annotation prefixes do not by themselves define released column names. |
| Interim visit purpose | `JIMEDMG`, `JISPEC`, `JIOUT`; F03 p1/C, DD9 p14 | Medication management, specimen collection and repeating a deficient outcome are distinct, potentially coexisting reasons. JIOUT supplies neither a diagnostic trigger/confirmation pair nor a positive result or test-specific failure reason. |
| Pregnancy-specific stopping-day candidates | `DAYSMETS_PRIOR`, `DAYSMETS_AFTER`, `DODISB`, `DODISA`; DD9 E04 listing p7 | Dictionary labels describe metformin stopping days relative to randomization before/after pregnancy and discontinuation indicators. This is a special-subgroup exception to a broad claim of absent medication dates. E04's original form, exact/estimated dating and actual coverage were not appraised; it is not a cohort-wide exposure history. |
| Lifestyle participation and activity | Files `L03`–`L05`, `Q03`–`Q05`; R2008 pp14–15, RM9 pp2–5 | Contact, group/activity participation and questionnaire files are documented. Their item-level scoring was not appraised here. Participation is not dietary dose. |
| Dietary observations | NCC `DT_KCAL`, `DT_CARB`, `DT_DFIB`, `DT_FAT`, `DT_PROT`, `DT_SFAT`, `FG1`–`FG27`, `PERCCARB`, `PERCFAT`, `PERCPROT`; R2008 pp17–21 | Coded energy, nutrient and food-group summaries at RUN/Y01. The original questionnaire is not released. These do not define a consumed UPF dose or isolate diet from the lifestyle package. |
| Competing death | `DEATH`, `DEATHDAYS`; R2008 p25, DD9 p9 | Death indicator and randomization-relative death days. Missing death time does not establish alive status. Comparing death days with DIABT years needs a verified conversion/event rule. |
| End of observation | `TOTALTIM`, `RANDPER` in R2008; `RAND_PER` in DD9; R2008 pp5–6,26, DD9 p9 | Native years through the last recorded visit of any type and grouped recruitment period. Neither supplies an independent last contact, loss reason, exact original-report horizon or a certified cross-version alias. |
| Missingness and follow-up selection | R2008 pp5,10–13; source-specific fields above | Incomplete collection, missed visits and historical form changes differ. No universal assay-refusal code or complete ascertainment history was verified. Non-research tracking and detailed adverse/serious-adverse-event records are omitted; F02 `APAEQ` / F03 `JIAEQ` symptom/event indicators remain documented. |

The matrix is a bounded finding about these documents. It does not establish
that original DPP analysis code or other uninspected materials lack additional
information. No importer for these fields is implemented or certified.

## Source versions must remain distinct

The original three-arm report ends March 31, 2001; R2008 describes a later
four-arm release through July 31, 2001. Catalog, publication and release
denominators are not interchangeable. P4.5 postdates the original report window;
later bridge/washout provisions cannot be appended as ordinary same-condition
observations. A roadmap file listing does not certify coverage at any version.

R2008 p26 names `RANDPER`, whereas DD9 p9 names `RAND_PER`. F05 p2 annotations
name `MAREL1` and `MAPRJBB`, whereas DD9 p16 lists `MARELI` and `MAPROBB`.
Preserve these verified discrepancies. A future authorized schema needs an
explicit reviewed mapping; correcting spelling silently would manufacture an
alias. R2008 p10 distinguishes released blue annotations from excluded gray
annotations; the relevant forms were checked visually as well as against DD9.

F02/F03 are final November 1999 forms. Their calendar visit and pregnancy dates
are gray/excluded (`AVSTDT`, `APDOLM`, `APDOPT`, `JIVSTDT`, `JIDOLM`, `JIDOPT`),
while DD9 separately lists `DAYSRAND`. F02's medication section is conditional
on pharmacological assignment; F03's final medication section excludes lifestyle
and troglitazone participants. DD9 retains historical troglitazone columns absent
from these final pages. Skipped sections cannot become zero use, and final forms
cannot establish every historical question or recall window (R2008 p10;
F02 pp1,4–5; F03 pp1–3; DD9 pp12–14).

Further literal discrepancies include F02 p4 `APQ08` versus DD9 p13 `APQOB`,
F03 p1 `JVSTTYPE` versus DD9 p14 `JVSTTYP`, and the repeated F03 p3 `JISBP1`
annotation over systolic/diastolic fields versus distinct `JISBP1`/`JIDBP1` in
DD9 p14. These are source discrepancies, not certified aliases or parser fixes.

## What this resolves, and what the next analysis needs

This review resolves documented meanings and field locators for several history,
missing-visit and medication observations. It rejects specific shortcuts:
annual history is not lifetime history; recent-week adherence is not an exact
treatment interval; confirmation-visit presence is not a positive diagnosis;
native-year and relative-day summaries are not already aligned.

| Proposed analysis | Disposition under the public-source route |
| --- | --- |
| Reproduce documented field meanings or compare published first-diabetes results | Public documents can support a version-specific factual appraisal or a separately registered published benchmark. Neither is a clinical fit. |
| Fit repeated-state progression/recovery | No participant observations or sufficient public state-history statistics were acquired. Require compatible repeated states, diagnosis/treatment history, ascertainment and censoring, then test identification and alternatives before fitting. |
| Fit remission | A later low assay does not establish treatment-free sustained remission or diagnosis history. The current engine also has no diabetes-remission flow. Do not rename glycemic reversion as remission. |
| Fit competing mortality | Death days are documented, but actual records, compatible event times and censoring/selection assumptions remain unresolved. No source-year conversion or competing hazards are activated. |
| Estimate an isolated dietary pathway | DPP assignment combines diet, activity, weight-loss goals and behavioral support. The inspected summaries do not identify an isolated consumed UPF dose, lag or dietary transition effect. |
| Initialize U.S. or PreChronic states | Selected impaired-glucose-tolerance trial participants are not a national observation sample or a validated PreChronic definition. This matrix does not resolve transport or point allocation. |

Further blank-form inspection cannot supply absent participant histories. The
next scientific priority is another compatible unrestricted longitudinal package,
or genuinely sufficient published aggregate observations with a precisely
supported estimand. Preserve unsuccessful candidates and restrict any analysis
to what its source identifies. An institutional DPP request remains optional
and would require a separate access decision; none was made here.

If compatible observations become available, resolve native-year conversion,
diagnostic event dating, source window, selection and informative observation
timing. Specify and freeze the likelihood, structural alternatives, joint
uncertainty and evaluation partition before fitting/reserved-record inspection.
Report failed checks and supported populations. Until then #57, #58, #1 and
milestone #27 remain open; additional software or documentation does not close
their scientific requirements.

## Provenance and redistribution

The coverage receipts record original/final URLs, retrieval times, byte sizes
and SHA-256 values, without machine-local paths. They are appraisal provenance,
separate from the four-source frozen
[observation contract](validation/dpp-observation-contract-v1.json). The adapter's
`evidence dpp-observations --raw` command still checks only its original four
documents; it does not validate the additional coverage documents or their
field interpretations.

`uv run demeter data verify-packages --check-tracked` now validates the typed
coverage receipts against all 15 independent documentation-rights entries and
links the original four sources back to the unchanged evidence registry. URL,
final URL, timestamp, size, hash, media type, status, filename and registry-link
disagreements fail the audit, even if the outer artifact checksum is refreshed.
The tracked-file guard also rejects these fetch-only document bytes under any
filename. This is recorded-provenance validation, not proof of field meaning or
permission to use participant data.

Offline, document-byte checks are explicitly `not_requested`, with no byte-pass
claim. If matching files are already cached, check all 15 documents without
fetching or interpreting them:

```bash
uv run demeter data verify-packages --check-tracked --documentation-raw outputs/dpp-appraisal --output outputs/dpp-coverage-audit.json
```

Missing or changed documents produce failed rows in the saved report and exit
status 1. Preserve existing snapshots; do not replace pins to make a new download
pass. Malformed receipt schemas are rejected before the document audit.

Full articles, forms, dictionaries and catalogs remain fetch-only local caches.
Only factual locators, paraphrased findings and receipts are redistributed, under
the conservative `dpp_documentation_fetch_only` approach in
[the rights inventory](../data/rights.json). R2008 p10 also limits use of its forms
for approved release analyses and distinguishes primary collection permission.
No participant records, source forms or new empirical parameters enter the
repository. Existing registry definitions, frozen protocols, health equations and
scenario files remain unchanged; scientific-release blockers stay open.
