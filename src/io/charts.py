import json
import logging
import os
from src.utils.models import MilestoneData


def getChartUrl(pages_base_url: str, html_filename: str) -> str:
    """Build the full GitHub Pages URL for a chart file."""
    base = pages_base_url.rstrip("/")
    return f"{base}/metrics/{html_filename}"


def writeIndexPage(
    chart_files: list[tuple[str, str]],
    index_file_path: str,
    logger: logging.Logger | None = None,
):
    """
    Generates an index.html landing page listing all available chart files.

    Args:
        chart_files: List of (display_name, html_filename) tuples
        index_file_path: Path to write the index.html file
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    items_html = "\n".join(
        f'        <li><a href="metrics/{fname}">{name}</a></li>'
        for name, fname in chart_files
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Interactive Metrics Charts</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 40px;
            background: #f6f8fa;
            color: #1f2328;
        }}
        h1 {{ font-size: 1.5rem; }}
        ul {{ list-style: none; padding: 0; }}
        li {{
            margin: 0.5rem 0;
            padding: 0.75rem 1rem;
            background: #fff;
            border: 1px solid #d0d7de;
            border-radius: 6px;
        }}
        a {{ color: #0969da; text-decoration: none; font-weight: 500; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>📊 Interactive Metrics Charts</h1>
    <ul>
{items_html}
    </ul>
</body>
</html>"""

    with open(index_file_path, mode="w") as f:
        f.write(html)
    logger.info(f"Index page written to {index_file_path}")


