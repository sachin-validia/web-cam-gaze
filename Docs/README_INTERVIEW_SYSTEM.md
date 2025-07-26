# Interview Gaze Tracking & Cheating Detection System

A comprehensive system for detecting cheating behavior in recorded interview videos using advanced gaze tracking and behavioral analysis.

## 🎯 Overview

This system solves the challenge of **retrospective screen dimension capture** and **gaze-to-screen mapping** for cheating detection in interview scenarios where videos have already been recorded.

## 🚀 Quick Start

### Step 1: Setup Candidate Calibration (Before Interview)

```bash
# Activate environment
source venv/bin/activate

# Run calibration system
python interview_calibration_system.py
```

**Process:**
1. Collect screen dimensions (manual input or automatic detection)
2. Run gaze calibration sequence (candidate looks at screen targets)
3. Save calibration data for later video analysis

### Step 2: Analyze Recorded Interview Video

```bash
# Analyze interview video using stored calibration
python interview_video_analyzer.py
```

**Input:** Video file + Candidate ID
**Output:** 
- Gaze mapped to screen coordinates
- Screen zone analysis
- GazeOnScreen.png-style visualizations
- Behavioral statistics

### Step 3: Detect Cheating Behavior

```bash
# Run advanced cheating detection
python cheating_detection_system.py
```

**Output:**
- Cheating probability score (0-1)
- Risk level classification
- Detailed behavioral analysis
- Actionable recommendations

## 📋 Complete Workflow

### Pre-Interview Setup

```python
from interview_calibration_system import InterviewCalibrationSystem

# Initialize system
calib_system = InterviewCalibrationSystem()

# Setup candidate (collects screen info + calibration)
calib_system.setup_candidate("candidate_001")
```

### Video Analysis

```python
from interview_video_analyzer import InterviewVideoAnalyzer

# Analyze recorded interview
analyzer = InterviewVideoAnalyzer()
result = analyzer.analyze_interview_video(
    video_path="interview_videos/candidate_001.mp4",
    candidate_id="candidate_001"
)
```

### Cheating Detection

```python
from cheating_detection_system import CheatingDetectionSystem

# Detect cheating behaviors
detector = CheatingDetectionSystem()
report = detector.analyze_cheating_indicators(
    analysis_data_path="results/interview_analysis/candidate_001_gaze_analysis.csv",
    candidate_id="candidate_001"
)
```

## 🔍 Detection Capabilities

### Screen Attention Analysis
- **Off-screen rate**: Percentage of time looking away from screen
- **Prolonged look-away periods**: Extended periods of inattention
- **Attention consistency**: Stability of focus over time

### Gaze Pattern Analysis
- **Zone transitions**: Excessive scanning across screen areas
- **Corner looking**: Looking at screen edges (potential note locations)
- **Gaze spread**: Concentration vs. scattered attention
- **Pattern entropy**: Randomness in gaze distribution

### Head Movement Analysis
- **Movement frequency**: Rate of head pose changes
- **Movement magnitude**: Degree of head turns
- **Stability score**: Overall head position consistency

### Temporal Behavior Analysis
- **Segment consistency**: Behavior changes over interview duration
- **Attention trends**: Improving vs. declining focus
- **Behavioral shifts**: Sudden changes in patterns

### Statistical Anomaly Detection
- **Coordinate outliers**: Unusual gaze positions
- **Z-score analysis**: Statistical deviations from normal patterns
- **Clustering analysis**: Identification of distinct behavior modes

## 📊 Output Examples

### Screen Mapping Results
```csv
frame_number,timestamp,gaze_x,gaze_y,gaze_z,screen_x_px,screen_y_px,zone_horizontal,zone_vertical,on_screen
1,0.033,-0.77,0.15,0.61,850,450,center,middle,True
2,0.067,-0.79,0.14,0.60,820,430,center,middle,True
3,0.100,0.12,0.85,0.52,1200,200,right,top,False
```

