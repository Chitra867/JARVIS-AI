import ipaddress
import re
import webbrowser

from urllib.parse import (
    urlparse,
)

from app.core.task_context import (
    ReferenceType,
)

from app.core.task_runtime import (
    PageResource,
    ReferenceResolution,
    RuntimeOutputType,
    SearchResult,
    StepRuntimeOutput,
)

from app.skills.base import (
    Skill,
)


class PageOpenSkill(
    Skill
):
    # =====================================================
    # REFERENCE COMMAND
    # =====================================================

    FIRST_RESULT_PATTERN = re.compile(
        (
            r"^open\s+"
            r"(?:the\s+)?"
            r"(?:first|top)\s+"
            r"(?:search\s+)?"
            r"result"
            r"\s*[.!?]*$"
        ),
        flags=re.IGNORECASE,
    )

    # =====================================================
    # ROUTING
    # =====================================================

    def can_handle(
        self,
        command: str,
    ) -> bool:
        normalized = (
            command
            .strip()
        )

        lowered = (
            normalized
            .lower()
        )

        return (
            bool(
                self
                .FIRST_RESULT_PATTERN
                .match(
                    normalized
                )
            )
            or lowered.startswith(
                "open http://"
            )
            or lowered.startswith(
                "open https://"
            )
        )

    # =====================================================
    # NORMAL EXECUTION
    # =====================================================
    #
    # Direct URL:
    #
    # open https://example.com
    #
    # Context commands such as:
    #
    # open the first result
    #
    # must go through execute_with_references().
    # =====================================================

    def execute(
        self,
        command: str,
    ) -> str:
        url = (
            self._extract_direct_url(
                command
            )
        )

        if not url:
            return (
                "Unable to resolve the page "
                "to open."
            )

        _, response = (
            self._open_url(
                url=url,
                title=None,
            )
        )

        return response

    # =====================================================
    # EXECUTE WITH RUNTIME REFERENCES
    # =====================================================

    def execute_with_references(
        self,
        step_index: int,
        command: str,
        resolutions: tuple[
            ReferenceResolution,
            ...
        ],
    ) -> tuple[
        str,
        StepRuntimeOutput | None,
    ]:
        del command

        for resolution in (
            resolutions
        ):
            if not resolution.resolved:
                continue

            if (
                resolution
                .reference
                .reference_type
                != ReferenceType
                .FIRST_SEARCH_RESULT
            ):
                continue

            value = (
                resolution.value
            )

            if not isinstance(
                value,
                SearchResult,
            ):
                continue

            opened, response = (
                self._open_url(
                    url=value.url,
                    title=value.title,
                )
            )

            if not opened:
                return (
                    response,
                    None,
                )

            runtime_output = (
                StepRuntimeOutput(
                    step_index=(
                        step_index
                    ),
                    output_type=(
                        RuntimeOutputType
                        .PAGE
                    ),
                    text=response,
                    page=PageResource(
                        url=value.url,
                        title=(
                            value.title
                            or None
                        ),
                        content=None,
                    ),
                )
            )

            return (
                response,
                runtime_output,
            )

        return (
            (
                "Unable to resolve the "
                "search result to open."
            ),
            None,
        )

    # =====================================================
    # DIRECT URL RUNTIME OUTPUT
    # =====================================================

    def build_runtime_output(
        self,
        step_index: int,
        command: str,
        response: str,
    ) -> StepRuntimeOutput:
        url = (
            self._extract_direct_url(
                command
            )
        )

        if (
            url
            and self._is_safe_url(
                url
            )
        ):
            return StepRuntimeOutput(
                step_index=(
                    step_index
                ),
                output_type=(
                    RuntimeOutputType.PAGE
                ),
                text=response,
                page=PageResource(
                    url=url,
                    content=None,
                ),
            )

        return StepRuntimeOutput(
            step_index=step_index,
            output_type=(
                RuntimeOutputType.TEXT
            ),
            text=response,
        )

    # =====================================================
    # DIRECT URL PARSER
    # =====================================================

    def _extract_direct_url(
        self,
        command: str,
    ) -> str | None:
        stripped = (
            command
            .strip()
        )

        lowered = (
            stripped
            .lower()
        )

        if not (
            lowered.startswith(
                "open http://"
            )
            or lowered.startswith(
                "open https://"
            )
        ):
            return None

        _, _, raw_url = (
            stripped.partition(
                " "
            )
        )

        url = (
            raw_url
            .strip()
            .rstrip(
                "."
            )
        )

        return (
            url
            or None
        )

    # =====================================================
    # OPEN URL
    # =====================================================

    def _open_url(
        self,
        url: str,
        title: str | None,
    ) -> tuple[
        bool,
        str,
    ]:
        clean_url = (
            url
            .strip()
        )

        if not self._is_safe_url(
            clean_url
        ):
            return (
                False,
                (
                    "Unable to open an unsafe "
                    "or invalid web address."
                ),
            )

        try:
            opened = (
                webbrowser
                .open(
                    clean_url
                )
            )

        except Exception:
            return (
                False,
                (
                    "I couldn't open "
                    "the web page."
                ),
            )

        if not opened:
            return (
                False,
                (
                    "I couldn't open "
                    "the web page."
                ),
            )

        clean_title = (
            title.strip()
            if title
            else ""
        )

        if clean_title:
            return (
                True,
                (
                    "Opening "
                    f"{clean_title}."
                ),
            )

        return (
            True,
            (
                "Opening the "
                "web page."
            ),
        )

    # =====================================================
    # SAFE URL
    # =====================================================

    def _is_safe_url(
        self,
        url: str,
    ) -> bool:
        if not url:
            return False

        try:
            parsed = (
                urlparse(
                    url
                )
            )

        except ValueError:
            return False

        if (
            parsed.scheme
            not in {
                "http",
                "https",
            }
        ):
            return False

        hostname = (
            parsed.hostname
            or ""
        ).strip().lower()

        if not hostname:
            return False

        if hostname in {
            "localhost",
            "localhost.localdomain",
        }:
            return False

        if hostname.endswith(
            ".local"
        ):
            return False

        try:
            address = (
                ipaddress
                .ip_address(
                    hostname
                )
            )

        except ValueError:
            address = None

        if (
            address is not None
            and (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_multicast
                or address.is_reserved
                or address.is_unspecified
            )
        ):
            return False

        return True