"""
observability_engine/reporters.py
=================================
Generates JSON and HTML observability reports.
"""

import json
from pathlib import Path
from observability_engine.models import PipelineReport
from job_model.universal_model import UniversalJobModel

class ReportGenerator:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_json_reports(self, report: PipelineReport, accepted_jobs: list[UniversalJobModel]) -> None:
        """Generates all requested JSON metrics files."""
        # 1. pipeline_report.json
        pipeline_path = self.output_dir / "pipeline_report.json"
        with open(pipeline_path, "w", encoding="utf-8") as f:
            json.dump(report.model_dump(), f, indent=4)

        # 2. rejected_jobs.json
        rejected_path = self.output_dir / "rejected_jobs.json"
        with open(rejected_path, "w", encoding="utf-8") as f:
            rejected_dicts = [r.model_dump() for r in report.rejected_jobs]
            json.dump(rejected_dicts, f, indent=4)

        # 3. accepted_jobs.json
        accepted_path = self.output_dir / "accepted_jobs.json"
        with open(accepted_path, "w", encoding="utf-8") as f:
            accepted_dicts = [j.model_dump() for j in accepted_jobs]
            json.dump(accepted_dicts, f, indent=4)

        # 4. metrics.json
        metrics_path = self.output_dir / "metrics.json"
        with open(metrics_path, "w", encoding="utf-8") as f:
            metrics_dict = {
                "health_score": report.health_score.model_dump(),
                "stages": {name: s.model_dump() for name, s in report.stages.items()},
                "sources": {name: s.model_dump() for name, s in report.sources.items()}
            }
            json.dump(metrics_dict, f, indent=4)

    def generate_html_dashboard(self, report: PipelineReport) -> None:
        """Generates a static HTML dashboard for observability."""
        html_path = self.output_dir / "pipeline_dashboard.html"
        
        # Simple HTML template for the dashboard
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>AI Job Tracker - Observability Dashboard</title>
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; margin: 20px; background-color: #f5f5f5; color: #333; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
                .summary {{ display: flex; gap: 20px; margin-bottom: 30px; }}
                .card {{ background: #f8f9fa; padding: 20px; border-radius: 8px; flex: 1; border-left: 4px solid #3498db; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #34495e; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
                .funnel-row {{ background-color: #ecf0f1; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Pipeline Observability Dashboard</h1>
                <p><strong>Execution Date:</strong> {report.execution_date}</p>
                <p><strong>Total Execution Time:</strong> {report.total_execution_time_seconds:.2f}s</p>
                
                <div class="summary">
                    <div class="card">
                        <h3>Overall Pipeline Health</h3>
                        <h2 style="color: {'#27ae60' if report.health_score.overall_pipeline_health >= 80 else '#c0392b'};">{report.health_score.overall_pipeline_health:.2f}%</h2>
                    </div>
                    <div class="card">
                        <h3>Total Jobs Rejected</h3>
                        <h2>{len(report.rejected_jobs)}</h2>
                    </div>
                </div>

                <h2>Pipeline Funnel</h2>
                <table>
                    <tr>
                        <th>Stage</th>
                        <th>Input</th>
                        <th>Output</th>
                        <th>Rejected</th>
                        <th>Success Rate</th>
                        <th>Time (s)</th>
                    </tr>
        """
        for name, stage in report.stages.items():
            html_content += f"""
                    <tr>
                        <td>{name}</td>
                        <td>{stage.input_jobs}</td>
                        <td>{stage.output_jobs}</td>
                        <td>{stage.rejected_jobs}</td>
                        <td>{stage.success_rate:.2f}%</td>
                        <td>{stage.execution_time_seconds:.2f}</td>
                    </tr>
            """
        
        html_content += """
                </table>

                <h2>Top Failure Reasons</h2>
                <table>
                    <tr>
                        <th>Reason</th>
                        <th>Count</th>
                        <th>Percentage</th>
                    </tr>
        """
        for reason, percentage in sorted(report.rejection_analytics.rejection_percentages.items(), key=lambda x: x[1], reverse=True):
            count = report.rejection_analytics.rejection_reasons.get(reason, 0)
            html_content += f"""
                    <tr>
                        <td>{reason}</td>
                        <td>{count}</td>
                        <td>{percentage:.2f}%</td>
                    </tr>
            """

        html_content += """
                </table>

                <h2>Source Reliability Health</h2>
                <table>
                    <tr>
                        <th>Source</th>
                        <th>Attempted</th>
                        <th>Retrieved</th>
                        <th>Accepted</th>
                        <th>Reliability</th>
                    </tr>
        """
        for name, src in report.sources.items():
            html_content += f"""
                    <tr>
                        <td>{name}</td>
                        <td>{src.attempted}</td>
                        <td>{src.jobs_retrieved}</td>
                        <td>{src.jobs_accepted}</td>
                        <td>{src.reliability_score:.2f}%</td>
                    </tr>
            """
            
        html_content += """
                </table>
            </div>
        </body>
        </html>
        """
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)
