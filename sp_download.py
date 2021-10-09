#!/usr/bin/env python3

import os
import threading
import subprocess
import glob
import platform
import time
import argparse
import sys
import json
#  external dependencies
import unidecode  # pip install unidecode
import yt_dlp  # pip install youtube-dl
import requests

# config options
from dl_opts import *

multi_language = False

DE_BASE_URL = "https://www.southpark.de"
EN_BASE_URL = "https://www.southparkstudios.com"
CONF = {
    "deu": {
        "url": DE_BASE_URL,
        "token": "F",
        "opts": ydl_opts_de
    },
    "eng": {
        "url": EN_BASE_URL,
        "token": "E",
        "opts": ydl_opts_en
    }
}
LANG_DE = "deu"
LANG_EN = "eng"
API_URL = "/api/episodes"
CACHE = ".cache"
SEPARATOR = " • "


def filter_season(episodes: list, season):
    # format of title is e.g. 'S1 • F13'
    filtered = [e for e in episodes if f"S{int(season)}" == e['meta']['header']['title'].split(SEPARATOR)[0]]
    return filtered


def filter_episode(episodes: list, episode, token="E"):
    # format of title is e.g. 'S1 • F13' or 'S1 • E13', pass token for splitting  for language
    filtered = [e for e in episodes if f"{token}{int(episode)}" == e['meta']['header']['title'].split(SEPARATOR)[1]]
    return filtered


def get_download_links(base_url: str, episodes: list):
    links = list()
    for e in episodes:
        link = f"{base_url}{e['url']}"
        links.append(link)
    return links


def get_episode(episodes: list, season, episode, lang: str = LANG_EN):
    filtered = filter_season(episodes, season)
    filtered = filter_episode(filtered, episode, CONF[lang]["token"])
    return filtered


def get_episode_by_id(episodes: list, id):
    filtered = [e for e in episodes if id == e['id']]
    return filtered


def request_all_episodes(lang: str = "eng", force_refresh=False):
    cache_file = f".cache.{lang}"
    episodes = list()
    if not os.path.isfile(cache_file) or force_refresh:
        load_more = {'url': "/api/episodes/1/25"}
        base_url = CONF[lang]["url"]

        while load_more is not None:
            r = requests.get(f"{base_url}{load_more['url']}")
            j_resp = json.loads(r.content)
            # check if there is more to load
            load_more = j_resp['loadMore']
            # add items from current page to episode list
            episodes.extend(j_resp['items'])
            # throttle download a little bit
            time.sleep(1)

        with open(cache_file, "w") as f:
            json.dump(episodes, f)


def get_episodes(lang: str = LANG_EN):
    cache_file = f".cache.{lang}"
    if not os.path.isfile(cache_file):
        request_all_episodes(lang)
    with open(cache_file, "r") as f:
        episodes = json.load(f)
    return episodes


def download_episode_internal(season, episode, lang):
    print(f"[Download start] S{season}E{episode} {lang}")
    english_episodes = get_episodes()
    e = get_episode(english_episodes, season, episode)
    if lang == LANG_DE:
        episodes = get_episodes(lang)
        e = get_episode_by_id(episodes, e[0]['id'])
    links = get_download_links(CONF[lang]["url"], e)
    opts = CONF[lang]["opts"]
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download(links)
    print(f"[Download finished] S{season}E{episode} {lang}")


def download_episode_lang(season, episode, lang: str):
    download_episode_internal(season, episode, lang)
    merge_episode(season, episode)


def download_episode(season, episode):
    print(f"[Start] S{season}E{episode}")
    if os.path.isfile(f"South_Park_S{int(season):02d}E{int(episode):02d}.mp4"):
        print("Episode already exists, skip download")
        return
    if multi_language:
        deu_thread = threading.Thread(target=download_episode_internal, args=(season, episode, LANG_DE))
        deu_thread.start()

    en_thread = threading.Thread(target=download_episode_internal, args=(season, episode, LANG_EN))
    en_thread.start()
    en_thread.join()
    if multi_language:
        deu_thread.join()
    merge_episode(season, episode)
    clean_up()
    print(f"[End] S{season}E{episode}")


