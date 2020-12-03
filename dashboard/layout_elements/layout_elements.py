from typing import Dict

import dash_html_components as html
import dash_table
from dash.development.base_component import Component
from pandas import DataFrame
import dash_core_components as dcc


def optstatus_table(id: str, df: DataFrame) -> dash_table.DataTable:
    return dash_table.DataTable(
        style_table={
            "whiteSpace": "normal",
            "height": "auto",
            "overflowX": "scroll",
            "overflowY": "auto",
        },
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold",
            "whiteSpace": "normal",
            "height": "auto",
        },
        style_data_conditional=[
            {
                "if": {
                    "filter_query": '{Routing} contains "OPTIMAL"',
                    "column_id": "Routing",
                },
                "backgroundColor": "rgb(0, 128, 0)",
            },
            {
                "if": {
                    "filter_query": '{Routing} contains "FEASIBLE"',
                    "column_id": "Routing",
                },
                "backgroundColor": "rgb(255, 255, 0)",
            },
            {
                "if": {
                    "filter_query": '{Routing} contains "INFEASIBLE"',
                    "column_id": "Routing",
                },
                "backgroundColor": "rgb(255, 0, 0)",
            },
            {
                "if": {
                    "filter_query": '{Scheduling} contains "OPTIMAL"',
                    "column_id": "Scheduling",
                },
                "backgroundColor": "rgb(0, 128, 0)",
            },
            {
                "if": {
                    "filter_query": '{Scheduling} contains "FEASIBLE"',
                    "column_id": "Scheduling",
                },
                "backgroundColor": "rgb(255, 255, 0)",
            },
            {
                "if": {
                    "filter_query": '{Scheduling} contains "INFEASIBLE"',
                    "column_id": "Scheduling",
                },
                "backgroundColor": "rgb(255, 0, 0)",
            },
            {
                "if": {
                    "filter_query": '{Pint} contains "OPTIMAL"',
                    "column_id": "Pint",
                },
                "backgroundColor": "rgb(0, 128, 0)",
            },
            {
                "if": {
                    "filter_query": '{Pint} contains "FEASIBLE"',
                    "column_id": "Pint",
                },
                "backgroundColor": "rgb(255, 255, 0)",
            },
            {
                "if": {
                    "filter_query": '{Pint} contains "INFEASIBLE"',
                    "column_id": "Pint",
                },
                "backgroundColor": "rgb(255, 0, 0)",
            },
        ],
        style_cell={
            "font_size": "20px",
            "text_align": "center",
        },
        id=id,
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict("records"),
        page_size=10,
    )


def table(id: str, df: DataFrame) -> dash_table.DataTable:
    return dash_table.DataTable(
        style_table={
            "whiteSpace": "normal",
            "height": "auto",
            "overflowX": "scroll",
            "overflowY": "auto",
        },
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold",
            "whiteSpace": "normal",
            "height": "auto",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "rgb(248, 248, 248)"}
        ],
        style_cell={
            "font_family": "arial",
            "font_size": "20px",
            "text_align": "center",
            "whiteSpace": "normal",
            "height": "auto",
        },
        id=id,
        columns=[{"name": i, "id": i} for i in df.columns],
        data=df.to_dict("records"),
        page_size=10,
    )


def stream_checklist(tc_F: Dict) -> dcc.Checklist:
    return dcc.Checklist(
        id="checklist-display-routes",
        options=[
            {"label": f_id, "value": f_id}
            for f_id in tc_F.keys()
        ],
        value=[],
        labelStyle={"font-size": "32px"},
        inputStyle={"width": "2em", "height": "2em"},
        className="checkmark",
    )

def cytoscape_layout_dropdown() -> dcc.Dropdown:
    return dcc.Dropdown(
        id="dropdown-update-layout",
        value="cola",
        clearable=False,
        options=[
            {"label": name, "value": name}
            for name in [
                "cose",
                "concentric",
                "cose-bilkent",
                "cola",
                "euler",
                "spread",
                "dagre",
                "klay",
            ]
        ],
    )

def header(text: str) -> html.Div:
    return html.Div([html.Div([html.H1(text, className="section__header")])])


def section(elements: [Component]) -> html.Div:
    return html.Div(elements, className="section__container")


def row(elements: [Component]) -> html.Div:
    return html.Div(elements, className="row__container")


def column(elements: [Component], size: str="one-half") -> html.Div:
    """
    size is defined in app.css
    """
    return html.Div(elements, className=f"{size} column")

def columns(columns: [Component]) -> html.Div:
    return html.Div(columns, className="column__container first")


def inner_container(header_text: str, component: Component, foldable=True) -> html.Div:
    if foldable:
        return html.Div(
            [
                html.H2(header_text, className="subsection__header"),
                html.Details([html.Summary(""), component], open=True),
            ],
            className="row__container",
        )
    else:
        return html.Div(
            [
                html.H3(header_text, className="subsection__header"),
                html.Details([html.Summary(""), component], open=True),
            ],
            className="row__container",
        )

def inner_element(component: Component) -> html.Div:
    return html.Div(
        [
            component
        ],
        style={"width" : "100%", "margin": "5px", "margin-bottom" : "15px"},
    )

def inner_element_topology(component: Component) -> html.Div:
    return html.Div(
        [
            component
        ],
        style= {"width" : "100%", "height" : "100%", "margin": "5px", "margin-bottom" : "15px"},
    )

def inner_element_dag(component: Component) -> html.Div:
    return html.Div(
        [
            component
        ],
        style={"width" : "100%", "height" : "100%", "margin": "5px", "margin-bottom" : "15px"},
    )
