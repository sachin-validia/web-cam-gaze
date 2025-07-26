#!/usr/bin/env python3
"""
Calibration Comparison Test Script
=================================

Systematically compare desktop calibration vs web calibration to identify differences.
This will help debug why web calibration isn't producing accurate gaze tracking.

Test Plan:
1. Run desktop calibration (scripts/interview/calibration.py) -> test_desktop_1
2. Run web calibration -> test_web_1  
3. Analyze same video with both calibrations
4. Compare results to identify root cause
"""

import sys
import pathlib
import cv2
import numpy as np
import pandas as pd
import json
from datetime import datetime
import shutil

# Add project paths
project_root = pathlib.Path(__file__).parent
sys.path.append(str(project_root / 'scripts' / 'interview'))

from analyzer import InterviewVideoAnalyzer
from calibration import InterviewCalibrationSystem

class CalibrationComparison:
    """Compare desktop vs web calibration results"""
    
    def __init__(self):
        self.analyzer = InterviewVideoAnalyzer()
        self.desktop_calib = InterviewCalibrationSystem()
        self.results_dir = pathlib.Path("results/calibration_comparison")
        self.results_dir.mkdir(exist_ok=True, parents=True)
        
    def show_menu(self):
        """Display comparison menu"""
        print("\n" + "="*70)
        print("CALIBRATION COMPARISON TEST")
        print("="*70)
        print("1. Run Desktop Calibration (test_desktop_1)")
        print("2. Compare Calibration Files (desktop vs web)")
        print("3. Analyze Video with Both Calibrations")
        print("4. Generate Detailed Comparison Report")
        print("5. View Existing Comparison Results")
        print("6. Exit")
        print("="*70)
        
    def run(self):
        """Main interactive loop"""
        while True:
            self.show_menu()
            choice = input("\nEnter choice (1-6): ").strip()
            
            if choice == "1":
                self.run_desktop_calibration()
            elif choice == "2":
                self.compare_calibration_files()
            elif choice == "3":
                self.analyze_with_both_calibrations()
            elif choice == "4":
                self.generate_comparison_report()
            elif choice == "5":
                self.view_existing_results()
            elif choice == "6":
                print("\nGoodbye!")
                break
            else:
                print("❌ Invalid choice. Please try again.")
                
    def run_desktop_calibration(self):
        """Run desktop calibration for comparison"""
        print("\n🖥️  Desktop Calibration Setup")
        print("-" * 40)
        
        candidate_id = "test_desktop_1"
        print(f"Creating desktop calibration for: {candidate_id}")
        print("\nThis will:")
        print("1. Collect screen information")
        print("2. Run live camera calibration sequence")
        print("3. Save calibration files in standard format")
        
        proceed = input("\nProceed with desktop calibration? (y/n): ").strip().lower()
        if proceed != 'y':
            return
            
        try:
            # Run complete desktop calibration
            success = self.desktop_calib.setup_candidate(candidate_id)
            
            if success:
                print(f"\n✅ Desktop calibration completed!")
                print(f"📁 Files saved in: results/interview_calibrations/")
                
                # Show what was created
                calib_dir = pathlib.Path("results/interview_calibrations")
                desktop_files = list(calib_dir.glob(f"{candidate_id}_*"))
                print(f"\n📋 Created files:")
                for file in desktop_files:
                    print(f"  - {file.name}")
                    
            else:
                print("❌ Desktop calibration failed")
                
        except Exception as e:
            print(f"❌ Error during desktop calibration: {e}")
            import traceback
            traceback.print_exc()
            
    def compare_calibration_files(self):
        """Compare desktop vs web calibration files"""
        print("\n📊 Calibration Files Comparison")
        print("-" * 40)
        
        # Check available calibrations
        desktop_id = "test_desktop_1"
        web_id = input("Enter web calibration candidate ID to compare: ").strip()
        
        if not web_id:
            print("❌ Invalid web candidate ID")
            return
            
        try:
            # Load desktop calibration
            desktop_calib = self._load_calibration_data(desktop_id, "desktop")
            web_calib = self._load_calibration_data(web_id, "web")
            
            # Compare and save results
            comparison = self._compare_calibrations(desktop_calib, web_calib)
            
            # Save comparison report
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            report_path = self.results_dir / f"calibration_comparison_{timestamp}.json"
            
            with open(report_path, 'w') as f:
                json.dump(comparison, f, indent=2, default=str)
                
            print(f"\n📈 Comparison saved to: {report_path}")
            self._display_comparison_summary(comparison)
            
        except Exception as e:
            print(f"❌ Error comparing calibrations: {e}")
            import traceback
            traceback.print_exc()
            
    def analyze_with_both_calibrations(self):
        """Analyze same video with both calibrations"""
        print("\n🎥 Video Analysis Comparison")
        print("-" * 40)
        
        # Get inputs
        desktop_id = "test_desktop_1"
        web_id = input("Enter web calibration candidate ID: ").strip()
        video_path = input("Enter video path to analyze: ").strip()
        
        if not web_id or not video_path:
            print("❌ Invalid inputs")
            return
            
        video_file = pathlib.Path(video_path)
        if not video_file.exists():
            print(f"❌ Video not found: {video_path}")
            return
            
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        print(f"\n🔍 Analyzing video with both calibrations...")
        print(f"Video: {video_file.name}")
        
        try:
            # Analyze with desktop calibration
            print(f"\n1️⃣ Analyzing with desktop calibration ({desktop_id})...")
            desktop_result = self.analyzer.analyze_interview_video(
                video_path=str(video_file),
                candidate_id=desktop_id,
                output_name=f"desktop_{video_file.stem}_{timestamp}"
            )
            
            # Analyze with web calibration  
            print(f"\n2️⃣ Analyzing with web calibration ({web_id})...")
            web_result = self.analyzer.analyze_interview_video(
                video_path=str(video_file),
                candidate_id=web_id,
                output_name=f"web_{video_file.stem}_{timestamp}"
            )
            
            if desktop_result and web_result:
                # Compare analysis results
                analysis_comparison = self._compare_analysis_results(
                    desktop_result, web_result, video_file.name
                )
                
                # Save comparison
                comparison_path = self.results_dir / f"analysis_comparison_{timestamp}.json"
                with open(comparison_path, 'w') as f:
                    json.dump(analysis_comparison, f, indent=2, default=str)
                    
                print(f"\n📊 Analysis comparison saved to: {comparison_path}")
                self._display_analysis_comparison(analysis_comparison)
                
            else:
                print("❌ One or both analyses failed")
                
        except Exception as e:
            print(f"❌ Error during analysis comparison: {e}")
            import traceback
            traceback.print_exc()
            
    def _load_calibration_data(self, candidate_id, calib_type):
        """Load calibration data for comparison"""
        try:
            calib_data = self.desktop_calib.load_candidate_calibration(candidate_id)
            
            # Load raw files for detailed comparison
            calib_dir = pathlib.Path("results/interview_calibrations")
            
            # Check if structured directory exists
            structured_dir = calib_dir / candidate_id
            if structured_dir.exists():
                base_path = structured_dir / candidate_id
            else:
                base_path = calib_dir / candidate_id
                
            raw_data = {}
            
            # Load CSV
            csv_path = f"{base_path}_calibration.csv"
            if pathlib.Path(csv_path).exists():
                raw_data['csv'] = pd.read_csv(csv_path)
                
            # Load NPZ
            npz_path = f"{base_path}_transform_matrix.npz"
            if pathlib.Path(npz_path).exists():
                npz_data = np.load(npz_path, allow_pickle=True)
                raw_data['npz'] = {key: npz_data[key] for key in npz_data.keys()}
                
            # Load JSON
            json_path = f"{base_path}_screen_info.json"
            if pathlib.Path(json_path).exists():
                with open(json_path) as f:
                    raw_data['json'] = json.load(f)
                    
            return {
                'type': calib_type,
                'candidate_id': candidate_id,
                'calib_data': calib_data,
                'raw_data': raw_data
            }
            
        except Exception as e:
            raise Exception(f"Failed to load {calib_type} calibration for {candidate_id}: {e}")
            
    def _compare_calibrations(self, desktop, web):
        """Compare desktop vs web calibration data"""
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'desktop_id': desktop['candidate_id'],
            'web_id': web['candidate_id'],
            'differences': {},
            'matrix_analysis': {},
            'data_quality': {}
        }
        
        # Compare screen info
        desktop_screen = desktop['raw_data']['json']
        web_screen = web['raw_data']['json']
        
        comparison['differences']['screen_info'] = {
            'desktop': desktop_screen,
            'web': web_screen,
            'identical': desktop_screen == web_screen
        }
        
        # Compare transformation matrices
        desktop_matrix = desktop['raw_data']['npz']['STransG']
        web_matrix = web['raw_data']['npz']['STransG']
        
        comparison['matrix_analysis'] = {
            'desktop_shape': desktop_matrix.shape,
            'web_shape': web_matrix.shape,
            'shape_match': desktop_matrix.shape == web_matrix.shape,
            'desktop_matrix': desktop_matrix.tolist(),
            'web_matrix': web_matrix.tolist()
        }
        
        # Compare calibration CSV data
        if 'csv' in desktop['raw_data'] and 'csv' in web['raw_data']:
            desktop_csv = desktop['raw_data']['csv']
            web_csv = web['raw_data']['csv']
            
            comparison['data_quality'] = {
                'desktop_rows': len(desktop_csv),
                'web_rows': len(web_csv),
                'desktop_columns': list(desktop_csv.columns),
                'web_columns': list(web_csv.columns),
                'columns_match': list(desktop_csv.columns) == list(web_csv.columns)
            }
            
            # Compare gaze data ranges
            if 'gaze_x' in desktop_csv.columns and 'gaze_x' in web_csv.columns:
                comparison['gaze_ranges'] = {
                    'desktop': {
                        'gaze_x': [float(desktop_csv['gaze_x'].min()), float(desktop_csv['gaze_x'].max())],
                        'gaze_y': [float(desktop_csv['gaze_y'].min()), float(desktop_csv['gaze_y'].max())],
                        'gaze_z': [float(desktop_csv['gaze_z'].min()), float(desktop_csv['gaze_z'].max())]
                    },
                    'web': {
                        'gaze_x': [float(web_csv['gaze_x'].min()), float(web_csv['gaze_x'].max())],
                        'gaze_y': [float(web_csv['gaze_y'].min()), float(web_csv['gaze_y'].max())],
                        'gaze_z': [float(web_csv['gaze_z'].min()), float(web_csv['gaze_z'].max())]
                    }
                }
        
        return comparison
        
    def _compare_analysis_results(self, desktop_result, web_result, video_name):
        """Compare analysis results from both calibrations"""
        return {
            'timestamp': datetime.now().isoformat(),
            'video_name': video_name,
            'desktop_analysis': {
                'detection_rate': desktop_result['detection_stats']['detection_rate_percent'],
                'on_screen_rate': desktop_result['detection_stats']['on_screen_rate_percent'],
                'suspicious_behavior': desktop_result['suspicious_behavior'],
                'avg_screen_x': desktop_result['gaze_distribution']['avg_screen_x'],
                'avg_screen_y': desktop_result['gaze_distribution']['avg_screen_y']
            },
            'web_analysis': {
                'detection_rate': web_result['detection_stats']['detection_rate_percent'],
                'on_screen_rate': web_result['detection_stats']['on_screen_rate_percent'],
                'suspicious_behavior': web_result['suspicious_behavior'],
                'avg_screen_x': web_result['gaze_distribution']['avg_screen_x'],
                'avg_screen_y': web_result['gaze_distribution']['avg_screen_y']
            }
        }
        
    def _display_comparison_summary(self, comparison):
        """Display calibration comparison summary"""
        print(f"\n📊 CALIBRATION COMPARISON SUMMARY")
        print("=" * 50)
        
        print(f"\n🖥️  Desktop: {comparison['desktop_id']}")
        print(f"🌐 Web: {comparison['web_id']}")
        
        # Screen info comparison
        screen_match = comparison['differences']['screen_info']['identical']
        print(f"\n📺 Screen Info: {'✅ Identical' if screen_match else '❌ Different'}")
        
        # Matrix comparison
        matrix_info = comparison['matrix_analysis']
        shape_match = matrix_info['shape_match']
        print(f"🔢 Matrix Shape: {'✅ Match' if shape_match else '❌ Mismatch'}")
        print(f"   Desktop: {matrix_info['desktop_shape']}")
        print(f"   Web: {matrix_info['web_shape']}")
        
        # Data quality
        if 'data_quality' in comparison:
            quality = comparison['data_quality']
            print(f"\n📋 Calibration Data:")
            print(f"   Desktop rows: {quality['desktop_rows']}")
            print(f"   Web rows: {quality['web_rows']}")
            print(f"   Columns match: {'✅' if quality['columns_match'] else '❌'}")
            
        # Gaze ranges
        if 'gaze_ranges' in comparison:
            ranges = comparison['gaze_ranges']
            print(f"\n👁️  Gaze Vector Ranges:")
            print(f"   Desktop X: {ranges['desktop']['gaze_x']}")
            print(f"   Web X: {ranges['web']['gaze_x']}")
            print(f"   Desktop Y: {ranges['desktop']['gaze_y']}")
            print(f"   Web Y: {ranges['web']['gaze_y']}")
            
    def _display_analysis_comparison(self, comparison):
        """Display analysis comparison summary"""
        print(f"\n🎯 ANALYSIS COMPARISON SUMMARY")
        print("=" * 50)
        
        desktop = comparison['desktop_analysis']
        web = comparison['web_analysis']
        
        print(f"\n📊 Detection Rates:")
        print(f"   Desktop: {desktop['detection_rate']:.1f}%")
        print(f"   Web: {web['detection_rate']:.1f}%")
        
        print(f"\n👀 On-Screen Rates:")
        print(f"   Desktop: {desktop['on_screen_rate']:.1f}%")
        print(f"   Web: {web['on_screen_rate']:.1f}%")
        
        print(f"\n🎯 Average Gaze Position:")
        print(f"   Desktop: ({desktop['avg_screen_x']:.1f}, {desktop['avg_screen_y']:.1f})")
        print(f"   Web: ({web['avg_screen_x']:.1f}, {web['avg_screen_y']:.1f})")
        
        print(f"\n⚠️  Suspicious Behaviors:")
        desktop_suspicious = any(desktop['suspicious_behavior'].values())
        web_suspicious = any(web['suspicious_behavior'].values())
        print(f"   Desktop: {'Detected' if desktop_suspicious else 'None'}")
        print(f"   Web: {'Detected' if web_suspicious else 'None'}")
        
    def generate_comparison_report(self):
        """Generate comprehensive comparison report"""
        print("\n📝 Generating Comprehensive Report...")
        # This would create a detailed markdown report
        print("This feature will create a detailed markdown report comparing all aspects.")
        
    def view_existing_results(self):
        """View existing comparison results"""
        print("\n📁 Existing Comparison Results:")
        comparison_files = list(self.results_dir.glob("*.json"))
        
        if not comparison_files:
            print("No comparison results found.")
            return
            
        for i, file in enumerate(comparison_files, 1):
            print(f"{i}. {file.name}")
            
        try:
            choice = int(input("\nEnter file number to view: ")) - 1
            if 0 <= choice < len(comparison_files):
                with open(comparison_files[choice]) as f:
                    data = json.load(f)
                print(json.dumps(data, indent=2))
            else:
                print("Invalid choice")
        except ValueError:
            print("Invalid input")

def main():
    """Main entry point"""
    tester = CalibrationComparison()
    tester.run()

if __name__ == "__main__":
    main()