import unittest

from app.core.search_provider import (
    SearchProvider,
    SearchProviderError,
    SearchProviderRegistry,
)

from app.core.task_runtime import (
    SearchResult,
)


class FakeSearchProvider(
    SearchProvider
):
    name = "fake"

    def __init__(
        self,
        results: tuple[
            SearchResult,
            ...
        ] = (),
    ) -> None:
        self.results = results

        self.calls: list[
            tuple[
                str,
                int,
            ]
        ] = []

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> tuple[
        SearchResult,
        ...
    ]:
        self.calls.append(
            (
                query,
                limit,
            )
        )

        return self.results


class BrokenSearchProvider(
    SearchProvider
):
    name = "broken"

    def search(
        self,
        query: str,
        limit: int = 5,
    ) -> tuple[
        SearchResult,
        ...
    ]:
        raise RuntimeError(
            "provider failure"
        )


class SearchProviderRegistryTests(
    unittest.TestCase
):
    def setUp(self) -> None:
        self.registry = (
            SearchProviderRegistry()
        )

    # ==================================================
    # REGISTER / LOOKUP
    # ==================================================

    def test_provider_can_be_registered(
        self,
    ) -> None:
        provider = (
            FakeSearchProvider()
        )

        self.registry.register(
            provider
        )

        self.assertTrue(
            self.registry
            .has_provider(
                "fake"
            )
        )

        self.assertIs(
            self.registry.get(
                "FAKE"
            ),
            provider,
        )

    # ==================================================
    # MISSING PROVIDER
    # ==================================================

    def test_missing_provider_is_rejected(
        self,
    ) -> None:
        with self.assertRaises(
            SearchProviderError
        ):
            self.registry.search(
                "missing",
                "FastAPI",
            )

    # ==================================================
    # STRUCTURED RESULTS
    # ==================================================

    def test_search_returns_results(
        self,
    ) -> None:
        provider = (
            FakeSearchProvider(
                results=(
                    SearchResult(
                        title="FastAPI",
                        url=(
                            "https://fastapi.tiangolo.com/"
                        ),
                    ),
                )
            )
        )

        self.registry.register(
            provider
        )

        results = (
            self.registry
            .search(
                "fake",
                "FastAPI",
            )
        )

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0].title,
            "FastAPI",
        )

        self.assertEqual(
            provider.calls,
            [
                (
                    "FastAPI",
                    5,
                )
            ],
        )

    # ==================================================
    # UNSAFE URL FILTERING
    # ==================================================

    def test_unsafe_urls_are_removed(
        self,
    ) -> None:
        provider = (
            FakeSearchProvider(
                results=(
                    SearchResult(
                        title="Unsafe",
                        url=(
                            "javascript:alert(1)"
                        ),
                    ),
                    SearchResult(
                        title="Safe",
                        url=(
                            "https://example.com/"
                        ),
                    ),
                )
            )
        )

        self.registry.register(
            provider
        )

        results = (
            self.registry
            .search(
                "fake",
                "test",
            )
        )

        self.assertEqual(
            len(results),
            1,
        )

        self.assertEqual(
            results[0].url,
            "https://example.com/",
        )

    # ==================================================
    # DUPLICATE / LIMIT
    # ==================================================

    def test_duplicates_and_limit_are_enforced(
        self,
    ) -> None:
        provider = (
            FakeSearchProvider(
                results=(
                    SearchResult(
                        title="One",
                        url="https://one.example/",
                    ),
                    SearchResult(
                        title="Duplicate",
                        url="https://one.example/",
                    ),
                    SearchResult(
                        title="Two",
                        url="https://two.example/",
                    ),
                    SearchResult(
                        title="Three",
                        url="https://three.example/",
                    ),
                )
            )
        )

        self.registry.register(
            provider
        )

        results = (
            self.registry
            .search(
                "fake",
                "test",
                limit=2,
            )
        )

        self.assertEqual(
            len(results),
            2,
        )

        self.assertEqual(
            results[0].url,
            "https://one.example/",
        )

        self.assertEqual(
            results[1].url,
            "https://two.example/",
        )

    # ==================================================
    # PROVIDER FAILURE
    # ==================================================

    def test_provider_exception_is_wrapped(
        self,
    ) -> None:
        self.registry.register(
            BrokenSearchProvider()
        )

        with self.assertRaises(
            SearchProviderError
        ):
            self.registry.search(
                "broken",
                "FastAPI",
            )


if __name__ == "__main__":
    unittest.main()
    