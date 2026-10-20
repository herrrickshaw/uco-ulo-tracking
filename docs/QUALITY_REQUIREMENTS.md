# Global quality requirements for UCO and ULO (reference, not legal advice)

Confidence tags: **[S]** seen in a primary/official source this session, **[2]** secondary source (review article, trade
press, vendor page), **[?]** not verified -- look up before relying on it. Gaps are listed honestly at the end.

## Used cooking oil (UCO)

UCO quality has two layers: (1) *food-safety limits that say when frying oil must be discarded* and (2) *commercial /
feedstock specs that say what a biofuel plant will accept*. There is **no single global UCO standard.**

### 1. When frying oil becomes "used" -- Total Polar Compounds (TPC) ceilings
| Country | Limit (TPC, % w/w) | Tag |
|---|---|---|
| India | 25 (FSS Licensing & Registration First Amendment 2017; monitoring from 1 Jul 2018) | [S] CPCB/FSSAI notice |
| Spain, Belgium, France, Portugal, Italy | 25 | [2] review article |
| Germany | 24 (another source cites 27 -- sources disagree) | [2] |
| Switzerland, China, Australia | 27 | [2] |
| Austria and others | national caps roughly 21-27 | [2], Austria unverified |

Implication for tracking: a "UCO" collection with TPC far *below* these limits is oil that was discarded early or is
fresh/blended oil -- the repo flags TPC < 8% as `suspiciously_fresh_uco` (our heuristic, not a regulation).

### 2. Commercial feedstock specs (buyer-driven)
Platts UCO benchmark specs [2]: FFA <= 5%, MIU (moisture + insolubles + unsaponifiables) <= 2%, sulfur <= 40-50 ppm,
iodine value >= 50-70, wax <= 300 ppm, and **ISCC-certified, RED-compliant**. Trade commentary: "good" UCO FFA <= 5%,
market grades run up to ~15% FFA [2]. Higher FFA correlates with worse everything else, so FFA alone is a weak gate.

### 3. Sustainability / chain-of-custody (what makes UCO *count*)
* **EU (RED II/III + ISCC EU or other approved voluntary scheme):** UCO is an Annex IX Part B waste feedstock; proof of
  sustainability and mass-balance chain of custody are required for it to count toward targets. [2] (Annex text not fetched.)
* **US:** EPA RFS/LCFS/45Z pathway eligibility requires UCO to qualify as "separated food waste" with records per
  pickup. [2] (Veriflux vendor page.)
* **India:** FSSAI RUCO -- FBOs using > 50 L/day keep usage records and hand UCO only to authorised agencies; traceability
  application live from 1 Mar 2023. [S] FSSAI notice (50 L figure: press/notice, check original order).
* **Fraud context:** UCO is called the most fraud-prone biofuel feedstock (fresh/virgin oil passed off as used); Indian
  industry commentary claims very high diversion but the figure is an executive's estimate [2].

Biodiesel *product* standards (EN 14214, ASTM D6751, IS 15607) govern the fuel, not the feedstock, and are out of scope here.

## Used lubricating oil (ULO)

ULO is regulated as hazardous waste almost everywhere; quality rules decide the **route**: re-refine (best), burn as
fuel (spec-limited), or treat as hazardous waste (off-spec / PCB).

| Jurisdiction | Key quality requirements | Tag |
|---|---|---|
| **India** | "Used oil" = crude/synthetic oils (engine, gear, hydraulic, turbine, compressor, transformer, heat-transfer + tank-bottom sludge) that meet **HOWM Rules 2016 Schedule V Part A**; "waste oil" (spills, slop, emulsions) is separate and meets Part B. Part A limits PCBs, Pb, As, Cd, Cr, Ni, PAH. Numeric values not retrieved. Under EPR the CPCB sets a recycler conversion factor from technology + base-oil quality, and BIS-conforming re-refined oil gets weightage. Transport: Form 10 manifest, GPS, NHWTS registration. | [S] CPCB FAQ/guidelines; Schedule V numbers [?] |
| **USA** | 40 CFR 279.11 "on-spec" used oil fuel: As <= 5 ppm, Cd <= 2, Cr <= 10, Pb <= 100, flash point >= 100 F, total halogens <= 4,000 ppm. Halogens > 1,000 ppm are *presumed hazardous* (rebuttable). PCB-containing oil falls under 40 CFR 761 (>= 50 ppm regulated). | [S] eCFR/Cornell |
| **EU** | Waste Framework Directive 2008/98/EC; regeneration has priority over burning. Legacy waste-oil directive set **PCB/PCT <= 50 ppm** for regenerated/fuel oil. Member states tighten: e.g. Austria <= 5 ppm PCB/PCT and <= 0.03% halogens for recycled oil. | 50 ppm and Austria [2]; current EU text [?] |
| **Other** | Many countries (UK, Canada, Australia, Gulf, SE Asia) follow a similar pattern -- PCB cap ~50 ppm, halogen/heavy-metal caps for fuel use, base-oil grade tests for re-refining. Not researched individually. | [?] |

Typical tests used to qualify a ULO lot (also what this repo captures): water %, PCB ppm, total chlorine/halogens ppm,
flash point, heavy metals, viscosity/colour for re-refining. The repo's thresholds (water <= 5%, PCB hazard >= 50 ppm,
chlorine <= 1,000 ppm) are **placeholders** pending the India Schedule V numbers.

## What I could not verify
India Schedule V Part A numeric limits; current EU waste-oil text and any EU chlorine limit; ISCC/RED Annex IX wording;
UK, China, Indonesia/Malaysia, Gulf UCO and ULO rules; ASTM/EN base-oil Group specs for re-refined oil.
