---
name: yolo-object-detection
description: YOLOv8/YOLO object detection patterns using Ultralytics — inference, training, SAHI sliced inference for small objects, export (ONNX/TensorRT), and ROS 2 integration. Use when building or debugging YOLO-based detection pipelines.
origin: custom
domains: [ai-ml, robotics, data]
technologies: [python, pytorch, opencv, cuda]
---

# YOLO Object Detection Patterns

Patterns for production-quality YOLO detection pipelines using Ultralytics, with emphasis on small-object detection via SAHI and ROS 2 deployment.

## When to Activate

- Running or debugging YOLO inference
- Training or fine-tuning YOLO models
- Implementing SAHI sliced inference
- Exporting models (ONNX, TensorRT)
- Integrating detection into a ROS 2 node
- Debugging class confusion, missed detections, or low mAP

## Core Inference Pattern

```python
from ultralytics import YOLO
import cv2

model = YOLO("model/best.pt")

# Basic inference — returns list of Results
results = model(
    source="frame.jpg",
    imgsz=640,
    conf=0.25,
    iou=0.45,
    device="cuda:0",
    half=True,       # FP16 — ~2x faster on A6000, minimal accuracy loss
    verbose=False,
)

# Extract detections
for r in results:
    boxes = r.boxes.xyxy.cpu().numpy()   # (N, 4) x1y1x2y2
    confs = r.boxes.conf.cpu().numpy()   # (N,)
    cls   = r.boxes.cls.cpu().numpy().astype(int)  # (N,)
    names = [model.names[c] for c in cls]
```

## SAHI Sliced Inference (small objects in 4K)

```python
from sahi import AutoDetectionModel
from sahi.predict import get_sliced_prediction

detection_model = AutoDetectionModel.from_pretrained(
    model_type="ultralytics",
    model_path="model/best.pt",
    confidence_threshold=0.25,
    device="cuda:0",
)

result = get_sliced_prediction(
    image="frame.jpg",          # path or np.ndarray (RGB)
    detection_model=detection_model,
    slice_height=640,
    slice_width=640,
    overlap_height_ratio=0.25,
    overlap_width_ratio=0.25,
    perform_standard_pred=True,  # also run full-image pass
    postprocess_type="NMM",      # NMM better than NMS for crowded scenes
    postprocess_match_threshold=0.5,
)

# Access detections
for obj in result.object_prediction_list:
    bbox = obj.bbox.to_xyxy()   # [x1, y1, x2, y2]
    label = obj.category.name
    score = obj.score.value
```

### SAHI for Video (batched, memory-efficient)

```python
import av
from sahi.predict import get_sliced_prediction

def process_video_sahi(
    input_path: str,
    output_path: str,
    detection_model,
    slice_size: int = 640,
    overlap: float = 0.25,
) -> None:
    container = av.open(input_path)
    stream = container.streams.video[0]
    fps = float(stream.average_rate)
    w = stream.codec_context.width
    h = stream.codec_context.height

    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (w, h),
    )

    try:
        for packet in container.demux(stream):
            for frame in packet.decode():
                # PyAV → numpy RGB
                img_rgb = frame.to_ndarray(format="rgb24")

                result = get_sliced_prediction(
                    image=img_rgb,
                    detection_model=detection_model,
                    slice_height=slice_size,
                    slice_width=slice_size,
                    overlap_height_ratio=overlap,
                    overlap_width_ratio=overlap,
                    verbose=0,
                )

                # Draw and write BGR
                img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
                for obj in result.object_prediction_list:
                    x1, y1, x2, y2 = map(int, obj.bbox.to_xyxy())
                    label = f"{obj.category.name} {obj.score.value:.2f}"
                    cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(img_bgr, label, (x1, y1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
                writer.write(img_bgr)
    finally:
        writer.close()
        writer.release()
```

## Training Patterns

### Two-phase Fine-tuning (backbone freeze → unfreeze)

