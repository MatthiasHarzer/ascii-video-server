import logging
from threading import Timer

from server.video_file_handler import VideoFileHandler

logger = logging.getLogger("ascii-video-server")

CACHE: dict[str, VideoFileHandler] = {}
TIMEOUT = 10 * 60  # 10 minutes
_TIMERS: dict[str, Timer] = {}


def _cleanup(video_name: str) -> None:
    """
    Cleans up the cache.
    :param video_name: The video name
    """
    if video_name in CACHE:
        logger.info(f"Cleaning up {video_name}")
        del CACHE[video_name]


def _schedule_cleanup(video_name: str) -> None:
    """
    Schedules the given video name for cleanup.
    :param video_name: The video name
    """
    if video_name in _TIMERS:
        _TIMERS[video_name].cancel()
    _TIMERS[video_name] = Timer(TIMEOUT, lambda: _cleanup(video_name))
    _TIMERS[video_name].start()


def get_video_worker(video_name: str, no_cleanup: bool = False) -> VideoFileHandler:
    """
    Returns the video worker for the given video name.
    :param video_name: The video name
    :param no_cleanup: Whether to skip the cleanup
    :return: The video worker
    """

    if video_name not in CACHE:
        CACHE[video_name] = VideoFileHandler(video_name)

    if not no_cleanup:
        _schedule_cleanup(video_name)

    return CACHE[video_name]
