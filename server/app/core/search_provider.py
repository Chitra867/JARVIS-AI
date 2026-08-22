from abc import ABC, abstractmethod
from urllib.parse import urlparse

from app.core.task_runtime import (
    SearchResult,
)


class SearchProviderError(
    RuntimeError
):
    pass


class SearchProvider(ABC):
    """
    Base contract for structured search providers.

    A provider performs a search and returns concrete
    SearchResult objects instead of only opening a browser.
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
                "Search provider must have a name."
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

        return self._providers.get(
            normalized
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
                    "No structured search provider "
                    f"is registered for "
                    f"'{provider_name}'."
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
                    "Structured search provider "
                    "failed."
                )
            ) from error

        return self._sanitize_results(
            raw_results,
            limit=limit,
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

        for result in results:
            url = (
                result.url
                .strip()
            )

            if not self._is_safe_url(
                url
            ):
                continue

            normalized_url = (
                url.lower()
            )

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
                len(clean_results)
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

        if (
            parsed.scheme
            not in {
                "http",
                "https",
            }
        ):
            return False

        return bool(
            parsed.netloc
        )


search_provider_registry = (
    SearchProviderRegistry()
)