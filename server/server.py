import math
import tempfile
import time
from typing import Any

import cv2
from PIL import Image
from fastapi import FastAPI, UploadFile

from server.stoppable_thread import StoppableThread
from server.video_worker import VideoWorker

CHARS = ["A", "O", "#", "&", "@", "$", "%", "*", "<", ":", "9", '+', '5', 'X', 'M']
CACHE: dict[str, VideoWorker] = {}
CLEANUP: dict[str, StoppableThread] = {}

app = FastAPI()


def get_video_worker(filename: str) -> VideoWorker:
    """
    Returns the video worker for the given filename.
    :param filename: The filename
    :return: The video worker
    """

    if filename not in CACHE:
        CACHE[filename] = VideoWorker(filename)

    return CACHE[filename]


def schedule_cleanup(filename: str) -> None:
    """
    Schedules the given filename for cleanup.
    :param filename: The filename
    """
    existing_thread = CLEANUP.get(filename)

    if existing_thread:
        existing_thread.terminate()

    def cleanup() -> None:
        """
        Cleans up the cache.
        """
        time.sleep(10 * 60)
        if CACHE.get(filename):
            del CACHE[filename]

    CLEANUP[filename] = StoppableThread(target=cleanup)
    CLEANUP[filename].start()


def convert_frame_to_ascii(frame: Any, width: int) -> str:
    """
    Converts the given frame to ascii art.
    :param frame: The frame to convert
    :param width: The width of the ascii art
    :return: The ascii art
    """

    image = Image.fromarray(frame)
    image = image.convert("L")

    aspect_ratio = image.width / image.height

    height = aspect_ratio * width * 0.55

    image = image.resize((width, int(height)))

    pixels_str = ""

    for pixel in image.getdata():
        pixels_str += CHARS[pixel // (math.ceil(255 / len(CHARS)) + 1)]

    pixels_array = [pixels_str[i:i + width] for i in range(0, len(pixels_str), width)]

    return "\n".join(pixels_array)


def convert_video_to_ascii(video: cv2.VideoCapture, width: int) -> list[str]:
    """
    Converts the video to ascii art.
    :param width: The width of the ascii art
    :param video: The file to convert
    :return: The ascii art
    """

    frames: list[str] = []

    while video.isOpened():
        ret, frame = video.read()

        if not ret:
            break

        color_converted_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(convert_frame_to_ascii(color_converted_frame, width))

    video.release()
    return frames


@app.post("/convert")
async def convert_uploaded(file: UploadFile, width: int = 240):
    print(file.filename, width)

    with tempfile.NamedTemporaryFile() as temp:
        temp.write(file.file.read())
        temp.flush()
        video = cv2.VideoCapture(temp.name)

        original_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = int(video.get(cv2.CAP_PROP_FPS))

        frames = convert_video_to_ascii(video, width)

        filename = file.filename.split(".")[0]

        VideoWorker.save_video(frames, filename, original_width, original_height, fps)

        return {"filename": filename, "width": original_width, "height": original_height, "fps": fps}


@app.get("/files/{filename}")
async def get_file(filename: str, frames: int = 0, reference_id: str = None):
    worker = get_video_worker(filename)

    schedule_cleanup(filename)

    if frames <= 0:
        return {"frames": worker.frames}

    if reference_id is None:
        reference_id = worker.new_client()

    frames = worker.advance_frames(reference_id, frames)

    return {
        "frames": frames,
        "reference_id": reference_id,
        "completed": worker.completed(reference_id),
        "fps": worker.fps,
        "original_width": worker.original_width,
        "original_height": worker.original_height
    }


@app.get("/files/{filename}/info")
async def get_file_info(filename: str):
    worker = get_video_worker(filename)

    return {
        "frames_count": len(worker.frames),
        "fps": worker.fps,
        "original_width": worker.original_width,
        "original_height": worker.original_height
    }
