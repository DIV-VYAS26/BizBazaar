from .ai.fallback import render_summary
from .context import prepare
from .metrics import calculate_metrics


def generate_daily_summary(
    transactions, config, context=None, locale="en-IN", provider=None
):
    if locale not in {"en-IN", "hi-IN"}:
        raise ValueError("Unsupported summary language")
    data = prepare(transactions, config, context)
    if data.start != data.end:
        raise ValueError("Daily summaries require a single reporting date")
    metrics = calculate_metrics(transactions, config, context)
    style, mode = "standard", "DETERMINISTIC_FALLBACK"
    if provider is not None:
        try:
            selected = provider.choose_style(
                {"date": data.end.isoformat(), "metrics": metrics, "locale": locale}
            )
            if selected not in {"standard", "brief"}:
                raise ValueError("Unsupported provider style")
            style, mode = selected, "EXTERNAL_LLM"
        except Exception:  # noqa: BLE001 - optional provider boundary must preserve fallback text
            # Provider timeouts, malformed responses and missing configuration never remove the text.
            style, mode = "standard", "DETERMINISTIC_FALLBACK"
    return {
        "date": data.end.isoformat(),
        "locale": locale,
        "summary_text": render_summary(
            metrics, data.end.isoformat(), data.config.timezone, locale, style
        ),
        "metrics": metrics,
        "data_sufficiency": "SUFFICIENT"
        if data.end in data.complete_days()
        else "INSUFFICIENT",
        "generation_mode": mode,
        "limitations": [
            "Text is rendered from calculated amounts; optional AI selects wording style only.",
            "Current or unknown-coverage days describe partial recorded activity.",
        ]
        + (
            [
                "Hindi template requires native-speaker usability validation before broad release."
            ]
            if locale == "hi-IN"
            else []
        ),
    }
