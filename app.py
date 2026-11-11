import hmac
import os
from uuid import uuid4

import dash_bootstrap_components as dbc
from dash import Dash, Input, Output, State, ctx, dcc, no_update
from dash.exceptions import PreventUpdate
from flask import Flask, Response, jsonify, request

from gbs_service import answer_question

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024


@app.before_request
def protect_application():
    password = os.getenv("APP_PASSWORD", "")
    username = os.getenv("APP_USERNAME", "oba")

    if not password:
        return Response(
            "APP_PASSWORD is nog niet ingesteld in Vercel.",
            status=503,
            content_type="text/plain; charset=utf-8",
        )

    credentials = request.authorization

    valid = (
        credentials is not None
        and credentials.type.lower() == "basic"
        and hmac.compare_digest(
            (credentials.username or "").encode("utf-8"),
            username.encode("utf-8"),
        )
        and hmac.compare_digest(
            (credentials.password or "").encode("utf-8"),
            password.encode("utf-8"),
        )
    )

    if not valid:
        return Response(
            "Aanmelden vereist.",
            status=401,
            headers={
                "WWW-Authenticate": 'Basic realm="GBS-vraagbaak"'
            },
            content_type="text/plain; charset=utf-8",
        )


@app.after_request
def response_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.post("/start_thread")
def start_thread():
    return jsonify(
        {
            "thread_id": str(uuid4()),
            "response": {
                "type": "faq",
                "message": "Stel je vraag over de GBS-migratie.",
                "results": [],
            },
        }
    )


@app.post("/send_message")
def send_message():
    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"error": "Ongeldige aanvraag."}), 400

    result, status = answer_question(
        data.get("user_input"),
        data.get("history", []),
    )

    thread_id = data.get("thread_id")
    if not isinstance(thread_id, str):
        thread_id = str(uuid4())

    return jsonify(
        {
            "thread_id": thread_id[:100],
            "response": {
                "type": "faq",
                "message": result["message"],
                "results": result["results"],
            },
        }
    ), status


BUTTON = {
    "background": "#ffffff",
    "color": "#000000",
    "border": "1px solid #000000",
    "borderRadius": "5px",
    "padding": "10px 14px",
    "cursor": "pointer",
    "fontSize": "15px",
    "fontFamily": "Arial, sans-serif",
}

BUBBLE = {
    "border": "1px solid #000000",
    "borderRadius": "5px",
    "padding": "12px",
    "marginBottom": "12px",
    "background": "#ffffff",
    "whiteSpace": "pre-wrap",
    "overflowWrap": "anywhere",
    "lineHeight": "1.5",
    "fontSize": "15px",
}

WELCOME = (
    "Stel je vraag over de GBS-migratie. "
    "Antwoorden komen uitsluitend uit de GBS-FAQ. "
    "Een antwoord kan nog voorlopig zijn."
)

web = Dash(
    __name__,
    server=app,
    title="OBA | GBS-vraagbaak",
    update_title="Antwoord zoeken…",
    serve_locally=True,
)


