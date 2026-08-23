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
    IGNORE_TAGS = {
        "script",
        "style",
        "noscript",
        "svg",
        "canvas",
        "template",
    }

    BLOCK_TAGS = {
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "footer",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "li",
        "main",
        "nav",
        "p",
        "section",
        "table",
        "td",
        "th",
        "tr",
    }

    def __init__(
        self,
    ) -> None:
        super().__init__(
            convert_charrefs=True,
        )

        self._ignored_depth = 0
        self._title_depth = 0

        self._title_parts: list[
            str
        ] = []

        self._parts: list[
            str
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
        del attrs

        normalized = (
            tag
            .strip()
            .lower()
        )

        if (
            normalized
            in self.IGNORE_TAGS
        ):
            self._ignored_depth += 1

            return

        if self._ignored_depth:
            return

        if normalized == "title":
            self._title_depth += 1

        if (
            normalized
            in self.BLOCK_TAGS
        ):
            self._parts.append(
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

        if (
            normalized
            in self.IGNORE_TAGS
        ):
            if self._ignored_depth:
                self._ignored_depth -= 1

            return

        if self._ignored_depth:
            return

        if (
            normalized == "title"
            and self._title_depth
        ):
            self._title_depth -= 1

        if (
            normalized
            in self.BLOCK_TAGS
        ):
            self._parts.append(
                "\n"
            )

    # =====================================================
    # TEXT
    # =====================================================

    def handle_data(
        self,
        data: str,
    ) -> None:
        if self._ignored_depth:
            return

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

        self._parts.append(
            text
        )

        self._parts.append(
            " "
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
    # CONTENT
    # =====================================================

    @property
    def content(
        self,
    ) -> str:
        raw = (
            "".join(
                self._parts
            )
        )

        lines: list[
            str
        ] = []

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

            if clean:
                lines.append(
                    clean
                )

        return "\n".join(
            lines
        )


# =========================================================
# PAGE READER
# =========================================================


class PageReader:
    # Maximum decoded webpage body.
    MAX_BYTES = (
        1_500_000
    )

    # Maximum readable text sent toward the AI.
    MAX_TEXT_CHARS = (
        24_000
    )

    MAX_REDIRECTS = 5

    TIMEOUT_SECONDS = 12.0

    # -----------------------------------------------------
    # Identify JARVIS honestly as an automated client.
    # -----------------------------------------------------

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

            # Prefer plain responses.
            #
            # Some servers may still return compressed
            # content, so _request() also handles that
            # safely.
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
                # -----------------------------------------
                # Every redirect destination is validated
                # before JARVIS connects to it.
                # -----------------------------------------

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

                # =========================================
                # REDIRECT
                # =========================================

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

                # =========================================
                # SPECIAL HTTP STATUS
                # =========================================

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

                # =========================================
                # GENERAL HTTP STATUS
                # =========================================

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

        # Capture metadata before closing the streamed
        # response.
        status_code = (
            response.status_code
        )

        original_headers = (
            response.headers
        )

        extensions = dict(
            response.extensions
        )

        # -------------------------------------------------
        # EARLY SIZE CHECK
        # -------------------------------------------------
        #
        # Content-Length can refer to compressed bytes.
        # It is therefore only an early guard.
        #
        # The decoded size is checked again while reading.
        # -------------------------------------------------

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
            # -------------------------------------------------
            # IMPORTANT:
            #
            # iter_bytes() returns decoded/decompressed bytes.
            #
            # Therefore Content-Encoding MUST NOT be copied
            # into the reconstructed response below.
            # -------------------------------------------------

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

        # -------------------------------------------------
        # CLEAN RESPONSE HEADERS
        # -------------------------------------------------
        #
        # The body is already decoded.
        #
        # Retaining Content-Encoding such as:
        #
        #   gzip
        #   deflate
        #   br
        #
        # would make httpx decode the body a SECOND time.
        # -------------------------------------------------

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

        # This length now describes the decoded body.
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

        # -------------------------------------------------
        # RECONSTRUCT BUFFERED RESPONSE
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Only readable textual resources.
        # -------------------------------------------------

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

        # -------------------------------------------------
        # HTML
        # -------------------------------------------------

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

        # -------------------------------------------------
        # PLAIN TEXT
        # -------------------------------------------------

        else:
            content = (
                re.sub(
                    r"\s+",
                    " ",
                    text,
                )
                .strip()
            )

        # -------------------------------------------------
        # LIMIT CONTENT SENT TO OLLAMA
        # -------------------------------------------------

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
    # SAFE PUBLIC URL
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

        # -------------------------------------------------
        # ONLY HTTP / HTTPS
        # -------------------------------------------------

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

        # -------------------------------------------------
        # BLOCK EMBEDDED CREDENTIALS
        #
        # https://user:password@example.com
        # -------------------------------------------------

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

        # -------------------------------------------------
        # LOCALHOST
        # -------------------------------------------------

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

        # -------------------------------------------------
        # PORT RESTRICTION
        # -------------------------------------------------

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

        # -------------------------------------------------
        # DNS / SSRF PROTECTION
        # -------------------------------------------------

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
        # -------------------------------------------------
        # LITERAL IP
        # -------------------------------------------------

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

        # -------------------------------------------------
        # DNS LOOKUP
        # -------------------------------------------------

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

        # -------------------------------------------------
        # FAIL CLOSED
        #
        # If ANY DNS result resolves to a private/local
        # address, do not fetch the page.
        # -------------------------------------------------

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