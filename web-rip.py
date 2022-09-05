from requests import get, post
import requests
from bs4 import BeautifulSoup
import m3u8_To_MP4
import re
stream_preferences_order = ["Streamlare", "Vidcloud"]
BASE_VIDEO_PATH="/volume1/media-files"
TV_FOLDER = "/tv-shows"
MOVIES_FOLDER="/movies"
def get_vidcloud_stream(id,season=None, episode=None ,type="show",m3u8=False):
    try:
        if type == "movie":
            media_server = (
                BeautifulSoup(
                    get(
                        "https://www.2embed.to/embed/imdb/movie?id={}".format(id),
                        headers={"user-agent": "Mozilla/5.0"},
                    ).text,
                    "html.parser",
                )
                .find("div", class_="media-servers dropdown")
                .find("a")["data-id"]
            )
        if type == "show":
            media_server = (
                BeautifulSoup(
                    get(
                        f"https://www.2embed.to/embed/imdb/tv?id={id}&s={season}&e={episode}",
                        headers={"user-agent": "Mozilla/5.0"},
                    ).text,
                    "html.parser",
                )
                .find("div", class_="media-servers dropdown")
                .find("a")["data-id"]
            )
            print(media_server)
        recaptcha_resp = get(
            "https://recaptcha.harp.workers.dev/?anchor=https%3A%2F%2Fwww.google.com%2Frecaptcha%2Fapi2%2Fanchor%3Far%3D1%26k%3D6Lf2aYsgAAAAAFvU3-ybajmezOYy87U4fcEpWS4C%26co%3DaHR0cHM6Ly93d3cuMmVtYmVkLnRvOjQ0Mw..%26hl%3Den%26v%3DPRMRaAwB3KlylGQR57Dyk-pF%26size%3Dinvisible%26cb%3D7rsdercrealf&reload=https%3A%2F%2Fwww.google.com%2Frecaptcha%2Fapi2%2Freload%3Fk%3D6Lf2aYsgAAAAAFvU3-ybajmezOYy87U4fcEpWS4C"
        ).json()["rresp"]
        vidcloudresp = get(
            "https://www.2embed.to/ajax/embed/play",
            params={"id": media_server, "_token": recaptcha_resp},
        )
        vid_id = vidcloudresp.json()["link"].split("/")[-1]
        rbstream = "https://rabbitstream.net/embed/m-download/{}".format(
            vid_id)
        soup = BeautifulSoup(get(rbstream).text, "html.parser")
        return [
            a["href"] for a in soup.find("div", class_="download-list").find_all("a")
        ] if not m3u8 else vid_id
    except:
        return None


def get_m3u8_rabbitstream(id):
    url = "https://rabbitstream.net/embed-5/{}".format(id)
    headers = {
        "referer": "https://www.2embed.to/",
    }
    params = {
        'id': id.split("?")[0],
        '_number': '1',
        'sId': 'tMK9W5pbb5PYDSCEuuMt',
    }
    resp = get("https://rabbitstream.net/ajax/embed-5/getSources", headers=headers, params=params).json()
    return resp

