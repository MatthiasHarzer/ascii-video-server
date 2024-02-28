# Ascii Video Server

A python server that converts video files to ascii videos and streams them to the browser.
[See it in action](https://just-a.web.app/).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Setup

- Copy the [docker-compose.yml](docker-compose.yml) file to your server.
- Run `docker-compose up -d` to start the server.
- The server will be available on port `9997` by default.

## Usage

The server provides three endpoints:

### `POST` `/convert`

Converts a video file to an ascii video and stores it on the server. Requires a `file` field in the
request body. Will return the name of the video file on success:

```json
{
    "state": "processing",
    "filename": "[filename]"
}
```

Converted videos will be stored in the `./files` compressed using `gzip`.

### `GET` `/files/{video_name}`

Returns a dictionary of frames as well as some metadata about the video in the following
format:

```json
{
    "frames": {
        "[frame_number]": "[frame_data]"
    },
    "fps": "[frames_per_second]",
    "original_width": "[original_video_width]",
    "original_height": "[original_video_height]"
}
```

`frame_data` is a string of characters that represent the frame. The characters are ordered from top left to bottom
right.

The request can specify the start frame and the number of frames to return using `start_frame` and `frames` query
parameters:
`https://example.com/files/{video_name}?start_frame=0&frames=10` will return the first 10 frames of the video.

### `GET` `/files/{video_name}/info`

Will return some basic info about the video in the following format:

```json
{
    "frames_count": "[number_of_frames]",
    "fps": "[frames_per_second]",
    "original_width": "[original_video_width]",
    "original_height": "[original_video_height]"
}
```

## Limitations
To reduce disk usage, the server will save the converted videos compressed using `gzip`. This means that the server
needs to decompress the video before it can be streamed to the client. For large videos, this can take a while.
To counteract this, the server will keep any video requested for at least 10 minutes in the RAM, resulting in faster
responses for consecutive requests.


## Some Configurations

Some environment variables can be set to configure the server:

| Environment Variable | Explanation                                                                                                |
|----------------------|------------------------------------------------------------------------------------------------------------|
| MAX_PARALLEL_RUNS    | Sets the number of parallel video conversions that can run on the server. Further requests will be denied. |
| ALWAYS_LOADED_FILES  | A comma-seperated list of video files to permanently keep loaded in the RAM for faster access.             |
| API_KEY              | The API key required to access the `/convert` endpoint (`X-API-Key`-header). If unset, the endpoint will be unrestricted.       |

## See Also

The [ascii-web-video-player](https://github.com/MatthiasHarzer/ascii-web-video-player) project, that builds on top of
this server to provide a basic web interface for the ascii videos.
