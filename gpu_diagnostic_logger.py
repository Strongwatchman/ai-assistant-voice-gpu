import subprocess
import time
import os

def log_gpu_usage(interval=2.0):
    print("🔍 Starting real-time GPU usage logging. Press Ctrl+C to stop.\n")
    try:
        while True:
            print("="*80)
            print("🕐", time.strftime("%Y-%m-%d %H:%M:%S"))
            subprocess.run(["nvidia-smi"], check=False)
            print("="*80)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n🛑 Stopped GPU monitoring.")

if __name__ == "__main__":
    log_gpu_usage()
