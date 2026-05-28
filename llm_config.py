"""LLM classification pipeline configuration."""

from dataclasses import dataclass, field


@dataclass
class LLMConfig:
    """LLM server configuration."""
    base_url: str = "http://localhost:8000"
    model: str = "default"
    api_key: str = ""  # Often not needed for local servers
    timeout: int = 120  # Seconds for long LLM responses
    max_retries: int = 3


@dataclass
class ClassificationConfig:
    """Classification pipeline configuration."""
    # Categories to classify articles into
    categories: list[str] = field(default_factory=lambda: [
        "health_outcomes",      # Cases, deaths, hospitalizations, ICU
        "vaccination",          # Vaccine rollout, efficacy, mandates
        "lockdown_measures",    # Restrictions, alert levels, curfews
        "border_policy",        # Quarantine, managed isolation, travel
        "economic_impact",      # Business closures, job losses, support
        "public_behavior",      # Mask mandates, social distancing
        "government_response",  # Policy announcements, cabinet decisions
        "science_research",     # Variants, studies, scientific findings
        "international",        # Global context, other countries
        "miscellaneous",        # Other COVID-related content
    ])

    # Batch processing
    batch_size: int = 10
    rate_limit_delay: float = 0.5  # Seconds between API calls

    # Output
    output_path: str = "llm_classifications.parquet"
    overwrite: bool = False


@dataclass
class PipelineConfig:
    """Main pipeline configuration."""
    llm: LLMConfig = field(default_factory=LLMConfig)
    classification: ClassificationConfig = field(default_factory=ClassificationConfig)

    # Input source
    input_path: str = "covid_nz_news_delta"  # Delta Lake table path
    input_filter: str | None = None  # Optional Polars filter expression

    # Processing
    limit: int | None = None  # Limit number of articles to process
    resume: bool = True  # Resume from existing classifications
