"""Risena – backend Flask: admin panel + penyaji website.

Jalankan:  python app.py   →  toko di http://localhost:5000 , admin di /admin
Data produk disimpan di ../data/products.js (format sama dengan yang dibaca website statis),
foto disimpan di ../foto/. Jadi folder frontend tetap bisa dijalankan TANPA backend.
"""
import csv, io, json, os, re, secrets, shutil, sqlite3, threading, time, uuid
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (Flask, Response, abort, flash, jsonify, redirect, render_template,
                   request, send_from_directory, session, url_for)
from PIL import Image, ImageOps, UnidentifiedImageError

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name(".env"))
except ImportError:
    pass

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent                      # folder frontend (index.html, assets, data, foto)
DATA_FILE = ROOT / "data" / "products.js"
FOTO_DIR = ROOT / "foto"
BACKUP_DIR = BASE / "backup"
DB_FILE = BASE / "pesanan.db"          # data pembeli: sengaja di luar folder frontend (tidak publik)
for d in (FOTO_DIR, BACKUP_DIR):
    d.mkdir(exist_ok=True)

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
ICONS = {"bag": "Tas", "wallet": "Dompet", "pouch": "Pouch", "key": "Gantungan"}
TAGS = {"": "Tanpa label", "best": "Best Seller", "hot": "Hot", "trendy": "Trendy"}
ALLOWED_EXT = {"png", "jpg", "jpeg", "webp"}
MAX_BANNER = 5
STATUS = {"menunggu": "Menunggu bayar", "dibayar": "Sudah dibayar", "diproses": "Diproses",
          "dikirim": "Dikirim", "selesai": "Selesai", "batal": "Batal"}

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
    MAX_CONTENT_LENGTH=16 * 1024 * 1024,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
)
_lock = threading.Lock()
_fails = {}
_order_hits = {}


# ------------------------------------------------------------------ data store
def load():
    txt = DATA_FILE.read_text("utf-8")
    m = re.search(r"=\s*(\{.*\})\s*;?\s*$", txt, re.S)
    return json.loads(m.group(1))


def save(data):
    if DATA_FILE.exists():  # backup otomatis, simpan 20 terakhir
        shutil.copy(DATA_FILE, BACKUP_DIR / f"products-{datetime.now():%Y%m%d-%H%M%S}.js")
        for old in sorted(BACKUP_DIR.glob("products-*.js"))[:-20]:
            old.unlink()
    out = "window.BATIKKU = " + json.dumps(data, indent=2, ensure_ascii=False) + ";\n"
    tmp = DATA_FILE.with_suffix(".tmp")
    tmp.write_text(out, "utf-8")
    os.replace(tmp, DATA_FILE)


def used_photos(data):
    s = {p.get("foto") for p in data["produk"]} | {b.get("foto") for b in data["banner"]}
    return {x for x in s if x}


def save_image(file, max_side=1200):
    """Validasi, perkecil, dan simpan sebagai WEBP. Mengembalikan 'foto/xxxx.webp'."""
    if not file or not file.filename:
        return None
    if file.filename.rsplit(".", 1)[-1].lower() not in ALLOWED_EXT:
        raise ValueError("Format foto harus JPG, PNG, atau WEBP.")
    try:
        img = Image.open(file.stream)
        img.load()
    except (UnidentifiedImageError, OSError):
        raise ValueError("File bukan gambar yang valid.")
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")
    img.thumbnail((max_side, max_side))
    name = f"{uuid.uuid4().hex[:12]}.webp"
    img.save(FOTO_DIR / name, "WEBP", quality=82)
    return f"foto/{name}"


def remove_photo(path, data):
    """Hapus file foto jika sudah tidak dipakai produk/banner mana pun."""
    if path and path.startswith("foto/") and path not in used_photos(data):
        f = (ROOT / path).resolve()
        if f.parent == FOTO_DIR.resolve() and f.exists():
            f.unlink()


