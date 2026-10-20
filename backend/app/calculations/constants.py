"""Editable regulatory / physical defaults. NOT hardcoded truth -- every value marked
VERIFY must be reconciled against the current official source before compliance use."""

# Densities (kg/L), typical values.
DENSITY_KG_PER_L = {"UCO": 0.92, "ULO": 0.89}

# FSSAI: frying oil must not be used beyond 25% total polar compounds (TPC) (FSS Licensing &
# Registration First Amendment 2017; monitoring from 1 Jul 2018).  VERIFY against current text.
FSSAI_TPC_LIMIT_PCT = 25.0

# FSSAI RUCO: FBOs using > 50 L/day of frying oil keep usage records and hand UCO only to
# authorised agencies (May 2019 order, via press notice).  VERIFY original order.
RUCO_RECORD_THRESHOLD_L_PER_DAY = 50.0

# HEURISTIC (not a regulation): collected "UCO" with TPC below this looks like fresh or
# blended oil passed off as used -- the classic UCO-fraud signature.
UCO_SUSPICIOUSLY_FRESH_TPC_PCT = 8.0

# HEURISTIC: max share of purchased oil/lubricant that can plausibly come back as used oil.
MAX_RECOVERABLE_FRACTION = {"UCO": 0.60, "ULO": 0.60}

# ULO acceptance (PLACEHOLDERS -- VERIFY against CPCB used-oil guidelines / buyer specs).
ULO_MAX_WATER_PCT = 5.0
ULO_PCB_HAZARD_PPM = 50.0
ULO_MAX_CHLORINE_PPM = 1000.0

# Plausible mass yields (output kg / input kg).  Exceeding the max is a data or fraud flag.
YIELD_RANGE = {
    "biodiesel": (0.70, 0.95),
    "hefa_feedstock": (0.80, 0.99),
    "base_oil": (0.45, 0.85),
    "fuel_oil": (0.50, 0.95),
}
# Allowed product per material.
PRODUCTS_BY_MATERIAL = {
    "UCO": {"biodiesel", "hefa_feedstock"},
    "ULO": {"base_oil", "fuel_oil"},
}

# Lot mass balance: processed input may not exceed lot received kg by more than this.
MASS_BALANCE_TOLERANCE_PCT = 2.0

# Used-oil EPR (HOWM Second Amendment Rules 2023, G.S.R. 677(E), eff. 1 Apr 2024), as reproduced in
# CPCB's Used Oil FAQ (eprusedoil.cpcb.gov.in) Q12.  Producer target in obligation year Y (FY start year)
# = pct x base oil / lubricant sold or imported in year Y-2.  2030-31 onwards: 50% of Y-2.
EPR_PRODUCER_PCT = {2024: 5.0, 2025: 10.0, 2026: 20.0, 2027: 20.0, 2028: 40.0, 2029: 40.0}
EPR_PRODUCER_PCT_FROM_2030 = 50.0
EPR_BASE_YEAR_LAG = 2            # producers: sales in Y-2
EPR_IMPORTER_PCT = 100.0         # used-oil importers: 100% of used oil imported in Y-1
EPR_IMPORTER_BASE_YEAR_LAG = 1

# Certificate generation: QEPR = Qp x CF x Wp (FAQ Q28).  CF is set per recycler by CPCB (default
# below is a PLACEHOLDER ~ 1/0.68 yield); Wp is 1.0 for re-refined base/lube oil and 0.25 for
# co-processing / energy recovery of used oil not suitable for recycling.
WEIGHTAGE = {"re_refining": 1.0, "co_processing": 0.25}
ROUTE_BY_PRODUCT = {"base_oil": "re_refining", "fuel_oil": "co_processing"}
DEFAULT_CONVERSION_FACTOR = 1.5
CERT_VALIDITY_YEARS_AFTER_FY_END = 2          # FAQ Q39
PURCHASE_CAP_MARGIN_PCT = 10.0                # FAQ Q38: liability + leftover + 10% of current-year liability
# FAQ Q35: exchange price floor/ceiling = 30% / 100% of Environmental Compensation per tonne.
# CPCB publishes the EC rate separately -- NOT captured here; set it once confirmed.
EC_INR_PER_TONNE: float | None = None
PRICE_BAND_PCT_OF_EC = (30.0, 100.0)

# Collection-agent rules (CPCB Guidelines, Jan 2025): CA-1 = no storage, containers <= 200 L,
# operates within 75 km of recycler / CA-2 (150 km if none available); CA-2 has storage.
CA1_MAX_CONTAINER_L = 200.0
CA1_RADIUS_KM = 75.0
CA1_RADIUS_NO_RECYCLER_KM = 150.0
TRANSIT_LOSS_TOLERANCE_PCT = 3.0    # HEURISTIC: dispatched vs received variance before flagging

# Returns: collection agents & recyclers file quarterly returns by end of the month after the
# quarter; annual returns by 30 June after the FY.  Portal notices extend some deadlines.
ANNUAL_RETURN_DUE = (6, 30)
RETURN_EXTENSIONS = {"Annual FY2025-26": (2026, 11, 30)}   # portal notice: FY2025-26 annual return extended

# GHG intensity defaults, gCO2e/MJ.  Indicative RED-style values for UCO-derived fuels;
# VERIFY against RED III Annex V / CORSIA default LCA tables before reporting.
FOSSIL_DIESEL_COMPARATOR_G_PER_MJ = 94.0
GHG_DEFAULT_G_PER_MJ = {"biodiesel": 20.0, "hefa_feedstock": 14.0}
LHV_MJ_PER_KG = {"biodiesel": 37.2, "hefa_feedstock": 37.0}
