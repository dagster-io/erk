from dataclasses import dataclass
from typing import LiteralString


@dataclass(frozen=True)
class HtmlString:
    unsafe_html: str

    @classmethod
    def join(cls, *html_strings: "HtmlString") -> "HtmlString":
        if not all(isinstance(html_string, HtmlString) for html_string in html_strings):
            raise ValueError("All arguments must be HtmlString instances")
        return cls(unsafe_html="".join(html_string.unsafe_html for html_string in html_strings))

    @classmethod
    def from_template(cls, template: LiteralString, **kwargs: "HtmlString | str") -> "HtmlString":
        import html

        subs = {}
        for k, v in kwargs.items():
            if isinstance(v, HtmlString):
                subs[k] = v.unsafe_html
            elif isinstance(v, str):
                subs[k] = html.escape(v)
            else:
                raise ValueError(f"Invalid type for {k}: {type(v)}")
        return cls(template.format(**subs))
