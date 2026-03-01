# DeepSeek v3 R1 32B Setup Requirements

## Hardware Analysis
- **GPU**: NVIDIA GTX 1060 6GB
- **VRAM**: 6GB (insufficient for 32B model)
- **CUDA**: 12.6 supported
- **Python**: 3.12.6

## Issues Identified
1. **Insufficient VRAM**: 32B model requires ~24GB+ VRAM for full precision
2. **Missing PyTorch**: Need to install PyTorch with CUDA support
3. **Missing dependencies**: Transformers, accelerate, bitsandbytes

## Solutions

### Option 1: Quantized Model (Recommended)
Use 4-bit quantization to reduce VRAM requirements to ~8-12GB:

```bash
# Install dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers accelerate bitsandbytes optimum

# Run with 4-bit quantization
python run_quantized.py
```

### Option 2: CPU + GPU Offloading
Use CPU for most layers, GPU for remaining:

```bash
# Install additional dependencies
pip install auto-gptq

# Run with device_map auto
python run_offload.py
```

### Option 3: Cloud/Remote Inference
Use API endpoints or cloud services with sufficient GPU memory.

## Next Steps
1. Choose your preferred approach
2. I'll create the appropriate script
3. Test with a smaller model first

Which option would you like to proceed with?