def create_file_list(season, episode, lang: str):
    f_season = f"{int(season):02d}"
    f_episode = f"{int(episode):02d}"
    print(f"[Create file list] S{f_season}E{f_episode} {lang}")
    file_list_name = f"files_{f_season}{f_episode}_{lang}.txt"
    with open(file_list_name, mode="w+") as file_list:
        for f in sorted(glob.glob(f"*download_{lang}*?m*")):
            file_list.write("file '" + f + "'\n")
    return file_list_name


def merge_episode(season, episode):
    for f in glob.glob(f"*_download_*?m*"):
        os.rename(f, make_safe(f.replace(" ", "")))

    ffmpeg_binary = "ffmpeg.exe" if (platform.system() == "Windows") else "ffmpeg"
    episode_name = f"South_Park_S{int(season):02d}E{int(episode):02d}"
    video_list = create_file_list(season, episode, "eng")
    if multi_language:
        audio_list = create_file_list(season, episode, "deu")

    if multi_language:
        print(f"[merge german audio tracks] S{season}E{episode}")
        ffmpeg_concat_audio_command = f"{ffmpeg_binary} -f concat -i {audio_list} -c copy -scodec copy {episode_name}_temp.m4a"
        subprocess.call(ffmpeg_concat_audio_command, shell=True)

        print(f"[merge english video tracks] S{season}E{episode}")
        ffmpeg_concat_video_command = f"{ffmpeg_binary} -f concat -i {video_list} -c copy -scodec copy {episode_name}_temp.mp4"
        print(ffmpeg_concat_video_command)
        subprocess.call(ffmpeg_concat_video_command, shell=True)

        print(f"[add german audio track to video] S{season}E{episode}")
        ffmpeg_add_audio_command = f"{ffmpeg_binary} -i {episode_name}_temp.mp4 -i {episode_name}_temp.m4a -c copy -map 0:v:0  -map 1:a:0 -map 0:a:0 -map 0:s:0? -metadata:s:a:0 language=ger -metadata:s:a:1 language=eng {episode_name}.mp4"
        subprocess.call(ffmpeg_add_audio_command, shell=True)

    else:
        print(f"[merge english video tracks] S{season}E{episode}")
        ffmpeg_concat_video_command = f"{ffmpeg_binary} -f concat -i {video_list} -c copy -scodec copy {episode_name}.mp4"
        subprocess.call(ffmpeg_concat_video_command, shell=True)


def make_safe(unsafe_string):
    def safe_char(c):
        if c.isalnum():
            return c
        elif c == ".":
            return "."
        else:
            return "_"

    return unidecode.unidecode("".join(safe_char(c) for c in unsafe_string).rstrip("_"))


def clean_up():
    for f in glob.glob("*_temp*?m*"):
        os.remove(f)
    for f in glob.glob("*_download_*"):
        os.remove(f)
    for f in glob.glob("file*"):
        os.remove(f)


def download_season(season):
    episodes = get_episodes()
    filtered = filter_season(episodes, season)
    for episode in range(1, len(filtered)):
        download_episode(season, episode)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--multilanguage", dest="multilanguage",
                        help="If activated stores video with german and english audio", action="store_true",
                        default=False)
    parser.add_argument("-e", "--episode", dest="episode", help="Download specific episode, e.g. 02:03", type=str)
    parser.add_argument("-s", "--season", dest="season", help="Download a whole season", type=int)
    parser.add_argument("-l", "--language", dest="language", help="Specify language, can be deu or eng", type=str)
    parser.add_argument("-r", "--refresh", dest="refresh", help="Refresh cache files", type=bool)
    args = parser.parse_args()
    multi_language = args.multilanguage
    clean_up()

    if args.episode is not None and args.season is not None:
        print("Use either -e or -s option!")
        sys.exit(1)

    if args.episode is not None:
        split = args.episode.split(":")
        season = f"{int(split[0]):02d}"
        episode = f"{int(split[1]):02d}"
        if args.language:
            download_episode_lang(season, episode, args.language)
        else:
            download_episode(season, episode)

    if args.season is not None:
        download_season(args.season)

    time.sleep(5)
    print("Clean up temporary data")
    clean_up()
