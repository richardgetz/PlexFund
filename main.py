import settings
from plexapi.server import PlexServer
from plexapi.myplex import MyPlexAccount, MyPlexUser
from plexapi.library import Library
import re
import torrse
import json
from debrid import RealDebrid
from tqdm import tqdm

# from debrid import RealDebrid
from py1337x import py1337x
from difflib import SequenceMatcher
import trakt
from threading import Thread
import country_converter as coco

cc = coco.CountryConverter()
trakt.APPLICATION_ID = "101039"
RD = RealDebrid(api_key=settings.CONFIG["Debrid Services"]["Real Debrid"]["api_key"])
PlexAccount = None


def preflight():
    library = False
    content = False
    debrid = False
    for type in settings.CONFIG["Library Services"]:
        if settings.CONFIG["Library Services"][type]["active"]:
            if len(settings.CONFIG["Library Services"][type]["users"]) > 0:
                library = True
                break
    for type in settings.CONFIG["Content Services"]:
        if settings.CONFIG["Content Services"][type]["active"]:
            if len(settings.CONFIG["Content Services"][type]["users"]) > 0:
                content = True
                break
    for type in settings.CONFIG["Debrid Services"]:
        if settings.CONFIG["Debrid Services"][type]["active"]:
            if settings.CONFIG["Debrid Services"][type].get("api_key", False):
                debrid = True
                break
    # True means ready to run
    if library and content and debrid:
        return True
    return False


def library_collection(library):

    if library.lower() == "plex":
        for user in settings.CONFIG["Library Services"][library]["users"]:
            print("Starting Plex Library check for", user["name"])
            plex_server = PlexServer(
                baseurl=settings.CONFIG["Library Services"][library]["server_location"],
                token=user["token"],
            )
            # return plex_server.library.all()
            return plex_server.library


def content_collection(type):
    watchlists = []
    global PlexAccount
    if type.lower() == "plex":
        for user in settings.CONFIG["Content Services"][type]["users"]:
            print("Starting Plex watchlisht check for", user["name"])
            PlexAccount = MyPlexAccount(token=user["token"])
            return PlexAccount.watchlist(filter="released", unwatched="True")
            # watchlists.extend(plex.watchlist())
    #         for w in watchlist:
    #             print(w.title, w.type, w.year, w.guid.split("/")[-1])
    # # Convert to plex ids to easily diff later
    # # if type.lower() == "trakt":
    # #     print(settings.CONFIG["Content Services"][type].keys())
    # #     for user in settings.CONFIG["Content Services"][type]["users"]:
    # #         try:
    # #             trakt.init(user["pin"])
    # #             for l in trakt.lists:
    # #                 print(l)
    # #         except Exception as e:
    # #             print(e)
    # #             continue

    return watchlists


def similar(a, b):
    return SequenceMatcher(None, a, b).ratio()


def compare_names(name1, name2):
    name1 = re.sub(r"[\s\_\-\.\(\)\'\"\n\:]", "", name1.strip())
    name2 = re.sub(r"[\s\_\-\.\(\)\'\"\n\:]", "", name2.strip())
    if name1.lower() == name2.lower():
        return 3

    sub_score = similar(name1.lower(), name2.lower())
    if sub_score > 0.90:
        print("90% but skipping", name1.lower(), name2.lower())
        return 0
        return 2
    if name1.lower().startswith(name2.lower()):
        print("starts with but skipping", name1.lower(), name2.lower())
        return 0
        return 1
    return 0
    if sub_score > 0.50:
        return sub_score
    print(sub_score)
    return 0


def show_classify(title, target_title):
    m1 = settings.RE_TV_SHOW.search(title)
    m2 = settings.RE_RESOLUTION.search(title)

    seasons = []
    episodes = []
    resolution = 0
    file_name = title
    complete = False
    need_episodes = True
    if m1:
        if m1.group(1):
            file_name = m1.group(1)

        if m1.group(2):
            if m1.group(2) == "00":
                seasons = [0]
            elif "-" in m1.group(2):
                s_temp = m1.group(2).split("-")
                seasons = [int(s.lstrip("0")) for s in s_temp]
            else:
                seasons = [int(m1.group(2).lstrip("0"))]
        if m1.group(3):
            if m1.group(3).strip().lower() == "complete":
                need_episodes = False
                complete = True
        if m1.group(4) and need_episodes:
            if m1.group(4) == "00":
                episodes = [0]
            elif "-" in m1.group(4):
                e_temp = m1.group(4).split("-")
                episodes = [int(e.lstrip("0")) for e in e_temp]
            else:
                episodes = [int(m1.group(4).lstrip("0"))]

    if m2:
        if m2.group(1):
            resolution = settings.RESOLUTION_SCORE.get(m2.group(1).upper(), 0)
    score = compare_names(file_name, target_title)
    return file_name, seasons, episodes, resolution, score, complete


# will eventually integrate max/min resolution checjk here
def torrent_decision_tree(
    items, show, number_of_seasons=0, type="show", season_inference=False
):
    # todo add movie
    if type in ["episode"]:
        for item in items:
            # todo make episode match exact so it pulls back just that single file
            file_name, seasons, episodes, resolution, score, complete = show_classify(
                item["name"], show["title"]
            )
            # eventually rework to make this seasons without episodes
            if show["episode"] not in episodes or show["season"] not in seasons:
                continue
            if score == 0:
                print(
                    "Scored too low:",
                    score,
                    "\nSkipping",
                    item["name"],
                    "compared to",
                    show["title"],
                )
                continue
            if resolution < settings.MINIMUM_RESOLUTION:
                print("Skipping low res")
                continue
            if not show.get("link", False):
                show["link"] = item["link"]
                show["score"] = score
                show["resolution"] = resolution
                show["torrent_name"] = file_name
                continue
            if show.get("resolution", -1) < resolution:
                show["link"] = item["link"]
                show["score"] = score
                show["resolution"] = resolution
                show["torrent_name"] = file_name
                continue
            if show.get("score", -1) < score:
                show["link"] = item["link"]
                show["score"] = score
                show["resolution"] = resolution
                show["torrent_name"] = file_name
                continue
        return show


