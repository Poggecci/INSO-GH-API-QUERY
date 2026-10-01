import json
import logging
import os
from urllib.parse import quote
from src.utils.models import MilestoneData


def getChartUrl(pages_base_url: str, html_filename: str) -> str:
    """Build the full GitHub Pages URL for a chart file, URL-encoding the filename."""
    base = pages_base_url.rstrip("/")
    return f"{base}/metrics/{quote(html_filename)}"


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
        f'        <li><a href="metrics/{quote(fname)}">{name}</a></li>'
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
    Generates an interactive HTML scatter plot of cycle time and lead time per
    issue over the milestone timeline (x = issue closed date, y = duration in
    hours). One dot per issue, colored by developer. Includes developer
    checkboxes and an average/sum aggregation overlay.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    developers = list(milestone_data.devMetrics.keys())

    # Per-developer scatter points: (closed_date_iso, cycle_hours, lead_hours, issue_number, title)
    chart_data: dict[str, list[dict]] = {}
    for dev in developers:
        points = []
        for issue_num, cycle, lead, closed_iso, title in milestone_data.devMetrics[
            dev
        ].issueTimings:
            if closed_iso is None:
                continue
            points.append(
                {
                    "x": closed_iso[:10],  # date only
                    "cycle": round(cycle, 1),
                    "lead": round(lead, 1),
                    "issue": issue_num,
                    "title": title,
                }
            )
        points.sort(key=lambda p: p["x"])
        chart_data[dev] = points

    html_content = _generate_chart_html(
        developers=developers,
        chart_data=chart_data,
        milestone_start=milestone_data.startDate.strftime("%Y-%m-%d"),
        milestone_end=milestone_data.endDate.strftime("%Y-%m-%d"),
    )

    with open(html_file_path, mode="w") as f:
        f.write(html_content)
    logger.info(f"Cycle/lead time chart written to {html_file_path}")


