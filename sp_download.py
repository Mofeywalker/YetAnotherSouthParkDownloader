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

multilanguage = False

DE_BASE_URL = "https://www.southpark.de"
EN_BASE_URL = "https://www.southparkstudios.com"
BASE_URLS = {
    "deu": DE_BASE_URL,
    "eng": EN_BASE_URL
}
CONF = {
    "deu": {
        "url": DE_BASE_URL,
        "token": "F"
    },
    "eng": {
        "url": EN_BASE_URL,
        "token": "E"
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
    filtered = [e for e in episodes if f"{token}{int(episode)}" == e['meta']['header']['title'].split(SEPARATOR)[1]]
    return filtered


def get_download_links(base_url: str, episodes: list):
    links = list()
    for e in episodes:
        link = f"{base_url}{e['url']}"
        links.append(link)
    return links


def get_episode(episodes: list, season, episode, lang):
    filtered = filter_season(episodes, season)
    filtered = filter_episode(filtered, episode, CONF[lang]["token"])
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


def get_episodes(lang: str = "eng"):
    cache_file = f".cache.{lang}"
    if not os.path.isfile(cache_file):
        request_all_episodes(lang)
    with open(cache_file, "r") as f:
        episodes = json.load(f)
    return episodes


def download_episode_internal(season, episode, lang):
    print(f"[Download start] S{season}E{episode} {lang}")
    episodes = get_episodes(lang)
    e = get_episode(episodes, season, episode, lang)
    links = get_download_links(BASE_URLS[lang], e)
    with yt_dlp.YoutubeDL(ydl_opts_en) as ydl:
        ydl.download(links)
    print(f"[Download finished] S{season}E{episode} {lang}")


def download_episode(season, episode):
    print("[Start] S" + season + "E" + episode)
    if multilanguage:
        de_thread = threading.Thread(target=download_episode_internal, args=(season, episode, "deu"))
        de_thread.start()

    en_thread = threading.Thread(target=download_episode_internal, args=(season, episode, "eng"))
    en_thread.start()
    en_thread.join()
    if multilanguage:
        de_thread.join()
    merge_episode(season, episode)
    print("[End] S" + season + "E" + episode)


def create_file_list(season, episode, lang: str):
    f_season = f"{int(season):02d}"
    f_episode = f"{int(episode):02d}"
    print("[Create file list]" + "S" + season + "E" + episode + " " + lang)
    file_list_name = f"files_{f_season}{f_episode}_{lang}.txt"
    with open(file_list_name, mode="w+") as file_list:
        for f in sorted(glob.glob(f"*E{f_season}{f_episode}*X{lang}*?m*")):
            file_list.write("file '" + f + "'\n")
    return file_list_name


def get_episode_title(season, episode, lang):
    print("[Get episode title]" + "S" + season + "E" + episode + " " + lang)
    for f in glob.glob("*" + season + episode + "*" + lang + "*"):
        return f.split(" - ")[1].strip().replace(" ", "_")


def merge_episode(season, episode):
    for f in glob.glob(f"*E {int(season):02d}{int(episode):02d}*"):
        os.rename(f, make_safe(f.replace(" ", "")))

    ffmpeg_binary = "ffmpeg.exe" if (platform.system() == "Windows") else "ffmpeg"
    episode_name = f"South_Park_S{int(season):02d}E{int(episode):02d}"
    video_list = create_file_list(season, episode, "eng")
    if multilanguage:
        audio_list = create_file_list(season, episode, "deu")

    if multilanguage:
        print("[merge german audio tracks]" + "S" + season + "E" + episode)
        ffmpeg_concat_audio_command = f"{ffmpeg_binary} -f concat -i {audio_list} -c copy -scodec copy {episode_name}_temp.m4a"
        subprocess.call(ffmpeg_concat_audio_command, shell=True)

        print("[merge english video tracks]" + "S" + season + "E" + episode)
        ffmpeg_concat_video_command = f"{ffmpeg_binary} -f concat -i {video_list} -c copy -scodec copy {episode_name}_temp.mp4"
        subprocess.call(ffmpeg_concat_video_command, shell=True)

        print("[add german audio track to video]" + "S" + season + "E" + episode)
        ffmpeg_add_audio_command = f"{ffmpeg_binary} -i {episode_name}_temp.mp4 -i {episode_name}_temp.m4a -c copy -map 0:v:0  -map 1:a:0 -map 0:a:0 -map 0:s:0 -metadata:s:a:0 language=ger -metadata:s:a:1 language=eng {episode_name}.mp4"
        subprocess.call(ffmpeg_add_audio_command, shell=True)

    else:
        print("[merge english video tracks]" + "S" + season + "E" + episode)
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
    for f in glob.glob("*ComedyCentralS*"):
        os.remove(f)
    for f in glob.glob("*Ak*"):
        os.remove(f)
    for f in glob.glob("*temp*"):
        os.remove(f)
    for f in glob.glob("file*"):
        os.remove(f)


def download_season(season):
    threads = []

    episodes = get_episodes()
    filtered = filter_season(episodes, season)
    for episode in range(1, len(filtered)):
        t = threading.Thread(target=download_episode, args=("%02d" % (season), "%02d" % (episode)))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--multilanguage", dest="multilanguage",
                        help="If activated stores video with german and english audio", action="store_true",
                        default=False)
    parser.add_argument("-e", "--episode", dest="episode", help="Download specific episode, e.g. 02:03", type=str)
    parser.add_argument("-s", "--season", dest="season", help="Download a whole season", type=int)
    args = parser.parse_args()
    multilanguage = args.multilanguage
    clean_up()

    if args.episode is not None and args.season is not None:
        print("Use either -e or -s option!")
        sys.exit(1)

    if args.episode is not None:
        split = args.episode.split(":")
        season = split[0]
        episode = split[1]
        download_episode(season, episode)

    if args.season is not None:
        download_season(args.season)

    time.sleep(10)
    print("Clean up temporary data")
    clean_up()
