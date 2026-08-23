import ipaddress
import re
import socket

from html.parser import (
    HTMLParser,
)

from urllib.parse import (
    urljoin,
    urlparse,
)

import httpx

from app.core.task_runtime import (
    PageResource,
)


# =========================================================
# ERRORS
# =========================================================


class PageReadError(
    RuntimeError
):
    pass


# =========================================================
# HTML TEXT EXTRACTOR
# =========================================================


class ReadableHTMLParser(
    HTMLParser
):
    HARD_IGNORE_TAGS = {
        "script",
        "style",
        "noscript",
        "svg",
        "canvas",
        "template",
        "iframe",
        "object",
    }

    UI_IGNORE_TAGS = {
        "nav",
        "footer",
        "aside",
        "form",
        "button",
        "menu",
        "dialog",
        "select",
        "option",
    }

    VOID_TAGS = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }

    BLOCK_TAGS = {
        "article",
        "blockquote",
        "br",
        "dd",
        "div",
        "dl",
        "dt",
        "figure",
        "figcaption",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "p",
        "pre",
        "section",
        "table",
        "td",
        "th",
        "tr",
    }

    PRIMARY_ID_PATTERN = re.compile(
        (
            r"^(?:"
            r"mw-content-text|"
            r"bodycontent|"
            r"content|"
            r"main-content|"
            r"article-content|"
            r"post-content|"
            r"entry-content"
            r")$"
        ),
        flags=re.IGNORECASE,
    )

    PRIMARY_CLASS_PATTERN = re.compile(
        (
            r"(?:^|\s)"
            r"(?:"
            r"mw-parser-output|"
            r"article-content|"
            r"post-content|"
            r"entry-content|"
            r"main-content"
            r")"
            r"(?:\s|$)"
        ),
        flags=re.IGNORECASE,
    )

    NOISE_LINES = {
        "jump to content",
        "main menu",
        "navigation",
        "search",
        "appearance",
        "personal tools",
        "create account",
        "log in",
        "donate",
        "tools",
        "actions",
        "general",
        "edit",
        "view history",
        "languages",
    }

    PRIMARY_MIN_CHARS = 100

    def __init__(
        self,
    ) -> None:
        super().__init__(
            convert_charrefs=True,
        )

        self._title_depth = 0
        self._body_depth = 0
        self._hard_ignore_depth = 0
        self._ui_ignore_depth = 0
        self._primary_depth = 0

        self._title_parts: list[
            str
        ] = []

        self._fallback_parts: list[
            str
        ] = []

        self._primary_parts: list[
            str
        ] = []

        # (
        #     tag,
        #     started_title,
        #     started_body,
        #     started_hard_ignore,
        #     started_ui_ignore,
        #     started_primary,
        # )
        self._stack: list[
            tuple[
                str,
                bool,
                bool,
                bool,
                bool,
                bool,
            ]
        ] = []

    # =====================================================
    # START TAG
    # =====================================================

    def handle_starttag(
        self,
        tag: str,
        attrs: list[
            tuple[
                str,
                str | None,
            ]
        ],
    ) -> None:
        normalized = (
            tag
            .strip()
            .lower()
        )

        attributes = self._normalize_attrs(
            attrs
        )

        started_title = False
        started_body = False
        started_hard_ignore = False
        started_ui_ignore = False
        started_primary = False

        # -------------------------------------------------
        # TITLE
        # -------------------------------------------------

        if (
            normalized == "title"
            and self._hard_ignore_depth == 0
        ):
            self._title_depth += 1
            started_title = True

        # -------------------------------------------------
        # BODY
        # -------------------------------------------------

        if normalized == "body":
            self._body_depth += 1
            started_body = True

        # -------------------------------------------------
        # HARD IGNORE
        # -------------------------------------------------

        if (
            normalized
            in self.HARD_IGNORE_TAGS
        ):
            self._hard_ignore_depth += 1
            started_hard_ignore = True

        # -------------------------------------------------
        # UI IGNORE
        # -------------------------------------------------

        elif (
            self._hard_ignore_depth == 0
            and normalized
            in self.UI_IGNORE_TAGS
        ):
            self._ui_ignore_depth += 1
            started_ui_ignore = True

        # -------------------------------------------------
        # PRIMARY CONTENT
        # -------------------------------------------------

        if (
            self._hard_ignore_depth == 0
            and self._ui_ignore_depth == 0
            and self._is_primary_container(
                normalized,
                attributes,
            )
        ):
            self._primary_depth += 1
            started_primary = True

        # -------------------------------------------------
        # FORMAT
        # -------------------------------------------------

        if self._is_readable():
            if (
                normalized
                in self.BLOCK_TAGS
            ):
                self._append_content(
                    "\n"
                )

            if normalized == "li":
                self._append_content(
                    "- "
                )

        # -------------------------------------------------
        # STACK
        # -------------------------------------------------

        if (
            normalized
            not in self.VOID_TAGS
        ):
            self._stack.append(
                (
                    normalized,
                    started_title,
                    started_body,
                    started_hard_ignore,
                    started_ui_ignore,
                    started_primary,
                )
            )

    # =====================================================
    # SELF-CLOSING TAG
    # =====================================================

    def handle_startendtag(
        self,
        tag: str,
        attrs: list[
            tuple[
                str,
                str | None,
            ]
        ],
    ) -> None:
        del attrs

        normalized = (
            tag
            .strip()
            .lower()
        )

        if not self._is_readable():
            return

        if (
            normalized
            in self.BLOCK_TAGS
        ):
            self._append_content(
                "\n"
            )

    # =====================================================
    # END TAG
    # =====================================================

    def handle_endtag(
        self,
        tag: str,
    ) -> None:
        normalized = (
            tag
            .strip()
            .lower()
        )

        matching_index: (
            int | None
        ) = None

        for index in range(
            len(self._stack) - 1,
            -1,
            -1,
        ):
            if (
                self._stack[
                    index
                ][0]
                == normalized
            ):
                matching_index = index
                break

        if matching_index is None:
            return

        if (
            self._is_readable()
            and normalized
            in self.BLOCK_TAGS
        ):
            self._append_content(
                "\n"
            )

        entries = (
            self._stack[
                matching_index:
            ]
        )

        del self._stack[
            matching_index:
        ]

        for (
            _,
            started_title,
            started_body,
            started_hard_ignore,
            started_ui_ignore,
            started_primary,
        ) in reversed(
            entries
        ):
            if (
                started_primary
                and self._primary_depth
            ):
                self._primary_depth -= 1

            if (
                started_ui_ignore
                and self._ui_ignore_depth
            ):
                self._ui_ignore_depth -= 1

            if (
                started_hard_ignore
                and self._hard_ignore_depth
            ):
                self._hard_ignore_depth -= 1

            if (
                started_body
                and self._body_depth
            ):
                self._body_depth -= 1

            if (
                started_title
                and self._title_depth
            ):
                self._title_depth -= 1

    # =====================================================
    # TEXT
    # =====================================================

    def handle_data(
        self,
        data: str,
    ) -> None:
        text = (
            data
            .strip()
        )

        if not text:
            return

        if self._title_depth:
            self._title_parts.append(
                text
            )
            return

        if not self._is_readable():
            return

        self._append_content(
            text
        )

        self._append_content(
            " "
        )

    # =====================================================
    # ATTRIBUTES
    # =====================================================

    def _normalize_attrs(
        self,
        attrs: list[
            tuple[
                str,
                str | None,
            ]
        ],
    ) -> dict[
        str,
        str,
    ]:
        return {
            key
            .strip()
            .lower():
                (
                    value
                    or ""
                )
                .strip()
                .lower()

            for (
                key,
                value,
            ) in attrs
        }

    # =====================================================
    # PRIMARY CONTENT DETECTION
    # =====================================================

    def _is_primary_container(
        self,
        tag: str,
        attributes: dict[
            str,
            str,
        ],
    ) -> bool:
        if tag in {
            "main",
            "article",
        }:
            return True

        if (
            attributes.get(
                "role"
            )
            == "main"
        ):
            return True

        element_id = (
            attributes.get(
                "id",
                "",
            )
        )

        if (
            element_id
            and self.PRIMARY_ID_PATTERN
            .search(
                element_id
            )
        ):
            return True

        class_name = (
            attributes.get(
                "class",
                "",
            )
        )

        if (
            class_name
            and self.PRIMARY_CLASS_PATTERN
            .search(
                class_name
            )
        ):
            return True

        return False

    # =====================================================
    # READABLE STATE
    # =====================================================

    def _is_readable(
        self,
    ) -> bool:
        if self._hard_ignore_depth:
            return False

        if self._ui_ignore_depth:
            return False

        # Prefer body content when <body> is present.
        if (
            self._body_depth
            > 0
        ):
            return True

        # Some HTML fragments do not contain <body>.
        return (
            self._primary_depth
            > 0
        )

    # =====================================================
    # APPEND CONTENT
    # =====================================================

    def _append_content(
        self,
        text: str,
    ) -> None:
        self._fallback_parts.append(
            text
        )

        if (
            self._primary_depth
            > 0
        ):
            self._primary_parts.append(
                text
            )

    # =====================================================
    # TITLE
    # =====================================================

    @property
    def title(
        self,
    ) -> str | None:
        title = (
            " ".join(
                self._title_parts
            )
            .strip()
        )

        return (
            title
            or None
        )

    # =====================================================
    # CLEAN CONTENT
    # =====================================================

    def _clean_parts(
        self,
        parts: list[
            str
        ],
    ) -> str:
        raw = (
            "".join(
                parts
            )
        )

        lines: list[
            str
        ] = []

        previous_line: (
            str | None
        ) = None

        for line in (
            raw.splitlines()
        ):
            clean = (
                re.sub(
                    r"\s+",
                    " ",
                    line,
                )
                .strip()
            )

            if not clean:
                continue

            lowered = (
                clean
                .casefold()
            )

            if (
                lowered
                in self.NOISE_LINES
            ):
                continue

            if (
                previous_line
                is not None
                and lowered
                == previous_line
                .casefold()
            ):
                continue

            lines.append(
                clean
            )

            previous_line = clean

        return "\n".join(
            lines
        )

    # =====================================================
    # CONTENT
    # =====================================================

    @property
    def content(
        self,
    ) -> str:
        primary = (
            self._clean_parts(
                self._primary_parts
            )
        )

        if (
            len(primary)
            >= self.PRIMARY_MIN_CHARS
        ):
            return primary

        return (
            self._clean_parts(
                self._fallback_parts
            )
        )