```python
from ultralytics import YOLO

model = YOLO("yolo11x.pt")  # or best.pt for domain fine-tune

# Phase 1: freeze backbone, train head only
model.train(
    data="dataset.yaml",
    epochs=30,
    imgsz=640,
    batch=16,
    freeze=10,          # freeze first 10 layers (backbone)
    lr0=1e-3,
    device="cuda:0",
    half=True,
    project="runs/phase1",
    name="freeze_backbone",
    exist_ok=True,
)

# Phase 2: unfreeze end-to-end
model = YOLO("runs/phase1/freeze_backbone/weights/best.pt")
model.train(
    data="dataset.yaml",
    epochs=60,
    imgsz=640,
    batch=8,
    freeze=0,           # all layers trainable
    lr0=1e-4,           # lower LR for fine-tune
    warmup_epochs=3,
    device="cuda:0",
    half=True,
    project="runs/phase2",
    name="full_finetune",
    exist_ok=True,
)
```

### Dataset YAML (nc=3, traffic lights)

```yaml
path: /workspace/datasets/merged_yolo
train: images/train
val: images/val
test: images/test

nc: 3
names:
  0: traffic_light
  1: pedestrian_signal
  2: traffic_signs
```

### Incremental Fine-tune (domain shift)

```python
# Fine-tune best.pt on new domain WITHOUT changing nc
model = YOLO("model/best.pt")
model.train(
    data="new_domain.yaml",
    epochs=20,
    imgsz=640,
    batch=8,
    lr0=5e-5,        # very low LR — preserve existing weights
    freeze=10,       # freeze backbone for stability
    device="cuda:0",
    half=True,
)
```

## Export

```python
# ONNX (CPU/GPU portable)
model.export(format="onnx", imgsz=640, half=False, dynamic=True)

# TensorRT FP16 (fastest on NVIDIA, A6000 target)
model.export(
    format="engine",
    imgsz=640,
    half=True,
    device="cuda:0",
    workspace=8,     # GB — A6000 has 48GB VRAM, workspace can be larger
)
```

## ROS 2 Node Integration

```python
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
from ultralytics import YOLO
import cv2

class YoloDetectorNode(Node):
    def __init__(self):
        super().__init__("yolo_detector")
        self.model = YOLO(
            self.declare_parameter("model_path", "model/best.pt")
                .get_parameter_value().string_value
        )
        self.conf = self.declare_parameter("conf", 0.25).get_parameter_value().double_value
        self.bridge = CvBridge()
        self.sub = self.create_subscription(Image, "/camera/image_raw", self.cb, 10)
        self.pub = self.create_publisher(Image, "/detections/image", 10)

    def cb(self, msg: Image) -> None:
        frame = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")
        results = self.model(frame, conf=self.conf, verbose=False)
        annotated = results[0].plot()
        out_msg = self.bridge.cv2_to_imgmsg(annotated, encoding="bgr8")
        out_msg.header = msg.header
        self.pub.publish(out_msg)

def main():
    rclpy.init()
    node = YoloDetectorNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()
```

## Debugging Checklist

| Symptom | Likely Cause | Fix |
|---|---|---|
| Low recall on distant objects | Full-image inference misses small objects | Enable SAHI slicing |
| Class confusion between classes | Insufficient training samples for minority class | Augment / oversample |
| mAP drops after incremental fine-tune | LR too high, catastrophic forgetting | Lower `lr0`, increase `freeze` layers |
| VRAM OOM during training | Batch too large | Reduce `batch`, enable `half=True` |
| Inference slow on 4K video | Single-frame CPU decode bottleneck | Use PyAV + batch frames |
| Detection boxes misaligned | Wrong image size fed to model | Use letterbox; check `imgsz` matches export |
| `nc` mismatch error on load | Fine-tuning changed class count | Never change `nc` when fine-tuning `best.pt` |
| TensorRT export fails | Wrong CUDA/TensorRT version pairing | Match TRT to CUDA 12.6 in container |

## VRAM Estimation

| Config | Approx VRAM |
|---|---|
| YOLOv8x inference FP32, batch=1 | ~3 GB |
| YOLOv8x inference FP16, batch=8 | ~6 GB |
| YOLOv8x training FP16, batch=16 | ~18 GB |
| SAHI 4K (100 slices), batch=1 | ~4 GB |
| TensorRT FP16 engine, batch=8 | ~5 GB |

A6000 (48 GB) fits all configs comfortably.
