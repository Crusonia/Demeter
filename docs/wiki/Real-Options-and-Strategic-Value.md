# Real options and strategic value

**A strategic option is a feasible ability to make a later choice as information and conditions change.** In Demeter, the intended question is: what is gained or lost by preserving the ability to learn, wait, expand, switch, or exit within a changing Food is Health market?

This is a proposed decision-analysis layer. The current prerelease has no real-option valuation engine and cannot support investment conclusions. The framework below describes the inputs and comparisons that would be needed.

## Why a trend can change the value of an option

Consider a producer evaluating capacity for a different food format. Demand may depend on treatment access, consumer preferences, affordability, distribution, and reimbursement. A dedicated plant, a smaller pilot, and a flexible production agreement expose the producer to different costs and future choices.

A change in one trend can alter both expected demand and the usefulness of waiting for information. A second change may remove a bottleneck or make another constraint binding. For example, broader access could increase potential demand while scarce ingredients or distribution limit reachable sales. The opportunity's value depends on that whole path.

Keeping an option open has a cost. A pilot consumes resources. Flexible equipment may be more expensive. Waiting can forfeit revenue, contracts, learning, or a market position. Competitors may enter, capacity may become unavailable, and the opportunity may expire before uncertainty resolves.

## Decisions to represent

| Option | What must exist to make it real? | What can consume its value? |
| --- | --- | --- |
| **Learn through a pilot** | A feasible experiment, measurable outcomes, and the ability to act on the result. | Noisy or unrepresentative evidence, long follow-up, or learning that arrives too late. |
| **Wait before committing** | An opportunity likely to remain available and signals expected to improve the decision. | Foregone cash flow, rising entry cost, preemption, lost relationships, or expiring rights. |
| **Expand after a trigger** | Capacity access, financing, people, inputs, and a credible build schedule. | Competition, construction delays, input scarcity, or demand reversal. |
| **Switch products or channels** | Technical capability, certifications, contracts, and customers for the alternative use. | Conversion expense, downtime, qualification delays, or correlated weakness across uses. |
| **Scale down or exit** | Contractual exit rights, redeployable assets, and realistic salvage value. | Fixed obligations, exit penalties, illiquid assets, or damage to other operations. |

An attractive future market does not by itself create an option for a particular company. Demeter would need to identify the decision rights, capabilities, financing, and capacity available to that actor.

## Separate three questions

### 1. How much system value could be created?

Estimate conditional health, resource, and economic outcomes through the scientific model. Report who benefits and when. Avoid counting transfers between actors as additional social benefit.

### 2. How much could the decision-maker capture?

Translate the relevant part of those outcomes into actor-specific volumes, prices, costs, and contractual cash flows. Account for competition, payment rules, bargaining power, capital requirements, and execution constraints. Healthcare savings do not automatically become the revenue or equity value of a food company.

### 3. How much does flexibility add?

Compare a strategy that commits now with a feasible strategy that adapts to information received later. Include the cost of acquiring and preserving flexibility. The adaptive strategy must use only information available at each decision date; selecting the best action after seeing an entire simulated future would overstate value.

Value from **learning** and value from **flexibility** are related but distinct. Information helps when it changes a decision. Flexibility helps when a useful change in action is available. A pilot may produce information without leaving enough time or capital to respond; a flexible asset may be valuable even without a new study.

## A worked decision structure: nutrition capacity

This example is qualitative and hypothetical. It makes no claim about future GLP-1 adoption, food demand, or profitability.

**Decision:** whether to commit capacity for a nutrition product serving a changing consumer population.

**Candidate strategies:** commit to a dedicated facility now; run a small contract-manufacturing pilot with an expansion right; purchase flexible capacity that can serve multiple products; or defer entry.

**Uncertain drivers:** reachable customers, repeat purchases, treatment persistence, willingness to pay, retailer access, ingredient costs, competitor supply, and capital cost. Changes in health outcomes require separate supporting evidence; commercial demand alone cannot establish them.

| Conditional path | What the model should investigate |
| --- | --- |
| Access broadens and repeat demand persists | Whether early capacity earns enough before competitors respond to justify committing sooner. |
| Initial interest is high but repeat demand is weak | Whether the pilot detects the problem before major capital is committed, and what its losses are. |
| Demand grows but margins compress | Whether scale improves costs enough, a different product is viable, or expansion destroys value. |
| Demand is strong but supply or distribution is constrained | Whether the scarce asset is processing, inputs, channel access, or execution capacity, and who captures the margin. |
| Access or reimbursement stalls or reverses | Whether the product has an independent customer base, assets can switch use, or exit is preferable. |

The analysis should report a **decision boundary**: combinations of observable demand, retained customers, attainable margin, financing, and lead time under which expansion becomes preferable. That boundary should include uncertainty and an area where evidence is insufficient to favor either action.

## How Demeter should calculate and present the comparison

1. **Specify the actor and objective.** Define the cash-flow perspective, decision dates, constraints, and evaluation horizon. Public-health decisions may require multiple outcomes rather than a single financial objective.
2. **Construct common scenario paths.** Evaluate every strategy under the same paths for prices, adoption, policy, and competition. Represent correlations and structural alternatives instead of assuming unrelated shocks by default.
3. **Define what is observable.** Record the timing, noise, and availability of signals. A strategy cannot react to a latent state or future outcome it would not know.
4. **Write the decision rules before evaluation.** Define triggers for piloting, scaling, switching, and exit. If rules are tuned, evaluate them on separate paths to limit overfitting.
5. **Account for all relevant flows.** Include development, operating and capital costs, working capital, delay, option fees, switching cost, foregone opportunity, and terminal or salvage value. State financing and discounting assumptions explicitly.
6. **Compare fixed and adaptive strategies.** Show gross benefit from flexibility, its cost, and the net difference against a clearly identified fixed strategy. When making an optimality claim, compare against the best feasible fixed strategy too.
7. **Report uncertainty honestly.** Use expected discounted values only when probabilities and valuation assumptions are defensible. Otherwise present scenario-specific outcomes, break-even conditions, downside exposure, and regret—the gap from the best feasible action in each scenario.
8. **Identify the next useful observation.** Show which measurement could change the action and whether its decision value could justify the time and cost of obtaining it.

Scenario dispersion is not automatically an option value, and greater uncertainty does not guarantee a more valuable strategy. Results depend on downside, reversibility, expiry, competition, and the ability to act.

## The eventual output: a map of conditional opportunity

A useful report should include:

- the action favored under each tested set of conditions;
- trigger ranges and observable leading indicators;
- the cost and duration of keeping each option available;
- delays and bottlenecks that can close the opportunity;
- the distribution of gains and losses across actors;
- exposure to adverse paths, correlated shocks, and model misspecification;
- evidence gaps that materially change the strategy.

Interactive views could show strategy regions across two drivers, trajectories with decision points, cash flows by actor, and sensitivity of the preferred action to evidence. Every view should state the model version, evidence status, scenario assumptions, and limits of the tested range.

Use [decision-focused tornado diagrams](Visualization-and-Tornado-Diagrams.md) to rank assumptions by their effect on the value difference between strategies. For example, compare pilot-then-expand with immediate commitment, and highlight bars that cross the zero-advantage line. This makes clear which trend, cost, or adoption assumption could change the choice. Report net option value after flexibility costs alongside the comparison against a named strategy; these are different measures.

The goal is to make conditional opportunity visible: **what becomes possible if a trend changes, what capability must exist beforehand, and what evidence would justify acting.** Investment interpretation remains downstream of the scientific model, with its own actor-specific assumptions and review.