def _generate_chart_html(
    developers: list[str],
    chart_data: dict,
    milestone_start: str,
    milestone_end: str,
) -> str:
    json_data = json.dumps(
        {
            "developers": developers,
            "chartData": chart_data,
            "milestoneStart": milestone_start,
            "milestoneEnd": milestone_end,
        }
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cycle Time & Lead Time — {milestone_start} to {milestone_end}</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-adapter-date-fns@3.0.0/dist/chartjs-adapter-date-fns.bundle.min.js"></script>
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
        .chart-wrapper {{ position: relative; height: 400px; }}
    </style>
</head>
<body>
    <h1>⏱️ Cycle Time & Lead Time</h1>
    <p class="subtitle">Milestone: {milestone_start} → {milestone_end} — Each dot is one closed issue; the x-axis is when it was closed.</p>

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

        function selectedPoints(metric) {{
            const pts = [];
            rawData.developers.forEach((dev, i) => {{
                if (!selectedDevs.has(dev)) return;
                rawData.chartData[dev].forEach(p => {{
                    pts.push({{ x: p.x, y: p[metric], dev, issue: p.issue, title: p.title, colorIdx: i }});
                }});
            }});
            pts.sort((a, b) => a.x.localeCompare(b.x));
            return pts;
        }}

        // Deterministic jitter: same issue always offsets the same way
        function jitter(issueNum) {{
            const h = (issueNum || 0) % 7;
            return (h - 3) * 3;  // -9..+9 hours, deterministic per issue
        }}

        function addHours(dateStr, hours) {{
            const d = new Date(dateStr + 'T12:00:00Z');
            d.setUTCHours(d.getUTCHours() + hours);
            return d.toISOString().slice(0, 10);
        }}

        function scatterDataset(pts) {{
            return {{
                data: pts.map(p => ({{ x: new Date(addHours(p.x, jitter(p.issue)) + 'T12:00:00Z'), y: p.y, issue: p.issue, title: p.title, dev: p.dev }})),
                showLine: false,
                pointRadius: 5,
                pointHoverRadius: 7,
                parsing: false,
            }};
        }}

        // Moving average over a sorted point list (window in days on the time axis)
        function movingAverage(pts, windowDays = 7) {{
            if (pts.length === 0) return [];
            const result = [];
            let lo = 0, sum = 0;
            const t = pts.map(p => Date.parse(p.x + 'T00:00:00Z'));
            for (let hi = 0; hi < pts.length; hi++) {{
                sum += pts[hi].y;
                while (t[hi] - t[lo] > windowDays * 86400000) {{
                    sum -= pts[lo].y;
                    lo++;
                }}
                result.push({{ x: pts[hi].x, y: sum / (hi - lo + 1) }});
            }}
            return result;
        }}

        // Per-day aggregation: sum or mean of all selected points per day
        function perDayAggregate(pts, mode) {{
            const byDay = new Map();
            pts.forEach(p => {{
                byDay.set(p.x, (byDay.get(p.x) || 0) + p.y);
            }});
            if (mode === 'avg') {{
                const counts = new Map();
                pts.forEach(p => counts.set(p.x, (counts.get(p.x) || 0) + 1));
                return Array.from(byDay.entries())
                    .sort((a, b) => a[0].localeCompare(b[0]))
                    .map(([d, total]) => ({{ x: d, y: total / (counts.get(d) || 1) }}));
            }}
            return Array.from(byDay.entries())
                .sort((a, b) => a[0].localeCompare(b[0]))
                .map(([d, total]) => ({{ x: d, y: total }}));
        }}

        function buildChartConfig(metric) {{
            const pts = selectedPoints(metric);
            const datasets = [];

            if (aggregation === 'avg') {{
                // Per-developer scatter dots + single moving-average trend line across all selected
                rawData.developers.forEach((dev, i) => {{
                    if (!selectedDevs.has(dev)) return;
                    const devPts = pts.filter(p => p.dev === dev);
                    if (devPts.length === 0) return;
                    const ds = scatterDataset(devPts);
                    ds.label = dev;
                    ds.backgroundColor = devColor(i);
                    ds.borderColor = devColor(i);
                    ds.tooltip = {{ callbacks: {{ label: ctx => ctx.raw.dev + ' #' + ctx.raw.issue + ': ' + ctx.parsed.y.toFixed(1) + 'h — ' + (ctx.raw.title || '') }} }};
                    datasets.push(ds);
                }});
                const trend = movingAverage(pts);
                if (trend.length > 0) {{
                    datasets.push({{
                        label: `Moving avg (${{pts.length}} issues)`,
                        data: trend.map(p => ({{ x: new Date(p.x + 'T12:00:00Z'), y: Math.round(p.y * 10) / 10 }})),
                        showLine: true,
                        borderColor: '#57606a',
                        backgroundColor: '#57606a',
                        borderDash: [6, 4],
                        pointRadius: 0,
                        borderWidth: 2,
                        tension: 0.3,
                        parsing: false,
                    }});
                }}
            }} else {{
                // Sum mode: single per-day aggregated curve across selected developers
                const agg = perDayAggregate(pts, 'sum');
                if (agg.length > 0) {{
                    datasets.push({{
                        label: `Sum of ${{pts.length}} issues`,
                        data: agg.map(p => ({{ x: new Date(p.x + 'T12:00:00Z'), y: Math.round(p.y * 10) / 10 }})),
                        showLine: true,
                        borderColor: '#0969da',
                        backgroundColor: '#0969da33',
                        pointRadius: 4,
                        borderWidth: 2,
                        tension: 0.2,
                        parsing: false,
                    }});
                }}
            }}

            return {{
                type: 'scatter',
                data: {{ datasets }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    parsing: false,
                    scales: {{
                        x: {{
                            type: 'time',
                            min: rawData.milestoneStart,
                            max: rawData.milestoneEnd,
                            time: {{ unit: 'day', tooltipFormat: 'MMM d, yyyy' }},
                            title: {{ display: true, text: 'Issue closed on' }},
                            adapters: {{ date: {{}} }}
                        }},
                        y: {{
                            beginAtZero: true,
                            title: {{ display: true, text: 'Hours' }}
                        }}
                    }},
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                title: () => '',
                                label: function(ctx) {{
                                    const hours = ctx.parsed.y;
                                    const days = (hours / 24).toFixed(1);
                                    const extra = ctx.raw.dev ? ctx.raw.dev + ' #' + ctx.raw.issue : '';
                                    return (ctx.raw.dev ? extra + ': ' : '') + hours.toFixed(1) + 'h (' + days + 'd)' + (ctx.raw.title ? ' — ' + ctx.raw.title : '');
                                }}
                            }}
                        }},
                        legend: {{ position: 'bottom' }}
                    }}
                }}
            }};
        }}

        function updateCharts() {{
            if (cycleChart) cycleChart.destroy();
            if (leadChart) leadChart.destroy();
            cycleChart = new Chart(document.getElementById('cycleChart'), buildChartConfig('cycle'));
            leadChart = new Chart(document.getElementById('leadChart'), buildChartConfig('lead'));
        }}

        renderCheckboxes();
        updateCharts();
    </script>
