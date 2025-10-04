from flask import Flask, request, render_template_string
import ranker

app = Flask(__name__)

HTML_TEMPLATE = """
<!doctype html>
<html>
<head>
    <title>VIT Project: Search Engine</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        h1 { color: #333; }
        form { margin-bottom: 20px; }
        input[type=text] { width: 300px; padding: 5px; }
        input[type=submit] { padding: 5px 10px; }
        ul { line-height: 1.8; }
    </style>
</head>
<body>
    <h1>VIT Project: Search Engine</h1>
    <form method="get">
        <input type="text" name="q" placeholder="Enter your search..." value="{{ query|default('') }}">
        <input type="submit" value="Search">
    </form>

    {% if results %}
        <h2>Results</h2>
        <ul>
        {% for url, score in results %}
            <li><a href="{{ url }}" target="_blank">{{ url }}</a> (score: {{ "%.4f"|format(score) }})</li>
        {% endfor %}
        </ul>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET"])
def search():
    query = request.args.get("q", "")
    results = []

    if query:
        results = ranker.rank_pages(query, top_k=10)

    return render_template_string(HTML_TEMPLATE, query=query, results=results)


if __name__ == "__main__":
    app.run(debug=True)