# ------------------------------------------------------------------ helpers
def slug(text):
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:40] or "produk"


def to_int(v, default=0):
    d = re.sub(r"\D", "", v or "")
    return int(d) if d else default


def parse_product(form):
    p = {
        "nama": form.get("nama", "").strip(),
        "kategori": form.get("kategori", "").strip(),
        "harga": to_int(form.get("harga")),
        "ikon": form.get("ikon") if form.get("ikon") in ICONS else "bag",
        "tag": form.get("tag") if form.get("tag") in TAGS else "",
        "terjual": to_int(form.get("terjual")),
        "aktif": form.get("aktif") == "on",
        "deskripsi": form.get("deskripsi", "").strip(),
        "spesifikasi": [l.strip() for l in form.get("spesifikasi", "").splitlines() if ":" in l],
    }
    errors = []
    if not p["nama"]:
        errors.append("Nama produk wajib diisi.")
    if not p["kategori"]:
        errors.append("Kategori wajib diisi.")
    if p["harga"] <= 0:
        errors.append("Harga harus lebih dari 0.")
    return p, errors


def blank():
    return {"nama": "", "kategori": "", "harga": "", "ikon": "bag", "tag": "", "terjual": 0,
            "aktif": True, "deskripsi": "", "spesifikasi": [], "foto": ""}


def find(data, pid):
    return next((p for p in data["produk"] if p["id"] == pid), None)


def categories(data):
    return sorted({p["kategori"] for p in data["produk"]})


# ------------------------------------------------------------------ pesanan (SQLite)
def db(sql, args=(), one=False, write=False):
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(sql, args)
        if write:
            con.commit()
            return cur.rowcount
        rows = cur.fetchall()
        return (rows[0] if rows else None) if one else rows
    finally:
        con.close()


db("""CREATE TABLE IF NOT EXISTS orders(
    id TEXT PRIMARY KEY, created TEXT, nama TEXT, alamat TEXT, metode TEXT, items TEXT,
    total INTEGER, ongkir INTEGER DEFAULT 0, status TEXT DEFAULT 'menunggu',
    resi TEXT DEFAULT '', catatan TEXT DEFAULT '')""", write=True)


def new_order_id():
    while True:
        oid = f"BTK-{datetime.now():%d%m}-{secrets.randbelow(9000) + 1000}"
        if not db("SELECT 1 FROM orders WHERE id=?", (oid,), one=True):
            return oid


def build_items(raw):
    """Susun item pesanan dari katalog server (harga tidak dipercaya dari klien)."""
    catalog = {p["id"]: p for p in load()["produk"] if p.get("aktif", True)}
    items = []
    for it in (raw or [])[:30]:
        try:
            qty = min(max(int(it.get("qty", 1)), 1), 999)
        except (TypeError, ValueError, AttributeError):
            continue
        p = catalog.get(str(it.get("id")))
        if p:
            items.append({"id": p["id"], "nama": p["nama"], "motif": str(it.get("motif", ""))[:40],
                          "harga": p["harga"], "qty": qty})
    return items


def insert_order(oid, nama, alamat, metode, items):
    total = sum(i["harga"] * i["qty"] for i in items)
    db("INSERT INTO orders(id,created,nama,alamat,metode,items,total) VALUES(?,?,?,?,?,?,?)",
       (oid, f"{datetime.now():%Y-%m-%d %H:%M}", nama, alamat, metode,
        json.dumps(items, ensure_ascii=False), total), write=True)


# ------------------------------------------------------------------ security
def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


app.jinja_env.globals.update(csrf_token=csrf_token, ICONS=ICONS, TAGS=TAGS, STATUS=STATUS)


@app.context_processor
def inject_pending():
    if session.get("admin"):
        return {"pending": db("SELECT COUNT(*) c FROM orders WHERE status='menunggu'", one=True)["c"]}
    return {"pending": 0}
app.jinja_env.filters["rupiah"] = lambda n: "Rp " + f"{int(n):,}".replace(",", ".")


