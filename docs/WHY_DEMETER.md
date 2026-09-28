# Why Demeter

*The name, the systems question, and the invitation behind an open Food is Health model.*

In the *Homeric Hymn to Demeter*, the goddess of grain withholds the harvest
after Hades takes her daughter Persephone. Crops fail. Humanity faces famine.
The threatened loss reaches Olympus, too: without people to sustain them, the
gods would lose their offerings and honors. Zeus intervenes, and the eventual
settlement allows Persephone to return to her mother for part of each year.
The story connects the renewal of the earth with separation and reunion.
([Homeric Hymn to Demeter](https://www-current.chs.harvard.edu/primary-source/homeric-hymn-to-demeter-sb/),
especially lines 305–333 and 445–473.)

Read as a systems metaphor, the story makes a useful point. A disruption in the
food foundation can travel through the entire social order. Those with the power
to respond are part of that system, even when they seem far removed from its
fields and harvests. Their incentives become visible when the consequences
reach them.

That is the question behind Demeter: **when something changes in food and
agriculture, how do its effects move through health and economics, and what
brings a response back through the system?**

Demeter is an [open-source project](https://github.com/Crusonia/Demeter) growing
out of [Food is Health](https://foodishealth.substack.com/). The aim is to turn
questions explored in essays and conversations into explicit relationships that
people can inspect, challenge, and test. We want to understand which changes
matter, where they meet constraints, who bears the cost, who receives the
benefit, and what makes a different course of action practical.

Consider a producer changing a farming practice, a food company reformulating
a product, or a retailer making a different food basket more affordable. Each
decision raises questions beyond the immediate transaction. Does the product
change in a meaningful way? Do people change what they buy and eat? Does that
change their health? Over what period? What happens to household spending,
healthcare use, business margins, and demand for agricultural production?

A benefit elsewhere in the system does not, by itself, pay the person who
created it. A farmer might bear a cost before a retailer sees a return. A food
business might invest in a product whose possible health benefits would accrue
years later to households or payers. Whether those connections exist, how large
they are, and what arrangements could return value to the original participant
are questions for investigation. Value creation, value capture, and the timing
of each need separate accounts.

The effects and the incentives may travel at different speeds. A change in
consumption could precede an observable health outcome by years. A contract may
reward a different outcome, over a different period, for a different population.
Demeter should help expose those mismatches and the evidence needed to assess
them. It should also show when a proposed pathway is too weak or uncertain to
carry the conclusion placed on it.

The longer-term ambition is a management flight simulator for the food and
health system. A farmer, food company, retailer, clinician, payer, policymaker,
or investor should be able to explore a decision, inspect delayed consequences,
and understand which assumptions produced the result. The learning cycle is to
state an expectation, run a defined experiment, inspect the mechanisms, and
revise the expectation. The [project vision](PROJECT_VISION.md) sets out that
staged ambition.

One intended exercise is a [shift toward real food](REAL_FOOD_VALUE_CHAIN.md).
To make it testable, we must define the foods, substitutions, prices, access,
and actual consumption involved. Another asks whether earlier intervention in
people at metabolic risk could improve healthspan and, eventually, reduce net
healthcare costs. The proposed PreChronic population needs defensible inclusion
criteria. A farming practice, product label, or population name cannot supply
the missing biological or economic relationships.

We are beginning with one complete health pathway:

**Dietary exposure → metabolic state → chronic-disease risk → mortality and healthspan.**

This first stage provides a place to make the basic disciplines work: explicit
population states, conserved flows, defined units, traceable evidence,
uncertainty, scenario comparison, and historical checks. The repository already
contains a working Python engine, documented scenarios, versioned source data
and official source links, an evidence registry, and tools for inspecting model
behavior. Alternative transition equations and scenario packages can be loaded
with their provenance visible.

The U.S. population and mortality foundation uses official observations.
Important metabolic-state allocations, transition rates, mortality ratios, and
dietary effects still include synthetic inputs used to validate software.
Clinical calibration and historical health validation remain unfinished.
Current dietary scenario differences are therefore validation-only outputs,
not established health benefits or lifespan predictions. The
[acceptance status](V0_1_STATUS.md) and [evidence gaps](EVIDENCE_GAPS.md) describe
what remains unresolved.

Food prices, consumer behavior, agricultural supply, provider economics, and
integrated feedback belong to later stages. The breadth of the purpose is a
reason to establish a credible foundation and clear interfaces. It is not a
reason to fill missing relationships with convenient numbers. A useful result
may be a rejected hypothesis, an unexpected constraint, or a clearer account of
which evidence would change a decision.

The name carries other associations that help explain this purpose. At Eleusis,
the worship of Demeter and Persephone connected agricultural cycles with human
concerns about death and the afterlife.
([The Metropolitan Museum of Art, *Mystery Cults in the Greek and Roman World*](https://www.metmuseum.org/essays/mystery-cults-in-the-greek-and-roman-world).)
In *De Legibus* 2.36, Cicero associates the mysteries with learning to live with
joy and to face death with greater hope.
([Cicero, Latin text](https://www.thelatinlibrary.com/cicero/leg2.shtml).)
For this project, the resonance is the connection between sustaining life and
the quality of the years people live. These religious ideas provide historical
context for the name; the model's healthspan measures require their own explicit
definitions and empirical validation.

Ovid offers a darker image in the story of Erysichthon. After he destroys an oak
in the sacred grove of Ceres, insatiable hunger consumes his wealth and finally
his own body.
([*Metamorphoses*, Book 8, lines 725–878](https://www.poetryintranslation.com/PITBR/Latin/Metamorph8.php).)
The image invites a question about the relationship between consumption and
satisfaction. In Demeter, questions about food composition, satiety, and intake
must become separately evidenced mechanisms. The story supplies no clinical
explanation of appetite or metabolic disease.

Ceres is the Roman counterpart of Demeter; her name also survives in the word
*cereal*. Even an ordinary word for grain retains the older association between
agriculture and the means of sustaining life.
([Cambridge Dictionary, *Ceres*](https://dictionary.cambridge.org/us/dictionary/english/ceres).)

Developers will recognize another association: the **Law of Demeter**, a software
design principle proposed by Ian Holland at Northeastern University in 1987.
It emerged from the Demeter Project, whose agricultural name reflected an
approach to growing software in small steps. The principle asks an object to
work through its immediate collaborators rather than depend on the internal
structure of distant objects.
([Northeastern's account of the Law of Demeter](https://khoury.northeastern.edu/home/lieber/LoD.html).)

For example, `farm.getSupplier().getTruck().getDriver().call()` makes the caller
depend on several layers of implementation. An operation such as
`farm.requestDelivery()` lets the responsible component manage those details.
Counting dots is only a shorthand; the concern is which implementation details
one part of the program needs to know about another.

This principle fits the model's engineering needs. We want to trace long causal
paths while keeping their software implementation understandable and replaceable.
The Law of Demeter limits unnecessary software dependencies; it does not prohibit
effects from propagating through a modeled system. Explicit interfaces allow a
module to communicate a defined quantity without reaching into another module's
private state. They also allow a researcher to test an alternative relationship
and see how the resulting system behaves. Today's
[module API](MODULE_API.md) and [local extension registry](EXTENSIONS.md) provide
an initial health-transition implementation of that approach. Broader domain
interfaces remain staged work under the [system architecture](SYSTEM_ARCHITECTURE.md).

The shared name does not imply an affiliation with Northeastern's Demeter
Project. Nor is this model part of the Demeter biodynamic certification system,
whose organization dates its symbol and first quality standards to 1928.
([Demeter International's history](https://demeter.net/about/history/).)
Use **Crusonia/Demeter**, the **Food is Health model**, to identify this project.
Its name does not endorse a certification standard or establish a health effect
for a production practice.

There is one more story that explains why the work should be open. In the
Triptolemus tradition, Demeter gives a young man agricultural knowledge, and he
travels in a winged chariot to spread the cultivation of wheat. Ancient Attic
vases depict that departure.
([The Metropolitan Museum of Art, *Terracotta hydria*, attributed to the Troilos Painter](https://www.metmuseum.org/art/collection/search/254912).)

The useful knowledge is meant to travel. For Demeter, that means making the
code, assumptions, source references, transformations, and experiments available
for other people to examine and improve. Project code is
[MIT licensed](../LICENSE); datasets retain their own documented terms.
Openness should make disagreement more productive. A competing explanation,
failed reproduction, or null result belongs in the work alongside a result that
supports the Food is Health thesis.

There are two broad invitations:

- **Help shape the strategy and evidence.** Bring a decision the model should
  help someone understand, a constraint from your part of the value chain, a
  better source, or an objection to a proposed causal link. Explain what should
  happen, through which mechanism, and what observation could show that the
  explanation is wrong. Coding is not required.
- **Help build and test the model.** Run an example, inspect an equation, improve
  a data transform, add a meaningful test, clarify documentation, or propose an
  alternative module. Keep changes small enough to review and preserve their
  evidence, assumptions, and limitations. The
  [contributing guide](../CONTRIBUTING.md) explains the process.

The [newcomer guide](START_HERE.md), [learning path](LEARNING_PATH.md), and
[issue tracker](https://github.com/Crusonia/Demeter/issues) are entry points.
The [Project Vision](PROJECT_VISION.md) remains the canonical phased roadmap;
this document supplies the shared background and naming rationale.

The harvest story gives us a question about connected consequences and the
incentives to respond. Triptolemus gives us an image of knowledge being carried
outward. Demeter brings those ideas together in a practical invitation: start
with one part of the system you know well, help us represent it accurately, and
make what we learn available to the next person.
