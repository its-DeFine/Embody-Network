"""
Comparison reporter for dual-mode trading results
Generates insights and visualizations comparing real vs simulated performance
"""

import json
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime, timedelta
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ComparisonReporter:
    """Generate comparison reports between real and simulated trading"""
    
    def __init__(self):
        self.report_history = []
        
    def generate_comparison_report(self, 
                                 real_data: Dict[str, Any], 
                                 sim_data: Dict[str, Any],
                                 execution_history: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate comprehensive comparison report"""
        
        report = {
            'timestamp': datetime.utcnow().isoformat(),
            'report_type': 'comparison',
            'period': 'session',
            'summary': {},
            'detailed_metrics': {},
            'insights': [],
            'recommendations': []
        }
        
        # Performance comparison
        performance = self._compare_performance(real_data, sim_data)
        report['performance_comparison'] = performance
        
        # Execution quality comparison
        if execution_history:
            execution_quality = self._analyze_execution_quality(execution_history)
            report['execution_quality'] = execution_quality
        
        # Risk metrics comparison
        risk_comparison = self._compare_risk_metrics(real_data, sim_data)
        report['risk_comparison'] = risk_comparison
        
        # Generate insights
        insights = self._generate_insights(performance, risk_comparison)
        report['insights'] = insights
        
        # Generate recommendations
        recommendations = self._generate_recommendations(performance, risk_comparison)
        report['recommendations'] = recommendations
        
        # Summary statistics
        report['summary'] = self._generate_summary(real_data, sim_data, performance)
        
        # Store report
        self.report_history.append(report)
        
        return report
    
    def _compare_performance(self, real_data: Dict[str, Any], sim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compare performance metrics between real and simulated"""
        
        comparison = {
            'returns': {},
            'win_rate': {},
            'profit_factor': {},
            'sharpe_ratio': {},
            'max_drawdown': {},
            'accuracy_score': 0.0
        }
        
        # Extract metrics
        real_metrics = real_data.get('metrics', {})
        sim_metrics = sim_data.get('metrics', {})
        
        # Returns comparison
        real_return = real_metrics.get('total_return_pct', 0)
        sim_return = sim_metrics.get('total_return_pct', 0)
        
        comparison['returns'] = {
            'real': real_return,
            'simulated': sim_return,
            'difference': real_return - sim_return,
            'relative_diff': (real_return - sim_return) / abs(real_return) if real_return != 0 else 0
        }
        
        # Win rate comparison
        real_win_rate = real_metrics.get('win_rate', 0)
        sim_win_rate = sim_metrics.get('win_rate', 0)
        
        comparison['win_rate'] = {
            'real': real_win_rate * 100,
            'simulated': sim_win_rate * 100,
            'difference': (real_win_rate - sim_win_rate) * 100
        }
        
        # Sharpe ratio comparison
        real_sharpe = real_metrics.get('sharpe_ratio', 0)
        sim_sharpe = sim_metrics.get('sharpe_ratio', 0)
        
        comparison['sharpe_ratio'] = {
            'real': real_sharpe,
            'simulated': sim_sharpe,
            'difference': real_sharpe - sim_sharpe
        }
        
        # Calculate accuracy score (how well simulation predicts real)
        accuracy_components = []
        
        # Return prediction accuracy (within 10%)
        if real_return != 0:
            return_accuracy = max(0, 1 - abs(real_return - sim_return) / abs(real_return))
            accuracy_components.append(return_accuracy)
        
        # Win rate accuracy
        if real_win_rate != 0:
            win_rate_accuracy = max(0, 1 - abs(real_win_rate - sim_win_rate) / real_win_rate)
            accuracy_components.append(win_rate_accuracy)
        
        # Sharpe accuracy
        if real_sharpe != 0:
            sharpe_accuracy = max(0, 1 - abs(real_sharpe - sim_sharpe) / abs(real_sharpe))
            accuracy_components.append(sharpe_accuracy)
        
        comparison['accuracy_score'] = np.mean(accuracy_components) * 100 if accuracy_components else 0
        
        return comparison
    
    def _analyze_execution_quality(self, execution_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze execution quality from history"""
        
        quality_analysis = {
            'total_comparisons': 0,
            'price_divergence': {
                'mean': 0.0,
                'std': 0.0,
                'max': 0.0,
                'percentiles': {}
            },
            'slippage_comparison': {
                'real_avg': 0.0,
                'sim_avg': 0.0,
                'difference': 0.0
            },
            'fill_rate': {
                'real': 0.0,
                'simulated': 0.0
            }
        }
        
        # Extract comparison data
        price_divergences = []
        real_slippages = []
        sim_slippages = []
        real_fills = 0
        sim_fills = 0
        total_real = 0
        total_sim = 0
        
        for execution in execution_history:
            results = execution.get('results', {})
            
            if 'real' in results and 'simulated' in results:
                real_result = results['real']
                sim_result = results['simulated']
                
                # Price divergence
                if 'price' in real_result and 'price' in sim_result:
                    divergence = abs(real_result['price'] - sim_result['price']) / real_result['price']
                    price_divergences.append(divergence)
                
                # Slippage
                if 'slippage' in real_result:
                    real_slippages.append(real_result['slippage'])
                if 'slippage' in sim_result:
                    sim_slippages.append(sim_result['slippage'])
                
                # Fill rates
                if real_result.get('status') == 'filled':
                    real_fills += 1
                total_real += 1
                
                if sim_result.get('status') == 'filled':
                    sim_fills += 1
                total_sim += 1
        
        quality_analysis['total_comparisons'] = len(price_divergences)
        
        # Price divergence statistics
        if price_divergences:
            quality_analysis['price_divergence'] = {
                'mean': np.mean(price_divergences) * 100,
                'std': np.std(price_divergences) * 100,
                'max': np.max(price_divergences) * 100,
                'percentiles': {
                    '50th': np.percentile(price_divergences, 50) * 100,
                    '90th': np.percentile(price_divergences, 90) * 100,
                    '95th': np.percentile(price_divergences, 95) * 100
                }
            }
        
        # Slippage comparison
        if real_slippages and sim_slippages:
            quality_analysis['slippage_comparison'] = {
                'real_avg': np.mean(real_slippages) * 10000,  # in bps
                'sim_avg': np.mean(sim_slippages) * 10000,
                'difference': (np.mean(real_slippages) - np.mean(sim_slippages)) * 10000
            }
        
        # Fill rates
        if total_real > 0:
            quality_analysis['fill_rate']['real'] = (real_fills / total_real) * 100
        if total_sim > 0:
            quality_analysis['fill_rate']['simulated'] = (sim_fills / total_sim) * 100
        
        return quality_analysis
    
    def _compare_risk_metrics(self, real_data: Dict[str, Any], sim_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compare risk metrics between real and simulated"""
        
        risk_comparison = {
            'volatility': {},
            'max_drawdown': {},
            'var_95': {},
            'risk_adjusted_return': {},
            'correlation': 0.0
        }
        
        real_metrics = real_data.get('risk_metrics', {})
        sim_metrics = sim_data.get('risk_metrics', {})
        
        # Volatility comparison
        real_vol = real_metrics.get('volatility', 0)
        sim_vol = sim_metrics.get('volatility', 0)
        
        risk_comparison['volatility'] = {
            'real': real_vol * 100,
            'simulated': sim_vol * 100,
            'difference': (real_vol - sim_vol) * 100,
            'ratio': real_vol / sim_vol if sim_vol > 0 else 1.0
        }
        
        # Max drawdown
        real_dd = real_metrics.get('max_drawdown', 0)
        sim_dd = sim_metrics.get('max_drawdown', 0)
        
        risk_comparison['max_drawdown'] = {
            'real': real_dd * 100,
            'simulated': sim_dd * 100,
            'difference': (real_dd - sim_dd) * 100
        }
        
        # VaR comparison
        real_var = real_metrics.get('var_95', 0)
        sim_var = sim_metrics.get('var_95', 0)
        
        risk_comparison['var_95'] = {
            'real': real_var * 100,
            'simulated': sim_var * 100,
            'difference': (real_var - sim_var) * 100
        }
        
        # Risk-adjusted returns
        real_rar = real_metrics.get('risk_adjusted_return', 0)
        sim_rar = sim_metrics.get('risk_adjusted_return', 0)
        
        risk_comparison['risk_adjusted_return'] = {
            'real': real_rar,
            'simulated': sim_rar,
            'difference': real_rar - sim_rar
        }
        
        return risk_comparison
    
    def _generate_insights(self, performance: Dict[str, Any], risk: Dict[str, Any]) -> List[str]:
        """Generate insights from comparison data"""
        
        insights = []
        
        # Performance insights
        accuracy = performance.get('accuracy_score', 0)
        if accuracy > 90:
            insights.append(f"✅ Excellent simulation accuracy: {accuracy:.1f}% - Simulation closely matches real trading")
        elif accuracy > 75:
            insights.append(f"📊 Good simulation accuracy: {accuracy:.1f}% - Simulation provides reliable estimates")
        else:
            insights.append(f"⚠️ Low simulation accuracy: {accuracy:.1f}% - Consider adjusting simulation parameters")
        
        # Return comparison
        return_diff = performance['returns']['difference']
        if abs(return_diff) < 1:
            insights.append("Returns are closely aligned between real and simulated trading")
        elif return_diff > 0:
            insights.append(f"Real trading outperformed simulation by {return_diff:.2f}%")
        else:
            insights.append(f"Simulation overestimated returns by {abs(return_diff):.2f}%")
        
        # Risk insights
        vol_ratio = risk['volatility'].get('ratio', 1)
        if vol_ratio > 1.2:
            insights.append("Real trading shows higher volatility than simulated - market conditions may be more turbulent")
        elif vol_ratio < 0.8:
            insights.append("Simulation overestimates volatility - consider reducing volatility multiplier")
        
        # Win rate insights
        win_rate_diff = performance['win_rate']['difference']
        if abs(win_rate_diff) > 10:
            if win_rate_diff > 0:
                insights.append(f"Real trading has {win_rate_diff:.1f}% higher win rate - execution may be better than modeled")
            else:
                insights.append(f"Simulation overestimates win rate by {abs(win_rate_diff):.1f}% - adjust success probability")
        
        return insights
    
    def _generate_recommendations(self, performance: Dict[str, Any], risk: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on comparison"""
        
        recommendations = []
        
        # Accuracy-based recommendations
        accuracy = performance.get('accuracy_score', 0)
        if accuracy < 75:
            recommendations.append("🔧 Calibrate simulation parameters to better match real market conditions")
            recommendations.append("📊 Increase simulation volatility if real returns are more variable")
        
        # Slippage recommendations
        if 'execution_quality' in performance:
            slippage_diff = performance['execution_quality']['slippage_comparison']['difference']
            if slippage_diff > 5:  # 5 bps
                recommendations.append("💡 Increase simulated slippage to match real execution costs")
            elif slippage_diff < -5:
                recommendations.append("💡 Reduce simulated slippage - real execution is better than modeled")
        
        # Risk recommendations
        dd_diff = risk['max_drawdown']['difference']
        if dd_diff > 5:  # 5%
            recommendations.append("⚠️ Real trading has higher drawdowns - consider more conservative position sizing")
        
        # General recommendations
        if accuracy > 85:
            recommendations.append("✅ Continue using simulation for strategy testing - high accuracy achieved")
            recommendations.append("🎯 Use hybrid mode to gradually increase real allocation as confidence grows")
        else:
            recommendations.append("🔍 Run in comparison mode longer to gather more calibration data")
            recommendations.append("📈 Focus on paper trading until simulation accuracy improves")
        
        return recommendations
    
    def _generate_summary(self, real_data: Dict[str, Any], sim_data: Dict[str, Any], 
                         performance: Dict[str, Any]) -> Dict[str, Any]:
        """Generate executive summary"""
        
        summary = {
            'overall_accuracy': performance.get('accuracy_score', 0),
            'recommendation': '',
            'confidence_level': '',
            'key_divergences': []
        }
        
        # Confidence level
        accuracy = summary['overall_accuracy']
        if accuracy > 90:
            summary['confidence_level'] = 'Very High'
            summary['recommendation'] = 'Simulation is highly reliable for strategy development'
        elif accuracy > 80:
            summary['confidence_level'] = 'High'
            summary['recommendation'] = 'Simulation provides good guidance with minor adjustments needed'
        elif accuracy > 70:
            summary['confidence_level'] = 'Moderate'
            summary['recommendation'] = 'Use simulation with caution - verify with small real trades'
        else:
            summary['confidence_level'] = 'Low'
            summary['recommendation'] = 'Significant calibration needed before relying on simulation'
        
        # Key divergences
        return_diff = abs(performance['returns']['difference'])
        if return_diff > 5:
            summary['key_divergences'].append(f"Returns differ by {return_diff:.1f}%")
        
        win_rate_diff = abs(performance['win_rate']['difference'])
        if win_rate_diff > 10:
            summary['key_divergences'].append(f"Win rate differs by {win_rate_diff:.1f}%")
        
        return summary
    
    def generate_period_report(self, 
                              executions: List[Dict[str, Any]], 
                              period_hours: int = 24) -> Dict[str, Any]:
        """Generate report for specific time period"""
        
        cutoff_time = datetime.utcnow() - timedelta(hours=period_hours)
        
        # Filter executions by period
        period_executions = [
            e for e in executions 
            if datetime.fromisoformat(e['timestamp'].replace('Z', '+00:00')) > cutoff_time
        ]
        
        report = {
            'period': f'last_{period_hours}_hours',
            'start_time': cutoff_time.isoformat(),
            'end_time': datetime.utcnow().isoformat(),
            'total_executions': len(period_executions),
            'comparison_stats': {}
        }
        
        # Analyze period performance
        if period_executions:
            # Calculate statistics
            divergences = []
            real_returns = []
            sim_returns = []
            
            for execution in period_executions:
                if 'divergence_analysis' in execution:
                    divergences.append(execution['divergence_analysis']['price_divergence'])
                
                results = execution.get('results', {})
                # Extract returns if available
                # ... additional analysis
            
            if divergences:
                report['comparison_stats'] = {
                    'avg_price_divergence': np.mean(divergences) * 100,
                    'max_price_divergence': np.max(divergences) * 100,
                    'divergence_trend': 'increasing' if divergences[-1] > divergences[0] else 'decreasing'
                }
        
        return report
    
    def export_report(self, report: Dict[str, Any], format: str = 'json') -> str:
        """Export report in specified format"""
        
        if format == 'json':
            return json.dumps(report, indent=2)
        
        elif format == 'markdown':
            md = f"# Trading Comparison Report\n\n"
            md += f"**Generated:** {report['timestamp']}\n\n"
            
            # Summary
            summary = report.get('summary', {})
            md += f"## Summary\n\n"
            md += f"- **Overall Accuracy:** {summary.get('overall_accuracy', 0):.1f}%\n"
            md += f"- **Confidence Level:** {summary.get('confidence_level', 'Unknown')}\n"
            md += f"- **Recommendation:** {summary.get('recommendation', 'N/A')}\n\n"
            
            # Performance Comparison
            if 'performance_comparison' in report:
                perf = report['performance_comparison']
                md += f"## Performance Comparison\n\n"
                md += f"| Metric | Real | Simulated | Difference |\n"
                md += f"|--------|------|-----------|------------|\n"
                
                returns = perf.get('returns', {})
                md += f"| Returns | {returns.get('real', 0):.2f}% | {returns.get('simulated', 0):.2f}% | {returns.get('difference', 0):.2f}% |\n"
                
                win_rate = perf.get('win_rate', {})
                md += f"| Win Rate | {win_rate.get('real', 0):.1f}% | {win_rate.get('simulated', 0):.1f}% | {win_rate.get('difference', 0):.1f}% |\n"
                
                sharpe = perf.get('sharpe_ratio', {})
                md += f"| Sharpe Ratio | {sharpe.get('real', 0):.2f} | {sharpe.get('simulated', 0):.2f} | {sharpe.get('difference', 0):.2f} |\n\n"
            
            # Insights
            if 'insights' in report:
                md += f"## Insights\n\n"
                for insight in report['insights']:
                    md += f"- {insight}\n"
                md += "\n"
            
            # Recommendations
            if 'recommendations' in report:
                md += f"## Recommendations\n\n"
                for rec in report['recommendations']:
                    md += f"- {rec}\n"
            
            return md
        
        else:
            raise ValueError(f"Unsupported format: {format}")