@app.before_request
def csrf_protect():
    if request.method == "POST" and request.endpoint != "api_pesanan":
        sent, real = request.form.get("csrf", ""), session.get("csrf", "")
        if not real or not secrets.compare_digest(sent.encode(), real.encode()):
            abort(400, "Token tidak valid, muat ulang halaman.")


def login_required(f):
    @wraps(f)
    def wrapper(*a, **kw):
        if not session.get("admin"):
            return redirect(url_for("login"))
        return f(*a, **kw)
    return wrapper


@app.after_request
def headers(resp):
    if request.path.startswith(("/admin", "/data")):
        resp.headers["Cache-Control"] = "no-store"
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    return resp


# ------------------------------------------------------------------ website (frontend)
@app.route("/")
def home():
    return send_from_directory(ROOT, "index.html")


@app.route("/assets/<path:p>")
def assets(p):
    return send_from_directory(ROOT / "assets", p)


@app.route("/data/<path:p>")
def data_files(p):
    return send_from_directory(ROOT / "data", p)


@app.route("/foto/<path:p>")
def foto(p):
    return send_from_directory(FOTO_DIR, p)


# ------------------------------------------------------------------ admin
@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        ip, now = request.remote_addr, time.time()
        _fails[ip] = [t for t in _fails.get(ip, []) if now - t < 300]
        if len(_fails[ip]) >= 5:
            flash("Terlalu banyak percobaan. Coba lagi 5 menit lagi.", "err")
            return render_template("login.html"), 429
        u, pw = request.form.get("user", ""), request.form.get("password", "")
        if (secrets.compare_digest(u.encode(), ADMIN_USER.encode())
                and secrets.compare_digest(pw.encode(), ADMIN_PASSWORD.encode())):
            session.clear()
            session["admin"] = True
            return redirect(url_for("dashboard"))
        _fails[ip].append(now)
        flash("Username atau password salah.", "err")
    return render_template("login.html")


@app.route("/admin/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin")
@login_required
def dashboard():
    return render_template("dashboard.html", produk=load()["produk"],
                           default_pw=(ADMIN_PASSWORD == "admin123"))


@app.route("/admin/produk/baru", methods=["GET", "POST"])
@login_required
def produk_baru():
    if request.method == "POST":
        p, errors = parse_product(request.form)
        photo = None
        if not errors:
            try:
                photo = save_image(request.files.get("foto"))
            except ValueError as e:
                errors.append(str(e))
        if not errors:
            with _lock:
                data = load()
                p["foto"] = photo or ""
                p["id"] = f"{slug(p['nama'])}-{uuid.uuid4().hex[:4]}"
                data["produk"].insert(0, p)
                save(data)
            flash("Produk berhasil ditambahkan.", "ok")
            return redirect(url_for("dashboard"))
        for e in errors:
            flash(e, "err")
        p["foto"] = ""
        return render_template("form.html", p=p, baru=True, kategori=categories(load()))
    return render_template("form.html", p=blank(), baru=True, kategori=categories(load()))


@app.route("/admin/produk/<pid>/edit", methods=["GET", "POST"])
@login_required
def produk_edit(pid):
    data = load()
    cur = find(data, pid)
    if not cur:
        abort(404)
    if request.method == "POST":
        p, errors = parse_product(request.form)
        photo = None
        if not errors:
            try:
                photo = save_image(request.files.get("foto"))
            except ValueError as e:
                errors.append(str(e))
        if not errors:
            with _lock:
                data = load()
                cur = find(data, pid)
                old = cur.get("foto", "")
                cur.update(p)
                if photo:
                    cur["foto"] = photo
                elif request.form.get("hapus_foto") == "on":
                    cur["foto"] = ""
                save(data)
                if old != cur["foto"]:
                    remove_photo(old, data)
            flash("Perubahan disimpan.", "ok")
            return redirect(url_for("dashboard"))
        for e in errors:
            flash(e, "err")
        p.update(id=pid, foto=cur.get("foto", ""))
        return render_template("form.html", p=p, baru=False, kategori=categories(data))
    return render_template("form.html", p=cur, baru=False, kategori=categories(data))