def writeCycleLeadTimeChart(
    milestone_data: MilestoneData,
    html_file_path: str,
    logger: logging.Logger | None = None,
):
    """
    Generates an interactive HTML file with Chart.js showing cycle time and lead time
    graphs across the milestone. Includes developer checkboxes and aggregation toggle.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    # Build data structure for the chart
    developers = list(milestone_data.devMetrics.keys())
    all_issues = set()
    for dev in developers:
        for issue_num, cycle, lead in milestone_data.devMetrics[dev].issueTimings:
            all_issues.add(issue_num)
    issue_numbers = sorted([i for i in all_issues if i is not None])

    # For each issue, store per-developer cycle and lead times
    chart_data = {dev: {"cycle": {}, "lead": {}} for dev in developers}
    for dev in developers:
        for issue_num, cycle, lead in milestone_data.devMetrics[dev].issueTimings:
            if issue_num is not None:
                chart_data[dev]["cycle"][issue_num] = cycle
                chart_data[dev]["lead"][issue_num] = lead

    html_content = _generate_chart_html(
        developers=developers,
        issue_numbers=issue_numbers,
        chart_data=chart_data,
        milestone_start=milestone_data.startDate.strftime("%Y-%m-%d"),
        milestone_end=milestone_data.endDate.strftime("%Y-%m-%d"),
    )

    with open(html_file_path, mode="w") as f:
        f.write(html_content)
    logger.info(f"Cycle/lead time chart written to {html_file_path}")


def _generate_chart_html(
    developers: list[str],
    issue_numbers: list[int],
    chart_data: dict,
    milestone_start: str,
    milestone_end: str,
) -> str:
    json_data = json.dumps(
        {
            "developers": developers,
            "issueNumbers": issue_numbers,
            "chartData": chart_data,
        }
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cycle Time & Lead Time — {milestone_start} to {milestone_end}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            margin: 20px;
            background: #f6f8fa;
            color: #1f2328;
        }}
        h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; }}
        .subtitle {{ color: #656d76; margin-bottom: 1rem; }}
        .controls {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 1rem;
            align-items: center;
        }}
        .dev-checkboxes {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-bottom: 1rem;
        }}
        .dev-chip {{
            display: inline-flex;
            align-items: center;
            gap: 0.25rem;
            background: #fff;
            border: 1px solid #d0d7de;
            border-radius: 999px;
            padding: 0.25rem 0.66rem;
            font-size: 0.85rem;
            cursor: pointer;
            user-select: none;
            transition: background 0.15s;
        }}
        .dev-chip:hover {{ background: #f3f4f6; }}
        .dev-chip input {{ margin: 0; cursor: pointer; }}
        .dev-chip.checked {{
            background: #ddf4ff;
            border-color: #54aeff;
            color: #0969da;
        }}
        .agg-toggle {{
            display: inline-flex;
            border: 1px solid #d0d7de;
            border-radius: 6px;
            overflow: hidden;
        }}
        .agg-toggle button {{
            border: none;
            padding: 0.4rem 0.9rem;
            background: #fff;
            cursor: pointer;
            font-size: 0.85rem;
            transition: background 0.15s;
        }}
        .agg-toggle button.active {{
            background: #0969da;
            color: #fff;
        }}
        .chart-container {{
            background: #fff;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .chart-container h2 {{ font-size: 1.1rem; margin: 0 0 0.5rem 0; }}
        .chart-wrapper {{ position: relative; height: 350px; }}
        .actions {{ display: flex; gap: 0.5rem; align-items: center; }}
    </style>
</head>
<body>
    <h1>⏱️ Cycle Time & Lead Time</h1>
    <p class="subtitle">Milestone: {milestone_start} → {milestone_end}</p>

    <div class="controls">
        <div class="agg-toggle">
            <button id="agg-avg" class="active" onclick="setAggregation('avg')">Average</button>
            <button id="agg-sum" onclick="setAggregation('sum')">Sum</button>
        </div>
        <button onclick="selectAll(true)" style="font-size:0.85rem;border:1px solid #d0d7de;border-radius:6px;padding:0.4rem 0.8rem;background:#fff;cursor:pointer;">Select All</button>
        <button onclick="selectAll(false)" style="font-size:0.85rem;border:1px solid #d0d7de;border-radius:6px;padding:0.4rem 0.8rem;background:#fff;cursor:pointer;">Deselect All</button>
    </div>

    <div class="dev-checkboxes" id="dev-checkboxes"></div>

    <div class="chart-container">
        <h2>Cycle Time (Assignment → Closure)</h2>
        <div class="chart-wrapper"><canvas id="cycleChart"></canvas></div>
    </div>

    <div class="chart-container">
        <h2>Lead Time (Creation → Closure)</h2>
        <div class="chart-wrapper"><canvas id="leadChart"></canvas></div>
    </div>

    <script>
        const rawData = {json_data};
        let aggregation = 'avg';
        let selectedDevs = new Set(rawData.developers);
        let cycleChart, leadChart;

        const COLORS = [
            '#0969da', '#1a7f37', '#bf3989', '#d1242f', '#9333ea',
            '#ca8a04', '#0891b2', '#4a154b', '#2d33be', '#bc4b00'
        ];

        function devColor(i) {{
            return COLORS[i % COLORS.length];
        }}

        function renderCheckboxes() {{
            const container = document.getElementById('dev-checkboxes');
            container.innerHTML = '';
            rawData.developers.forEach((dev, i) => {{
                const chip = document.createElement('label');
                chip.className = 'dev-chip' + (selectedDevs.has(dev) ? ' checked' : '');
                chip.innerHTML = `<input type="checkbox" ${{selectedDevs.has(dev) ? 'checked' : ''}} onchange="toggleDev('${{dev}}')"><span style="width:10px;height:10px;border-radius:50%;background:${{devColor(i)}};display:inline-block;"></span>${{dev}}`;
                container.appendChild(chip);
            }});
        }}

        function toggleDev(dev) {{
            if (selectedDevs.has(dev)) selectedDevs.delete(dev);
            else selectedDevs.add(dev);
            renderCheckboxes();
            updateCharts();
        }}

        function selectAll(on) {{
            selectedDevs = on ? new Set(rawData.developers) : new Set();
            renderCheckboxes();
            updateCharts();
        }}

        function setAggregation(agg) {{
            aggregation = agg;
            document.getElementById('agg-avg').classList.toggle('active', agg === 'avg');
            document.getElementById('agg-sum').classList.toggle('active', agg === 'sum');
            updateCharts();
        }}

        function buildDatasets(metric) {{
            const labels = rawData.issueNumbers.map(n => '#' + n);
            const datasets = [];
            const selectedDevsArray = rawData.developers.filter((d, i) => selectedDevs.has(d));
            if (selectedDevsArray.length === 0) return {{ labels, datasets }};
            const values = rawData.issueNumbers.map(issueNum => {{
                const vals = selectedDevsArray
                    .map(dev => rawData.chartData[dev][metric][issueNum])
                    .filter(v => v !== undefined && v !== null);
                if (vals.length === 0) return null;
                if (aggregation === 'sum') return vals.reduce((a, b) => a + b, 0);
                return vals.reduce((a, b) => a + b, 0) / vals.length;
            }});
            const label = aggregation === 'sum'
                ? `Sum of ${{selectedDevsArray.length}} dev(s)`
                : `Average of ${{selectedDevsArray.length}} dev(s)`;
            datasets.push({{
                label: label,
                data: values,
                borderColor: '#0969da',
                backgroundColor: '#0969da' + '33',
                tension: 0.3,
                fill: false,
                pointRadius: 4,
                pointHoverRadius: 6,
                spanGaps: true,
            }});
            return {{ labels, datasets }};
        }}

        function buildChartConfig(metric, title) {{
            const {{ labels, datasets }} = buildDatasets(metric);
            return {{
                type: 'line',
                data: {{ labels, datasets }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(ctx) {{
                                    const hours = ctx.parsed.y;
                                    const days = (hours / 24).toFixed(1);
                                    return ctx.dataset.label + ': ' + hours.toFixed(1) + 'h (' + days + 'd)';
                                }}
                            }}
                        }},
                        legend: {{ position: 'bottom' }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{ display: true, text: 'Hours' }}
                        }},
                        x: {{
                            title: {{ display: true, text: 'Issue' }}
                        }}
                    }}
                }}
            }};
        }}

        function updateCharts() {{
            if (cycleChart) cycleChart.destroy();
            if (leadChart) leadChart.destroy();
            cycleChart = new Chart(document.getElementById('cycleChart'), buildChartConfig('cycle', 'Cycle Time'));
            leadChart = new Chart(document.getElementById('leadChart'), buildChartConfig('lead', 'Lead Time'));
        }}

        renderCheckboxes();
        updateCharts();
    </script>
</body>
</html>"""