### Cheating Detection Report
```json
{
  "candidate_id": "candidate_001",
  "cheating_score": {
    "total_score": 0.75,
    "normalized_score": 0.75
  },
  "risk_level": "HIGH",
  "detection_indicators": {
    "screen_attention": {
      "off_screen_rate": 0.35,
      "prolonged_off_screen_periods": 8,
      "suspicious_off_screen": true
    },
    "gaze_patterns": {
      "zone_change_rate": 0.28,
      "corner_looking_rate": 0.15,
      "suspicious_patterns": true
    }
  },
  "recommendations": [
    "High off-screen attention detected. Review prolonged look-away periods.",
    "ALERT: Multiple suspicious behaviors detected. Manual review recommended."
  ]
}
```

## 🎯 Cheating Detection Zones

### Screen Zone Classification
```
┌─────────────────────────┐
│  TOP-LEFT  │    TOP     │  TOP-RIGHT   │
│   (corner) │  (normal)  │   (corner)   │
├─────────────────────────┤
│    LEFT    │   CENTER   │    RIGHT     │
│ (suspicious)│ (normal)  │ (suspicious) │
├─────────────────────────┤
│ BOTTOM-LEFT│   BOTTOM   │ BOTTOM-RIGHT │
│  (corner)  │  (normal)  │   (corner)   │
└─────────────────────────┘
```

### Risk Indicators
- **🔴 HIGH RISK**: Corner zones, frequent off-screen, rapid scanning
- **🟡 MEDIUM RISK**: Edge zones, moderate movements
- **🟢 LOW RISK**: Center zones, stable attention

## ⚙️ Configuration

### Detection Thresholds (Customizable)
```python
thresholds = {
    'off_screen_rate': 0.25,          # 25% off screen is suspicious
    'zone_change_rate': 0.20,         # 20% zone changes is high
    'head_movement_threshold': 15.0,   # degrees
    'prolonged_look_away': 90,        # frames (3 seconds at 30fps)
    'frequent_movements': 0.15,       # 15% of frames with movement
    'attention_focus_score': 0.6      # below 60% is concerning
}
```

## 📁 File Structure

```
results/
├── interview_calibrations/
│   ├── candidate_001_screen_info.json
│   ├── candidate_001_calibration.csv
│   └── candidate_001_transform_matrix.npy
├── interview_analysis/
│   ├── candidate_001_gaze_analysis.csv
│   ├── candidate_001_analysis_plots.png
│   └── candidate_001_analysis_report.json
└── cheating_analysis/
    ├── candidate_001_cheating_analysis.json
    └── candidate_001_cheating_analysis.png
```

## 🔧 Technical Requirements

### Dependencies
```bash
pip install opencv-python pandas numpy matplotlib seaborn scipy scikit-learn
```

### Hardware Requirements
- **Webcam**: Any USB/laptop camera for calibration
- **Screen**: Any size (system adapts to dimensions)
- **Processing**: Moderate CPU for video analysis

## 📖 Usage Scenarios

### Scenario 1: Real-time Interview Setup
1. Candidate joins interview platform
2. Run calibration sequence (2-3 minutes)
3. Conduct interview while recording
4. Analyze video afterward for cheating detection

### Scenario 2: Retrospective Analysis
1. Have candidate perform calibration on their setup
2. Use calibration data to analyze previously recorded videos
3. Generate cheating detection reports


## 🎯 Key Advantages

### Solves Retrospective Problem
- ✅ Works with already recorded videos
- ✅ No need for live calibration during interview
- ✅ Adapts to any screen size/setup

### Comprehensive Detection
- ✅ Multiple behavioral indicators
- ✅ Statistical anomaly detection
- ✅ Temporal pattern analysis
- ✅ Machine learning clustering

### Actionable Results
- ✅ Clear risk classifications
- ✅ Specific recommendations
- ✅ Visual evidence plots
- ✅ Timestamp-level analysis

## 🚨 Important Notes

1. **Calibration Quality**: Accuracy depends on calibration quality
2. **Environment Consistency**: Best results when calibration and interview use same setup
3. **Manual Review**: High-risk cases should always be manually reviewed
4. **Privacy Compliance**: Ensure compliance with privacy regulations
5. **False Positives**: System may flag nervous behavior - context matters
