---
name: opencv-patterns
description: OpenCV best practices for computer vision pipelines — image I/O, color spaces, geometric transforms, video decoding, contour analysis, and GPU-accelerated operations with CUDA. Use when writing or reviewing OpenCV-based image/video processing code.
origin: custom
domains: [ai-ml, data, robotics]
technologies: [python, opencv, cuda]
---

# OpenCV Patterns

Best practices for robust, efficient OpenCV-based computer vision pipelines in Python.

## When to Activate

- Reading/writing images or video frames
- Preprocessing images before model inference
- Implementing post-processing (NMS, contour analysis, drawing detections)
- Debugging image pipeline issues (wrong color space, wrong dtype)
- GPU-accelerated image operations (cv2.cuda)

## Core Principles

### 1. Color Space Discipline

OpenCV reads images as BGR, not RGB. Models expect RGB. Always convert explicitly.

```python
# Good: explicit conversion
img_bgr = cv2.imread("frame.jpg")           # HxWx3 uint8 BGR
img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)  # for model input

# Good: VideoCapture → RGB for inference
ret, frame = cap.read()
frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

# Bad: passing BGR directly to PyTorch/PIL model
tensor = transforms.ToTensor()(frame)  # wrong colors, silent bug
```

### 2. dtype and Range Awareness

```python
# uint8: [0, 255]  — disk, display, VideoWriter
# float32: [0.0, 1.0] — model input after normalize
# float32: [0.0, 255.0] — some cv2 operations

# Good: explicit normalization
img = img.astype(np.float32) / 255.0

# Good: safe cast back before VideoWriter
out_frame = (img * 255).clip(0, 255).astype(np.uint8)

# Bad: writing float32 to VideoWriter → garbled output
writer.write(img_float)
```

### 3. VideoCapture Resource Management

```python
# Good: context manager pattern
class VideoReader:
    def __init__(self, path: str):
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            raise IOError(f"Cannot open: {path}")

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.cap.release()

    @property
    def fps(self) -> float:
        return self.cap.get(cv2.CAP_PROP_FPS)

    @property
    def frame_size(self) -> tuple[int, int]:
        w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        return w, h

    def frames(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                break
            yield frame

# Usage
with VideoReader("input.mp4") as reader:
    for frame in reader.frames():
        process(frame)
```

### 4. VideoWriter Codec Selection

```python
# 4K H.264 output — most compatible
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter("out.mp4", fourcc, fps, (width, height))

# High quality lossless (large files)
fourcc = cv2.VideoWriter_fourcc(*"FFV1")

# Always verify writer opened
if not writer.isOpened():
    raise RuntimeError("VideoWriter failed to open — check codec/path")

# Always release
try:
    for frame in frames:
        writer.write(frame)
finally:
    writer.release()
```

## Image Preprocessing for Inference

### Letterbox Resize (preserves aspect ratio)

```python
def letterbox(
    img: np.ndarray,
    target_size: tuple[int, int] = (640, 640),
    color: tuple[int, int, int] = (114, 114, 114),
) -> tuple[np.ndarray, float, tuple[int, int]]:
    """Resize with padding. Returns (padded_img, scale, (pad_w, pad_h))."""
    h, w = img.shape[:2]
    th, tw = target_size
    scale = min(tw / w, th / h)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    pad_w = (tw - new_w) // 2
    pad_h = (th - new_h) // 2
    padded = cv2.copyMakeBorder(
        resized, pad_h, th - new_h - pad_h, pad_w, tw - new_w - pad_w,
        cv2.BORDER_CONSTANT, value=color,
    )
    return padded, scale, (pad_w, pad_h)
```

### Batch Preparation

```python
def prepare_batch(frames: list[np.ndarray], size: int = 640) -> np.ndarray:
    """BGR frames → float32 NCHW tensor ready for model."""
    batch = []
    for f in frames:
        f, _, _ = letterbox(f, (size, size))
        f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        f = f.astype(np.float32) / 255.0
        batch.append(f)
    arr = np.stack(batch)          # NHWC
    return arr.transpose(0, 3, 1, 2)  # NCHW
```

## Detection Post-processing

### Draw Bounding Boxes

```python
def draw_detections(
    img: np.ndarray,
    boxes: list[tuple[int, int, int, int]],
    labels: list[str],
    scores: list[float],
    colors: dict[str, tuple[int, int, int]] | None = None,
) -> np.ndarray:
    out = img.copy()
    for (x1, y1, x2, y2), label, score in zip(boxes, labels, scores):
        color = (colors or {}).get(label, (0, 255, 0))
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {score:.2f}"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
        cv2.rectangle(out, (x1, y1 - th - 6), (x1 + tw, y1), color, -1)
        cv2.putText(out, text, (x1, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1)
    return out
```

### Coordinate Rescaling (after letterbox)

```python
def rescale_boxes(
    boxes: np.ndarray,
    scale: float,
    pad: tuple[int, int],
    orig_shape: tuple[int, int],
) -> np.ndarray:
    """Map boxes from letterboxed space back to original image space."""
    boxes = boxes.copy().astype(float)
    pad_w, pad_h = pad
    boxes[:, [0, 2]] = (boxes[:, [0, 2]] - pad_w) / scale
    boxes[:, [1, 3]] = (boxes[:, [1, 3]] - pad_h) / scale
    h, w = orig_shape
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, w)
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, h)
    return boxes.astype(int)
```

## CUDA-Accelerated Operations

```python
# Check CUDA support at runtime
cuda_available = cv2.cuda.getCudaEnabledDeviceCount() > 0

# Upload/download
gpu_mat = cv2.cuda_GpuMat()
gpu_mat.upload(cpu_frame)

# GPU resize
gpu_resized = cv2.cuda.resize(gpu_mat, (640, 640))

# GPU color convert
gpu_rgb = cv2.cuda.cvtColor(gpu_mat, cv2.COLOR_BGR2RGB)

# Download back
cpu_result = gpu_resized.download()
```

## Common Pitfalls

| Symptom | Cause | Fix |
|---|---|---|
| Colors look wrong | BGR not converted to RGB | `cv2.cvtColor(img, cv2.COLOR_BGR2RGB)` |
| `VideoWriter` writes black frames | float32 input instead of uint8 | Cast to uint8 before `writer.write()` |
| Blurry detections on 4K video | `cv2.INTER_NEAREST` resize | Use `cv2.INTER_LINEAR` or `INTER_AREA` |
| Memory leak in long video | `cap.release()` not called | Use context manager pattern |
| `cap.read()` returns wrong shape | CAP_PROP not queried before first read | Query props after first successful `read()` |
| AV1/HEVC decode fails | OpenCV doesn't support codec | Fall back to PyAV (`av` package) |