class StreamGrabber:
    def __init__(self, id, type, id_type="imdb",season=None, episode=None):
        self.base_url = "https://www.2embed.to"
        self.recaptcha_resp=None
        self.id = id
        self.type = type
        self.id_type = id_type
        self.season = season
        self.episode = episode
        self.embed_headers= {
            "referer": "https://www.2embed.to/",
        }
        self.m3u8_params = {
            'id': self.id.split("?")[0],
            '_number': '1',
            'sId': 'tMK9W5pbb5PYDSCEuuMt',
        }
        if self.type == "show":
            if not self.season:
                print("Must include a season number")
                return
            if not self.episode:
                print("Must include an episode number")
                return
    def get_available_servers(self):
        if self.type == "show":
            servers = (
                BeautifulSoup(
                    requests.get(
                        f"{self.base_url}/embed/{self.id_type}/tv?id={self.id}&s={self.season}&e={self.episode}",
                        headers={"user-agent": "Mozilla/5.0"},
                    ).text,
                    "html.parser",
                )
                .find("div", class_="media-servers dropdown")
                .find_all("a")
            )
            self.available_servers = {}
            for s in servers:
                self.available_servers[s.text.split("Server ")[-1].lower()]:{"id":s["data-id"], "name":s.text.split("Server ")[-1]})
    def get_captcha(self):
        self.recaptcha_resp = requests.get(
            "https://recaptcha.harp.workers.dev/?anchor=https%3A%2F%2Fwww.google.com%2Frecaptcha%2Fapi2%2Fanchor%3Far%3D1%26k%3D6Lf2aYsgAAAAAFvU3-ybajmezOYy87U4fcEpWS4C%26co%3DaHR0cHM6Ly93d3cuMmVtYmVkLnRvOjQ0Mw..%26hl%3Den%26v%3DPRMRaAwB3KlylGQR57Dyk-pF%26size%3Dinvisible%26cb%3D7rsdercrealf&reload=https%3A%2F%2Fwww.google.com%2Frecaptcha%2Fapi2%2Freload%3Fk%3D6Lf2aYsgAAAAAFvU3-ybajmezOYy87U4fcEpWS4C"
        ).json()["rresp"]
    def get_stream(self, id):
        # if not self.recaptcha_resp:
        self.get_captcha()
        response = requests.get(
            "https://www.2embed.to/ajax/embed/play",
            params={"id": id, "_token": self.recaptcha_resp},
        )
        return response.json()
    def get_file_link(self, name, link):
        if name.lower() == "streamlare":
            id = link.split("/")[-1]
            response = requests.post("https://sltube.org/api/video/stream/get", headers={"referer":f"https://sltube.org/e/{id}"}, data={"id":id})
            data = response.json()
            if data.get("type", None) == "mp4":

                #instead iterate over result keys and grab original if they have it if not, highest quality
                if "Original" in data["result"].keys():
                    return data["result"]["Original"]["file"], data["type"]
                if "4K" in data["result"].keys():
                    return data["result"]["4K"]["file"], data["type"]
                if "1080p" in data["result"].keys():
                    return data["result"]["1080p"]["file"], data["type"]
                if "720p" in data["result"].keys():
                    return data["result"]["720p"]["file"], data["type"]
                if "480p" in data["result"].keys():
                    return data["result"]["720p"]["file"], data["type"]
                if "360p" in data["result"].keys():
                    return data["result"]["360p"]["file"], data["type"]
                # download_file(next["result"]["Original"]["file"], filename="test.mp4")
        if name.lower() == "vidcloud":
            response = requests.get(link, headers={"referer": "https://www.2embed.to/"})
            m = re.search(r'(recaptchaNumber\s?\=\s?[\'\"](\d)[\'\"])',response.text)
            recaptcha_number='1'
            if m.group(1):
                recaptcha_number = str(m.group(1))
            response = requests.get("https://rabbitstream.net/ajax/embed-5/getSources", headers = {
                "referer": "https://www.2embed.to/",
            }, params = {
                'id': link.split("/")[-1].split("?")[0],
                '_number': recaptcha_number,
                'sId': 'tMK9W5pbb5PYDSCEuuMt',
            })
            for source in response.json()["sources"]:
                if source["type"] == 'hls':
                    return source["file"], "m3u8"
            return None, None
        else:
            print(name, "not yet implemented")
            return None, None
def download_file(url, filename=None):
    if not filename:
        filename = url.split('/')[-1]
    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                # If you have chunk encoded response uncomment if
                # and set chunk_size parameter to None.
                #if chunk:
                f.write(chunk)
    return filename
if __name__ == '__main__':
    stream = StreamGrabber("tt11173006","show", season=1, episode=1)
    stream.get_available_servers()
    for n in stream_preferences_order:
        if stream.available_servers.get(n.lower(), False):
            data = stream.get_stream(k["id"])
            file_url, type = stream.get_file_link(k["name"], data["link"])
            if file_url and type:
                if type.lower() in ["mp4", "mkv", "mov", "wmv", "avi"]:
                    download_file(file_url, filename=f"{BASE_VIDEO_PATH}/name.of.show.SNNENN.ext")
                if type.lower() in ["m3u8", "hls"]:
                    #todo filename/path
                    m3u8_To_MP4.multithread_uri_download(file_url, customied_http_header={
                        "referer": "https://www.2embed.to/",
                    })
