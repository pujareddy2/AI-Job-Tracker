"""
observability_engine/recommender.py
===================================
Analyzes observability metrics to suggest rule adjustments.
"""

from observability_engine.models import PipelineReport

class Recommender:
    @staticmethod
    def generate_recommendations(report: PipelineReport) -> list[str]:
        recommendations = []
        
        rejections = report.rejection_analytics.rejection_percentages
        
        # Analyze experience drop rate
        exp_drop = rejections.get("Experience threshold unmet", 0) + rejections.get("Experience Too Low", 0) + rejections.get("Experience Too High", 0)
        if exp_drop > 60:
            recommendations.append(f"Experience filter removed {exp_drop:.1f}% of jobs. Recommend relaxing 0-2 year rule.")
            
        # Analyze tech drop rate
        tech_drop = rejections.get("Missing core technology keywords", 0) + rejections.get("Technology Match Failed", 0)
        if tech_drop > 50:
            recommendations.append(f"Technology filter removed {tech_drop:.1f}% of jobs. Recommend adding semantic skill matching or lowering threshold.")
            
        # Analyze graduation drop rate
        grad_drop = rejections.get("Invalid graduation year", 0) + rejections.get("Graduation Rules Failed", 0)
        if grad_drop > 40:
            recommendations.append(f"Graduation filter removed {grad_drop:.1f}% of jobs. Recommend treating graduation as soft scoring instead of hard rejection.")
            
        # Analyze confidence drop rate
        conf_drop = rejections.get("Low Confidence", 0)
        if conf_drop > 70:
            recommendations.append(f"Confidence threshold removed {conf_drop:.1f}% of jobs. Recommend lowering threshold from 50 to 40.")
            
        # General missing info drop rate
        missing_url_drop = rejections.get("Missing Application URL", 0)
        if missing_url_drop > 20:
            recommendations.append(f"Missing URLs caused {missing_url_drop:.1f}% drop. Scrapers may need selector updates for application buttons.")
            
        if not recommendations:
            recommendations.append("Pipeline funnel looks healthy. No major bottlenecks detected.")
            
        return recommendations
