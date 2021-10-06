ydl_opts_en = {
    'format': 'bestaudio/best',
    'retries': 10,
    'ignoreerrors': True,
    'hls_prefer_native': False,
    'continuedl': True,
    'writesubtitles': True,
    'subtitlesformat': 'vtt',
    'outtmpl': '%(title)s_eng.%(ext)s',
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
    'writesubtitles': False,
    'outtmpl': '%(title)s_deu.%(ext)s',
    'quiet': True,
    'postprocessors': [
        {
            'key': "FFmpegExtractAudio"
        }
    ],
    'nocheckcertificate': True
}