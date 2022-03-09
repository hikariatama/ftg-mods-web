import re
import hashlib
import flask
import os
import logging
from threading import Thread
from time import sleep
from PIL import Image, ImageDraw, ImageFont
import io
import requests
import textwrap
import random
import time

URL = "mods.hikariatama.ru"
LICENSE = "CC BY-NC-ND 4.0"
PORT = 1119

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_PATH)

if not os.path.isdir("mods"):
    os.mkdir("mods", mode=0o755)

if not os.path.isdir("badges"):
    os.mkdir("badges", mode=0o755)

logger = logging.getLogger("root")
logger.addHandler(logging.StreamHandler())

SIZE = (1200, 320)
INNER_MARGIN = (16, 16)
PADDING = (128, 0)

TRACK_FS = 48
ARTIST_FS = 32
MINITEXT = 24

with open("font.ttf", "rb") as f:
    font = f.read()

font_smaller = ImageFont.truetype(io.BytesIO(font), ARTIST_FS, encoding="UTF-8")

f = ImageFont.truetype(io.BytesIO(font), 17, encoding="UTF-8")


liliput = ImageFont.truetype(io.BytesIO(font), MINITEXT, encoding="UTF-8")
font = ImageFont.truetype(io.BytesIO(font), TRACK_FS, encoding="UTF-8")

mojies_ = []


def random_in_area(area):
    return (
        random.randint(area[0][0], area[1][0]),
        random.randint(area[0][1], area[1][1]),
    )


def moji():
    return random.choice(mojies_)


def update_badges():
    while True:
        logger.debug("Reloading badges")

        for i, mod in enumerate(mods):
            badge = create_badge(mod)
            with open(f'badges/{mod["file"].split(".")[0]}.jpg', "wb") as f:
                f.write(badge)
            logger.debug(f"Processed {i + 1}/{len(mods)}")

        logger.debug("Badges reloaded")
        time.sleep(120)


def download_mojies():
    global mojies_
    for _ in os.scandir("pics"):
        if _.path.endswith(".png"):
            mojies_ += [Image.open(_.path).convert("RGBA")]

    logger.debug("Read emojies")

    Thread(target=update_badges).start()


Thread(target=download_mojies).start()


def create_badge(mod):
    thumb = Image.open(io.BytesIO(requests.get(mod["pic"]).content)).convert("RGBA")

    comm = f"{mod['lines']:,} lines | {mod['chars']:,} chars | © {URL} | {LICENSE}"

    thumb_size = 128

    thumb = thumb.resize((thumb_size, thumb_size))

    lines = textwrap.wrap(mod["desc"], width=40)

    longest_line = max(font_smaller.getsize(line)[0] for line in lines)

    width = longest_line + INNER_MARGIN[0] + thumb_size

    DOUBLE_MARGIN = (28, 28)

    PADDING = (SIZE[0] // 2 - width // 2, 0)

    x = INNER_MARGIN[0] + PADDING[0] - DOUBLE_MARGIN[0]
    y = SIZE[1] // 2 - thumb_size // 2 - DOUBLE_MARGIN[1]

    rect = ((x, y), (SIZE[0] - x + DOUBLE_MARGIN[0] + 8, SIZE[1] - y + 8))

    im = Image.new("RGBA", SIZE, (30, 30, 30, 255))

    draw = ImageDraw.Draw(im)
    for x in range(-20, SIZE[0], 65):
        for y in range(-20, SIZE[1], 65):
            esize = random.randint(40, 55)
            angle = random.randint(-45, 45)
            EMOJI_1 = moji().rotate(angle)
            EMOJI_1 = EMOJI_1.resize((esize, esize))
            im.paste(EMOJI_1, (x, y), mask=EMOJI_1)

    im = Image.alpha_composite(im, Image.new("RGBA", SIZE, (0, 0, 0, 140)))
    draw = ImageDraw.Draw(im)

    draw.rounded_rectangle(rect, 15, fill=(10, 10, 10))
    draw.rounded_rectangle(
        ((8, 8), (liliput.getsize(comm)[0] + 24, liliput.getsize(comm)[1] + 24)),
        5,
        fill=(10, 10, 10),
    )

    im.paste(
        thumb,
        (INNER_MARGIN[0] + PADDING[0], SIZE[1] // 2 - thumb_size // 2),
        mask=thumb,
    )

    tpos = INNER_MARGIN

    tpos = (
        tpos[0] + thumb_size + INNER_MARGIN[0] + 8 + PADDING[0],
        SIZE[1] // 2 - TRACK_FS // 2 - ARTIST_FS * len(lines) // 2 - 8,
    )

    draw.text(tpos, mod["name"], (255, 255, 255), font=font)
    draw.text((16, 16), comm, (100, 100, 100), font=liliput)

    offset = tpos[1] + TRACK_FS + 8
    for line in lines:
        draw.text((tpos[0], offset), line, font=font_smaller, fill=(180, 180, 180))
        offset += font_smaller.getsize(line)[1]

    img = io.BytesIO()
    im.save(img, format="PNG")

    return img.getvalue()


SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))