</body>
</html>"""


def writeCumulativeTimelineChart(
    milestone_data: MilestoneData,
    html_file_path: str,
    logger: logging.Logger | None = None,
):
    """
    Generates an interactive HTML file showing cumulative points closed per day
    across the milestone, with one line per developer. Makes bursty contribution
    patterns (flat then spike near sprint end) immediately visible.
    """
    if logger is None:
        logger = logging.getLogger(__name__)

    developers = list(milestone_data.devMetrics.keys())

    # Build a sorted list of all unique dates across all developers
    all_dates = set()
    for dev in developers:
        for date_str, _ in milestone_data.devMetrics[dev].pointsTimeline:
            all_dates.add(date_str[:10])  # Truncate to day

    # Include milestone start and end dates for context
    all_dates.add(milestone_data.startDate.strftime("%Y-%m-%d"))
    all_dates.add(milestone_data.endDate.strftime("%Y-%m-%d"))
    sorted_dates = sorted(all_dates)

    # Build cumulative data per developer per day
    chart_data = {}
    for dev in developers:
        # Group points by day and sort
        daily_points = {}
        for date_str, points in milestone_data.devMetrics[dev].pointsTimeline:
            day = date_str[:10]
            daily_points[day] = daily_points.get(day, 0) + points

        # Build cumulative array aligned to sorted_dates
        cumulative = 0.0
        cum_array = []
        for day in sorted_dates:
            cumulative += daily_points.get(day, 0)
            cum_array.append(round(cumulative, 1))
        chart_data[dev] = cum_array

    html_content = _generate_timeline_html(
        developers=developers,
        dates=sorted_dates,
        chart_data=chart_data,
        milestone_start=milestone_data.startDate.strftime("%Y-%m-%d"),
        milestone_end=milestone_data.endDate.strftime("%Y-%m-%d"),
    )

    with open(html_file_path, mode="w") as f:
        f.write(html_content)
    logger.info(f"Cumulative timeline chart written to {html_file_path}")


def _generate_timeline_html(
    developers: list[str],
    dates: list[str],
    chart_data: dict,
    milestone_start: str,
    milestone_end: str,
) -> str:
    json_data = json.dumps({
        "developers": developers,
        "dates": dates,
        "chartData": chart_data,
    })

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cumulative Contribution Timeline — {milestone_start} to {milestone_end}</title>
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
        .chart-container {{
            background: #fff;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .chart-container h2 {{ font-size: 1.1rem; margin: 0 0 0.5rem 0; }}
        .chart-wrapper {{ position: relative; height: 400px; }}
    </style>
</head>
<body>
    <h1>📈 Cumulative Contribution Timeline</h1>
    <p class="subtitle">Milestone: {milestone_start} â {milestone_end} â Steady slopes indicate consistent contributors; flat lines followed by spikes indicate bursty work patterns.</p>

    <div class="controls">
        <button onclick="selectAll(true)" style="font-size:0.85rem;border:1px solid #d0d7de;border-radius:6px;padding:0.4rem 0.8rem;background:#fff;cursor:pointer;">Select All</button>
        <button onclick="selectAll(false)" style="font-size:0.85rem;border:1px solid #d0d7de;border-radius:6px;padding:0.4rem 0.8rem;background:#fff;cursor:pointer;">Deselect All</button>
    </div>

    <div class="dev-checkboxes" id="dev-checkboxes"></div>

    <div class="chart-container">
        <h2>Cumulative Points Closed Per Day</h2>
        <div class="chart-wrapper"><canvas id="timelineChart"></canvas></div>
    </div>

    <script>
        const rawData = {json_data};
        let selectedDevs = new Set(rawData.developers);
        let timelineChart;

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
            updateChart();
        }}

        function selectAll(on) {{
            selectedDevs = on ? new Set(rawData.developers) : new Set();
            renderCheckboxes();
            updateChart();
        }}

        function updateChart() {{
            if (timelineChart) timelineChart.destroy();
            const labels = rawData.dates;
            const datasets = [];
            rawData.developers.forEach((dev, i) => {{
                if (!selectedDevs.has(dev)) return;
                datasets.push({{
                    label: dev,
                    data: rawData.chartData[dev],
                    borderColor: devColor(i),
                    backgroundColor: devColor(i) + '33',
                    tension: 0.1,
                    fill: false,
                    pointRadius: 3,
                    pointHoverRadius: 5,
                    spanGaps: true,
                }});
            }});
            timelineChart = new Chart(document.getElementById('timelineChart'), {{
                type: 'line',
                data: {{ labels, datasets }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        tooltip: {{
                            callbacks: {{
                                label: function(ctx) {{
                                    return ctx.dataset.label + ': ' + ctx.parsed.y + ' pts';
                                }}
                            }}
                        }},
                        legend: {{ position: 'bottom' }}
                    }},
                    scales: {{
                        y: {{
                            beginAtZero: true,
                            title: {{ display: true, text: 'Cumulative Points Closed' }}
                        }},
                        x: {{
                            title: {{ display: true, text: 'Date' }},
                            ticks: {{ maxRotation: 45, autoSkip: true, maxTicksLimit: 15 }}
                        }}
                    }}
                }}
            }});
        }}

        renderCheckboxes();
        updateChart();
    </script>
</body>
</html>""";
