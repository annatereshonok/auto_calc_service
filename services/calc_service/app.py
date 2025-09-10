from flask import Flask, request, jsonify
from PIL import Image
import imagehash
import os
import uuid
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
try:
    import seaborn as sns
    sns.set_theme()
except Exception:
    pass
from datetime import datetime

app = Flask(__name__)

WORKDIR = os.path.abspath(os.environ.get("WORKDIR", "/workspace"))
IMAGES_DIR = os.path.join(WORKDIR, "plots")
os.makedirs(IMAGES_DIR, exist_ok=True)
PLOTS_DIR = IMAGES_DIR
REF_DIR = IMAGES_DIR


@app.get("/health")
def health():
    return {"status": "ok", "workspace": WORKDIR}


@app.post("/sum")
def do_sum():
    data = request.get_json(force=True)
    numbers = data.get("numbers", [])
    period = data.get("period", {})
    try:
        nums = [float(x) for x in numbers if x is not None]
    except Exception:
        return jsonify({"error": "numbers must be numeric list"}), 400

    s = float(sum(nums))
    c = int(len(nums))
    result_id = str(uuid.uuid4())
    return jsonify({
        "id": result_id,
        "sum": s,
        "count": c,
        "period": {
            "start": period.get("start"),
            "end": period.get("end")
        }
    })


@app.post("/plot")
def make_plot():
    data = request.get_json(force=True)
    dates = data.get("dates", [])
    values = data.get("values", [])
    title = data.get("title", "Сумма по периодам")

    if len(dates) != len(values):
        return jsonify({"error": "dates and values must have equal length"}), 400
    if not dates:
        return jsonify({"error": "empty series"}), 400

    xs = []
    for d in dates:
        try:
            xs.append(datetime.fromisoformat(str(d)))
        except Exception:
            xs.append(str(d))

    fig = plt.figure()
    plt.plot(xs, values, marker="o")
    plt.title(title)
    plt.xlabel("Дата")
    plt.ylabel("Значение")
    plt.grid(True)
    plt.tight_layout()

    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out_path = os.path.join(PLOTS_DIR, f"plot_{ts}.png")
    fig.savefig(out_path, dpi=160)
    plt.close(fig)

    ph = imagehash.phash(Image.open(out_path))
    return jsonify({
        "image_path": out_path,
        "phash": str(ph)
    })


@app.post("/similar")
def similar_images():
    data = request.get_json(force=True)
    target_path = data.get("image_path")
    search_dir = data.get("search_dir", REF_DIR)
    top_k = int(data.get("top_k", 5))

    if not target_path or not os.path.exists(target_path):
        return jsonify({"error": "target image not found"}), 400
    if not os.path.isdir(search_dir):
        return jsonify({"error": "search_dir not found"}), 400

    with Image.open(target_path) as im:
        target_hash = imagehash.phash(im)
    target_abs = os.path.abspath(target_path)
    max_bits = target_hash.hash.size

    results = []
    for root, _, files in os.walk(search_dir):
        for fname in files:
            if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                continue
            p = os.path.join(root, fname)

            try:
                if os.path.samefile(p, target_abs):
                    continue
            except Exception:
                if os.path.abspath(p) == target_abs:
                    continue

            try:
                with Image.open(p) as im:
                    h = imagehash.phash(im)
                dist = int(target_hash - h)
                sim = 1.0 - (dist / float(max_bits))
                results.append({
                    "path": p,
                    "phash": str(h),
                    "distance": dist,
                    "similarity": round(sim, 4)
                })
            except Exception:
                pass

    results.sort(key=lambda x: x["distance"])
    return jsonify({"target": target_path, "top": results[:top_k]})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