def layout():
    return dbc.Container(
        [
            dcc.Store(
                id="conversation",
                storage_type="memory",
                data=[],
            ),
            dbc.Card(
                [
                    dbc.CardHeader(
                        [
                            dbc.Label(
                                "OBA | GBS-vraagbaak",
                                style={
                                    "fontWeight": "bold",
                                    "fontSize": "20px",
                                    "margin": "0",
                                },
                            ),
                            dbc.Button(
                                "Nieuw gesprek",
                                id="restart",
                                n_clicks=0,
                                style=BUTTON,
                            ),
                        ],
                        style={
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "space-between",
                            "gap": "12px",
                            "flexWrap": "wrap",
                            "padding": "14px",
                            "borderBottom": "1px solid #000000",
                        },
                    ),
                    dbc.Label(
                        "Database: GBS-FAQ · Nieuwste vraag bovenaan",
                        style={
                            "fontSize": "12px",
                            "padding": "10px 14px 0",
                            "margin": "0",
                            "color": "#555555",
                        },
                    ),
                    dbc.CardBody(
                        id="chat",
                        children=[
                            dbc.CardBody(
                                WELCOME,
                                style=BUBBLE,
                            ),
                        ],
                        style={
                            "flex": "1",
                            "minHeight": "0",
                            "overflowY": "auto",
                            "padding": "14px",
                        },
                    ),
                    dbc.Label(
                        "",
                        id="status",
                        style={
                            "margin": "0",
                            "padding": "0 14px 8px",
                            "fontSize": "13px",
                        },
                    ),
                    dbc.CardBody(
                        [
                            dbc.Input(
                                id="question",
                                type="text",
                                placeholder="Stel je vraag over GBS…",
                                maxLength=2000,
                                n_submit=0,
                                autoComplete="off",
                                style={
                                    "flex": "1",
                                    "minWidth": "0",
                                    "padding": "12px",
                                    "border": "1px solid #000000",
                                    "borderRadius": "5px",
                                    "fontSize": "16px",
                                    "fontFamily": "Arial, sans-serif",
                                    "background": "#ffffff",
                                    "color": "#000000",
                                },
                            ),
                            dbc.Button(
                                "Verstuur",
                                id="send",
                                n_clicks=0,
                                style=BUTTON,
                            ),
                        ],
                        style={
                            "display": "flex",
                            "gap": "8px",
                            "padding": "12px",
                            "borderTop": "1px solid #000000",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "width": "100%",
                    "maxWidth": "650px",
                    "height": "90dvh",
                    "border": "1px solid #000000",
                    "borderRadius": "5px",
                    "overflow": "hidden",
                    "background": "#ffffff",
                },
            ),
        ],
        fluid=True,
        style={
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "minHeight": "100dvh",
            "padding": "12px",
            "boxSizing": "border-box",
            "background": "#ffffff",
            "color": "#000000",
            "fontFamily": "Arial, sans-serif",
        },
    )


web.layout = layout


def render_conversation(turns):
    blocks = []

    for turn in reversed(turns):
        blocks.append(
            dbc.CardBody(
                turn["question"],
                style={
                    **BUBBLE,
                    "marginLeft": "15%",
                    "fontWeight": "bold",
                },
            )
        )

        response = turn.get("response") or {}
        results = response.get("results") or []

        if response.get("message"):
            blocks.append(
                dbc.CardBody(
                    response["message"],
                    style={**BUBBLE, "marginRight": "8%"},
                )
            )

        for document in results:
            blocks.append(
                dbc.Card(
                    [
                        dbc.CardHeader(
                            document["onderwerp"],
                            style={
                                "fontSize": "12px",
                                "color": "#555555",
                                "marginBottom": "8px",
                            },
                        ),
                        dbc.Label(
                            document["vraag"],
                            style={
                                "display": "block",
                                "fontWeight": "bold",
                                "marginBottom": "8px",
                            },
                        ),
                        dbc.CardBody(
                            document["antwoord"],
                            style={"whiteSpace": "pre-wrap"},
                        ),
                    ],
                    style={**BUBBLE, "marginRight": "8%"},
                )
            )

    if not blocks:
        blocks.append(dbc.CardBody(WELCOME, style=BUBBLE))

    return blocks


@web.callback(
    Output("conversation", "data"),
    Output("chat", "children"),
    Output("question", "value"),
    Input("send", "n_clicks"),
    Input("question", "n_submit"),
    Input("restart", "n_clicks"),
    State("question", "value"),
    State("conversation", "data"),
    prevent_initial_call=True,
    running=[
        (Output("send", "disabled"), True, False),
        (Output("question", "disabled"), True, False),
        (Output("restart", "disabled"), True, False),
        (Output("status", "children"), "Antwoord zoeken…", ""),
    ],
)
def handle_question(send_clicks, submits, restarts, question, turns):
    if ctx.triggered_id == "restart":
        return [], render_conversation([]), ""

    if not isinstance(question, str) or not question.strip():
        raise PreventUpdate

    if len(question) > 2000:
        return no_update, no_update, no_update

    question = question.strip()

    if not isinstance(turns, list):
        turns = []

    safe_turns = [
        turn
        for turn in turns[-12:]
        if isinstance(turn, dict)
        and isinstance(turn.get("question"), str)
        and isinstance(turn.get("response"), dict)
    ]

    history = [turn["question"] for turn in safe_turns][-6:]
    result, status = answer_question(question, history)

    # Bewaar mislukte aanvragen niet als gesprekscontext.
    if status >= 400:
        error_turn = {"question": question, "response": result}
        return (
            safe_turns,
            render_conversation(safe_turns + [error_turn]),
            question,
        )

    updated = (
        safe_turns + [{"question": question, "response": result}]
    )[-12:]

    return updated, render_conversation(updated), ""


if __name__ == "__main__":
    web.run(host="127.0.0.1", port=8000, debug=False)
