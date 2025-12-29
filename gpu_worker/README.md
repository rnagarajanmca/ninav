# GPU Worker for Face Detection

High-performance face detection service using InsightFace with CUDA acceleration.

## Overview

The GPU Worker is an optional component that accelerates face detection by 30-100x using NVIDIA GPUs. It runs as a standalone FastAPI service and can be deployed on:

- Local Windows/Linux machine with NVIDIA GPU
- Cloud GPU instances (AWS, GCP, RunPod, etc.)
- Remote servers with GPU access

## Features

- **🚀 Fast**: 50-100 images/second vs 1-2 images/second on CPU
- **🎯 Accurate**: State-of-the-art InsightFace model (99.8% accuracy on LFW)
- **🔌 Plug-and-Play**: Works with main backend via simple HTTP API
- **🔄 Auto-Fallback**: Main backend falls back to CPU if GPU unavailable
- **📊 Better Embeddings**: 512-dimensional vs 128-dimensional

## Quick Start

### Prerequisites

- **NVIDIA GPU** (GTX 1060 or better)
- **CUDA 11.8 or 12.x**
- **Python 3.10-3.12**
- **8GB+ RAM**

### Installation

```bash
# 1. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Install PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# 3. Install dependencies
pip install -r requirements.txt

# 4. Start worker
python main.py
```

### Verify Installation

```bash
# Check health
curl http://localhost:8001

# Expected response:
# {"status":"healthy","gpu_available":true,"model_loaded":true,"device":"CUDA (NVIDIA GPU)"}
```

## Configuration

### Backend Setup

On your main application server, set the GPU worker URL:

```bash
# In your .env file
GPU_WORKER_URL=http://<gpu-worker-ip>:8001
```

Then restart your backend:
```bash
docker compose restart backend
```

### Network Setup

**Firewall (Windows)**:
- Allow inbound TCP port 8001
- Windows Firewall → Inbound Rules → New Rule → Port 8001

**Firewall (Linux)**:
```bash
sudo ufw allow 8001/tcp
```

## API Endpoints

### Health Check
```http
GET /
```

Response:
```json
{
  "status": "healthy",
  "gpu_available": true,
  "model_loaded": true,
  "device": "CUDA (NVIDIA GPU)"
}
```

### Detect Faces
```http
POST /detect
Content-Type: multipart/form-data
```

Parameters:
- `file`: Image file (JPG, PNG, etc.)

Response:
```json
{
  "faces": [
    {
      "bbox_x": 100,
      "bbox_y": 150,
      "bbox_width": 200,
      "bbox_height": 220,
      "embedding": [0.123, ...],  // 512-dimensional
      "confidence": 0.98,
      "landmarks": [[x1, y1], ...]  // 5 facial keypoints
    }
  ],
  "image_width": 1920,
  "image_height": 1080,
  "processing_time_ms": 12.5
}
```

## Performance

### Speed Comparison

| Hardware | Images/Second | 1000 Images |
|----------|--------------|-------------|
| CPU (dlib) | 1-2 | ~8-16 hours |
| GTX 1080 Ti | 20-30 | ~30-50 sec |
| RTX 3070 | 30-50 | ~20-35 sec |
| RTX 3080 | 50-80 | ~12-20 sec |
| RTX 4090 | 80-120 | ~8-12 sec |

### Model Details

- **Model**: buffalo_l (InsightFace)
- **Input Size**: 640x640
- **Embedding**: 512-dimensional
- **Accuracy**: 99.8% (LFW benchmark)

## Deployment Options

### Option 1: Local Machine

Best for home labs and always-on setups.

```bash
python main.py
```

### Option 2: Cloud GPU

**RunPod** (~$0.20/hour for RTX 4090):
```bash
# Deploy via RunPod CLI or web interface
# Point GPU_WORKER_URL to RunPod instance
```

**AWS EC2** (g4dn instances):
```bash
# Launch g4dn.xlarge instance
# Install dependencies and run worker
```

### Option 3: Windows Service

Run worker automatically on startup:

```powershell
# Using NSSM (Non-Sucking Service Manager)
nssm install GpuFaceWorker "C:\path\to\venv\Scripts\python.exe" "C:\path\to\main.py"
nssm start GpuFaceWorker
```

## Troubleshooting

### CUDA Not Available

**Problem**: `gpu_available: false`

**Solutions**:
1. Update NVIDIA drivers
2. Reinstall PyTorch with correct CUDA version:
   ```bash
   pip uninstall torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```
3. Verify CUDA: `nvidia-smi`

### Out of Memory

**Problem**: GPU runs out of VRAM

**Solutions**:
1. Close other GPU applications
2. Reduce detection size in `main.py`:
   ```python
   face_analyzer.prepare(ctx_id=0, det_size=(512, 512))  # Reduced from 640
   ```
3. Use smaller model: `buffalo_s` instead of `buffalo_l`

### Connection Refused

**Problem**: Cannot connect from main backend

**Solutions**:
1. Check firewall rules
2. Verify worker is running: `curl http://localhost:8001`
3. Check network connectivity: `ping <gpu-worker-ip>`
4. Ensure port 8001 is not in use: `netstat -an | grep 8001`

## Advanced Configuration

### Change Port

Edit `main.py`:
```python
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)  # Changed from 8001
```

### Use Different GPU

```python
# In main.py, change ctx_id
face_analyzer.prepare(ctx_id=1, det_size=(640, 640))  # Use GPU 1
```

### Enable Logging

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Monitoring

### GPU Usage

```bash
# Live GPU stats
nvidia-smi -l 1

# Or use this one-liner
watch -n 1 nvidia-smi
```

### Worker Logs

```bash
# With uvicorn
python main.py --log-level info

# Or redirect to file
python main.py > worker.log 2>&1
```

## Development

### Running Tests

```bash
pytest tests/
```

### API Testing

```bash
# Test with sample image
curl -X POST http://localhost:8001/detect \
  -F "file=@test_image.jpg" \
  | jq
```

## Security

- Worker has no authentication by default
- Intended for use on trusted networks
- For internet exposure, add reverse proxy with auth (nginx + basic auth)

## License

Same as main project (MIT)

## Support

For issues or questions:
- Main project: [GitHub Issues](https://github.com/rnagarajanmca/ninav/issues)
- GPU-specific: Tag with `gpu-worker` label
