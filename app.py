"""
    █ █ ▀ █▄▀ ▄▀█ █▀█ ▀    ▄▀█ ▀█▀ ▄▀█ █▀▄▀█ ▄▀█
    █▀█ █ █ █ █▀█ █▀▄ █ ▄  █▀█  █  █▀█ █ ▀ █ █▀█

    Copyright 2022 t.me/hikariatama
    Licensed under the GNU GPLv3
"""


from fastapi import (
    FastAPI,
    Request,
    Response,
)
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware


import re

import hashlib
import os
import json
import io

from PIL import Image, ImageDraw, ImageFont
import textwrap

import logging
import random

import requests
import flask

import asyncio

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(SCRIPT_PATH, "config.json"), "r") as f:
    config = json.loads(f.read())

templates = Jinja2Templates(directory="templates")

minimal_txt = """backuper
cloud
terminal"""

URL = config["url"]
LICENSE = config["license"]
PORT = config["port"]

if not os.path.isdir(os.path.join(SCRIPT_PATH, "badges")):
    os.mkdir(os.path.join(SCRIPT_PATH, "badges"), mode=0o755)

logger = logging.getLogger("root")
logger.addHandler(logging.StreamHandler())

SIZE = (1200, 320)
INNER_MARGIN = (16, 16)
PADDING = (128, 0)

TRACK_FS = 48
ARTIST_FS = 32
MINITEXT = 18

with open(os.path.join(SCRIPT_PATH, "font.ttf"), "rb") as f:
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


async def update_badges():
    while True:
        logger.debug("Reloading badges")

        for i, mod in enumerate(mods):
            badge = create_badge(mod)
            with open(
                os.path.join(
                    os.path.join(SCRIPT_PATH, "badges"),
                    f'{mod["file"].split(".")[0]}.jpg',
                ),
                "wb",
            ) as f:
                f.write(badge)
            logger.debug(f"Processed {i + 1}/{len(mods)}")

        logger.debug("Badges reloaded")
        await asyncio.sleep(120)


