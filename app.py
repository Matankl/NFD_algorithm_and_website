"""
Flask front-end for the 'Nearly-Fair Division with Capacity Constraints' demo.

To run locally with:
    $ python3 -m venv venv && . venv/bin/activate
    (venv)$ pip install -r requirements.txt
    (venv)$ flask --app app run --debug

Open http://127.0.0.1:5000/ in your browser.
"""

import io
import json
import logging
import traceback

from flask import (Flask, flash, redirect, render_template,
                   request, url_for)

# ----------------------------------------------------------------------
#  Import your algorithm and helpers (they live in NFD.py / fairpyx)
# ----------------------------------------------------------------------
from NFD import Nearly_Fair_Division
from fairpyx import Instance, divide
from is_EF11 import is_EF11  # Import the EF11 checker

# ----------------------------------------------------------------------
#  Flask setup
# ----------------------------------------------------------------------
app = Flask(__name__)
app.secret_key = "CHANGE-ME-IN-PRODUCTION"        # Needed for flash messages

# ----------------------------------------------------------------------
#  Logging: capture algorithm output into an in-memory StringIO
# ----------------------------------------------------------------------
algo_logger = logging.getLogger("fair_division_demo")
algo_logger.setLevel(logging.INFO)
# algo_logger.setLevel(logging.WARNING)
if not algo_logger.handlers:
    import sys
    algo_logger.addHandler(logging.StreamHandler(sys.stdout))


def run_algorithm_and_capture_logs(instance: Instance) -> tuple[dict, str]:
    """
    Execute Nearly_Fair_Division on *instance* and return:
        (allocation_dict, log_text)
    """
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(
        logging.Formatter("[%(levelname)s] %(message)s")
    )

    # Capture the NFD module's logger
    nfd_logger = logging.getLogger("NFD")
    nfd_logger.addHandler(handler)
    nfd_logger.setLevel(logging.INFO)  # or logging.DEBUG for more detail

    try:
        allocation = divide(Nearly_Fair_Division, instance=instance)
    finally:
        handler.flush()
        nfd_logger.removeHandler(handler)

    return allocation, log_stream.getvalue()


# ----------------------------------------------------------------------
#  Routes
# ----------------------------------------------------------------------
@app.route("/")
def index():
    """Landing page – high-level explanation & nav links."""
    return render_template("index.html")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/demo", methods=["GET", "POST"])
def demo():
    """
    GET  → show the input form.
    POST → parse JSON, run the algorithm, show allocation + logs.
    """
    if request.method == "GET":
        # Blank form (prefilled with the example from the prompt)
        return render_template("input.html", example=_EXAMPLE_INPUT)

    # ------------------------------------------------------------------
    # POST: read & validate the four JSON blocks
    # ------------------------------------------------------------------
    try:
        valuations = json.loads(request.form["valuations"])
        item_categories = json.loads(request.form["item_categories"])
        item_capacities = {item: 1 for item in item_categories}
        category_capacities = json.loads(request.form["category_capacities"])
    except json.JSONDecodeError as exc:
        flash(f" JSON parsing error: {exc}", "danger")
        return redirect(url_for("demo"))

    # ------------------------------------------------------------------
    # Build an Instance object and run the algorithm
    # ------------------------------------------------------------------
    try:
        instance = Instance(
            valuations=valuations,
            item_categories=item_categories,
            item_capacities=item_capacities,
            category_capacities=category_capacities,
        )
        allocation, log_text = run_algorithm_and_capture_logs(instance)

        # Run EF11 analysis
        ef11_result = None
        if allocation:
            try:
                ef11_result = is_EF11(instance, allocation)
            except Exception as e:
                log_text += f"\n\n[WARNING] EF11 analysis failed: {e}"

    except Exception as exc:
        # Any failure (invalid input, algorithm bug, etc.) lands here
        tb = traceback.format_exc()
        flash(f"Algorithm raised an exception: {exc}", "danger")
        return render_template(
            "result.html",
            raw_input=_pretty_json(
                valuations, category_capacities,
                ),
            logs=tb,
            allocation=None,
            ef11_result=None,
            item_details=None,
            agents=None,
        )

    # ------------------------------------------------------------------
    # Prepare item details for display
    # ------------------------------------------------------------------
    item_details = []
    agents = list(valuations.keys())
    for item, category in item_categories.items():
        detail = {
            'item': item,
            'category': category,
            'values': {agent: valuations[agent].get(item, 0) for agent in agents},
            'allocated_to': None
        }
        # Find which agent got this item
        for agent, bundle in allocation.items():
            if item in bundle:
                detail['allocated_to'] = agent
                break
        item_details.append(detail)

    # Sort by category then by item name
    item_details.sort(key=lambda x: (x['category'], x['item']))

    # ------------------------------------------------------------------
    # Success: show everything
    # ------------------------------------------------------------------
    return render_template(
        "result.html",
        raw_input=_pretty_json(
            valuations, item_categories, category_capacities
        ),
        logs=log_text,
        allocation=allocation,
        ef11_result=ef11_result,
        item_details=item_details,
        agents=agents,
    )


# ----------------------------------------------------------------------
#  Helpers
# ----------------------------------------------------------------------
def _pretty_json(*objs) -> str:
    """Nicely indent several JSON dicts one after another."""
    return "\n\n".join(json.dumps(o, indent=2, ensure_ascii=False) for o in objs)


# ----------------------------------------------------------------------
#  Prefill-example exactly as you gave it
# ----------------------------------------------------------------------
_EXAMPLE_INPUT = {
    "valuations": {
        "Agent1": {"o1": 0, "o2": -1, "o3": -4, "o4": -5, "o5": 0, "o6": 2},
        "Agent2": {"o1": 0, "o2": -1, "o3": -2, "o4": -1, "o5": -1, "o6": 0},
    },
    "item_categories": {
        "o1": "cat1",
        "o2": "cat1",
        "o3": "cat1",
        "o4": "cat1",
        "o5": "cat2",
        "o6": "cat2",
    },
    "category_capacities": {"cat1": 2, "cat2": 1},
}

# ----------------------------------------------------------------------
#  'main' guard – so gunicorn / flask run both work
# ----------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True,host="0.0.0.0",port=5000)