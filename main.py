from typing import Union
import re

RFC_3986_RESERVED_CHARACTERS = re.compile(r"[\"|!|#|$|&|'|(|)|*|+|,|/|:|;|=|?|@|\[|\]|\-|<|>|@|~|\||\\|\.|%]")
WHITESPACE = re.compile(r"\s+")

import uvicorn
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.templating import _TemplateResponse as TemplateResponse

from database import Database

d = Database("database.sqlite")

app = Starlette(
    routes=[Mount("/static", StaticFiles(directory="static"), name="static")],
    on_startup=[d.connect],
    on_shutdown=[d.disconnect],
)

templates = Jinja2Templates("html")


@app.route("/", methods=["GET"])
async def home(request: Request) -> TemplateResponse:
    posts = await d.connection.fetchall("SELECT * FROM articles;")
    return templates.TemplateResponse(
        name="index.jinja2", context={"request": request, "posts": posts}
    )

@app.route("/login", methods=["GET", "POST"])
async def login(request: Request) -> TemplateResponse:
    if request.method == "GET":
        return templates.TemplateResponse(
            name="login.jinja2", context={"request": request}
        )

@app.route("/register", methods=["GET", "POST"])
async def register(request: Request) -> TemplateResponse:
    if request.method == "GET":
        return templates.TemplateResponse(
            name="register.jinja2", context={"request": request}
        )

@app.route("/submit", methods=["GET", "POST"])
async def submit(request: Request) -> Union[TemplateResponse, RedirectResponse]:
    if request.method == "GET":
        return templates.TemplateResponse(
            name="submit.jinja2", context={"request": request}
        )
    else:
        form = await request.form()
        author, title, content = tuple(form.values())
        url_name = WHITESPACE.sub("-", RFC_3986_RESERVED_CHARACTERS.sub("", title.lower()))

        if not url_name:
            return templates.TemplateResponse(
                name="error.jinja2",
                context={
                    "request": request,
                    "reason": "Your article name was comprised"
                    " entirely of RFC 3986 section 2.2 Reserved Characters, they were all"
                    " removed and now your article is called nothing...",
                },
                status_code=400,
            )

        if not await d.connection.fetchone(
            "SELECT * FROM articles WHERE url_name=?;", url_name
        ):
            await d.connection.execute(
                "INSERT INTO articles(url_name, title, author, content) VALUES (?, ?, ?, ?);",
                url_name,
                title,
                author,
                content,
            )

            return RedirectResponse("/", status_code=303)
        else:
            return templates.TemplateResponse(
                name="error.jinja2",
                context={"request": request, "reason": "That article already exists!"},
                status_code=400,
            )


@app.route("/articles/{name}", methods=["GET"])
async def article(request: Request) -> Union[TemplateResponse, RedirectResponse]:
    name = request.path_params["name"].lower()
    if row := await d.connection.fetchone(
        "SELECT * FROM articles WHERE url_name=?;", name
    ):
        return templates.TemplateResponse(
            name="article.jinja2",
            context={
                "request": request,
                "title": row["title"],
                "author": row["author"],
                "content": row["content"],
            },
        )
    else:
        return templates.TemplateResponse(
            name="error.jinja2",
            context={"request": request, "reason": "That article does not exist."},
            status_code=404,
        )


if __name__ == "__main__":
    uvicorn.run(app, port=8080)  # type: ignore
