from setup import *


class extractZingMp3(ProgressBar):
    def __init__(self, *args, **kwargs):
        self._url = kwargs.get('url')
        self._show_json_info = kwargs.get('show_json_info')
        self._down_lyric = kwargs.get('down_lyric')
        self._down_media = kwargs.get('down_media')
        self._path_save = kwargs.get('path_save') or os.getcwd()
        self._headers = HEADERS
        self._regex_url = '''(?x)^
                ((http[s]?|fpt):)\/?\/(www\.|m\.|)
                (?P<site>
                    (?:(zingmp3\.vn)|   
                    (mp3\.zing\.vn))
                )\/                                                        # check domain (zingmp3 and mp3.zing.vn)
                (
                    (?P<type>bai-hat|album|video-clip|playlist|embed)\/    # get type (bai-hat, album,video-clip, playlist)
                    (?P<slug>.*?)\/                                        # get slug of media
                    (?P<id>.*?)(?:$|\W)                                    # get id of media
                    |                                                      # if not media url, url is artist's profile url
                    (?:nghe-si\/|)(?P<name_artist>.*?)\/                   # get name artits
                    (?P<slug_artist>.*?$)                                  # get artist's slug
                )
                        '''

        '''
        
            All url test
            
            {
                "url":"https://zingmp3.vn/video-clip/Tim-Ve-Loi-Ru-New-Version-Thanh-Hung-Various-Artists/ZW6ZOIZ7.html",
                "note":"video clip (label max is 480p)"
            }
            
            {
                "url":"https://zingmp3.vn/video-clip/Yeu-Nhieu-Ghen-Nhieu-Thanh-Hung/ZWB087B9.html",
                "note":"video clip (labal max is 1080p)"
            }
            
            {
                "url":[
                    "https://zingmp3.vn/nghe-si/Huong-Giang-Idol/bai-hat",
                    "https://zingmp3.vn/nghe-si/Huong-Giang-Idol/album",
                    "https://zingmp3.vn/nghe-si/Huong-Giang-Idol/video",
                ],
                "note":"artist's profile type 1"
            }
            
            {
                "url":[
                    "https://zingmp3.vn/Mr-Siro/bai-hat",
                    "https://zingmp3.vn/Mr-Siro/playlist",
                    "https://zingmp3.vn/Mr-Siro/video"
                ],
                "note":"artist's profile type 2"
            }
            
            {
                "url":"https://zingmp3.vn/bai-hat/Khoc-Cung-Em-Mr-Siro-Gray-Wind/ZWBI0DFI.html",
                "note":"bai hat"            
            }
            
            {
                "url":"https://zingmp3.vn/album/Khoc-Cung-Em-Single-Mr-Siro-Gray-Wind/ZF90UA9I.html",
                "note":"album"
            }
            
            {
                "url":"https://zingmp3.vn/playlist/Sofm-s-playlist/IWE606EA.html",
                "note":"playlist"
            }
            
        '''

        self.default_http = 'https://zingmp3.vn/'
        self._api_video = """http://api.mp3.zing.vn/api/mobile/video/getvideoinfo?requestdata={"id":"%s"}"""
        self._type_supported = ['bai-hat', 'album', 'video-clip', 'playlist', 'embed']

    def run(self):
        item = re.search(self._regex_url, self._url)
        if not item:
            return 'Invalid url.'
        video_id = item.group('id')
        type = item.group('type')
        name_artist = item.group('name_artist')
        slug = item.group('slug')
        if type in self._type_supported:
            return self.real_extract_media(type, video_id, slug)
        elif name_artist:
            return self.real_extract_user(item, name_artist)
        else:
            sys.stdout.write(fg + '[' + fr + '*' + fg + '] : Invalid url.\n')
        return

    def real_extract_user(self, item, name_artist):
        slug_user = item.group('slug_artist')
        content = get_req(url="https://mp3.zing.vn/nghe-si/" + name_artist, headers=self._headers, type='text')
        soup = get_soup(content, 'html5lib')
        s_tag = soup.find(r's', attrs={'class': 'fn-followed', 'data-id': True})
        if not s_tag:
            return 'null'
        id_artist = s_tag.get('data-id')
        list_name_api = {
            'bai-hat': "/song/get-list",  # get artist's bai-hat
            "playlist": "/playlist/get-list",  # get artist's album
            "video": "/video/get-list"  # get artist's video or artist's MV
        }
        name_api = list_name_api.get(slug_user) or None
        if not name_api:
            sys.stdout.write(fg + '[' + fr + '*' + fg + '] : Invalid url.\n')
            return
        api = self.get_api(name_api=list_name_api.get(slug_user), video_id=id_artist)

        start = 0
        count = 30
        while True:
            f = get_req(url=api, headers=self._headers, type='json', params={
                'type': 'artist',
                'start': start,
                'count': count,
                'sort': 'hot',
            })
            if self._show_json_info:
                print(json.dumps(f, ensure_ascii=False, indent=4))
                return
            if f.get('msg').lower() != 'success':
                sys.stdout.write(fg + '[' + fr + '*' + fg + '] : Data playlist null.\n')
                return
            datas = try_get(f, lambda x: x['data']['items'])

            for data in datas:
                self.real_extract_media(
                    type=search_regex(r'(?x)\/(.*?)\/', data.get('link')),
                    video_id=data.get('id'),
                )
            total = is_int(try_get(f, lambda x: x['data']['total']))
            start += count

            if total <= start:
                break
        return

    def real_extract_media(self, type, video_id, slug=None):
        if type == 'video-clip':
            _json = get_req(url=self._api_video % (video_id), headers=self._headers, type='json')
            data = _json.get('source') or None
            if not data:
                sys.stdout.write(fg + '[' + fr + '*' + fg + f"] : {self._url} don't have video.\n")
                return
            f = _json
        else:
            name_api = ''
            if type == 'album' or type == 'playlist':
                name_api = '/playlist/get-playlist-detail'
            elif type == 'bai-hat':
                name_api = '/song/get-song-info'
            elif type == 'embed':
                if slug and slug == 'song':
                    name_api = '/song/get-song-info'
            else:
                sys.stdout.write(fg + '[' + fr + '*' + fg + f"] : {self._url} invalid.\n")
                return

            api = self.get_api(name_api, video_id)
            data = get_req(url=api, headers=self._headers, type='json')
            if not data:
                return 'null'
            f = data

        if self._show_json_info:
            print(json.dumps(f, ensure_ascii=False, indent=4))
            return
        return self.start_download(f)

    def start_download(self, f):
        if not f:
            return
        msg = f.get('msg')
        if msg and msg.lower() != 'success':
            sys.stdout.write(fg + '[' + fr + '*' + fg + '] : Data null.\n')
            return
        data = f.get('data')

        def get_best_label_video(source):
            """
            - Get best label of source
            :param source: {
                label: url.
            }
            Ex: {
                    360p: https://.....
                    720p: https://.....
                    1080p: https://.....
                } or
                {
                    128: https://.....
                    320: https://.....
                }
            :return: url and label
            """
            keys = list(source.keys())
            while True:
                if not keys:
                    break
                label_best = keys[-1]
                url = source[label_best]
                if url:
                    return url, label_best
                keys.remove(label_best)
            return None, None

        def down_media():
            """
            - Download media.
            :return:
            """
            url, label_best = get_best_label_video(sources)
            if not url:
                sys.stdout.write(fg + '[' + fr + '*' + fg + f"] : {title} don't have media.")
                return
            if not url.startswith('http') or not url.startswith('https'):
                url = 'https:' + url
            sys.stdout.write(fg + '[' + fc + '*' + fg + f'] : Downloading {title} - {label_best} .\n')
            down = Downloader(url=url)
            down.download(
                filepath='%s/%s_%s.mp3' % (path_download, title, label_best),
                callback=self.show_progress
            )
            sys.stdout.write('\n')
            return

        def down_lyric():
            """
            - Download lyric
            :return:
            """
            sys.stdout.write(fg + '[' + fc + '*' + fg + f'] : Downloading {title} - Lyric .\n')
            if lyric:
                if is_url(lyric):
                    fname = filename_from_url(lyric)
                    if fname.split('.')[-1] != 'lrc':
                        sys.stdout.write(fg + '[' + fr + '*' + fg + f'] : Error when download lyric.')
                        return
                    down = Downloader(url=lyric)
                    down.download(
                        filepath=f"{path_download}/{title}.{fname.split('.')[-1]}",
                        callback=self.show_progress
                    )
                else:
                    with io.open(f"{path_download}/{title}.lrc", 'w', encoding='utf-8-sig') as f:
                        f.write(lyric)
                    sys.stdout.write(fg + '[' + fc + '*' + fg + '] : Done.\n')
            else:
                sys.stdout.write(fg + '[' + fr + '*' + fg + f"] : {title} dont't have Lyric .")
            sys.stdout.write('\n')
            return

        if not data:  # video-clip
            title = f.get('title')
            title = removeCharacter_filename(title)
            sys.stdout.write(fg + '[' + fc + '*' + fg + f'] : Downloading {title} .\n')
            source = try_get(f, lambda x: x['source'])
            url, label_best = get_best_label_video(source)
            if not url:
                sys.stdout.write(fg + '[' + fr + '*' + fg + f"] : {title} don't have video.")
                return
            path_download = os.path.join(self._path_save, 'DOWNLOAD')
            if not os.path.exists(path=path_download):
                os.mkdir(path_download)
            if not url.startswith('http') or not url.startswith('https'):
                url = 'https:' + url
            down = Downloader(url=url)
            down.download(
                filepath='%s/%s_%s.mp4' % (path_download, title, label_best),
                callback=self.show_progress
            )
            sys.stdout.write('\n\n')
            return

        title = data.get('title') or data.get('alias')
        sys.stdout.write(fg + '[' + fc + '*' + fg + f'] :   {title} .\n')
        title = removeCharacter_filename(title)
        lyric = data.get('lyric') or try_get(data, lambda x: x['lyrics'][0]['content'])
        sources = try_get(data,
                          lambda x: x['streaming']['default'] if x['streaming']['msg'].lower() == 'success' else None)

        if not sources:
            song_items = try_get(data, lambda x: x['song']['items'])
            if not song_items:
                sys.stdout.write(fg + '[' + fr + '*' + fg + f"] : {try_get(data, lambda x: x['streaming']['msg'])}.\n")
            else:
                for song in song_items:
                    self.real_extract_media(
                        type=search_regex(r'(?x)\/(.*?)\/', song.get('link')),
                        video_id=song.get('id'),
                    )
        else:
            path_download = os.path.join(self._path_save, 'DOWNLOAD')
            if not os.path.exists(path=path_download):
                os.mkdir(path_download)
            if self._down_lyric is True and self._down_media is False:
                down_lyric()
            elif self._down_lyric is False and self._down_media is True:
                down_media()
            else:
                down_media()
                down_lyric()
        sys.stdout.write('\n\n')
        return

    def get_api(self, name_api, video_id=''):
        API_KEY = '38e8643fb0dc04e8d65b99994d3dafff'
        SECRET_KEY = b'10a01dcf33762d3a204cb96429918ff6'
        if not name_api:
            return

        def get_hash256(string):
            return hashlib.sha256(string.encode('utf-8')).hexdigest()

        def get_hmac512(string):
            return hmac.new(SECRET_KEY, string.encode('utf-8'), hashlib.sha512).hexdigest()

        def get_request_path(data):
            def mapping(key, value):
                return quote(key) + "=" + quote(value)

            data = [mapping(k, v) for k, v in data.items()]
            data = "&".join(data)
            return data

        def get_api_by_id(id):
            url = f"https://zingmp3.vn/api{name_api}?id={id}&"
            time = str(int(datetime.datetime.now().timestamp()))
            sha256 = get_hash256(f"ctime={time}id={id}")

            data = {
                'ctime': time,
                'api_key': API_KEY,
                'sig': get_hmac512(f"{name_api}{sha256}")
            }
            return url + get_request_path(data)

        return get_api_by_id(video_id)


