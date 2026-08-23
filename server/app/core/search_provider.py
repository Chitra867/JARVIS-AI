import ipaddress

from abc import (
    ABC,
    abstractmethod,
)

from urllib.parse import (
    urlparse,
)

from ddgs import (
    DDGS,
)

from ddgs.exceptions import (
    DDGSException,
    RatelimitException,
    TimeoutException,
)

from app.core.task_runtime import (
    SearchResult,
)


# =========================================================
# ERRORS
# =========================================================


class SearchProviderError(
    RuntimeError
):
    """
    Raised when a structured search provider cannot
    complete a search safely or successfully.
    """

    pass


# =========================================================
# BASE PROVIDER
# =========================================================


class SearchProvider(
    ABC
):
    """
    Base contract for structured search providers.

    Providers return concrete SearchResult objects
    instead of only opening a browser.
    """

    name: str

    @abstractmethod
    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> tuple[
        SearchResult,
        ...
    ]:
        raise NotImplementedError


# =========================================================
# DDGS SEARCH PROVIDER
# =========================================================


class DDGSSearchProvider(
    SearchProvider
):
    """
    Free structured web-search provider using DDGS.

    No API key is required.

    DDGS can query multiple public search backends and
    returns structured results containing title and URL.
    """

    name = "ddgs"

    def __init__(
        self,
        timeout_seconds: int = 10,
        region: str = "us-en",
        safesearch: str = "moderate",
        backend: str = "auto",
    ) -> None:
        self._timeout_seconds = max(
            1,
            int(
                timeout_seconds
            ),
        )

        self._region = (
            region.strip()
            or "us-en"
        )

        self._safesearch = (
            safesearch.strip()
            or "moderate"
        )

        self._backend = (
            backend.strip()
            or "auto"
        )

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> tuple[
        SearchResult,
        ...
    ]:
        clean_query = (
            query
            .strip()
        )

        if not clean_query:
            return ()

        if limit <= 0:
            return ()

        # Keep structured searches small and predictable.
        result_limit = min(
            max(
                int(
                    limit
                ),
                1,
            ),
            20,
        )

        try:
            engine = DDGS(
                timeout=(
                    self._timeout_seconds
                ),
            )

            raw_results = (
                engine.text(
                    query=clean_query,
                    region=(
                        self._region
                    ),
                    safesearch=(
                        self._safesearch
                    ),
                    max_results=(
                        result_limit
                    ),
                    backend=(
                        self._backend
                    ),
                )
            )

        except TimeoutException as error:
            raise SearchProviderError(
                (
                    "Structured web search "
                    "timed out."
                )
            ) from error

        except RatelimitException as error:
            raise SearchProviderError(
                (
                    "Structured web search "
                    "was temporarily rate limited."
                )
            ) from error

        except DDGSException as error:
            raise SearchProviderError(
                (
                    "Structured web search "
                    "failed."
                )
            ) from error

        except Exception as error:
            raise SearchProviderError(
                (
                    "Unexpected structured "
                    "search failure."
                )
            ) from error

        if not raw_results:
            return ()

        results: list[
            SearchResult
        ] = []

        for raw_result in (
            raw_results
        ):
            if not isinstance(
                raw_result,
                dict,
            ):
                continue

            title = str(
                raw_result.get(
                    "title",
                    "",
                )
            ).strip()

            # DDGS text results use "href"
            # for the result URL.
            url = str(
                raw_result.get(
                    "href",
                    "",
                )
            ).strip()

            if not url:
                continue

            results.append(
                SearchResult(
                    title=(
                        title
                        or url
                    ),
                    url=url,
                )
            )

            if (
                len(
                    results
                )
                >= result_limit
            ):
                break

        return tuple(
            results
        )


# =========================================================
# PROVIDER REGISTRY
# =========================================================


