"""
Advanced Cheating Detection System
=================================

Comprehensive system for detecting cheating behaviors in interview videos
using gaze tracking, head pose analysis, and behavioral pattern recognition.
"""

import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
import pathlib

class CheatingDetectionSystem:
    """
    Advanced cheating detection using multiple behavioral indicators
    """
    
    def __init__(self):
        self.results_dir = pathlib.Path("results/cheating_analysis")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        
        # Detection thresholds (configurable)
        self.thresholds = {
            'off_screen_rate': 0.25,          # 25% off screen is suspicious
            'zone_change_rate': 0.20,         # 20% zone changes is high
            'head_movement_threshold': 15.0,   # degrees
            'prolonged_look_away': 90,        # frames (3 seconds at 30fps)
            'frequent_movements': 0.15,       # 15% of frames with movement
            'attention_focus_score': 0.6      # below 60% is concerning
        }
    
    def analyze_cheating_indicators(self, analysis_data_path, candidate_id):
        """
        Comprehensive cheating analysis from gaze analysis data
        """
        print(f"\n=== Cheating Detection Analysis for {candidate_id} ===")
        
        # Load analysis data
        df = pd.read_csv(analysis_data_path)
        detected_df = df[df['detected']].copy()
        
        if len(detected_df) == 0:
            print("❌ No gaze detection data available for analysis")
            return None
        
        # Run multiple detection algorithms
        indicators = {}
        
        # 1. Screen attention analysis
        indicators['screen_attention'] = self._analyze_screen_attention(detected_df)
        
        # 2. Gaze pattern analysis
        indicators['gaze_patterns'] = self._analyze_gaze_patterns(detected_df)
        
        # 3. Head movement analysis
        indicators['head_movement'] = self._analyze_head_movement(detected_df)
        
        # 4. Temporal behavior analysis
        indicators['temporal_behavior'] = self._analyze_temporal_behavior(detected_df)
        
        # 5. Statistical anomaly detection
        indicators['statistical_anomalies'] = self._detect_statistical_anomalies(detected_df)
        
        # 6. Clustering-based behavior analysis
        indicators['behavior_clusters'] = self._analyze_behavior_clusters(detected_df)
        
        # Calculate overall cheating score
        cheating_score = self._calculate_cheating_score(indicators)
        
        # Generate comprehensive report
        report = {
            'candidate_id': candidate_id,
            'analysis_timestamp': pd.Timestamp.now().isoformat(),
            'total_frames_analyzed': len(detected_df),
            'detection_indicators': indicators,
            'cheating_score': cheating_score,
            'risk_level': self._classify_risk_level(cheating_score),
            'recommendations': self._generate_recommendations(indicators, cheating_score)
        }
        
        # Save detailed report
        report_path = self.results_dir / f"{candidate_id}_cheating_analysis.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Generate visualizations
        self._generate_cheating_visualizations(detected_df, candidate_id, indicators)
        
        # Print summary
        self._print_analysis_summary(report)
        
        return report
    
    def _analyze_screen_attention(self, df):
        """
        Analyze attention to screen vs looking away
        """
        total_frames = len(df)
        on_screen_frames = df['on_screen'].sum()
        off_screen_rate = 1 - (on_screen_frames / total_frames)
        
        # Find consecutive off-screen periods
        off_screen_periods = []
        current_period = 0
        
        for on_screen in df['on_screen']:
            if not on_screen:
                current_period += 1
            else:
                if current_period > 0:
                    off_screen_periods.append(current_period)
                current_period = 0
        
        # Add final period if ended off-screen
        if current_period > 0:
            off_screen_periods.append(current_period)
        
        # Analyze periods
        prolonged_periods = [p for p in off_screen_periods if p > self.thresholds['prolonged_look_away']]
        
        return {
            'off_screen_rate': off_screen_rate,
            'total_off_screen_periods': len(off_screen_periods),
            'prolonged_off_screen_periods': len(prolonged_periods),
            'max_consecutive_off_screen': max(off_screen_periods) if off_screen_periods else 0,
            'avg_off_screen_duration': np.mean(off_screen_periods) if off_screen_periods else 0,
            'suspicious_off_screen': off_screen_rate > self.thresholds['off_screen_rate']
        }
    
    def _analyze_gaze_patterns(self, df):
        """
        Analyze gaze movement patterns across screen zones
        """
        # Zone transition analysis
        horizontal_changes = (df['zone_horizontal'].shift() != df['zone_horizontal']).sum()
        vertical_changes = (df['zone_vertical'].shift() != df['zone_vertical']).sum()
        total_changes = horizontal_changes + vertical_changes
        change_rate = total_changes / len(df)
        
        # Zone distribution
        zone_distribution = df.groupby(['zone_horizontal', 'zone_vertical']).size()
        zone_entropy = stats.entropy(zone_distribution.values)
        
        # Gaze spread analysis
        on_screen_df = df[df['on_screen']].copy()
        if len(on_screen_df) > 0:
            gaze_std_x = on_screen_df['screen_x_px'].std()
            gaze_std_y = on_screen_df['screen_y_px'].std()
            gaze_spread = np.sqrt(gaze_std_x**2 + gaze_std_y**2)
        else:
            gaze_spread = 0
        
        # Corner looking (potential cheating indicator)
        corner_zones = ['left_top', 'left_bottom', 'right_top', 'right_bottom']
        corner_looks = 0
        for _, row in df.iterrows():
            zone = f"{row['zone_horizontal']}_{row['zone_vertical']}"
            if zone in corner_zones:
                corner_looks += 1
        corner_rate = corner_looks / len(df)
        
        return {
            'zone_change_rate': change_rate,
            'horizontal_changes': horizontal_changes,
            'vertical_changes': vertical_changes,
            'zone_entropy': zone_entropy,
            'gaze_spread': gaze_spread,
            'corner_looking_rate': corner_rate,
            'suspicious_patterns': change_rate > self.thresholds['zone_change_rate']
        }
    
    def _analyze_head_movement(self, df):
        """
        Analyze head pose changes as indicator of looking around
        """
        # Calculate head movement magnitudes
        yaw_diff = df['yaw'].diff().abs()
        pitch_diff = df['pitch'].diff().abs()
        roll_diff = df['roll'].diff().abs()
        
        # Total head movement
        total_movement = np.sqrt(yaw_diff**2 + pitch_diff**2 + roll_diff**2)
        
        # Large movements
        large_movements = total_movement > self.thresholds['head_movement_threshold']
        large_movement_rate = large_movements.sum() / len(df)
        
        # Head stability
        yaw_std = df['yaw'].std()
        pitch_std = df['pitch'].std()
        head_stability = 1 / (1 + yaw_std + pitch_std)  # Higher = more stable
        
        return {
            'avg_head_movement': total_movement.mean(),
            'max_head_movement': total_movement.max(),
            'large_movement_rate': large_movement_rate,
            'head_stability_score': head_stability,
            'yaw_range': df['yaw'].max() - df['yaw'].min(),
            'pitch_range': df['pitch'].max() - df['pitch'].min(),
            'suspicious_movement': large_movement_rate > self.thresholds['frequent_movements']
        }
    
    def _analyze_temporal_behavior(self, df):
        """
        Analyze behavior patterns over time
        """
        # Divide video into segments
        num_segments = 5
        segment_size = len(df) // num_segments
        segment_stats = []
        
        for i in range(num_segments):
            start_idx = i * segment_size
            end_idx = start_idx + segment_size if i < num_segments - 1 else len(df)
            segment = df.iloc[start_idx:end_idx]
            
            segment_stats.append({
                'segment': i + 1,
                'on_screen_rate': segment['on_screen'].mean(),
                'zone_changes': (segment['zone_horizontal'].shift() != segment['zone_horizontal']).sum(),
                'avg_head_movement': segment[['yaw', 'pitch']].diff().abs().mean().mean()
            })
        
        segment_df = pd.DataFrame(segment_stats)
        
        # Analyze consistency
        on_screen_consistency = 1 - segment_df['on_screen_rate'].std()
        movement_consistency = 1 - segment_df['avg_head_movement'].std()
        
        # Trend analysis
        on_screen_trend = np.polyfit(range(num_segments), segment_df['on_screen_rate'], 1)[0]
        
        return {
            'segment_analysis': segment_stats,
            'on_screen_consistency': on_screen_consistency,
            'movement_consistency': movement_consistency,
            'attention_trend': on_screen_trend,  # Positive = improving, negative = declining
            'suspicious_inconsistency': on_screen_consistency < 0.8
        }
    
    def _detect_statistical_anomalies(self, df):
        """
        Detect statistical anomalies in gaze patterns
        """
        anomalies = {}
        
        # Z-score analysis for screen coordinates
        on_screen_df = df[df['on_screen']].copy()
        if len(on_screen_df) > 10:
            # X coordinate anomalies
            x_zscore = np.abs(stats.zscore(on_screen_df['screen_x_px']))
            x_anomalies = (x_zscore > 3).sum()
            
            # Y coordinate anomalies
            y_zscore = np.abs(stats.zscore(on_screen_df['screen_y_px']))
            y_anomalies = (y_zscore > 3).sum()
            
            anomalies['coordinate_anomalies'] = x_anomalies + y_anomalies
            anomalies['anomaly_rate'] = (x_anomalies + y_anomalies) / len(on_screen_df)
        else:
            anomalies['coordinate_anomalies'] = 0
            anomalies['anomaly_rate'] = 0
        
        # Head pose anomalies
        yaw_anomalies = (np.abs(stats.zscore(df['yaw'].dropna())) > 3).sum()
        pitch_anomalies = (np.abs(stats.zscore(df['pitch'].dropna())) > 3).sum()
        
        anomalies['head_pose_anomalies'] = yaw_anomalies + pitch_anomalies
        anomalies['suspicious_anomalies'] = anomalies['anomaly_rate'] > 0.05  # >5% anomalies
        
        return anomalies
    
    def _analyze_behavior_clusters(self, df):
        """
        Use clustering to identify behavior patterns
        """
        # Prepare features for clustering
        on_screen_df = df[df['on_screen']].copy()
        
        if len(on_screen_df) < 50:
            return {'insufficient_data': True}
        
        features = on_screen_df[['screen_x_px', 'screen_y_px', 'yaw', 'pitch']].dropna()
        
        if len(features) < 20:
            return {'insufficient_data': True}
        
        # Standardize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # DBSCAN clustering
        clustering = DBSCAN(eps=0.5, min_samples=10)
        clusters = clustering.fit_predict(features_scaled)
        
        # Analyze clusters
        n_clusters = len(set(clusters)) - (1 if -1 in clusters else 0)
        n_outliers = list(clusters).count(-1)
        outlier_rate = n_outliers / len(clusters)
        
        return {
            'n_clusters': n_clusters,
            'n_outliers': n_outliers,
            'outlier_rate': outlier_rate,
            'cluster_diversity': n_clusters,
            'suspicious_clustering': outlier_rate > 0.15 or n_clusters > 5
        }
    
    def _calculate_cheating_score(self, indicators):
        """
        Calculate overall cheating probability score (0-1)
        """
        score_components = []
        
        # Screen attention (30% weight)
        screen_score = indicators['screen_attention']['off_screen_rate'] * 0.3
        score_components.append(('screen_attention', screen_score, 0.3))
        
        # Gaze patterns (25% weight)
        pattern_score = min(indicators['gaze_patterns']['zone_change_rate'] * 2, 1.0) * 0.25
        score_components.append(('gaze_patterns', pattern_score, 0.25))
        
        # Head movement (20% weight)
        movement_score = min(indicators['head_movement']['large_movement_rate'] * 3, 1.0) * 0.2
        score_components.append(('head_movement', movement_score, 0.2))
        
        # Temporal consistency (15% weight)
        temporal_score = (1 - indicators['temporal_behavior']['on_screen_consistency']) * 0.15
        score_components.append(('temporal_behavior', temporal_score, 0.15))
        
        # Statistical anomalies (10% weight)
        anomaly_score = min(indicators['statistical_anomalies']['anomaly_rate'] * 5, 1.0) * 0.1
        score_components.append(('anomalies', anomaly_score, 0.1))
        
        total_score = sum(score for _, score, _ in score_components)
        
        return {
            'total_score': total_score,
            'components': score_components,
            'normalized_score': min(total_score, 1.0)
        }
    
    def _classify_risk_level(self, cheating_score):
        """
        Classify risk level based on cheating score
        """
        score = cheating_score['normalized_score']
        
        if score < 0.3:
            return 'LOW'
        elif score < 0.6:
            return 'MEDIUM'
        elif score < 0.8:
            return 'HIGH'
        else:
            return 'CRITICAL'
    
    def _generate_recommendations(self, indicators, cheating_score):
        """
        Generate actionable recommendations based on analysis
        """
        recommendations = []
        score = cheating_score['normalized_score']
        
        if score < 0.3:
            recommendations.append("Candidate shows normal interview behavior patterns.")
        
        if indicators['screen_attention']['suspicious_off_screen']:
            recommendations.append("High off-screen attention detected. Review prolonged look-away periods.")
        
        if indicators['gaze_patterns']['suspicious_patterns']:
            recommendations.append("Unusual gaze patterns detected. Check for excessive screen scanning.")
        
        if indicators['head_movement']['suspicious_movement']:
            recommendations.append("Frequent head movements detected. May indicate looking at unauthorized materials.")
        
        if indicators['temporal_behavior']['suspicious_inconsistency']:
            recommendations.append("Inconsistent attention patterns over time. Review behavior changes during interview.")
        
        if score > 0.6:
            recommendations.append("ALERT: Multiple suspicious behaviors detected. Manual review recommended.")
        
        if score > 0.8:
            recommendations.append("CRITICAL: High probability of cheating behavior. Immediate manual review required.")
        
        return recommendations
    
    def _generate_cheating_visualizations(self, df, candidate_id, indicators):
        """
        Generate comprehensive visualization for cheating analysis
        """
        fig, axes = plt.subplots(3, 2, figsize=(16, 18))
        fig.suptitle(f'Cheating Detection Analysis: {candidate_id}', fontsize=16)
        
        # 1. Attention timeline
        ax1 = axes[0, 0]
        ax1.plot(df['timestamp'], df['on_screen'].astype(int), alpha=0.7, linewidth=1)
        ax1.fill_between(df['timestamp'], 0, df['on_screen'].astype(int), alpha=0.3)
        ax1.set_title('Screen Attention Timeline')
        ax1.set_ylabel('On Screen (1=Yes, 0=No)')
        ax1.set_xlabel('Time (seconds)')
        ax1.grid(True, alpha=0.3)
        
        # 2. Zone transition heatmap
        ax2 = axes[0, 1]
        zone_pivot = df.pivot_table(values='timestamp', 
                                   index='zone_vertical', 
                                   columns='zone_horizontal', 
                                   aggfunc='count', 
                                   fill_value=0)
        sns.heatmap(zone_pivot, annot=True, cmap='YlOrRd', ax=ax2)
        ax2.set_title('Gaze Zone Distribution')
        
        # 3. Head movement over time
        ax3 = axes[1, 0]
        ax3.plot(df['timestamp'], df['yaw'], label='Yaw', alpha=0.7)
        ax3.plot(df['timestamp'], df['pitch'], label='Pitch', alpha=0.7)
        ax3.set_title('Head Movement Over Time')
        ax3.set_ylabel('Angle (degrees)')
        ax3.set_xlabel('Time (seconds)')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Behavioral indicators radar chart
        ax4 = axes[1, 1]
        categories = ['Off-Screen Rate', 'Zone Changes', 'Head Movement', 
                     'Inconsistency', 'Anomalies']
        values = [
            indicators['screen_attention']['off_screen_rate'],
            indicators['gaze_patterns']['zone_change_rate'],
            indicators['head_movement']['large_movement_rate'],
            1 - indicators['temporal_behavior']['on_screen_consistency'],
            indicators['statistical_anomalies']['anomaly_rate']
        ]
        
        angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False)
        values += values[:1]  # Complete the circle
        angles = np.concatenate((angles, [angles[0]]))
        
        ax4.plot(angles, values, 'o-', linewidth=2, label='Candidate')
        ax4.fill(angles, values, alpha=0.25)
        ax4.set_xticks(angles[:-1])
        ax4.set_xticklabels(categories)
        ax4.set_ylim(0, 1)
        ax4.set_title('Behavioral Risk Indicators')
        ax4.grid(True)
        
        # 5. Temporal segment analysis
        ax5 = axes[2, 0]
        segment_data = indicators['temporal_behavior']['segment_analysis']
        segments = [s['segment'] for s in segment_data]
        on_screen_rates = [s['on_screen_rate'] for s in segment_data]
        
        ax5.bar(segments, on_screen_rates, alpha=0.7, color='skyblue')
        ax5.axhline(y=0.8, color='red', linestyle='--', label='Threshold')
        ax5.set_title('Attention by Interview Segment')
        ax5.set_ylabel('On-Screen Rate')
        ax5.set_xlabel('Interview Segment')
        ax5.legend()
        ax5.grid(True, alpha=0.3)
        
        # 6. Risk summary
        ax6 = axes[2, 1]
        ax6.axis('off')
        
        # Create risk summary text
        score = indicators  # This should be the cheating score, but using indicators for now
        risk_text = f"""
        CHEATING RISK ASSESSMENT
        
        Overall Risk Level: HIGH
        
        Key Findings:
        • Off-screen rate: {indicators['screen_attention']['off_screen_rate']:.1%}
        • Zone changes: {indicators['gaze_patterns']['zone_change_rate']:.1%}
        • Head movement rate: {indicators['head_movement']['large_movement_rate']:.1%}
        • Attention consistency: {indicators['temporal_behavior']['on_screen_consistency']:.1%}
        
        Recommendations:
        • Manual review required
        • Check timestamps with high activity
        • Verify environmental factors
        """
        
        ax6.text(0.1, 0.9, risk_text, transform=ax6.transAxes, fontsize=10,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        
        plt.tight_layout()
        
        # Save visualization
        plot_path = self.results_dir / f"{candidate_id}_cheating_analysis.png"
        plt.savefig(plot_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"📊 Cheating analysis visualizations saved to: {plot_path}")
    
    def _print_analysis_summary(self, report):
        """
        Print summary of cheating analysis
        """
        print(f"\n{'='*60}")
        print(f"CHEATING DETECTION SUMMARY")
        print(f"{'='*60}")
        print(f"Candidate: {report['candidate_id']}")
        print(f"Risk Level: {report['risk_level']}")
        print(f"Cheating Score: {report['cheating_score']['normalized_score']:.3f}")
        print(f"Frames Analyzed: {report['total_frames_analyzed']}")
        
        print(f"\n📊 KEY INDICATORS:")
        indicators = report['detection_indicators']
        print(f"• Off-screen rate: {indicators['screen_attention']['off_screen_rate']:.1%}")
        print(f"• Zone change rate: {indicators['gaze_patterns']['zone_change_rate']:.1%}")
        print(f"• Large head movements: {indicators['head_movement']['large_movement_rate']:.1%}")
        print(f"• Attention consistency: {indicators['temporal_behavior']['on_screen_consistency']:.1%}")
        
        print(f"\n⚠️  RECOMMENDATIONS:")
        for i, rec in enumerate(report['recommendations'], 1):
            print(f"{i}. {rec}")

def main():
    """
    Main function for cheating detection
    """
    detector = CheatingDetectionSystem()
    
    print("Cheating Detection System")
    print("1. Analyze candidate video")
    print("2. Batch analyze multiple candidates")
    print("3. Exit")
    
    choice = input("Enter choice (1-3): ").strip()
    
    if choice == "1":
        candidate_id = input("Enter candidate ID: ").strip()
        analysis_file = input("Enter path to gaze analysis CSV: ").strip()
        
        if candidate_id and analysis_file:
            detector.analyze_cheating_indicators(analysis_file, candidate_id)
        else:
            print("Invalid input")
    
    elif choice == "2":
        analysis_dir = input("Enter directory with analysis files: ").strip()
        # Batch processing implementation
        print("Batch processing not implemented yet")
    
    elif choice == "3":
        print("Goodbye!")
    
    else:
        print("Invalid choice")

if __name__ == "__main__":
    main()