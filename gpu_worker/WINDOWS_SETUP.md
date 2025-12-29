# GPU Worker Setup for Windows

This guide will help you set up the GPU worker on your Windows machine with NVIDIA GPU.

## Prerequisites

- **Windows 10/11** (64-bit)
- **NVIDIA GPU** (GTX 1060 or better recommended)
- **NVIDIA Drivers** (Latest version)
- **CUDA 11.8 or 12.x** (will be installed via PyTorch)
- **Python 3.10, 3.11, or 3.12**
- **8GB+ RAM** (16GB recommended)

## Quick Start

### Step 1: Check GPU and CUDA

Open PowerShell or Command Prompt and run:

```powershell
nvidia-smi
```

You should see your GPU listed. If not, install/update NVIDIA drivers from:
https://www.nvidia.com/Download/index.aspx

### Step 2: Install Python

Download Python 3.11 from: https://www.python.org/downloads/

**Important:** Check "Add Python to PATH" during installation!

Verify installation:
```powershell
python --version
```

### Step 3: Create Project Directory

```powershell
# Create directory
cd C:\
mkdir ninav-gpu-worker
cd ninav-gpu-worker

# Copy GPU worker files here
# You need: main.py and requirements.txt
```

### Step 4: Install Dependencies

```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\activate

# Install PyTorch with CUDA support (choose based on your CUDA version)
# For CUDA 11.8:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.x:
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install other dependencies
pip install -r requirements.txt
```

### Step 5: Verify GPU is Detected

```powershell
python
```

Then in Python:
```python
import torch
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
exit()
```

Expected output:
```
CUDA available: True
GPU: NVIDIA GeForce RTX 3080
```

### Step 6: Start GPU Worker

```powershell
# Make sure venv is activated
.\venv\Scripts\activate

# Start the worker
python main.py
```

You should see:
```
Initializing InsightFace model...
Device: CUDA (NVIDIA GPU)
✓ InsightFace initialized successfully on CUDA (NVIDIA GPU)
✓ Detection size: 640x640
✓ Model: buffalo_l (high accuracy)
INFO:     Uvicorn running on http://0.0.0.0:8001
```

### Step 7: Get Your Windows Machine IP Address

In PowerShell:
```powershell
ipconfig
```

Look for "IPv4 Address" under your active network adapter (e.g., `192.168.1.100`)

### Step 8: Test GPU Worker

Open a browser on your Windows machine and go to:
```
http://localhost:8001
```

You should see:
```json
{
  "status": "healthy",
  "gpu_available": true,
  "model_loaded": true,
  "device": "CUDA (NVIDIA GPU)"
}
```

### Step 9: Configure Mac Backend

On your Mac, edit the `.env` file:

```bash
cd /Users/naga/naga/AI/windsurf/Face-detection
nano .env
```

Add this line (replace with your Windows IP):
```
GPU_WORKER_URL=http://192.168.1.100:8001
```

Save and restart Docker:
```bash
docker compose restart backend
```

### Step 10: Test from Mac

From your Mac, test the connection:

```bash
# Replace with your Windows IP
curl http://192.168.1.100:8001

# Should return:
# {"status":"healthy","gpu_available":true,"model_loaded":true,"device":"CUDA (NVIDIA GPU)"}
```

## Firewall Configuration

If you can't connect from Mac to Windows:

1. **Open Windows Firewall**:
   - Press `Win + R`, type `wf.msc`, press Enter

2. **Create Inbound Rule**:
   - Click "Inbound Rules" → "New Rule"
   - Select "Port" → Next
   - Select "TCP" → Specific local ports: `8001` → Next
   - Select "Allow the connection" → Next
   - Check all profiles → Next
   - Name: "Face Detection GPU Worker" → Finish

3. **Test again from Mac**

## Performance Expectations

| Hardware | Images/Second | 594 Images Time |
|----------|--------------|-----------------|
| RTX 4090 | 80-100 | ~6-8 seconds |
| RTX 4080 | 60-80 | ~8-10 seconds |
| RTX 3090 | 50-70 | ~9-12 seconds |
| RTX 3080 | 40-60 | ~10-15 seconds |
| RTX 3070 | 30-50 | ~12-20 seconds |
| GTX 1080 Ti | 20-30 | ~20-30 seconds |

## Troubleshooting

### "CUDA not available"

**Problem**: PyTorch can't find CUDA
**Solutions**:
1. Reinstall PyTorch with correct CUDA version:
   ```powershell
   pip uninstall torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```
2. Update NVIDIA drivers
3. Restart computer

### "Out of memory" errors

**Problem**: GPU doesn't have enough VRAM
**Solutions**:
1. Close other GPU-intensive applications
2. Reduce batch size in main.py (edit detection size from 640 to 512)
3. Use a lower resolution model

### Can't connect from Mac

**Problem**: Network/firewall blocking connection
**Solutions**:
1. Verify Windows firewall rule (see above)
2. Check both machines are on same network
3. Try pinging Windows from Mac: `ping 192.168.1.100`
4. Temporarily disable Windows firewall to test

### Worker crashes on startup

**Problem**: Missing dependencies or model download issues
**Solutions**:
1. Check Python version (must be 3.10-3.12)
2. Reinstall dependencies: `pip install -r requirements.txt --force-reinstall`
3. Check internet connection (first run downloads ~600MB model)
4. Check disk space (models need ~2GB)

## Running as Windows Service (Optional)

To run GPU worker automatically on Windows startup:

### Option 1: Use Task Scheduler

1. Press `Win + R`, type `taskschd.msc`
2. Create Basic Task
3. Name: "GPU Face Detection Worker"
4. Trigger: "When I log on"
5. Action: "Start a program"
6. Program: `C:\ninav-gpu-worker\venv\Scripts\python.exe`
7. Arguments: `C:\ninav-gpu-worker\main.py`
8. Start in: `C:\ninav-gpu-worker`

### Option 2: Use NSSM (Non-Sucking Service Manager)

1. Download NSSM: https://nssm.cc/download
2. Install as service:
   ```powershell
   nssm install GpuFaceWorker "C:\ninav-gpu-worker\venv\Scripts\python.exe" "C:\ninav-gpu-worker\main.py"
   nssm start GpuFaceWorker
   ```

## Advanced Configuration

### Change Port

Edit `main.py`, change:
```python
port=8001
```

Update firewall rule and Mac `.env` file accordingly.

### Enable Logging

Create `logging_config.json`:
```json
{
  "version": 1,
  "handlers": {
    "file": {
      "class": "logging.FileHandler",
      "filename": "gpu_worker.log",
      "level": "INFO"
    }
  }
}
```

### Monitor GPU Usage

While worker is running:
```powershell
nvidia-smi -l 1
```

This shows live GPU utilization.

## Uninstallation

```powershell
# Stop worker (Ctrl+C)

# Deactivate venv
deactivate

# Delete directory
cd C:\
rmdir /s ninav-gpu-worker
```

## Support

If you encounter issues:
1. Check logs in terminal
2. Verify GPU is working: `nvidia-smi`
3. Test Python imports: `python -c "import insightface; import onnxruntime"`
4. Check network connectivity from Mac

## Next Steps

Once GPU worker is running:
- Start face scanning from Mac frontend
- Monitor performance in Settings modal
- Check GPU usage with `nvidia-smi`
- Enjoy 30-100x faster face detection!