# =========================================================
# PAGE READER
# =========================================================


class PageReader:
    MAX_BYTES = (
        1_500_000
    )

    MAX_TEXT_CHARS = (
        24_000
    )

    MAX_REDIRECTS = 5

    TIMEOUT_SECONDS = 12.0

    USER_AGENT = (
        "JARVIS-OS/1.0 "
        "(https://github.com/Chitra867/JARVIS-AI; "
        "local research assistant) "
        "httpx"
    )

    # =====================================================
    # READ
    # =====================================================

    def read(
        self,
        url: str,
    ) -> PageResource:
        current_url = (
            url
            .strip()
        )

        if not current_url:
            raise PageReadError(
                "Page URL is empty."
            )

        headers = {
            "User-Agent":
                self.USER_AGENT,

            "Accept":
                (
                    "text/html,"
                    "text/plain;"
                    "q=0.9,"
                    "application/xhtml+xml;"
                    "q=0.8"
                ),

            "Accept-Language":
                "en-US,en;q=0.9",

            "Accept-Encoding":
                "identity",

            "Cache-Control":
                "no-cache",
        }

        with httpx.Client(
            timeout=(
                self.TIMEOUT_SECONDS
            ),
            follow_redirects=False,
            headers=headers,
        ) as client:
            for _ in range(
                self.MAX_REDIRECTS
                + 1
            ):
                self._validate_public_url(
                    current_url
                )

                try:
                    response = (
                        self._request(
                            client=client,
                            url=current_url,
                        )
                    )

                except PageReadError:
                    raise

                except (
                    httpx.TimeoutException
                ) as error:
                    raise PageReadError(
                        (
                            "The webpage request "
                            "timed out."
                        )
                    ) from error

                except (
                    httpx.HTTPError
                ) as error:
                    raise PageReadError(
                        (
                            "Unable to download "
                            "the webpage."
                        )
                    ) from error

                if (
                    response.status_code
                    in {
                        301,
                        302,
                        303,
                        307,
                        308,
                    }
                ):
                    location = (
                        response
                        .headers
                        .get(
                            "location"
                        )
                    )

                    if not location:
                        raise PageReadError(
                            (
                                "Webpage redirect "
                                "has no destination."
                            )
                        )

                    current_url = (
                        urljoin(
                            current_url,
                            location,
                        )
                    )

                    continue

                if (
                    response.status_code
                    == 403
                ):
                    raise PageReadError(
                        (
                            "The webpage refused "
                            "automated access "
                            "(HTTP 403)."
                        )
                    )

                if (
                    response.status_code
                    == 429
                ):
                    raise PageReadError(
                        (
                            "The webpage temporarily "
                            "rate-limited JARVIS "
                            "(HTTP 429)."
                        )
                    )

                try:
                    response.raise_for_status()

                except (
                    httpx.HTTPStatusError
                ) as error:
                    raise PageReadError(
                        (
                            "The webpage returned "
                            f"HTTP "
                            f"{response.status_code}."
                        )
                    ) from error

                return (
                    self._build_page(
                        response=response,
                        url=current_url,
                    )
                )

        raise PageReadError(
            (
                "The webpage redirected "
                "too many times."
            )
        )

    # =====================================================
    # REQUEST WITH SIZE LIMIT
    # =====================================================

    def _request(
        self,
        client: httpx.Client,
        url: str,
    ) -> httpx.Response:
        request = (
            client.build_request(
                "GET",
                url,
            )
        )

        response = (
            client.send(
                request,
                stream=True,
            )
        )

        status_code = (
            response.status_code
        )

        original_headers = (
            response.headers
        )

        extensions = dict(
            response.extensions
        )

        content_length = (
            original_headers
            .get(
                "content-length"
            )
        )

        if content_length:
            try:
                declared_size = int(
                    content_length
                )

            except (
                TypeError,
                ValueError,
            ):
                declared_size = 0

            if (
                declared_size
                > self.MAX_BYTES
            ):
                response.close()

                raise PageReadError(
                    (
                        "The webpage is too "
                        "large to analyze."
                    )
                )

        chunks: list[
            bytes
        ] = []

        total = 0

        try:
            for chunk in (
                response
                .iter_bytes()
            ):
                if not chunk:
                    continue

                total += len(
                    chunk
                )

                if (
                    total
                    > self.MAX_BYTES
                ):
                    raise PageReadError(
                        (
                            "The webpage is too "
                            "large to analyze."
                        )
                    )

                chunks.append(
                    chunk
                )

        except (
            httpx.DecodingError
        ) as error:
            raise PageReadError(
                (
                    "Unable to decode the "
                    "webpage response."
                )
            ) from error

        finally:
            response.close()

        body = (
            b"".join(
                chunks
            )
        )

        excluded_headers = {
            "content-encoding",
            "content-length",
            "transfer-encoding",
        }

        clean_headers: list[
            tuple[
                str,
                str,
            ]
        ] = []

        for (
            header_name,
            header_value,
        ) in (
            original_headers
            .multi_items()
        ):
            if (
                header_name
                .lower()
                in excluded_headers
            ):
                continue

            clean_headers.append(
                (
                    header_name,
                    header_value,
                )
            )

        clean_headers.append(
            (
                "Content-Length",
                str(
                    len(
                        body
                    )
                ),
            )
        )

        return httpx.Response(
            status_code=(
                status_code
            ),
            headers=(
                clean_headers
            ),
            content=body,
            request=request,
            extensions=(
                extensions
            ),
        )

    # =====================================================
    # BUILD PAGE RESOURCE
    # =====================================================

    def _build_page(
        self,
        response: httpx.Response,
        url: str,
    ) -> PageResource:
        content_type = (
            response
            .headers
            .get(
                "content-type",
                "",
            )
            .lower()
        )

        if not (
            "text/html"
            in content_type

            or "text/plain"
            in content_type

            or "application/xhtml+xml"
            in content_type

            or not content_type
        ):
            raise PageReadError(
                (
                    "The selected result "
                    "is not a readable webpage."
                )
            )

        try:
            text = (
                response.text
            )

        except Exception as error:
            raise PageReadError(
                (
                    "Unable to decode "
                    "the webpage."
                )
            ) from error

        title: (
            str | None
        ) = None

        looks_like_html = (
            "text/html"
            in content_type

            or "application/xhtml+xml"
            in content_type

            or "<html"
            in text[
                :2000
            ].lower()

            or "<!doctype html"
            in text[
                :2000
            ].lower()
        )

        if looks_like_html:
            parser = (
                ReadableHTMLParser()
            )

            try:
                parser.feed(
                    text
                )

                parser.close()

            except Exception as error:
                raise PageReadError(
                    (
                        "Unable to parse "
                        "the webpage."
                    )
                ) from error

            title = (
                parser.title
            )

            content = (
                parser.content
            )

        else:
            content = (
                re.sub(
                    r"\s+",
                    " ",
                    text,
                )
                .strip()
            )

        content = (
            content[
                :self.MAX_TEXT_CHARS
            ]
            .strip()
        )

        if not content:
            raise PageReadError(
                (
                    "The webpage contains "
                    "no readable text."
                )
            )

        return PageResource(
            url=url,
            title=title,
            content=content,
        )

    # =====================================================
    # URL SAFETY
    # =====================================================

    def _validate_public_url(
        self,
        url: str,
    ) -> None:
        try:
            parsed = (
                urlparse(
                    url
                )
            )

        except ValueError as error:
            raise PageReadError(
                "Invalid webpage URL."
            ) from error

        if (
            parsed.scheme
            not in {
                "http",
                "https",
            }
        ):
            raise PageReadError(
                (
                    "Only HTTP and HTTPS "
                    "pages are allowed."
                )
            )

        if (
            parsed.username
            or parsed.password
        ):
            raise PageReadError(
                (
                    "Web addresses containing "
                    "credentials are not allowed."
                )
            )

        hostname = (
            parsed.hostname
            or ""
        ).strip().lower()

        if not hostname:
            raise PageReadError(
                (
                    "Webpage hostname "
                    "is missing."
                )
            )

        if hostname in {
            "localhost",
            "localhost.localdomain",
        }:
            raise PageReadError(
                (
                    "Local network pages "
                    "cannot be analyzed."
                )
            )

        if hostname.endswith(
            ".local"
        ):
            raise PageReadError(
                (
                    "Local network pages "
                    "cannot be analyzed."
                )
            )

        try:
            port = (
                parsed.port
            )

        except ValueError as error:
            raise PageReadError(
                (
                    "Invalid webpage port."
                )
            ) from error

        if port is not None:
            expected_port = (
                443
                if (
                    parsed.scheme
                    == "https"
                )
                else 80
            )

            if (
                port
                != expected_port
            ):
                raise PageReadError(
                    (
                        "Non-standard webpage "
                        "ports are not allowed."
                    )
                )

        self._validate_hostname_ips(
            hostname
        )

    # =====================================================
    # DNS / IP SAFETY
    # =====================================================

    def _validate_hostname_ips(
        self,
        hostname: str,
    ) -> None:
        try:
            literal_ip = (
                ipaddress
                .ip_address(
                    hostname
                )
            )

        except ValueError:
            literal_ip = None

        if (
            literal_ip
            is not None
        ):
            if not (
                self._is_public_ip(
                    literal_ip
                )
            ):
                raise PageReadError(
                    (
                        "Local or private network "
                        "addresses are not allowed."
                    )
                )

            return

        try:
            addresses = (
                socket
                .getaddrinfo(
                    hostname,
                    None,
                    type=(
                        socket
                        .SOCK_STREAM
                    ),
                )
            )

        except (
            socket.gaierror
        ) as error:
            raise PageReadError(
                (
                    "Unable to resolve "
                    "the webpage hostname."
                )
            ) from error

        if not addresses:
            raise PageReadError(
                (
                    "The webpage hostname "
                    "could not be resolved."
                )
            )

        for address_info in (
            addresses
        ):
            raw_ip = (
                address_info[
                    4
                ][
                    0
                ]
            )

            try:
                address = (
                    ipaddress
                    .ip_address(
                        raw_ip
                    )
                )

            except ValueError:
                continue

            if not (
                self._is_public_ip(
                    address
                )
            ):
                raise PageReadError(
                    (
                        "The webpage resolves "
                        "to a private or local "
                        "network address."
                    )
                )

    # =====================================================
    # PUBLIC IP CHECK
    # =====================================================

    def _is_public_ip(
        self,
        address:
            ipaddress.IPv4Address
            | ipaddress.IPv6Address,
    ) -> bool:
        return not (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_multicast
            or address.is_reserved
            or address.is_unspecified
        )


page_reader = (
    PageReader()
)