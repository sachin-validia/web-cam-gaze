#!/usr/bin/env python3
"""
Analyze the differences between web and desktop calibration approaches
"""

import numpy as np
import pandas as pd
import json
import pathlib
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import sys

# Add project paths
project_root = pathlib.Path(__file__).parent
sys.path.append(str(project_root / 'src'))
sys.path.append(str(project_root))

def analyze_calibration_matrices():
    """Analyze transformation matrices from both calibration approaches"""
    
    print("=== Calibration Matrix Analysis ===\n")
    
    # Read comparison report
    with open('results/calibration_comparison/calibration_comparison_20250725_175726.json', 'r') as f:
        comparison = json.load(f)
    
    # Desktop calibration matrix
    desktop_matrix = np.array(comparison['matrix_analysis']['desktop_matrix'])
    print("Desktop Calibration Matrix:")
    print(desktop_matrix)
    print(f"\nTranslation components (mm): [{desktop_matrix[0,3]:.2f}, {desktop_matrix[1,3]:.2f}, {desktop_matrix[2,3]:.2f}]")
    
    # Web calibration matrix  
    web_matrix = np.array(comparison['matrix_analysis']['web_matrix'])
    print("\nWeb Calibration Matrix:")
    print(web_matrix)
    print(f"\nTranslation components (mm): [{web_matrix[0,3]:.2f}, {web_matrix[1,3]:.2f}, {web_matrix[2,3]:.2f}]")
    
    # Key differences
    print("\n=== Key Differences ===")
    print(f"1. X-axis translation difference: {abs(web_matrix[0,3] - desktop_matrix[0,3]):.2f}mm")
    print(f"2. Y-axis translation difference: {abs(web_matrix[1,3] - desktop_matrix[1,3]):.2f}mm")
    print(f"3. Z-axis translation difference: {abs(web_matrix[2,3] - desktop_matrix[2,3]):.2f}mm")
    
    # Gaze vector ranges
    print("\n=== Gaze Vector Ranges ===")
    desktop_gaze = comparison['gaze_ranges']['desktop']
    web_gaze = comparison['gaze_ranges']['web']
    
    print("\nDesktop gaze ranges:")
    print(f"  X: [{desktop_gaze['gaze_x'][0]:.3f}, {desktop_gaze['gaze_x'][1]:.3f}]")
    print(f"  Y: [{desktop_gaze['gaze_y'][0]:.3f}, {desktop_gaze['gaze_y'][1]:.3f}]")
    print(f"  Z: [{desktop_gaze['gaze_z'][0]:.3f}, {desktop_gaze['gaze_z'][1]:.3f}]")
    
    print("\nWeb gaze ranges:")
    print(f"  X: [{web_gaze['gaze_x'][0]:.3f}, {web_gaze['gaze_x'][1]:.3f}]")
    print(f"  Y: [{web_gaze['gaze_y'][0]:.3f}, {web_gaze['gaze_y'][1]:.3f}]")
    print(f"  Z: [{web_gaze['gaze_z'][0]:.3f}, {web_gaze['gaze_z'][1]:.3f}]")
    
    return desktop_matrix, web_matrix, comparison

def analyze_coordinate_systems():
    """Analyze the coordinate system differences"""
    
    print("\n\n=== Coordinate System Analysis ===\n")
    
    # Both use the same rotation matrix
    SRotG = np.array([[-1,0,0],[0,-1,0],[0,0,1]])
    print("Both systems use the same rotation matrix:")
    print(SRotG)
    
    print("\nThis indicates:")
    print("- X-axis is inverted (camera sees left as positive, screen uses right as positive)")
    print("- Y-axis is inverted (camera sees up as positive, screen uses down as positive)")
    print("- Z-axis remains the same (depth)")
    
    # The key difference is in the translation components
    print("\n=== Critical Observation ===")
    print("Desktop calibration Z-translation: -532.51mm (negative, behind screen)")
    print("Web calibration Z-translation: +283.16mm (positive, in front of screen)")
    print("\nThis 815.66mm difference suggests opposite Z-axis conventions!")
    