@app.route("/admin/produk/<pid>/toggle", methods=["POST"])
@login_required
def produk_toggle(pid):
    with _lock:
        data = load()
        p = find(data, pid) or abort(404)
        p["aktif"] = not p.get("aktif", True)
        save(data)
    flash(("Produk ditampilkan." if p["aktif"] else "Produk disembunyikan."), "ok")
    return redirect(url_for("dashboard"))


@app.route("/admin/produk/<pid>/hapus", methods=["POST"])
@login_required
def produk_hapus(pid):
    with _lock:
        data = load()
        p = find(data, pid) or abort(404)
        data["produk"].remove(p)
        save(data)
        remove_photo(p.get("foto"), data)
    flash("Produk dihapus.", "ok")
    return redirect(url_for("dashboard"))


@app.route("/admin/pengaturan", methods=["GET", "POST"])
@login_required
def settings():
    data = load()
    if request.method == "POST":
        errors, banners, olds = [], [], []
        wa = re.sub(r"\D", "", request.form.get("wa", ""))
        wa = "62" + wa[1:] if wa.startswith("0") else wa
        if len(wa) < 9:
            errors.append("Nomor WhatsApp tidak valid (contoh: 6281234567890).")
        for i in range(MAX_BANNER):
            f = request.form
            atas, judul = f.get(f"atas_{i}", "").strip(), f.get(f"judul_{i}", "").strip()
            foto_lama = f.get(f"foto_lama_{i}", "")
            try:
                new = save_image(request.files.get(f"foto_{i}"), max_side=1800)
            except ValueError as e:
                errors.append(f"Banner {i + 1}: {e}")
                new = None
            foto_final = new or ("" if f.get(f"hapus_{i}") == "on" else foto_lama)
            if foto_lama and foto_final != foto_lama:
                olds.append(foto_lama)
            if atas or judul or foto_final:
                banners.append({"atas": atas, "judul": judul, "foto": foto_final})
        if not banners:
            errors.append("Minimal harus ada 1 banner.")
        if not errors:
            with _lock:
                data = load()
                data["wa"], data["banner"] = wa, banners
                save(data)
                for o in olds:
                    remove_photo(o, data)
            flash("Pengaturan disimpan.", "ok")
            return redirect(url_for("settings"))
        for e in errors:
            flash(e, "err")
    slots = data["banner"] + [{"atas": "", "judul": "", "foto": ""}] * (MAX_BANNER - len(data["banner"]))
    return render_template("settings.html", d=data, slots=slots)


# ------------------------------------------------------------------ API publik: catat pesanan dari toko
@app.route("/api/pesanan", methods=["POST"])
def api_pesanan():
    ip, now = request.remote_addr, time.time()
    hits = [t for t in _order_hits.get(ip, []) if now - t < 600]
    if len(hits) >= 8:
        return jsonify(ok=False, error="terlalu banyak permintaan"), 429
    j = request.get_json(silent=True) or {}
    oid = str(j.get("id", ""))
    items = build_items(j.get("items"))
    if not re.fullmatch(r"BTK-\d{4}-\d{3,4}", oid) or not items:
        return jsonify(ok=False), 400
    nama, alamat = str(j.get("nama", "")).strip()[:80], str(j.get("alamat", "")).strip()[:400]
    metode = str(j.get("metode", "")).strip()[:40]
    total = sum(i["harga"] * i["qty"] for i in items)
    dup = db("SELECT 1 FROM orders WHERE (id=? OR (nama=? AND alamat=? AND total=? AND created>=?))",
             (oid, nama, alamat, total, f"{datetime.fromtimestamp(now - 900):%Y-%m-%d %H:%M}"), one=True)
    if not dup:
        insert_order(oid, nama, alamat, metode, items)
    _order_hits[ip] = hits + [now]
    return jsonify(ok=True)


