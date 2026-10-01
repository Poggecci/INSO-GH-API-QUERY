"""Regression tests: the charts module must expose every function the
entry points import. The scatter rework silently dropped
writeCumulativeTimelineChart, which only surfaced as an ImportError in
student repos' Actions runs — the test suite never imported the entry
point module. These tests close that gap."""


def test_charts_module_exposes_all_writers():
    from src.io.charts import (  # noqa: F401
        getChartUrl,
        writeCycleLeadTimeChart,
        writeCumulativeTimelineChart,
        writeIndexPage,
    )


def test_entry_point_module_imports():
    import src.generateMilestoneMetricsForActions  # noqa: F401
