"""Inject a provider callable; no network, secrets, or external service is configured here."""


class ExternalStyleProvider:
    def __init__(self, generate):
        self.generate = generate

    def choose_style(self, facts):
        response = self.generate(facts)
        if (
            not isinstance(response, dict)
            or set(response) != {"style"}
            or response["style"] not in {"standard", "brief"}
        ):
            raise ValueError("Provider may select an approved style only")
        return response["style"]
