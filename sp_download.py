#!/usr/bin/env python3

import os
import threading
import subprocess
import glob
import platform
import time
import argparse
#  external dependencies
import unidecode # pip install unidecode
import youtube_dl # pip install youtube-dl

multilanguage = False

ydl_opts_en = {
	'format': 'bestaudio/best',
        'retries': 10,
        'ignoreerrors': True,
        'hls_prefer_native': False,
        'continuedl': True,
	'writesubtitles': True,
        'subtitlesformat': 'vtt',
        'outtmpl': '%(title)s_en.%(ext)s',
        'quiet': True,
	'postprocessors': [
                {
                        'key': 'FFmpegEmbedSubtitle'
                }
	],
        'nocheckcertificate': True
}

ydl_opts_de = {
        'format': 'bestaudio/best',
        'retries': 10,
        'ignoreerrors': True,
        'hls_prefer_native': False,
        'continuedl': True,
        'outtmpl': '%(title)s_de.%(ext)s',
        'quiet': True,
        'postprocessors': [
                {
                        'key': "FFmpegExtractAudio"
                }
        ],
        'nocheckcertificate': True
}        

def download_episode_en(season, episode):
        print("[Download start]" + " "+ "S"+season+"E"+episode+" english")
        with youtube_dl.YoutubeDL(ydl_opts_en) as ydl:
                ydl.download(['http://southpark.cc.com/full-episodes/s'+season+'e'+episode])
        print("[Download finished]" + " "+ "S"+season+"E"+episode+" english")


def download_episode_de(season, episode):
        print("[Download start]" + " "+ "S"+season+"E"+episode+" german")
        with youtube_dl.YoutubeDL(ydl_opts_de) as ydl:
                ydl.download(['http://www.southpark.de/alle-episoden/s'+season+'e'+episode])
        print("[Download finished]" + " "+ "S"+season+"E"+episode+" german")

        
def download_episode(season, episode):
        print("[Start] S"+season+"E"+episode)
        if multilanguage:
                de_thread = threading.Thread(target=download_episode_de, args=(season, episode))
                de_thread.start()
        
        en_thread = threading.Thread(target=download_episode_en, args=(season, episode))
        en_thread.start()
        en_thread.join()
        if multilanguage:
                de_thread.join()
        merge_episode(season, episode)
        print("[End] S"+season+"E"+episode)


def create_video_list_file(season, episode, lang):
        print("[Create video list file]" + "S"+season+"E"+episode+" "+lang)
        file_list_name = "files_"+season+episode+lang+".txt"
        with open(file_list_name, mode="w+") as file_list:
                for f in glob.glob("*_"+season+episode+"_*"+lang+"?m*"):
                        file_list.write("file '"+f+"'\n")
        return file_list_name

def get_episode_title(season, episode, lang):
        print("[Get episode title]" + "S"+season+"E"+episode+" "+lang)
        for f in glob.glob("*"+season+episode+"*"+lang+"*"):
                return f.split(" - ")[1].strip().replace(" ", "_")

def merge_episode(season, episode):
        for f in glob.glob("*_"+season+episode+"_*"):
                os.rename(f, make_safe(f.replace(" ", "")))
                
        ffmpeg_binary = "ffmpeg.exe" if (platform.system() == "Windows") else "ffmpeg" 
        episode_name = "South_Park_S"+season+"E"+episode
        video_list = create_video_list_file(season,episode, "en")
        audio_list = create_video_list_file(season,episode, "de")

        if multilanguage:
                print("[merge german audio tracks]" + "S"+season+"E"+episode)
                ffmpeg_concat_audio_command = ffmpeg_binary+" -f concat -i "+ audio_list + " -c copy -scodec copy " + episode_name+"_temp.m4a"
                subprocess.call(ffmpeg_concat_audio_command)
                print("[merge english video tracks]" + "S"+season+"E"+episode)
                ffmpeg_concat_video_command = ffmpeg_binary+" -f concat -i "+ video_list + " -c copy -scodec copy " + episode_name+"_temp.mp4"
                subprocess.call(ffmpeg_concat_video_command)
                print("[add german audio track to video]" + "S"+season+"E"+episode)
                ffmpeg_add_audio_command = ffmpeg_binary+" -i "+episode_name+"_temp.mp4 -i "+ episode_name+"_temp.m4a -c copy -map 0:v:0  -map 1:a:0 -map 0:a:0 -map 0:s:0 -metadata:s:a:0 language=ger -metadata:s:a:1 language=eng "+episode_name+".mp4" 
                subprocess.call(ffmpeg_add_audio_command)
 
        else:
                print("[merge english video tracks]" + "S"+season+"E"+episode)
                ffmpeg_concat_video_command = ffmpeg_binary+" -f concat -i "+ video_list + " -c copy -scodec copy " + episode_name+".mp4"
                subprocess.call(ffmpeg_concat_video_command)   


def make_safe(unsafe_string):
        def safe_char(c):
                if c.isalnum():
                        return c
                elif c == ".":
                        return "."
                else:
                        return "_"
        return unidecode.unidecode("".join(safe_char(c) for c in  unsafe_string).rstrip("_"))


def clean_up():       
        for f in glob.glob("*Ac*"):
                os.remove(f)
        for f in glob.glob("*Teil*"):
                os.remove(f)
        for f in glob.glob("*Ak*"):
                os.remove(f)
        for f in glob.glob("*temp*"):
                os.remove(f)   
        for f in glob.glob("file*"):
                os.remove(f)             


def download_season(season):
        number_of_episodes = 0
        threads = []
        if season == 1:
                number_of_episodes = 13
        if season == 2:
                number_of_episodes = 18
        if season == 7:
                number_of_episodes = 15
        if season in [3,4,6]:
                number_of_episodes = 17
        if season in range(8, 17) or season == 5:
                number_of_episodes = 14
        if season >= 17:
                number_of_episodes = 10
        for episode in range(1, number_of_episodes+1):
                t = threading.Thread(target=download_episode, args=("%02d"%(season), "%02d"%(episode)))
                threads.append(t)
                t.start()
        for t in threads:
                t.join()


if __name__ == '__main__':
        parser = argparse.ArgumentParser()
        parser.add_argument("-m", "--multilanguage", dest="multilanguage", help="only store english version with subtitles", action="store_true", default=False)
        parser.add_argument("-e", "--episode", dest="episode", help="Download specific episode, e.g. 02:03", type=str)
        parser.add_argument("-s", "--season", dest="season", help="Download a whole season", type=int)
        args = parser.parse_args()
        multilanguage = args.multilanguage
        if args.episode != None:
                split = args.episode.split(":")
                season = split[0]
                episode = split[1]
                download_episode(season, episode)
        
        if args.season != None:
                download_season(args.season)

        time.sleep(4)
        print("Clean up temporary data")
        clean_up() 
        