def test_gaze_transformation(desktop_matrix, web_matrix):
    """Test gaze transformation with sample vectors"""
    
    print("\n\n=== Testing Gaze Transformations ===\n")
    
    # Test gaze vectors (normalized)
    test_gazes = [
        np.array([0, 0, 1]),      # Looking straight ahead
        np.array([0.3, 0, 0.95]), # Looking right
        np.array([-0.3, 0, 0.95]),# Looking left
        np.array([0, 0.3, 0.95]), # Looking down
        np.array([0, -0.3, 0.95]) # Looking up
    ]
    
    labels = ['Center', 'Right', 'Left', 'Down', 'Up']
    
    # Screen info (same for both)
    screen_width_mm = 474.13
    screen_height_mm = 296.33
    
    print("Screen dimensions: {:.1f}mm x {:.1f}mm".format(screen_width_mm, screen_height_mm))
    
    for i, (gaze, label) in enumerate(zip(test_gazes, labels)):
        print(f"\n{label} gaze vector: {gaze}")
        
        # Desktop transformation
        # Scale calculation (from HomTransform._getScale)
        scale_d = -desktop_matrix[2,3] / gaze[2]
        gaze_scaled_d = scale_d * gaze
        gaze_4d = np.append(gaze_scaled_d, 1)
        screen_coords_d = desktop_matrix @ gaze_4d
        
        # Web transformation
        scale_w = -web_matrix[2,3] / gaze[2]
        gaze_scaled_w = scale_w * gaze
        gaze_4d = np.append(gaze_scaled_w, 1)
        screen_coords_w = web_matrix @ gaze_4d
        
        print(f"  Desktop: ({screen_coords_d[0]:.1f}, {screen_coords_d[1]:.1f})mm")
        print(f"  Web:     ({screen_coords_w[0]:.1f}, {screen_coords_w[1]:.1f})mm")
        
    return test_gazes

def visualize_calibration_points():
    """Visualize calibration points on screen"""
    
    print("\n\n=== Visualizing Calibration Points ===\n")
    
    # Read calibration data
    desktop_calib = pd.read_csv('results/interview_calibrations/test_desktop_1_calibration.csv')
    web_calib = pd.read_csv('results/interview_calibrations/test_3/test_3_calibration.csv')
    
    # Screen dimensions
    screen_width_mm = 474.13
    screen_height_mm = 296.33
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    # Desktop calibration points
    ax1.set_title('Desktop Calibration Target Points')
    ax1.add_patch(Rectangle((0, 0), screen_width_mm, screen_height_mm, 
                           fill=False, edgecolor='black', linewidth=2))
    
    # Extract unique target positions
    desktop_targets = desktop_calib[['set_x', 'set_y']].drop_duplicates()
    ax1.scatter(desktop_targets['set_x'], desktop_targets['set_y'], 
               s=100, c='red', marker='x', label='Targets')
    ax1.set_xlim(-50, screen_width_mm + 50)
    ax1.set_ylim(-50, screen_height_mm + 50)
    ax1.set_xlabel('X (mm)')
    ax1.set_ylabel('Y (mm)')
    ax1.grid(True, alpha=0.3)
    
    # Web calibration points
    ax2.set_title('Web Calibration Target Points')
    ax2.add_patch(Rectangle((0, 0), screen_width_mm, screen_height_mm, 
                           fill=False, edgecolor='black', linewidth=2))
    
    web_targets = web_calib[['set_x', 'set_y']].drop_duplicates()
    ax2.scatter(web_targets['set_x'], web_targets['set_y'], 
               s=100, c='blue', marker='x', label='Targets')
    ax2.set_xlim(-50, screen_width_mm + 50)
    ax2.set_ylim(-50, screen_height_mm + 50)
    ax2.set_xlabel('X (mm)')
    ax2.set_ylabel('Y (mm)')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('results/calibration_comparison/calibration_points_comparison.png', dpi=150)
    plt.close()
    
    print(f"Desktop calibration points: {len(desktop_targets)}")
    print(f"Web calibration points: {len(web_targets)}")
    print("Visualization saved to: results/calibration_comparison/calibration_points_comparison.png")

def main():
    """Main analysis function"""
    
    print("=" * 60)
    print("Calibration System Comparison Analysis")
    print("=" * 60)
    
    # Analyze matrices
    desktop_matrix, web_matrix, comparison = analyze_calibration_matrices()
    
    # Analyze coordinate systems
    analyze_coordinate_systems()
    
    # Test transformations
    test_gaze_transformation(desktop_matrix, web_matrix)
    
    # Visualize calibration points
    visualize_calibration_points()
    
    print("\n\n=== CONCLUSIONS ===")
    print("\n1. COORDINATE SYSTEM ISSUE:")
    print("   - Desktop and web calibrations use opposite Z-axis conventions")
    print("   - Desktop: Z=-532mm (camera behind screen)")
    print("   - Web: Z=+283mm (camera in front of screen)")
    print("   - This causes inverted depth calculations")
    
    print("\n2. TRANSLATION DIFFERENCES:")
    print("   - X-offset differs by 433.8mm")
    print("   - Y-offset differs by 149.4mm")
    print("   - These suggest different origin points")
    
    print("\n3. RECOMMENDATION:")
    print("   - Fix the Z-axis sign convention in web calibration")
    print("   - Ensure consistent origin point (screen center)")
    print("   - Validate with known gaze targets after fix")
    
    print("\n4. GAZE VECTOR RANGES:")
    print("   - Desktop Z is always positive (0.68 to 0.98)")
    print("   - Web Z is always negative (-0.96 to -0.53)")
    print("   - This confirms the inverted Z-axis issue")

if __name__ == "__main__":
    main()