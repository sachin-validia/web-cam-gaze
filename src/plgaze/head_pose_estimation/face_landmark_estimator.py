"""Face landmark estimation utilities with optional dependencies.

This module optionally imports heavy dependencies like ``dlib`` and ``face_alignment``.
If these libraries are **not** installed but the corresponding detector modes are **not**
requested, we can still initialize the estimator (e.g. when using ``mediapipe`` only).

This change prevents the entire application from crashing at import-time when those
optional libraries are missing. Instead, we raise a clear error **only** if the user
explicitly selects a detector mode that depends on the missing library.
"""

from typing import List

# Optional heavy dependencies ---------------------------------------------------
try:
    import dlib  # type: ignore
except ModuleNotFoundError:  # pragma: no cover — optional dependency
    dlib = None  # type: ignore

try:
    import face_alignment  # type: ignore
    import face_alignment.detection.sfd  # type: ignore  # noqa: E402
except ModuleNotFoundError:  # pragma: no cover — optional dependency
    face_alignment = None  # type: ignore

# Always-required dependencies ---------------------------------------------------
import mediapipe
import numpy as np
from omegaconf import DictConfig

from plgaze.common import Face


class LandmarkEstimator:
    def __init__(self, config: DictConfig):
        self.mode = config.face_detector.mode
        if self.mode == "dlib":
            # ------------------------------------------------------------------
            # dlib-based detector ------------------------------------------------
            # ------------------------------------------------------------------
            if dlib is None:
                raise ImportError(
                    "face_detector.mode is set to 'dlib' but the 'dlib' package "
                    "is not installed. Install it via `pip install dlib` or choose "
                    "a different detector mode such as 'mediapipe'."
                )
            self.detector = dlib.get_frontal_face_detector()
            self.predictor = dlib.shape_predictor(config.face_detector.dlib_model_path)
        elif self.mode == "face_alignment_dlib":
            # ------------------------------------------------------------------
            # face_alignment with dlib detector ---------------------------------
            # ------------------------------------------------------------------
            if dlib is None or face_alignment is None:
                raise ImportError(
                    "face_detector.mode is 'face_alignment_dlib' but required "
                    "packages are missing. Install 'dlib' and 'face_alignment' "
                    "or use a different detector mode."
                )
            self.detector = dlib.get_frontal_face_detector()
            self.predictor = face_alignment.FaceAlignment(
                face_alignment.LandmarksType._2D,
                face_detector="dlib",
                flip_input=False,
                device=config.device,
            )
        elif self.mode == "face_alignment_sfd":
            # ------------------------------------------------------------------
            # face_alignment with SFD detector ----------------------------------
            # ------------------------------------------------------------------
            if face_alignment is None:
                raise ImportError(
                    "face_detector.mode is 'face_alignment_sfd' but the "
                    "'face_alignment' package is not installed. Install it via "
                    "`pip install face_alignment` or choose a different mode."
                )
            self.detector = face_alignment.detection.sfd.sfd_detector.SFDDetector(
                device=config.device
            )
            self.predictor = face_alignment.FaceAlignment(
                face_alignment.LandmarksType._2D, flip_input=False, device=config.device
            )
        elif self.mode == "mediapipe":
            self.detector = mediapipe.solutions.face_mesh.FaceMesh(
                max_num_faces=config.face_detector.mediapipe_max_num_faces,
                static_image_mode=config.face_detector.mediapipe_static_image_mode,
            )
        else:
            raise ValueError

    def detect_faces(self, image: np.ndarray) -> List[Face]:
        if self.mode == "dlib":
            return self._detect_faces_dlib(image)
        elif self.mode == "face_alignment_dlib":
            return self._detect_faces_face_alignment_dlib(image)
        elif self.mode == "face_alignment_sfd":
            return self._detect_faces_face_alignment_sfd(image)
        elif self.mode == "mediapipe":
            return self._detect_faces_mediapipe(image)
        else:
            raise ValueError

    def _detect_faces_dlib(self, image: np.ndarray) -> List[Face]:
        bboxes = self.detector(image[:, :, ::-1], 0)
        detected = []
        for bbox in bboxes:
            predictions = self.predictor(image[:, :, ::-1], bbox)
            landmarks = np.array(
                [(pt.x, pt.y) for pt in predictions.parts()], dtype=np.float64
            )
            bbox = np.array(
                [[bbox.left(), bbox.top()], [bbox.right(), bbox.bottom()]],
                dtype=np.float64,
            )
            detected.append(Face(bbox, landmarks))
        return detected

    def _detect_faces_face_alignment_dlib(self, image: np.ndarray) -> List[Face]:
        bboxes = self.detector(image[:, :, ::-1], 0)
        bboxes = [
            [bbox.left(), bbox.top(), bbox.right(), bbox.bottom()] for bbox in bboxes
        ]
        predictions = self.predictor.get_landmarks(
            image[:, :, ::-1], detected_faces=bboxes
        )
        if predictions is None:
            predictions = []
        detected = []
        for bbox, landmarks in zip(bboxes, predictions):
            bbox = np.array(bbox, dtype=np.float64).reshape(2, 2)
            detected.append(Face(bbox, landmarks))
        return detected

    def _detect_faces_face_alignment_sfd(self, image: np.ndarray) -> List[Face]:
        bboxes = self.detector.detect_from_image(image[:, :, ::-1].copy())
        bboxes = [bbox[:4] for bbox in bboxes]
        predictions = self.predictor.get_landmarks(
            image[:, :, ::-1], detected_faces=bboxes
        )
        if predictions is None:
            predictions = []
        detected = []
        for bbox, landmarks in zip(bboxes, predictions):
            bbox = np.array(bbox, dtype=np.float64).reshape(2, 2)
            detected.append(Face(bbox, landmarks))
        return detected

    def _detect_faces_mediapipe(self, image: np.ndarray) -> List[Face]:
        h, w = image.shape[:2]
        predictions = self.detector.process(image[:, :, ::-1])
        detected = []
        if predictions.multi_face_landmarks:
            for prediction in predictions.multi_face_landmarks:
                pts = np.array(
                    [(pt.x * w, pt.y * h) for pt in prediction.landmark],
                    dtype=np.float64,
                )
                bbox = np.vstack([pts.min(axis=0), pts.max(axis=0)])
                bbox = np.round(bbox).astype(np.int32)
                detected.append(Face(bbox, pts))
        return detected