def get_watchlist_thread():
    print("Starting watchlist(s) collection")
    needs_to_be_collected = []
    for content in settings.CONFIG["Content Services"]:
        if settings.CONFIG["Content Services"][content]["active"] and len(
            settings.CONFIG["Content Services"][content]["users"]
        ):
            data = content_collection(content)
            needs_to_be_collected.extend(data)
    return needs_to_be_collected


def get_library_thread():
    needed = True
    all = []
    for library in settings.CONFIG["Library Services"]:
        if settings.CONFIG["Library Services"][library]["active"] and len(
            settings.CONFIG["Library Services"][library]["users"]
        ):
            all.extend(library_collection(library))

    return all


def get_needed(watchlist, library):
    final_content = []
    # for l in library.all():
    #     if l.type == "show":
    #         print(l.title)
    #         for season in l.seasons():
    #             for ep in season.episodes():
    #                 print(ep.__dict__)
    #                 print(ep.lastViewedAt, ep.parentIndex, ep.index)

    for m in watchlist:
        if m.type == "show":
            print(m.title)
            print(m.childCount)
            # print(m.key)
            # for x in range(1, m.childCount + 1):
            #     season = m.season(x)
            #     PlexAccount._toOnlineMetadata([season])
            for season in m.seasons():
                if season.index == 0:
                    continue
                PlexAccount._toOnlineMetadata([season])
                print("Season", season.index)

                if season.isPlayed:
                    print(season.viewedLeafCount, "/", season.leafCount)
                    continue
                for ep in season.episodes():
                    # look into why this works later bc this was luck lol
                    if len(library.search(guid=ep.guid, libtype="episode")) == 0:
                        final_content.append(
                            {
                                "type": ep.type,
                                "season": ep.parentIndex,
                                "episode": ep.index,
                                "title": ep.grandparentTitle,
                                "query": f"{ep.grandparentTitle} S{ep.parentIndex:02d}E{ep.index:02d}",
                            }
                        )

        if m.type == "movie":
            if len(library.search(guid=m.guid, libtype=m.type)) == 0:
                final_content.append(
                    {
                        "year": m.year,
                        "type": m.type,
                        "title": m.title,
                        "query": f"{str(m.title)} {str(m.year)}",
                    }
                )
    return final_content


def remove_watched():
    for media in library_collection("Plex").search(watched=True):
        if media.type == "episode":
            print("delete (will need an easy way to lookup)")


def main():
    if not preflight():
        print("Setup not built yet")
    library_threads = []
    content_threads = []
    magnets = set()
    watchlist_data = content_collection("Plex")
    already_have = library_collection("Plex")
    content_tracker = get_needed(watchlist_data, already_have)
    # threadpool for this isntead
    for data in tqdm(content_tracker):
        print("starting", data["title"])
        if data["type"] == "episode":
            cat = "tv"
            max = 5
        if data["type"] == "movie":
            cat = "movie"
            max = 10
            continue
        try:
            response = torrse.search(
                data["query"],
                cat,
                max,
                magnet=False,
                engines=[
                    # torrse.engine_1337x,
                    torrse.engine_limetorrents,
                    torrse.engine_zooqle,
                    torrse.engine_magnetdl,
                    # torrse.engine_uniondht,
                    # torrse.engine_kickasstorrents,
                ],
            )
            data = torrent_decision_tree(
                response, data, number_of_seasons=None, type=data["type"],
            )
        except Exception as e:
            print(e)
            continue
        print(data)
        if data.get("link", False):
            mag = torrse.get_magnet(data["link"])
            if not mag:
                print(
                    "No magnet?", data["link"],
                )
            # print(mag)
            # will have to change depending on debrid service
            # add them all now then run auto clean later to determine
            mag_id = RD.add_magnet(mag)
            if mag_id:
                data["current_magnet"] = {
                    "service": "realdebrid",
                    "id": mag_id,
                }
    with open("torrent_cache.json", "w") as f:
        json.dump(content_tracker, f, indent=4)
    # magnets = list(magnets)
    # RD.add_magnets(magnets)


if __name__ == "__main__":
    main()

    # plex_server = PlexServer(
    #     baseurl=settings.CONFIG["Library Services"]["Plex"]["server_location"],
    #     token=settings.CONFIG["Content Services"]["Plex"]["users"][0]["token"],
    # )
    # print(len(plex_server.library.all()))
    # for s in plex_server.library.search(unwatched=True):
    #     print(s.__dict__)

    # print(compare_names("The-Challenge-USA", "The-Challenge"))
    # needed = get_needed(content_collection("Plex"), library_collection("Plex"))
    # lib = get_library_thread()
    # lib = library_collection("Plex")
    # print(lib.search(libtype="show", title="The Challenge",)[0].seasons())
    # r = content_collection("Trakt")
    # print(compare_names("The Challenge", "the-challenge"))
    # this will need to be done an episode level to know if a new episode should be downloaded
    # write large can look at the over all episode count to also determine if needed to kick off the process at all
    # library = library_collection("Plex", "5d9c08780aaccd001f8f0ba0")
    # print(library)
    # print(library.keys())
