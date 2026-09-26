# Model specification (validation scaffold)

The current cohort simulator uses three metabolic stocks: healthy, insulin resistant, and type 2 diabetes. At each one-year step, state-specific deaths are removed first. Survivors then move among states. The insulin-resistant state's two exits are scaled proportionally if their combined annual probability exceeds one, preventing negative stocks. Dietary exposure multipliers change progression probabilities using synthetic log coefficients in `evidence/parameters.yaml`. These are software fixtures, not estimated causal effects.

A separate period life-table calculator in `src/demeter/life_table.py` computes survivorship `l_x`, deaths `d_x = l_x q_x`, person-years in a closed interval `L_x = n l_x − (n − a_x) d_x`, remaining person-years `T_x`, and life expectancy `e_x = T_x / l_x`. The final open interval requires a source-supplied mean remaining years. Its unit tests use synthetic fixtures.

The cohort simulation is not yet age-stratified and its fixed mortality rates cannot produce a U.S. period life expectancy. The life-table module has not yet been fed an authoritative mortality schedule or calibrated. No numeric output from this version is a scientific finding.