# ------------------------------------------------------------------ admin: pesanan
@app.route("/admin/pesanan")
@login_required
def pesanan():
    st, q = request.args.get("status", ""), request.args.get("q", "").strip()
    sql, args = "SELECT * FROM orders WHERE 1=1", []
    if st in STATUS:
        sql += " AND status=?"
        args.append(st)
    if q:
        sql += " AND (id LIKE ? OR nama LIKE ?)"
        args += [f"%{q}%"] * 2
    rows = db(sql + " ORDER BY created DESC, id DESC LIMIT 300", args)
    orders = [dict(r, items=json.loads(r["items"])) for r in rows]
    counts = {r["status"]: r["c"] for r in db("SELECT status, COUNT(*) c FROM orders GROUP BY status")}
    omzet = db("SELECT COALESCE(SUM(total+ongkir),0) s FROM orders WHERE status='selesai'", one=True)["s"]
    return render_template("orders.html", orders=orders, counts=counts, st=st, q=q, omzet=omzet)


@app.route("/admin/pesanan/baru", methods=["GET", "POST"])
@login_required
def pesanan_baru():
    prods = [p for p in load()["produk"] if p.get("aktif", True)]
    if request.method == "POST":
        f = request.form
        raw = [{"id": f.get(f"p_{i}"), "motif": f.get(f"m_{i}", ""), "qty": f.get(f"q_{i}") or 1}
               for i in range(6) if f.get(f"p_{i}")]
        items = build_items(raw)
        if not items:
            flash("Pilih minimal satu produk.", "err")
        else:
            insert_order(new_order_id(), f.get("nama", "").strip()[:80], f.get("alamat", "").strip()[:400],
                         f.get("metode", "").strip()[:40], items)
            flash("Pesanan manual dicatat.", "ok")
            return redirect(url_for("pesanan"))
    return render_template("order_new.html", prods=prods)


@app.route("/admin/pesanan/<oid>/update", methods=["POST"])
@login_required
def pesanan_update(oid):
    st = request.form.get("status")
    if st not in STATUS:
        abort(400)
    n = db("UPDATE orders SET status=?, resi=?, ongkir=?, catatan=? WHERE id=?",
           (st, request.form.get("resi", "").strip()[:40], to_int(request.form.get("ongkir")),
            request.form.get("catatan", "").strip()[:300], oid), write=True)
    if not n:
        abort(404)
    flash(f"Pesanan {oid} diperbarui.", "ok")
    return redirect(url_for("pesanan", status=request.form.get("back", "")))


@app.route("/admin/pesanan/<oid>/hapus", methods=["POST"])
@login_required
def pesanan_hapus(oid):
    db("DELETE FROM orders WHERE id=?", (oid,), write=True)
    flash("Pesanan dihapus.", "ok")
    return redirect(url_for("pesanan", status=request.form.get("back", "")))


@app.route("/admin/pesanan/export.csv")
@login_required
def pesanan_csv():
    safe = lambda v: ("'" + str(v)) if str(v)[:1] in "=+-@" else v   # cegah CSV injection
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(["ID", "Waktu", "Nama", "Alamat", "Pembayaran", "Item", "Subtotal", "Ongkir", "Total", "Status", "Resi", "Catatan"])
    for r in db("SELECT * FROM orders ORDER BY created DESC"):
        it = "; ".join(f"{i['nama']} ({i['motif']}) x{i['qty']}" for i in json.loads(r["items"]))
        w.writerow([safe(x) for x in [r["id"], r["created"], r["nama"], r["alamat"], r["metode"], it, r["total"],
                                      r["ongkir"], r["total"] + r["ongkir"], STATUS.get(r["status"], r["status"]), r["resi"], r["catatan"]]])
    return Response("\ufeff" + out.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=pesanan-batikku.csv"})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("DEBUG") == "1")
