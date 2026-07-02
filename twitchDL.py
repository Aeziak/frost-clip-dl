import os
import re
import sys
from datetime import datetime
from os import path
from typing import Callable, Generator, Optional

import click
import yaml
from twitchdl import twitch, utils
from twitchdl.commands.download import get_clip_authenticated_url
from twitchdl.http import download_file
from twitchdl.output import (
    green,
    print_clip,
    print_clip_compact,
    print_json,
    print_paged,
    yellow,
)
from twitchdl.twitch import Clip, ClipsPeriod


def _get_clip_access_token_patched(slug: str):
    query = f"""
    {{
        clip(slug: "{slug}") {{
            id
            playbackAccessToken(params: {{
                platform: "web",
                playerBackend: "mediaplayer",
                playerType: "site"
            }}) {{
                signature
                value
            }}
            videoQualities {{
                frameRate
                quality
                sourceURL
            }}
        }}
    }}
    """
    response = twitch.gql_query(query.strip())
    return response["data"]["clip"]


twitch.get_clip_access_token = _get_clip_access_token_patched


def _download_clips(generator: Generator[Clip, None, None], streamerName):
    for clip in generator:
        target = _target_filename(clip)
        today = datetime.today().strftime("%Y-%m-%d")
        directoryPath = "clips/" + streamerName + "/" + today
        print(directoryPath)
        if not path.exists(directoryPath):
            os.makedirs(directoryPath)

        directoryPath = directoryPath + "/" + target
        if path.exists(directoryPath):
            click.echo(f"Already downloaded: {green(directoryPath)}")
        else:
            url = get_clip_authenticated_url(clip["slug"], "source")
            click.echo(f"Downloading: {yellow(directoryPath)}")
            download_file(url, directoryPath)


def _target_filename(clip: Clip):
    url = clip["videoQualities"][0]["sourceURL"]
    _, ext = path.splitext(url)
    ext = ext.lstrip(".")

    match = re.search(r"^(\d{4})-(\d{2})-(\d{2})T", clip["createdAt"])
    if not match:
        raise ValueError(f"Failed parsing date from: {clip['createdAt']}")
    date = "".join(match.groups())

    name = "_".join(
        [
            date,
            clip["id"],
            clip["broadcaster"]["login"],
            utils.slugify(clip["title"]),
        ]
    )

    return f"{name}.{ext}"


with open("streamers.yaml") as stream:
    try:
        streamers = yaml.safe_load(stream)
        for streamer in streamers:
            print(streamer)
            generator = twitch.channel_clips_generator(streamer, "last_day", 100)
            _download_clips(generator, streamer)
    except yaml.YAMLError as exc:
        print(exc)
