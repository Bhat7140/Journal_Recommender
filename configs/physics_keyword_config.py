PHYSICS_QUERIES = [
    # Core physics
    "physics",
    "classical mechanics",
    "statistical physics",
    "thermodynamics",
    "electromagnetism",

    # Quantum physics
    "quantum mechanics",
    "quantum field theory",
    "quantum information",
    "quantum optics",

    # Matter and materials
    "condensed matter physics",
    "solid state physics",
    "materials physics",
    "soft matter physics",

    # Particles, nuclear, and high energy
    "particle physics",
    "high energy physics",
    "nuclear physics",
    "accelerator physics",

    # Space and gravitation
    "astrophysics",
    "cosmology",
    "general relativity",
    "gravitational physics",

    # Applied and computational physics
    "plasma physics",
    "fluid physics",
    "biophysics",
    "computational physics",
]


# OpenAlex field filter: keeps keyword searches inside the Physics and Astronomy field.
OPENALEX_PHYSICS_FIELD_NAMES = ["Physics and Astronomy"]

# OpenAlex metadata filters: keeps records useful for embeddings and avoids books/datasets.
OPENALEX_PHYSICS_WORK_FILTERS = ["has_abstract:true", "type:article"]

# Crossref search filters: useful if Crossref is used as a primary search source later.
CROSSREF_PHYSICS_WORK_FILTERS = ["has-abstract:1", "type:journal-article"]


ARXIV_PHYSICS_CATEGORIES = [
    # General and interdisciplinary physics
    "physics.gen-ph",
    "physics.comp-ph",
    "physics.data-an",
    "physics.ed-ph",
    "physics.hist-ph",

    # Quantum, atomic, molecular, and optical physics
    "quant-ph",
    "physics.atom-ph",
    "physics.optics",

    # Condensed matter and materials
    "cond-mat.dis-nn",
    "cond-mat.mes-hall",
    "cond-mat.mtrl-sci",
    "cond-mat.other",
    "cond-mat.quant-gas",
    "cond-mat.soft",
    "cond-mat.stat-mech",
    "cond-mat.str-el",
    "cond-mat.supr-con",

    # High-energy, nuclear, and gravitational physics
    "hep-ex",
    "hep-lat",
    "hep-ph",
    "hep-th",
    "nucl-ex",
    "nucl-th",
    "gr-qc",

    # Astrophysics and cosmology
    "astro-ph.CO",
    "astro-ph.EP",
    "astro-ph.GA",
    "astro-ph.HE",
    "astro-ph.IM",
    "astro-ph.SR",

    # Applied physics domains
    "physics.acc-ph",
    "physics.ao-ph",
    "physics.app-ph",
    "physics.bio-ph",
    "physics.chem-ph",
    "physics.class-ph",
    "physics.flu-dyn",
    "physics.geo-ph",
    "physics.ins-det",
    "physics.med-ph",
    "physics.plasm-ph",
    "physics.pop-ph",
    "physics.soc-ph",
    "physics.space-ph",
]
