import logging
import math
from multiprocessing import Process

import cv2
from PIL import Image
from cv2 import Mat

from server.video_file_handler import VideoFileHandler

logger = logging.getLogger("ascii-video-server")
CHARS = ["A", "O", "#", "&", "@", "$", "%", "*", "<", ":", "9", "+", "5", "X", "M"]


class VideoRenderer:
    """
    Renders a video to ascii-coded frames.
    """

    def __init__(self, video: cv2.VideoCapture, width: int, video_name: str):
        """
        Creates a new video renderer, that exports the provided video to an ascii-coded video file.
        :param video: The video to export
        :param width: The width of the ascii art
        :param video_name: The name of the video on the disk
        """
        self.target_width = width
        self.video = video
        self.video_name = video_name
        self.original_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.original_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.number_of_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = int(video.get(cv2.CAP_PROP_FPS))
        self.progress = 0

        if self.number_of_frames == 0:
            raise ValueError("The video has no frames!")

        self.process = Process(target=self._run)

    def _render_frame(self, frame: Mat) -> str:
        """
        Renders a single frame into ascii art.
        :param frame: The frame to render
        :return: The rendered frame as a string
        """
        image = Image.fromarray(frame)
        image = image.convert("L")

        aspect_ratio = image.height / image.width
        height = aspect_ratio * self.target_width * 0.55  # some magic number

        image = image.resize((self.target_width, int(height)))

        pixels_str = ""

        for pixel in image.getdata():
            pixels_str += CHARS[pixel // (math.ceil(255 / len(CHARS)) + 1)]

        pixels_array = [pixels_str[i:i + self.target_width] for i in range(0, len(pixels_str), self.target_width)]

        return "\n".join(pixels_array)

    def _render(self) -> list[str]:
        """
        Renders the video.
        """
        logger.info(f"[{self.video_name}] Starting rendering")

        frames: list[str] = []

        frame_num = 0

        while self.video.isOpened():
            frame_num += 1
            ret, frame = self.video.read()

            if not ret:
                break

            if frame_num % 100 == 0:
                logger.info(f"[{self.video_name}] Processing frame {frame_num} of {self.number_of_frames}")

            self.progress = frame_num / self.number_of_frames

            color_converted_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = self._render_frame(color_converted_frame)
            frames.append(frame)

        self.video.release()

        return frames

    def _run(self) -> None:
        """
        Runs the rendering process.
        """
        frames = self._render()

        logger.info(f"[{self.video_name}] Rendering finished, writing to disk")

        VideoFileHandler.save_video(frames, self.video_name, self.original_width, self.original_height, self.fps)

    def start_render(self) -> None:
        """
        Starts the rendering process.
        """
        self.process.start()