KNOWN_HASHES_DB = os.path.join(SCRIPT_PATH, "verified_mods.db")

logging.basicConfig(
    filename="debug.log",
    format="[%(levelname)s]: %(message)s",
    level=logging.ERROR,
)
root = logging.getLogger()
root.addHandler(flask.logging.default_handler)

app = flask.Flask(__name__, static_folder=os.path.join(SCRIPT_PATH, "static"))
app.logger.setLevel(logging.ERROR)
app.config["TEMPLATES_AUTO_RELOAD"] = True


@app.route("/<mod>")
def module(mod):
    if "/" in mod:
        return

    module = [_ for _ in mods if _["file"] == mod]

    if not module:
        return "Not found", 404

    module = module[0]

    try:
        with open(f"mods/{mod}", "r", encoding="utf-8") as f:
            code = f.read()
    except FileNotFoundError:
        return "Not found", 404

    resp = flask.Response(code)
    resp.headers["content-type"] = "text/plain; charset=utf-8"
    return resp


@app.route("/badges/<mod>")
def ready_badge(mod):
    if "/" in mod:
        return

    return flask.send_file(f"badges/{mod}", mimetype="image/jpeg")


@app.route("/badge/<mod>")
def badge(mod):
    if "/" in mod:
        return

    if all(_["file"] != f"{mod}.py" for _ in mods):
        return "Not found", 404

    return flask.jsonify(
        {
            "badge": f"https://{URL}/badges/{mod}.jpg",
            "info": [_ for _ in mods if _["file"] == f"{mod}.py"][0],
        }
    )


@app.route("/full.txt")
def full():
    resp = flask.Response("\n".join([_["file"].split(".")[0] for _ in mods]))
    resp.headers["content-type"] = "text/plain; charset=utf-8"
    return resp


@app.route("/minimal.txt")
def minimal():
    resp = flask.Response(mods[0]["file"])
    resp.headers["content-type"] = "text/plain; charset=utf-8"
    return resp


@app.route("/view/<mod>")
def view(mod):
    if "/" in mod:
        return

    module = [_ for _ in mods if _["file"] == mod]
    if not module:
        return "Not found", 404

    module = module[0]

    with open(f"mods/{mod}", "r", encoding="utf-8") as f:
        code = f.read()

    return flask.render_template(
        "view.html",
        mod_name=mod,
        mod_code=code,
        mod_icon=module["pic"],
        mod_desc=module["desc"],
        url=URL,
    )


@app.route("/", methods=["GET"])
def mods_router():
    return flask.render_template("mods.html", mods=mods, url=URL)


mods = []


def scan():
    global mods
    while True:
        mods = []
        for mod in os.scandir("mods"):
            if not mod.path.endswith(".py"):
                continue

            try:
                with open(mod.path, "r") as f:
                    code = f.read()

                sha1 = hashlib.sha1()
                sha1.update(code.encode("utf-8"))

                try:
                    modname = re.search(r"# ?meta title: (.*?)\n", code, re.S).group(1)
                except Exception:
                    try:
                        modname = re.search(
                            r'strings ?= ?{.*?[\'"]name[\'"]: ?[\'"](.+?)[\'"]',
                            code,
                            re.S,
                        ).group(1)
                    except Exception:
                        try:
                            modname = re.search(r"class (.+?)Mod\(", code, re.S).group(
                                1
                            )
                        except Exception:
                            modname = "Unknown"

                try:
                    description = re.search(
                        r"# ?meta desc: ?(.*?)\n", code, re.S
                    ).group(1)
                except Exception:
                    try:
                        description = re.search(
                            r'class .+?Mod\(.*?Module\):.*?\n[ \t]*[\'"]{1,3}(.+?)[\'"]{1,3}',
                            code,
                            re.S,
                        ).group(1)
                    except Exception:
                        description = "No description"

                try:
                    pic = re.search(
                        r"# ?meta pic: ?(https?://.*?)\n", code, re.S
                    ).group(1)
                except Exception:
                    pic = "https://img.icons8.com/external-icongeek26-flat-icongeek26/64/000000/external-no-photo-museum-icongeek26-flat-icongeek26.png"

                mods.append(
                    {
                        "sha": str(sha1.hexdigest()),
                        "name": modname,
                        "pic": pic,
                        "desc": description,
                        "link": f"https://{URL}/{mod.path.split('/')[-1]}",
                        "lines": code.count("\n") + 1,
                        "chars": len(code),
                        "cws": len(code)
                        - sum(len(_) for _ in re.findall(r'(""".*?""")|(#.*)', code)),
                        "file": mod.path.split("/")[-1],
                    }
                )
            except AttributeError:
                pass

        mods.sort(key=lambda x: x["name"].lower())

        sleep(10)


Thread(target=scan).start()

app.run(port=PORT)