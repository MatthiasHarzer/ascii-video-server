import logging
import math
import tempfile
import time
from typing import Any

import cv2
from PIL import Image
from fastapi import FastAPI, UploadFile, HTTPException

from server.stoppable_thread import StoppableThread
from server.video_worker import VideoWorker

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

CHARS = ["A", "O", "#", "&", "@", "$", "%", "*", "<", ":", "9", '+', '5', 'X', 'M']
CACHE: dict[str, VideoWorker] = {}
CLEANUP: dict[str, StoppableThread] = {}
RUNNER: dict[str, StoppableThread] = {}
PROGRESS: dict[str, float] = {}

MAX_PARALLEL_RUNS = 2

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

    aspect_ratio = image.height / image.width

    height = aspect_ratio * width * 0.55

    image = image.resize((width, int(height)))

    pixels_str = ""

    for pixel in image.getdata():
        pixels_str += CHARS[pixel // (math.ceil(255 / len(CHARS)) + 1)]

    pixels_array = [pixels_str[i:i + width] for i in range(0, len(pixels_str), width)]

    return "\n".join(pixels_array)


def convert_video_to_ascii(filename: str, video: cv2.VideoCapture, width: int) -> list[str]:
    """
    Converts the video to ascii art.
    :param filename: The filename
    :param width: The width of the ascii art
    :param video: The file to convert
    :return: The ascii art
    """

    frames: list[str] = []

    number_of_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))

    frame_num = 0

    while video.isOpened():
        frame_num += 1
        ret, frame = video.read()

        if not ret:
            break

        if frame_num % 100 == 0:
            logging.info(f"[{filename}] Processing frame {frame_num} of {number_of_frames}...")

        PROGRESS[filename] = frame_num / number_of_frames

        color_converted_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(convert_frame_to_ascii(color_converted_frame, width))

    video.release()
    return frames


def convert_runner(video: cv2.VideoCapture, width: int, filename: str) -> None:
    original_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(video.get(cv2.CAP_PROP_FPS))

    logging.info(f"[{filename}] Starting processing.")

    frames = convert_video_to_ascii(filename, video, width)

    filename = filename.split(".")[0]

    VideoWorker.save_video(frames, filename, original_width, original_height, fps)

    logging.info(f"[{filename}] Finished processing.")

    del RUNNER[filename]
    del PROGRESS[filename]


@app.post("/convert")
async def convert_uploaded(file: UploadFile, width: int = 240):
    filename = ".".join(file.filename.split(".")[:-1])

    logging.info(f"Received file {file.filename}.")

    if filename in RUNNER:
        raise HTTPException(status_code=409, detail="File is already processing")

    if len(RUNNER) >= MAX_PARALLEL_RUNS:
        raise HTTPException(status_code=409, detail="Too many parallel runs")

    with tempfile.NamedTemporaryFile() as temp:
        temp.write(file.file.read())
        temp.flush()
        video = cv2.VideoCapture(temp.name)

        thread = StoppableThread(target=convert_runner, args=(video, width, filename))
        thread.start()

        RUNNER[filename] = thread

        return {
            "state": "processing",
            "filename": filename
        }


@app.get("/files/{filename}")
async def get_file(filename: str, start_frame: int = 0, frames: int = 0):
    if filename in RUNNER:
        raise HTTPException(status_code=409, detail={
            "state": "processing",
            "progress": round(PROGRESS[filename] * 10000) / 100,
            "message": "File is still processing"
        })

    worker = get_video_worker(filename)

    schedule_cleanup(filename)

    if frames <= 0:
        return {
            "frames": worker.get_all_frames()
        }

    frames = worker.get_frames(start_frame, frames)

    return {
        "frames": frames,
        "fps": worker.fps,
        "original_width": worker.original_width,
        "original_height": worker.original_height
    }


@app.get("/files/{filename}/info")
async def get_file_info(filename: str):
    if filename in RUNNER:
        raise HTTPException(status_code=409, detail={
            "state": "processing",
            "progress": f"{round(PROGRESS[filename] * 10000) / 100} %",
            "message": "File is still processing"
        })

    worker = get_video_worker(filename)

    return {
        "frames_count": len(worker.frames),
        "fps": worker.fps,
        "original_width": worker.original_width,
        "original_height": worker.original_height
    }
