import subprocess
import sys
import time
import pathlib

def run_batch_processing():
    """Run batch processing with proper logging"""
    
    print("Starting batch processing of all videos...")
    
    # Run the batch processing script
    try:
        result = subprocess.run(
            [sys.executable, 'batch_process_videos.py'],
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        print(f"Return code: {result.returncode}")
        
        # Check results
        results_dir = pathlib.Path("results/batch_processing")
        if results_dir.exists():
            print(f"\nResults directory created: {results_dir}")
            
            # Count processed videos
            video_dirs = [d for d in results_dir.iterdir() if d.is_dir()]
            print(f"Number of video directories: {len(video_dirs)}")
            
            # Check for CSV files
            csv_files = list(results_dir.glob("**/*.csv"))
            print(f"Number of CSV result files: {len(csv_files)}")
            
            # Check for summary files
            summary_files = list(results_dir.glob("**/*summary.txt"))
            print(f"Number of summary files: {len(summary_files)}")
            
            # Show sample results
            if csv_files:
                print(f"\nSample CSV files:")
                for csv_file in csv_files[:3]:
                    print(f"  - {csv_file}")
        
    except subprocess.TimeoutExpired:
        print("Batch processing timed out after 10 minutes")
    except Exception as e:
        print(f"Error during batch processing: {e}")

if __name__ == "__main__":
    run_batch_processing()