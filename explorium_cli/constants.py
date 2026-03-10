"""Valid enum values and aliases for API filter fields."""

VALID_DEPARTMENTS = {
    "administration", "real estate", "healthcare", "partnerships", "c-suite",
    "design", "human resources", "engineering", "education", "strategy",
    "product", "sales", "r&d", "retail", "customer success", "security",
    "public service", "creative", "it", "support", "marketing", "trade",
    "legal", "operations", "procurement", "data", "manufacturing",
    "logistics", "finance",
}

VALID_JOB_LEVELS = {
    "cxo", "vp", "director", "manager", "senior", "entry",
    "training", "owner", "partner", "unpaid",
}

DEPARTMENT_ALIASES = {
    "information technology": "it",
    "info tech": "it",
    "tech": "it",
    "technology": "it",
    "hr": "human resources",
    "cs": "customer success",
    "eng": "engineering",
    "mktg": "marketing",
    "ops": "operations",
    "mfg": "manufacturing",
    "research": "r&d",
    "research and development": "r&d",
    "dev": "engineering",
    "devops": "engineering",
    "infra": "it",
    "infrastructure": "it",
    "swe": "engineering",
    "software engineering": "engineering",
    "executive": "c-suite",
    "management": "c-suite",
    "supply chain": "logistics",
}

JOB_LEVEL_ALIASES = {
    "c-suite": "cxo",
    "c-level": "cxo",
    "chief": "cxo",
    "executive": "cxo",
    "vice president": "vp",
    "vice-president": "vp",
    "dir": "director",
    "mgr": "manager",
    "sr": "senior",
    "junior": "entry",
    "intern": "training",
    "founder": "owner",
}
