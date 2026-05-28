"""LLM client for OpenAI-compatible local servers."""

from typing import Iterator

import openai

from llm_config import PipelineConfig


class LLMClient:
    """Client for OpenAI-compatible LLM servers."""

    def __init__(self, config: PipelineConfig):
        self.config = config
        self.client = openai.OpenAI(
            base_url=config.llm.base_url,
            api_key=config.llm.api_key or "dummy",  # Required but often ignored locally
            timeout=config.llm.timeout,
        )

    def classify_article(
        self,
        title: str,
        content: str,
        categories: list[str],
    ) -> str:
        """Classify an article into one of the given categories.

        Args:
            title: Article title
            content: Article content (may be truncated)
            categories: List of category names to choose from

        Returns:
            The selected category name
        """
        # Truncate content to avoid token limits
        max_content_length = 4000
        if len(content) > max_content_length:
            content = content[:max_content_length] + "..."

        categories_str = "\n".join(f"- {cat}" for cat in categories)

        prompt = f"""You are a news article classifier. Classify the following article into exactly ONE of these categories:

{categories_str}

Article Title: {title}

Article Content:
{content}

Respond with ONLY the category name, nothing else."""

        response = self.client.chat.completions.create(
            model=self.config.llm.model,
            messages=[
                {"role": "system", "content": "You are a helpful classifier. Respond with only the category name."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=10,  # Just need the category name
        )

        category = response.choices[0].message.content.strip() if response.choices[0].message.content else "unknown"
        return category

    def batch_classify(
        self,
        articles: list[dict],
        categories: list[str],
    ) -> Iterator[str]:
        """Batch classify articles with rate limiting.

        Args:
            articles: List of article dicts with 'title' and 'content' keys
            categories: List of category names

        Yields:
            Category name for each article
        """
        import time

        for article in articles:
            title = article.get("title", "")
            content = article.get("content", "")

            try:
                category = self.classify_article(title, content, categories)
                yield category
            except Exception as e:
                print(f"Error classifying article: {e}")
                yield "error"

            # Rate limiting
            time.sleep(self.config.classification.rate_limit_delay)