def main(argv):
    parser = argparse.ArgumentParser(description='Zingmp3 - A tool crawl data from zingmp3.vn .')
    parser.add_argument('url', type=str, help='Url.')
    parser.add_argument('-s', '--save', type=str, default=os.getcwd(), help='Path to save', dest='path_save')
    parser.add_argument('-j', '--json', default=False, action='store_true', help="Show json of info media.",
                        dest='show_json_info')
    parser.add_argument('-l','--only-lyric', default=False, action='store_true', help='Download only lyric.',
                        dest='down_lyric')
    parser.add_argument('-m','--only-media', default=False, action='store_true', help='Download only media.',
                        dest='down_media')
    args = parser.parse_args()

    if args.url:
        extract = extractZingMp3(
            url=args.url,
            path_save=args.path_save,
            show_json_info=args.show_json_info,
            down_lyric=args.down_lyric,
            down_media=args.down_media
        )
        extract.run()


if __name__ == '__main__':
    try:
        if sys.stdin.isatty():
            main(sys.argv)
        else:
            argv = sys.stdin.read().split(' ')
            main(argv)
    except KeyboardInterrupt:
        sys.stdout.write(
            fc + sd + "\n[" + fr + sb + "-" + fc + sd + "] : " + fr + sd + "User Interrupted..\n")
        sys.exit(0)
