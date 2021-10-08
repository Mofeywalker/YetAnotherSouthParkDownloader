ydl_opts_en = {
    'format': 'best',
    'retries': 10,
    'ignoreerrors': True,
    'hls_prefer_native': False,
    'continuedl': True,
    'writesubtitles': True,
    'subtitlesformat': 'vtt',
    # 'outtmpl': '%(series)s/%(season_number|0)s/S%(season_number|0)sE%(episode_number)s_eng.%(ext)s',
    'outtmpl': '%(playlist)sS%(playlist_index)s_download_eng.%(ext)s',
    'quiet': True,
    'postprocessors': [
        {
            'key': 'FFmpegEmbedSubtitle'
        }
    ],
    'nocheckcertificate': True
}

ydl_opts_de = {
    'format': 'best',
    'retries': 10,
    'ignoreerrors': True,
    'hls_prefer_native': False,
    'continuedl': True,
    'writesubtitles': False,
    # 'outtmpl': '%(series)s/%(season_number)s/S%(season_number)sE%(episode_number)s_deu.%(ext)s',
    'outtmpl': '%(playlist)sS%(playlist_index)s_download_deu.%(ext)s',
    'quiet': True,
    'postprocessors': [
        {
            'key': "FFmpegExtractAudio"
        }
    ],
    'nocheckcertificate': True
}
