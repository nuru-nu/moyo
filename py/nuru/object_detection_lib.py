from ultralytics import YOLO
from collections import defaultdict
import numpy as np
import torch
from nurulib import util


class YOLOSegmentation:
    def __init__(self, model_path, class_ids_filter=None):
        """Initialize the YOLO segmentation model."""

        self.model = YOLO(model_path)
        self.class_ids_filter = class_ids_filter
        self.device: str = 'cpu'
        if torch.backends.mps.is_available():
            util.logger.info("Apple Silicon detected. Using GPU.")
            self.device = 'mps'

    def detect(self, img):
        """Detect objects in the image."""

        height, width, channels = img.shape

        results = self.model.predict(
            source=img.copy(),
            save=False,
            save_txt=False,
            verbose=False,
            device=self.device
        )
        result = results[0]

        self.bboxes = np.array(result.boxes.xyxy.cpu(), dtype="int")
        self.class_ids = np.array(result.boxes.cls.cpu(), dtype="int")
        self.scores = np.array(result.boxes.conf.cpu(), dtype="float").round(2)

        self.segmentations = []
        if result.masks is not None:
            for seg in result.masks.xyn:
                # contours
                seg[:, 0] *= width
                seg[:, 1] *= height
                self.segmentations.append(np.array(seg, dtype=np.int32))

        img_segments = defaultdict(list)
        for class_id, seg, bbox, score in zip(self.class_ids, self.segmentations, self.bboxes, self.scores):
            if self.class_ids_filter is None or class_id in self.class_ids_filter:
                c, r = np.mean(seg, axis=0).astype(int)
                img_segments[class_id].append({
                    "rgb_loc": [c, r],
                    "2D_outline": seg,
                    "bbox": bbox,
                    "score": score,
                    "class_name": self.model.names[int(class_id)],
                })
        return img_segments
