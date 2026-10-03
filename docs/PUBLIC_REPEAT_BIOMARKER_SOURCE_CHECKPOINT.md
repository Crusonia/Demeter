# Public repeated-biomarker source checkpoint

Demeter needs to distinguish a recorded glucose label from a lasting metabolic
state. Repeated measurements can help, but clinical transition estimates also
need visit timing, diagnosis history, deaths and missed visits. This checkpoint
records what a bounded metadata check found for MIDUS and the Mexican Health and
Aging Study (MHAS). It admits no participant data, clinical parameters or fitted
effects.

The project continues to prefer the best public sources. This particular check
used anonymous documentation access: no account was created, agreement accepted
or participant file requested. Registration-required public-use data are not
permanently excluded. Access availability and clinical suitability are separate
questions; neither changes a scientific gate.

The [authored metadata receipts](validation/public-repeat-biomarker-source-checkpoint-v1.json)
distinguish browser-readable descriptions, original metadata-byte acquisitions
and failed requests. Publisher HTML and PDF originals remain in ignored storage,
fetch-only and unredistributed. Their hashes identify inspected documents, not
admitted model inputs. This is used-source discovery: descriptions and search
snippets were examined before the receipts and checkpoint were written. It is
not preregistration, an independent holdout or expert scientific approval.

## MIDUS: repeated measurements with important selection

The official [MIDUS 2 biomarker release](https://www.icpsr.umich.edu/web/ICPSR/studies/29282)
is ICPSR29282.v11, updated June 18, 2025; collection ran from July 2004 to May
2009. Its version history identifies glucose, insulin and HOMA-IR additions.
The [MIDUS 3 release](https://www.icpsr.umich.edu/web/NACDA/studies/38837/staff),
ICPSR38837.v1, describes an unweighted clinical panel collected April 2017 to May
2022, with fasting specimens, medical history and medication measures. Both
identify `M2ID` linkage. Exact current glucose/HbA1c, fasting, diagnosis,
medication and visit-date fields and cross-wave assay comparability remain
unverified.

Later biomarker participation requires being alive and healthy enough to travel.
An adjusted response denominator excludes noncontact. Broad collection periods
are not individual visit intervals. A selected-return panel cannot silently
stand for the original baseline cohort or imply independent censoring.

The separate [core mortality release](https://www.icpsr.umich.edu/web/NACDA/studies/37237),
DOI 10.3886/ICPSR37237.v7, was updated August 13, 2026 and covers confirmed
decedents through 2025. [Public variable metadata](https://www.icpsr.umich.edu/web/NACDA/studies/37237/variables)
identifies `DECEASED`, `M2ID` and `DOD_M`; the catalog describes death month and
year. It is a decedent-only file. Absence does not establish confirmed survival,
last contact or complete death ascertainment. Death-year coding, observation
closeout and a complete biomarker attendance/disposition crosswalk remain
unresolved.

The advertised [MIDUS portal](https://midus.colectica.org/) redirected to login
in this check. Ordinary requests for both ICPSR biomarker catalog pages returned
HTTP 403, although descriptions were readable through the browsing tool. No raw
hash is claimed for a refused page, and no anonymous participant acquisition
route was verified. The [producer access policy](https://midus.wisc.edu/data/index.php)
prohibits redistribution of data obtained through ICPSR or the portal. Its
public-use wording does not itself establish anonymous download access.

## MHAS: useful coverage fields are not assay outcomes

The [master-follow-up documentation](https://www.mhasweb.org/resources/DOCUMENTS/2018/MHAS_Master_Follow_up_File_2001_2003_2012_2015_2018.pdf),
Version 1, July 2020, includes the selected cohort, including never-interviewed
participants. The following are documentary roles; no participant linkage or
joint coverage was inspected. Page numbers refer to PDF pages, starting at one.

| Documented fields | Meaning | Interpretation that remains unsupported |
| --- | --- | --- |
| `UNHHIDNP` | Person linkage | A verified repeated-assay intersection |
| `TIPNE_XX`, `TIPENT_XX` | Noninterview/interview type | Collapsing proxy, nonresponse and unknown (PDF 11–15) |
| `INT_DATE_XX` | Interview date | Blood-draw time (PDF 15) |
| `FALLECIDO_XX` | Completed deceased-subject next-of-kin interview | Treating zero as confirmed survival (PDF 15) |
| `SUBSAMPLE_12`, `RES_BIOMARKERS_12` | Biomarker selection and participation | Ignoring refusal, absence or death (PDF 17, 42) |
| `SUBSAMPLE_16`, `PHASE_MXCOG_16`, `RES_BIOMARKERS_16` | Mex-Cog selection, phase and participation | An exact individual assay interval (PDF 18–19) |
| `HBA1C_12`, `HBA1C_16` | Whether HbA1c was measured | An HbA1c concentration (PDF 19, 22–23) |

Exact assay-value, fasting-glucose, diagnosis/treatment, specimen-date and
death-date fields, missing codes and assay comparability remain unverified.
The [ancillary overview](https://www.mhasweb.org/DataProducts/AncillaryStudies.aspx)
describes different biomarker and Mex-Cog selection frames; it does not establish
an identical repeated-biomarker cohort. The main interview-to-health-visit
schedule is not an individual blood-draw timestamp.

[MHAS access](https://www.mhasweb.org/DataProducts/Home.aspx) requires registration,
limits third-party transfer and requests research-product notification. No
account or participant data were obtained. No anonymous acquisition route was
verified in this metadata-only check.

## Smallest useful next step

Our inference from these descriptions is that MIDUS is the stronger conditional
candidate: it explicitly offers panel linkage and a mortality release. This is
not a finding about its data quality or clinical identification. The next useful
step is a current producer-documentary **per-field crosswalk**, rather than
another publication-count benchmark:

1. Verify assay names, native units, fasting requirements, methods, missing codes
   and diagnosis/medication roles separately for each biomarker wave.
2. Distinguish survey dates, clinical visit dates, death dates and contact
   closeout. Leave unsupported clocks unknown instead of assigning a common lag.
3. Identify a complete baseline frame and disposition linkage, keeping deaths,
   noncontact, clinical nonparticipation and unobserved assays distinct.
4. Record actual public access and reuse conditions without inferring rights
   from a public-use label. Preserve ordinary access failures.

For MHAS, first verify that proposed outcome fields hold assay concentrations,
not completion indicators, and establish the repeat-subset intersection and
clock roles. Source-native labels, diagnosis history and treatment need separate
observation mappings; none identifies latent T2D by itself.

If a later reviewed intake becomes feasible, preserve all baseline outcomes and
unknowns. A falsifiable software comparison should test whether conditioning on
return attendance changes the observation likelihood; selected-return and
all-baseline likelihoods must not be presumed equivalent. Empirical estimation
would additionally need a frozen observation/selection contract, original raw
receipts and admitted calculation code before new diagnostics.

This feeds the existing [clinical observation contract](CLINICAL_OBSERVATION_CONTRACT.md)
and design inputs I-01, I-05, I-07, I-11, I-12, F-04/F-08 and T-05/T-08. It
changes no model semantics. Direct initialization, clinical fitting, engine
activation, an assumed sampling distribution and scientific release remain
inactive. [Scientific review](SCIENTIFIC_REVIEW.md) distinguishes documentation,
software verification, scientific acceptance and permission to merge.