async def download_mojies():
    global mojies_
    for _ in os.scandir(os.path.join(SCRIPT_PATH, "pics")):
        if _.path.endswith(".png"):
            mojies_ += [Image.open(_.path).convert("RGBA")]

    await update_badges()


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

    if mod["hikka_only"]:
        thickness = 5

        rect_2 = (
            (rect[0][0] - thickness * 3, rect[0][1] - thickness * 3),
            (rect[1][0] + thickness * 3, rect[1][1] + thickness * 3),
        )
        draw.rounded_rectangle(rect_2, 15, fill="#913597")

        rect_2 = (
            (rect[0][0] - thickness * 2, rect[0][1] - thickness * 2),
            (rect[1][0] + thickness * 2, rect[1][1] + thickness * 2),
        )
        draw.rounded_rectangle(rect_2, 15, fill="#712a76")

        rect_2 = (
            (rect[0][0] - thickness, rect[0][1] - thickness),
            (rect[1][0] + thickness, rect[1][1] + thickness),
        )
        draw.rounded_rectangle(rect_2, 15, fill="#4a1d4d")

    draw.rounded_rectangle(rect, 15, fill=(10, 10, 10))
    draw.rounded_rectangle(
        ((4, 4), (liliput.getsize(comm)[0] + 16, liliput.getsize(comm)[1] + 16)),
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
    draw.text((8, 8), comm, (100, 100, 100), font=liliput)

    offset = tpos[1] + TRACK_FS + 8
    for line in lines:
        draw.text((tpos[0], offset), line, font=font_smaller, fill=(180, 180, 180))
        offset += font_smaller.getsize(line)[1]

    img = io.BytesIO()
    im.save(img, format="PNG")

    return img.getvalue()


logging.basicConfig(
    filename="debug.log",
    format="[%(levelname)s]: %(message)s",
    level=logging.ERROR,
)
root = logging.getLogger()
root.addHandler(flask.logging.default_handler)

app = FastAPI(docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/badge/{mod}")
async def get_badge_url_of_selected_mod(
    request: Request,
    mod: str,
):
    try:
        return JSONResponse(
            status_code=200,
            content={
                "badge": f"https://{URL}/badges/{mod}.jpg",
                "info": [_ for _ in mods if _["file"] == f"{mod}.py"][0],
            },
        )
    except IndexError:
        return Response(content="Not found", status_code=404)


@app.get("/badges/{mod}")
async def get_badge_file_of_selected_mod(
    request: Request,
    mod: str,
):
    if not os.path.isfile(f"badges/{mod}"):
        return Response(content="Not found", status_code=404)

    return FileResponse(f"badges/{mod}", media_type="image/jpeg")


@app.get("/full.txt")
async def get_all_mods_for_ftg_dlmod(request: Request):
    return Response(
        content="\n".join([_["file"].split(".")[0] for _ in mods]),
        media_type="text/plain; charset=utf-8",
    )


@app.get("/minimal.txt")
async def get_minimal_mods_for_ftg_dlmod(request: Request):
    return Response(
        content=minimal_txt or mods[0]["file"].split(".")[0],
        media_type="text/plain; charset=utf-8",
    )


@app.get("/mods.json")
async def get_mods_in_json_format(request: Request):
    global mods
    l_mods = {}
    for mod in mods.copy():
        l_mod = mod.copy()
        n = l_mod["name"]
        del l_mod["name"]
        l_mods[n] = l_mod

    return JSONResponse(
        status_code=200,
        content=l_mods,
    )


@app.get("/{mod}")
async def get_one_particular_mod(
    request: Request,
    mod: str,
):
    try:
        with open(
            os.path.join(os.path.join(SCRIPT_PATH, config["mods_path"]), mod),
            "r",
            encoding="utf-8",
        ) as f:
            code = f.read()
    except FileNotFoundError:
        return Response(content="Not found", status_code=404)

    return Response(content=code, media_type="text/plain; charset=utf-8")


@app.get("/view/{mod}")
async def get_web_view_of_mod(request: Request, mod: str):
    module = [_ for _ in mods if _["file"] == mod]
    if not module:
        return "Not found", 404

    module = module[0]

    with open(
        os.path.join(os.path.join(SCRIPT_PATH, config["mods_path"]), mod),
        "r",
        encoding="utf-8",
    ) as f:
        code = f.read()

    return templates.TemplateResponse(
        "view.html",
        {
            "request": request,
            "mod_name": mod,
            "mod_code": code,
            "mod_icon": module["pic"],
            "mod_desc": module["desc"],
            "url": URL,
        },
    )


@app.get("/")
async def main_page(request: Request):
    return templates.TemplateResponse(
        "mods.html", {"request": request, "mods": mods, "url": URL}
    )


mods = []


async def scan():
    global mods
    while True:
        mods = []
        for mod in os.scandir(os.path.join(SCRIPT_PATH, config["mods_path"])):
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

                commands = re.findall(r"async def ([^\n]+?)cmd\(self,", code, re.S)
                commands.sort()
                commands = [f".{i}" for i in commands]

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
                        "commands": commands,
                        "hikka_only": "#scope:hikka_only" in code.replace(" ", ""),
                    }
                )
            except AttributeError:
                logger.warning(f"Can't load module {mod.path.split('/')[-1]}")

        mods.sort(key=lambda x: x["name"].lower())

        await asyncio.sleep(10)


async def git_poller():
    if "disable_git_pull" not in config or not config["disable_git_pull"]:
        while True:
            os.popen(
                f"cd {os.path.join(SCRIPT_PATH, config['mods_path'])} && git stash && git pull -f && cd .."
            ).read()
            logger.debug("Pulled from git")
            await asyncio.sleep(60)


@app.on_event("shutdown")
def shutdown_event():
    for task in tasks:
        task.cancel()


tasks = []


@app.on_event("startup")
async def startup_event():
    global tasks
    tasks = [
        asyncio.ensure_future(download_mojies()),
        asyncio.ensure_future(git_poller()),
        asyncio.ensure_future(scan()),
    ]
