from typing import Literal, Protocol

SummaryStyle = Literal["standard", "brief"]


class StyleProvider(Protocol):
    def choose_style(self, facts: dict) -> SummaryStyle: ...
