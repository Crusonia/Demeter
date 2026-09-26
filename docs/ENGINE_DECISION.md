# Engine decision

For the current health slice, use NumPy arrays for age/state stocks, explicit competing-hazard transition equations, and an independent life-table calculator.

BPTK-Py 3.2.0 was installed and its `Model(starttime, stoptime, dt, ...)` API inspected. It supports the project direction, but the present calculation primarily shifts single-year age cells, applies stock-conserving matrices, and integrates a period life table. An additional scheduler or symbolic equation layer would duplicate the annual loop without resolving a current validation failure. BPTK-Py stays in the available stack for later aggregate feedback and delay modules.

SALib 1.6.0's Sobol sample/analyze APIs were inspected and used directly. NumPy handles arrays; Pydantic validates inputs; openpyxl reads official NCHS files; uv.lock pins dependencies. Polars remains available for future larger analytical tables. The small bundled public inputs do not require a database.

This decision implements the current phase and does not narrow the hybrid systems-dynamics/agent-based program in PROJECT_VISION.md. No web or hosting layer has been added.