class SearchProviderRegistry:
    def __init__(
        self,
    ) -> None:
        self._providers: dict[
            str,
            SearchProvider,
        ] = {}

    # ==================================================
    # REGISTER
    # ==================================================

    def register(
        self,
        provider: SearchProvider,
    ) -> None:
        name = (
            str(
                provider.name
            )
            .strip()
            .lower()
        )

        if not name:
            raise ValueError(
                (
                    "Search provider must "
                    "have a name."
                )
            )

        self._providers[
            name
        ] = provider

    # ==================================================
    # AVAILABLE
    # ==================================================

    def has_provider(
        self,
        name: str,
    ) -> bool:
        normalized = (
            name
            .strip()
            .lower()
        )

        return (
            normalized
            in self._providers
        )

    # ==================================================
    # GET PROVIDER
    # ==================================================

    def get(
        self,
        name: str,
    ) -> SearchProvider | None:
        normalized = (
            name
            .strip()
            .lower()
        )

        return (
            self._providers
            .get(
                normalized
            )
        )

    # ==================================================
    # SEARCH
    # ==================================================

    def search(
        self,
        provider_name: str,
        query: str,
        limit: int = 5,
    ) -> tuple[
        SearchResult,
        ...
    ]:
        provider = (
            self.get(
                provider_name
            )
        )

        if provider is None:
            raise SearchProviderError(
                (
                    "No structured search "
                    "provider is registered "
                    f"for '{provider_name}'."
                )
            )

        clean_query = (
            query
            .strip()
        )

        if not clean_query:
            return ()

        if limit <= 0:
            return ()

        try:
            raw_results = (
                provider.search(
                    clean_query,
                    limit=limit,
                )
            )

        except SearchProviderError:
            raise

        except Exception as error:
            raise SearchProviderError(
                (
                    "Structured search "
                    "provider failed."
                )
            ) from error

        return (
            self._sanitize_results(
                raw_results,
                limit=limit,
            )
        )

    # ==================================================
    # SANITIZE RESULTS
    # ==================================================

    def _sanitize_results(
        self,
        results: tuple[
            SearchResult,
            ...
        ],
        limit: int,
    ) -> tuple[
        SearchResult,
        ...
    ]:
        clean_results: list[
            SearchResult
        ] = []

        seen_urls: set[
            str
        ] = set()

        if limit <= 0:
            return ()

        for result in results:
            url = (
                result.url
                .strip()
            )

            if not self._is_safe_url(
                url
            ):
                continue

            # Remove URL fragments so links to the same
            # page are treated as duplicates.
            try:
                parsed = (
                    urlparse(
                        url
                    )
                )

                normalized_url = (
                    parsed
                    ._replace(
                        fragment="",
                    )
                    .geturl()
                    .lower()
                )

            except ValueError:
                continue

            if (
                normalized_url
                in seen_urls
            ):
                continue

            seen_urls.add(
                normalized_url
            )

            title = (
                result.title
                .strip()
            )

            if not title:
                title = url

            clean_results.append(
                SearchResult(
                    title=title,
                    url=url,
                )
            )

            if (
                len(
                    clean_results
                )
                >= limit
            ):
                break

        return tuple(
            clean_results
        )

    # ==================================================
    # SAFE URL
    # ==================================================

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

        # Only normal web URLs are acceptable.
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

        # Explicit localhost names.
        if hostname in {
            "localhost",
            "localhost.localdomain",
        }:
            return False

        # Local-network mDNS names.
        if hostname.endswith(
            ".local"
        ):
            return False

        # -------------------------------------------------
        # BLOCK LITERAL PRIVATE / LOCAL IP ADDRESSES
        # -------------------------------------------------

        try:
            address = (
                ipaddress
                .ip_address(
                    hostname
                )
            )

        except ValueError:
            # Normal domain name.
            address = None

        if address is not None:
            if (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_multicast
                or address.is_reserved
                or address.is_unspecified
            ):
                return False

        return True


# =========================================================
# GLOBAL REGISTRY
# =========================================================


search_provider_registry = (
    SearchProviderRegistry()
)


# =========================================================
# REGISTER PROVIDERS
# =========================================================


search_provider_registry.register(
    DDGSSearchProvider()
)