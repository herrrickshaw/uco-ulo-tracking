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

# Used-oil EPR (Hazardous & Other Wastes Second Amendment Rules 2023, G.S.R. 677(E),
# effective 1 Apr 2024).  Only the endpoints are sourced (5% FY2024-25 -> 50% FY2030-31);
# the intermediate years are a LINEAR ASSUMPTION -- replace with the Schedule values.
EPR_TARGET_PCT = {2024: 5.0, 2025: 12.5, 2026: 20.0, 2027: 27.5, 2028: 35.0, 2029: 42.5, 2030: 50.0}

# GHG intensity defaults, gCO2e/MJ.  Indicative RED-style values for UCO-derived fuels;
# VERIFY against RED III Annex V / CORSIA default LCA tables before reporting.
FOSSIL_DIESEL_COMPARATOR_G_PER_MJ = 94.0
GHG_DEFAULT_G_PER_MJ = {"biodiesel": 20.0, "hefa_feedstock": 14.0}
LHV_MJ_PER_KG = {"biodiesel": 37.2, "hefa_feedstock": 37.0}
