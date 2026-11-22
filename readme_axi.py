#!/usr/bin/env python3
"""readme-axi — kiểm tra README song ngữ Anh – Việt theo khung chung của ngoviet.

Lệnh:
  readme_axi.py [check] [dir] [--type T] [--repo name]      kiểm tra README.md + README.vi.md
  readme_axi.py drift [dir] [--strict]                      README.md đổi mà README.vi.md chưa theo
  readme_axi.py meta [dir] [--repo owner/name]              ô About trên GitHub (cần gh): mô tả, topic, giấy phép, ảnh preview
  readme_axi.py social [dir] [--repo owner/name] [--out f]  vẽ ảnh social preview 1280x640 (SVG, PNG khi có Edge/Chrome)
  readme_axi.py support [dir] [--repo name] [--write]       chèn/thay khối Ủng hộ chung (mặc định chỉ xem)
  readme_axi.py scaffold [dir] --type T --title "..." [--private] [--repo name] [--force]
  readme_axi.py names                                       tên mục chuẩn, mục bắt buộc theo loại
Loại T: ha, card, esp32, tool, app, ops, config, docs.
Repo private: dấu <!-- readme-axi type=T private --> (vẫn song ngữ, không bắt khối Ủng hộ và mục License).
Tên repo (cho khối Ủng hộ): --repo, rồi git remote origin, rồi tên thư mục.
Mã thoát: 0 = đạt, 1 = có lỗi, 2 = sai cách gọi. Output dạng TOON.
Chỉ dùng thư viện chuẩn để workflow tải về một tệp là chạy được.
"""
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
from bisect import bisect_right
from pathlib import Path
from urllib.parse import unquote

VERSION = "0.3.0"
EN, VI = "README.md", "README.vi.md"
SWITCH_EN = "**English** · [Tiếng Việt](README.vi.md)"
SWITCH_VI = "[English](README.md) · **Tiếng Việt**"
# <!-- readme-axi type=tool --> hoặc <!-- readme-axi type=tool private -->
TYPE_RE = re.compile(r"<!--\s*readme-axi\s+type=(\w+)((?:\s+[\w-]+)*)\s*-->")
FLAGS = {"private"}
START, END = "<!-- support:start -->", "<!-- support:end -->"
ASSET = "https://raw.githubusercontent.com/ngoviet/.github/main/assets/support"
BEP20 = "0xcbf0402b232cb24b4d998f09a4884f87b5f74750"

# tên mục chuẩn: EN -> VI
NAMES = {
    "Contents": "Mục lục", "Features": "Tính năng", "Supported devices": "Thiết bị hỗ trợ",
    "Requirements": "Yêu cầu", "Installation": "Cài đặt", "Configuration": "Cấu hình",
    "Entities": "Thực thể", "Services": "Dịch vụ", "Troubleshooting": "Xử lý sự cố",
    "How it works": "Cách hoạt động", "Development": "Phát triển", "Usage": "Cách dùng",
    "Options": "Tuỳ chọn", "Hardware": "Phần cứng", "Quick start": "Bắt đầu nhanh",
    "Home Assistant": "Home Assistant", "Project layout": "Cấu trúc dự án", "Commands": "Lệnh",
    "Deployment": "Triển khai",
    "Support the project": "Ủng hộ dự án", "License": "Giấy phép",
}
# mục bắt buộc theo loại repo, đúng thứ tự (mục khác được chen vào giữa)
REQUIRED = {
    "ha": ["Features", "Installation", "Configuration", "Entities", "Troubleshooting", "Development"],
    "card": ["Features", "Installation", "Usage"],
    "esp32": ["Features", "Hardware", "Quick start", "Home Assistant"],
    "tool": ["Installation", "Usage"],
    "app": ["Features", "Development", "Deployment"],     # web app, dịch vụ
    "ops": ["Usage", "Project layout"],                   # repo vận hành (script, máy chủ)
    "config": ["Project layout", "Deployment"],           # repo cấu hình (vd HA-Config)
    "docs": ["Project layout"],                           # kho tài liệu, ghi chép
}
TYPES = "|".join(REQUIRED)
# phần đuôi mà repo public bắt buộc, repo private thì không
TAIL = ["Support the project", "License"]
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿⌀-⏿️‍�]")


def toon(v):
    s = str(v)
    return '"' + s.replace('"', "'") + '"' if re.search(r'[,:"\n]|^\s|\s$', s) or s == "" else s


def table(name, fields, rows):
    out = [f"{name}[{len(rows)}]{{{','.join(fields)}}}:"]
    out += ["  " + ",".join(toon(r[f]) for f in fields) for r in rows]
    return out


def die(msg, code=2, hint=None):
    print(f"error: {msg}")
    print(f"code: {'USAGE' if code == 2 else 'FAILED'}")
    if hint:
        print(f"help[1]:\n  {hint}")
    sys.exit(code)


def read(p):
    return p.read_bytes().decode("utf-8-sig").replace("\r\n", "\n")


def label(name, vi):
    """Tên mục chuẩn theo ngôn ngữ của tệp."""
    return NAMES[name] if vi else name


def prose(text):
    """(số dòng, dòng) nằm ngoài code block.

    Như CommonMark: rào đóng phải cùng ký tự và dài ít nhất bằng rào mở, nên ```` bọc được ``` bên trong.
    """
    fence = None
    for i, ln in enumerate(text.split("\n"), 1):
        m = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", ln)
        if m:
            tok, rest = m.groups()
            if fence is None:
                fence = tok
            elif tok[0] == fence[0] and len(tok) >= len(fence) and not rest.strip():
                fence = None
            continue
        if fence is None:
            yield i, ln


def headings(text):
    """(cấp, chữ, số dòng) của các tiêu đề, bỏ qua dòng trong code block."""
    out = []
    for i, ln in prose(text):
        m = re.match(r"^(#{1,6})\s+(.*?)\s*#*\s*$", ln)
        if m:
            out.append((len(m.group(1)), m.group(2), i))
    return out


# ---------- link và ảnh ----------
# Đọc trên cả văn bản (không theo từng dòng) để bắt thẻ HTML xuống dòng, ảnh lồng trong link (badge) và link
# kiểu tham chiếu. Code và chú thích HTML được che bằng dấu cách, giữ nguyên vị trí nên số dòng vẫn đúng.

FENCE_ANY = re.compile(r"^(?:\s*>)*\s*(`{3,}|~{3,})(.*)$")   # rào thụt trong list hay nằm trong trích dẫn
HTML_TAG = re.compile(r"<(img|a|source)\b((?:[^>\"']|\"[^\"]*\"|'[^']*')*)>", re.I)
ATTR = re.compile(r"""(?<![\w:-])(src|href|srcset|alt)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'=<>`]+))""", re.I)
REF_DEF = re.compile(r"""^ {0,3}\[([^\]\n]+)\]:[ \t]*(<[^>\n]*>|\S+)"""
                     r"""[ \t]*(?:"[^"\n]*"|'[^'\n]*'|\([^)\n]*\))?[ \t]*$""", re.M)
REF_IMG = re.compile(r"!\[([^\]\n]*)\]\[([^\]\n]*)\]")
MAX_BYTES = 500 * 1024  # GitHub cắt README dài hơn 500 KiB


def blank(m):
    return re.sub(r"[^\n]", " ", m.group(0))


def mask_code(text):
    """Bản sao cùng độ dài của text, khối code, code trong dòng và <!-- --> thay bằng dấu cách."""
    out, fence = [], None
    for ln in text.split("\n"):
        m = FENCE_ANY.match(ln)
        # rào mở bằng ` không được có ` trong info string (```code``` là code trong dòng, không phải rào)
        opens = m and fence is None and not (m.group(1)[0] == "`" and "`" in m.group(2))
        closes = m and fence is not None and m.group(1)[0] == fence[0] and len(m.group(1)) >= len(fence) \
            and not m.group(2).strip()
        if opens or closes:
            fence = m.group(1) if opens else None
            out.append(" " * len(ln))
        else:
            out.append(" " * len(ln) if fence else ln)
    s = re.sub(r"<!--.*?-->", blank, "\n".join(out), flags=re.S)
    # code trong dòng: dãy ` mở và đóng dài bằng nhau, không vượt qua dòng trống
    return re.sub(r"(?<!`)(`+)(?!`)(?:(?!\n[ \t]*\n).)+?(?<!`)\1(?!`)", blank, s, flags=re.S)


def unescape(url):
    return re.sub(r"\\([!-/:-@\[-`{-~])", r"\1", url.strip())


def destination(s, j):
    """Đọc phần (đích "tiêu đề") của link inline bắt đầu ngay sau '(' ở vị trí j: (đích, vị trí sau ')') hoặc None."""
    n = len(s)
    while j < n and s[j] in " \t\n":
        j += 1
    if j < n and s[j] == "<":                      # <đích có dấu cách>
        k = s.find(">", j)
        if k < 0 or "\n" in s[j:k]:
            return None
        dest, j = s[j + 1:k], k + 1
    else:                                          # đích thường: ngoặc đơn bên trong phải cân
        k, depth = j, 0
        while k < n and s[k] not in " \t\n":
            if s[k] == "\\":
                k += 2
                continue
            if s[k] == "(":
                depth += 1
            elif s[k] == ")":
                if depth == 0:
                    break
                depth -= 1
            k += 1
        dest, j = s[j:k], k
    while j < n and s[j] in " \t\n":
        j += 1
    if j < n and s[j] in "\"'(":                   # tiêu đề "…", '…' hoặc (…)
        close = ")" if s[j] == "(" else s[j]
        k = s.find(close, j + 1)
        if k < 0:
            return None
        j = k + 1
        while j < n and s[j] in " \t\n":
            j += 1
    if j < n and s[j] == ")":
        return unescape(dest), j + 1
    return None


def md_targets(s):
    """(vị trí, đích, là ảnh, alt) của link và ảnh Markdown inline; ảnh lồng trong link được đọc cả hai."""
    stack, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 2
            continue
        if c == "[":
            stack.append((i, i > 0 and s[i - 1] == "!"))
        elif c == "]" and stack:
            start, img = stack.pop()
            if i + 1 < n and s[i + 1] == "(":
                got = destination(s, i + 2)
                if got:
                    yield (start - 1 if img else start), got[0], img, s[start + 1:i].strip() if img else None
                    i = got[1]
                    continue
        i += 1


def targets(text):
    """(số dòng, đích, là ảnh, alt hoặc None) của mọi link và ảnh ngoài code."""
    s = mask_code(text)
    found = list(md_targets(s))
    defs = {}
    for m in REF_DEF.finditer(s):
        url = m.group(2)[1:-1] if m.group(2).startswith("<") else m.group(2)
        defs[re.sub(r"\s+", " ", m.group(1).strip().lower())] = url
        found.append((m.start(2), unescape(url), False, None))
    for m in REF_IMG.finditer(s):
        key = re.sub(r"\s+", " ", (m.group(2) or m.group(1)).strip().lower())
        found.append((m.start(), "", True, m.group(1).strip()))  # đích đã kiểm ở dòng định nghĩa
        if key not in defs:
            found.append((m.start(), f"[{key}]", False, None))   # tham chiếu không có định nghĩa
    for m in HTML_TAG.finditer(s):
        tag = m.group(1).lower()
        attrs = {}
        for a in ATTR.finditer(m.group(2)):
            attrs.setdefault(a.group(1).lower(), next(v for v in a.groups()[1:] if v is not None))
        urls = [attrs.get("src") or attrs.get("href") or ""]
        urls += [c.split()[0] for c in (attrs.get("srcset") or "").split(",") if c.strip()]
        alt = (attrs.get("alt") or "").strip() if tag == "img" else None
        for k, url in enumerate(dict.fromkeys(u for u in urls if u) or [""]):
            found.append((m.start(), url, tag == "img" and k == 0, alt))
    lines = [0] + [k + 1 for k, ch in enumerate(s) if ch == "\n"]
    for pos, url, img, alt in sorted(found, key=lambda x: x[0]):
        yield bisect_right(lines, pos), url, img, alt


_listing = {}


def exists_exact(root, rel):
    """Có tệp hay thư mục rel (đường dẫn /) đúng từng chữ hoa thường, như trên CI Linux và trên GitHub."""
    cur = Path(root)
    for part in rel.split("/"):
        key = str(cur)
        if key not in _listing:
            try:
                _listing[key] = set(os.listdir(cur))
            except OSError:
                _listing[key] = set()
        if part not in _listing[key]:
            return False
        cur = cur / part
    return True


def broken(root, url):
    """True khi url là đường dẫn tương đối tới tệp không có trong repo.

    Không kiểm: link web, anchor (#…), và đường dẫn trèo ra khỏi gốc repo (../../issues là lối viết hợp lệ của
    GitHub, ../repo-khác trỏ tới thư mục anh em trên máy): cả hai không xác minh được từ trong repo.
    """
    if url.startswith("[") and url.endswith("]"):
        return True   # ảnh kiểu tham chiếu mà không có dòng định nghĩa
    if not url or url.startswith(("#", "//")) or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", url):
        return False
    path = unquote(re.split(r"[#?]", url, maxsplit=1)[0]).strip()
    if not path:
        return False
    rel = posixpath.normpath(path.lstrip("/"))
    if rel == ".":
        return False
    if rel == ".." or rel.startswith("../"):
        return False
    return not exists_exact(root, rel)


def marker(text):
    """(loại, tập cờ) từ dòng <!-- readme-axi type=... -->, hoặc (None, set())."""
    m = TYPE_RE.search(text)
    return (m.group(1), set(m.group(2).split())) if m else (None, set())


def is_private(root):
    """Repo private khi dấu trong README.md (hoặc README.vi.md nếu thiếu bản Anh) có cờ private."""
    for f in (EN, VI):
        p = root / f
        if p.exists():
            return "private" in marker(read(p))[1]
    return False


def origin_url(root):
    try:
        r = subprocess.run(["git", "-C", str(root), "remote", "get-url", "origin"],
                           capture_output=True, text=True, encoding="utf-8")
    except OSError:
        return ""
    return r.stdout.strip() if r.returncode == 0 else ""


def repo_slug(root):
    """owner/name từ origin trên github.com (https hoặc ssh), hoặc None."""
    m = re.search(r"github\.com[/:]([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", origin_url(root))
    return f"{m.group(1)}/{m.group(2)}" if m else None


def repo_name(root, given=None):
    """(tên, nguồn): --repo, rồi tên repo trong git remote origin, rồi tên thư mục.

    Tên thư mục sai khi chạy trong worktree hay bản clone tạm, nên origin đứng trước.
    """
    if given:
        return given, "flag"
    url = origin_url(root)
    name = re.split(r"[/:\\]", url.rstrip("/\\"))[-1] if url else ""
    if name.endswith(".git"):
        name = name[:-4]
    if name:
        return name, "origin"
    return root.resolve().name, "dir"


# ---------- check ----------

# chỉ cảnh báo, --strict mới làm đỏ: luật mới (link, alt, size) và khối Ủng hộ theo mẫu cũ
WARN_RULES = {"link", "alt", "size", "support-outdated"}


def check(root, forced_type=None, repo=None, strict=False):
    """(loại, private, mục ##, danh sách lỗi); mỗi lỗi có level "error" hoặc "warning"."""
    issues = []

    def add(f, rule, detail):
        level = "warning" if rule in WARN_RULES and not strict else "error"
        issues.append({"file": f, "rule": rule, "detail": detail, "level": level})

    files = {}
    for f in (EN, VI):
        p = root / f
        if p.exists():
            files[f] = read(p)
        else:
            add(f, "missing", "tệp không có")
    rtype = forced_type
    marks = {}
    for f, text in files.items():
        t, flags = marks[f] = marker(text)
        if not t:
            add(f, "type-marker", f"thiếu dòng <!-- readme-axi type={TYPES} [private] -->")
        elif t not in REQUIRED:
            add(f, "type-marker", f"loại lạ: {t}")
        for x in sorted(flags - FLAGS):
            add(f, "type-marker", f"cờ lạ trong dấu: {x} (chỉ có private)")
        rtype = rtype or t
    if EN in marks and VI in marks and marks[EN] != marks[VI]:
        add(VI, "type-marker", "dấu khác với README.md (loại hoặc cờ private)")
    private = "private" in next(iter(marks.values()), (None, set()))[1]
    repo = repo or repo_name(root)[0]

    heads = {}
    for f, text in files.items():
        vi = f == VI
        hs = headings(text)
        h1 = [h for h in hs if h[0] == 1]
        if len(h1) != 1 or not text.lstrip().startswith("# "):
            add(f, "h1", f"cần đúng 1 tiêu đề # ở dòng đầu (đang có {len(h1)})")
        top = "\n".join(text.split("\n")[:15])
        if (SWITCH_VI if vi else SWITCH_EN) not in top:
            add(f, "switcher", f"thiếu dòng chuyển ngôn ngữ trong 15 dòng đầu: {SWITCH_VI if vi else SWITCH_EN}")
        h2 = [h for h in hs if h[0] == 2]
        heads[f] = h2
        for _, t, ln in hs:
            if EMOJI.search(t):
                add(f, "emoji-heading", f"dòng {ln}: {t}")
        size = len(text.encode("utf-8"))
        if size > MAX_BYTES:
            add(f, "size", f"{size // 1024} KiB, GitHub chỉ hiện {MAX_BYTES // 1024} KiB đầu")
        for ln, url, img, alt in targets(text):
            if url.startswith("[") and url.endswith("]"):
                add(f, "link", f"dòng {ln}: tham chiếu {url} chưa có dòng định nghĩa")
            elif broken(root, url):
                add(f, "link", f"dòng {ln}: {url} không có trong repo")
            if img and not alt:
                add(f, "alt", f"dòng {ln}: ảnh {url or '?'} thiếu chữ thay thế")
        names = [t for _, t, _ in h2]
        want = [label(n, vi) for n in REQUIRED.get(rtype, [])]
        pos = -1
        for w in want:
            if w not in names:
                add(f, "section", f"thiếu mục ## {w}")
            elif names.index(w) < pos:
                add(f, "order", f"## {w} sai thứ tự")
            else:
                pos = names.index(w)
        if private:
            continue  # repo private: không ai ngoài chủ đọc, mã không cấp phép MIT
        lic, sup = label("License", vi), label("Support the project", vi)
        if lic not in names:
            add(f, "section", f"thiếu mục ## {lic}")
        elif names[-1] != lic:
            add(f, "order", f"## {lic} phải là mục cuối")
        if text.count(START) != 1 or text.count(END) != 1:
            add(f, "support", f"cần đúng một khối {START} … {END}")
        else:
            blk = text[text.index(START):text.index(END) + len(END)]
            if blk != support_block(repo, vi):
                if any(blk == support_block(repo, vi, era) for era in LEGACY_ERAS):
                    add(f, "support-outdated", f"khối ## {sup} theo mẫu cũ, vẫn được chấp nhận")
                else:
                    add(f, "support", f"khối ## {sup} khác mẫu chung (repo {repo})")
            # so với dòng của tiêu đề thật, không phải chuỗi "## License" đầu tiên (có thể nằm trong code block)
            start_ln = text[:text.index(START)].count("\n") + 1
            lic_ln = next((ln for _, t, ln in h2 if t == lic), None)
            if lic_ln is not None and start_ln > lic_ln:
                add(f, "order", f"khối Ủng hộ phải đứng trước ## {lic}")
    if EN in heads and VI in heads and len(heads[EN]) != len(heads[VI]):
        add(VI, "parity", f"số mục ## khác nhau: EN {len(heads[EN])}, VI {len(heads[VI])}")
    return rtype, private, heads, issues


def cmd_check(root, forced_type, repo_opt=None, strict=False):
    if forced_type and forced_type not in REQUIRED:
        die(f"--type phải là một trong {TYPES.replace('|', ', ')}")
    repo, source = repo_name(root, repo_opt)
    rtype, private, heads, found = check(root, forced_type, repo, strict)
    issues = [i for i in found if i["level"] == "error"]
    warnings = [i for i in found if i["level"] == "warning"]
    print(f"repo: {toon(repo)}")
    print(f"repo_from: {source}")
    print(f"type: {rtype or 'unknown'}")
    print(f"profile: {'private' if private else 'public'}")
    en, vi = heads.get(EN, []), heads.get(VI, [])
    rows = [{"n": i + 1, "en": en[i][1] if i < len(en) else "-", "vi": vi[i][1] if i < len(vi) else "-"}
            for i in range(max(len(en), len(vi)))]
    print("\n".join(table("sections", ["n", "en", "vi"], rows)) if rows else "sections: 0 results")
    print(f"result: {'pass' if not issues else 'fail'}, {len(issues)} issues, {len(warnings)} warnings")
    if issues:
        print("\n".join(table("issues", ["file", "rule", "detail"], issues)))
    if warnings:
        print("\n".join(table("warnings", ["file", "rule", "detail"], warnings)))
    hints = []
    if any(i["rule"] == "support" for i in issues):
        hints.append("Run `readme_axi.py support --write` to insert the shared support block "
                     "(private repo: add `private` to the marker instead)")
    if any(i["rule"] == "support-outdated" for i in found):
        hints.append("Run `readme_axi.py support --write` to move the support block to the current template")
    if any(i["rule"] == "type-marker" for i in issues):
        hints.append(f"Marker line: <!-- readme-axi type=<{TYPES}> --> (append ` private` for a private repo)")
    if any(i["rule"] == "link" for i in found):
        hints.append("Relative links resolve from the repo root: add the missing file or fix the path")
    if any(i["rule"] == "missing" for i in issues):
        hints.append(f"Run `readme_axi.py scaffold --type <{TYPES}> --title \"<name>\" [--private]` for a skeleton")
    if issues:
        hints.append("Section names (EN -> VI) are listed by `readme_axi.py names`")
    if warnings:
        hints.append("Warnings do not fail the check; `check --strict` fails on them too")
    if not found:
        hints.append("Run `readme_axi.py drift` to see whether README.vi.md lags behind README.md")
    print(f"help[{len(hints)}]:")
    for h in hints:
        print(f"  {h}")
    return 1 if issues else 0


# ---------- drift ----------

def git(root, *a):
    r = subprocess.run(["git", "-C", str(root), *a], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        die(f"git {' '.join(a[:2])}: {r.stderr.strip()[:200]}", 1)
    return r.stdout.strip()


def cmd_drift(root, strict):
    last_vi = git(root, "log", "-1", "--format=%H", "--", VI)
    if not last_vi:
        die("README.vi.md chưa có trong lịch sử git", 1, "Commit README.vi.md first")
    behind = git(root, "log", "--format=%h %s", f"{last_vi}..HEAD", "--", EN).splitlines()
    print(f"repo: {toon(repo_name(root)[0])}")
    print(f"last_vi_commit: {last_vi[:8]}")
    if behind:
        rows = [{"commit": b.split(" ", 1)[0], "subject": (b.split(" ", 1) + [""])[1][:80]} for b in behind]
        print("\n".join(table("en_commits_since", ["commit", "subject"], rows)))
        print(f"result: drift, README.md changed in {len(behind)} commits after README.vi.md")
        print("help[1]:\n  Port these README.md changes into README.vi.md, then commit both")
        return 1 if strict else 0
    print("en_commits_since: 0 results")
    print("result: in sync")
    return 0


# ---------- meta ----------
# Ô tìm của GitHub mặc định chỉ đọc tên repo, mô tả và topics (không đọc README), Google lấy mô tả làm
# tiêu đề và tóm tắt trang repo: nên kiểm cả ô About, không chỉ tệp README.

DESC_MAX = 120          # standard-readme: mô tả ngắn dưới 120 ký tự
TOPICS_MIN, TOPICS_MAX = 5, 20
TOPIC_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,49}$")
GH_FIELDS = "description,repositoryTopics,licenseInfo,usesCustomOpenGraphImage,visibility,isFork"


def intro(text):
    """Đoạn giới thiệu: đoạn chữ đầu tiên sau dòng chuyển ngôn ngữ.

    Bỏ qua code block, tiêu đề, badge, ảnh, trích dẫn, bảng và dòng chỉ có thẻ HTML; dòng có chữ thì giữ chữ,
    bỏ thẻ (đoạn mở đầu bằng <b>Tên</b> vẫn là đoạn giới thiệu).
    """
    sw = next((i for i, ln in enumerate(text.split("\n"), 1) if SWITCH_EN in ln or SWITCH_VI in ln), 0)
    para, prev = [], None
    for i, ln in prose(text):
        if i <= sw:
            continue
        if para and i != prev + 1:
            break  # giữa hai dòng có code block (prose() đã bỏ): hết đoạn
        prev = i
        s = ln.strip()
        visible = re.sub(r"<[^>]*>", "", s).strip()
        if not visible or s.startswith(("#", "![", "[![", ">", "|", "<!--")):
            if para:
                break
            continue
        para.append(visible)
    s = " ".join(para)
    s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", s)
    return re.sub(r"[`*_]", "", s)


def words(s):
    return set(re.findall(r"[^\W_]{4,}", s.lower()))


def gh_meta(slug):
    """(ô About, lỗi): (dict, None) khi đọc được, (None, None) khi máy không có gh, (None, "lỗi") khi gh lỗi.

    READMEAXI_GH_JSON thay gh trong test; tệp đó có khoá "__gh_error__" thì giả lập gh lỗi.
    """
    fake = os.environ.get("READMEAXI_GH_JSON")
    if fake:
        data = json.loads(Path(fake).read_text(encoding="utf-8"))
        return (None, data["__gh_error__"]) if "__gh_error__" in data else (data, None)
    try:
        r = subprocess.run(["gh", "repo", "view", slug, "--json", GH_FIELDS],
                           capture_output=True, text=True, encoding="utf-8")
    except OSError:
        return None, None
    if r.returncode:
        return None, r.stderr.strip()[:200] or f"gh exited {r.returncode}"
    return json.loads(r.stdout), None


def cmd_meta(root, slug):
    meta, err = gh_meta(slug)
    if err:
        die(f"gh repo view {slug}: {err}", 1, "Run `gh auth status`, or check --repo owner/name")
    print(f"repo: {toon(slug)}")
    if meta is None:
        print("result: skipped, gh is not installed")
        print("help[1]:\n  Install GitHub CLI (https://cli.github.com) and run `gh auth login`, then rerun")
        return 0
    issues = []

    def add(rule, detail):
        issues.append({"field": rule, "detail": detail})

    private = meta.get("visibility", "").upper() == "PRIVATE"
    desc = (meta.get("description") or "").strip()
    topics = [t["name"] if isinstance(t, dict) else t for t in meta.get("repositoryTopics") or []]
    print(f"visibility: {'private' if private else 'public'}")
    print(f"fork: {'yes' if meta.get('isFork') else 'no'}")
    print(f"description: {toon(desc) if desc else '(none)'}")
    print(f"description_chars: {len(desc)}")
    print(f"topics[{len(topics)}]: {','.join(topics)}" if topics else "topics: 0 results")

    marked = is_private(root)
    if (root / EN).exists() and marked != private:
        add("visibility", f"dấu README ghi {'private' if marked else 'public'} nhưng GitHub là "
                          f"{'private' if private else 'public'}")
    if not desc:
        add("description", "trống: ô tìm GitHub và Google đều đọc trường này")
    elif len(desc) > DESC_MAX:
        add("description", f"{len(desc)} ký tự, nên dưới {DESC_MAX}")
    dw = words(desc)
    intros = [words(intro(read(root / f))) for f in (EN, VI) if (root / f).exists()]
    if dw and intros:
        # mô tả có thể viết tiếng Anh hay tiếng Việt: so với bản nào khớp hơn
        hit = max(len(dw & iw) for iw in intros) / len(dw)
        if hit < 0.5:
            add("intro", f"đoạn giới thiệu README chỉ chứa {hit:.0%} từ của mô tả: hai nơi nên nói cùng một ý")
    owner, name = slug.split("/", 1)
    # fork: topic và giấy phép thuộc repo gốc; repo hồ sơ (owner/owner): GitHub không hiện topic hay preview
    if not private and not meta.get("isFork") and owner.lower() != name.lower():
        if len(topics) < TOPICS_MIN:
            add("topics", f"{len(topics)} topic, cần ít nhất {TOPICS_MIN} (tối đa {TOPICS_MAX})")
        elif len(topics) > TOPICS_MAX:
            add("topics", f"{len(topics)} topic, GitHub chỉ cho {TOPICS_MAX}")
        for t in topics:
            if not TOPIC_RE.match(t):
                add("topics", f"{t}: chỉ chữ thường, số, gạch nối, tối đa 50 ký tự")
        if not meta.get("licenseInfo"):
            add("license", "GitHub không nhận ra giấy phép: thêm tệp LICENSE đúng văn bản chuẩn")
        if not meta.get("usesCustomOpenGraphImage"):
            add("social-preview", "chưa có ảnh social preview: link chia sẻ lên chat, mạng xã hội chỉ hiện thẻ chung")
    print(f"result: {'pass' if not issues else 'fail'}, {len(issues)} issues")
    if issues:
        print("\n".join(table("issues", ["field", "detail"], issues)))
        hints = []
        if any(i["field"] in ("description", "topics") for i in issues):
            hints.append(f"Edit them with `gh repo edit {slug} --description \"...\" --add-topic <topic>`")
        if any(i["field"] == "social-preview" for i in issues):
            hints.append("Run `readme_axi.py social` to render a 1280x640 image, then upload it in "
                         "Settings > General > Social preview")
        if any(i["field"] == "intro" for i in issues):
            hints.append("Make the first paragraph of README.md and the GitHub description tell the same story")
        print(f"help[{len(hints)}]:")
        for h in hints:
            print(f"  {h}")
    return 1 if issues else 0


# ---------- social ----------
# GitHub không có API tải ảnh social preview: lệnh này chỉ vẽ ảnh, chủ tải lên trong Settings.

SOCIAL_W, MARGIN = 1280, 96
TEXT_W = SOCIAL_W - 2 * MARGIN


def text_px(s, size):
    """Ước độ rộng (px) của chữ không chân ở cỡ size; hơi rộng hơn thật để chữ không tràn khung."""
    w = 0.0
    for ch in s:
        if ch in " il.,:;'!|":
            w += 0.30
        elif ch in "fjrtI()[]{}-/\\\"":
            w += 0.38
        elif ch in "mwMW@%":
            w += 0.90
        elif ch.isupper() or ch.isdigit():
            w += 0.66
        else:
            w += 0.56
    return w * size


def ellipsize(s, size, width):
    """s kết thúc bằng … và vừa width."""
    s = s.rstrip("…").rstrip(" ,.;:")
    while s and text_px(s + "…", size) > width:
        s = s[:-1].rstrip(" ,.;:")
    return s + "…"


def fit(s, size, width):
    """Giữ nguyên s nếu vừa width, không thì cắt và thêm …"""
    return s if text_px(s, size) <= width else ellipsize(s, size, width)


def greedy_lines(s, size, width):
    """Ngắt tham lam: mỗi dòng nhận thêm từ cho tới khi vượt width."""
    out, cur = [], ""
    for w in s.split():
        if cur and text_px(f"{cur} {w}", size) > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


def wrap(s, size, width, lines):
    """Ngắt s theo độ rộng ước tính thành tối đa `lines` dòng; dòng cuối thêm … nếu còn chữ.

    Chữ vừa đủ số dòng thì cân lại như text-wrap: balance của CSS: thu hẹp bề rộng tới mức nhỏ nhất
    mà số dòng không tăng, để dòng cuối không trơ một từ.
    """
    out = greedy_lines(s, size, width)
    if 1 < len(out) <= lines:
        lo, hi = 0.0, float(width)          # ở bề rộng hi, ngắt tham lam luôn ra len(out) dòng
        while hi - lo > 1:
            mid = (lo + hi) / 2
            if len(greedy_lines(s, size, mid)) <= len(out):
                hi = mid
            else:
                lo = mid
        out = greedy_lines(s, size, hi)
    out = [fit(x, size, width) for x in out]   # một từ dài hơn cả dòng
    if len(out) > lines:
        out = out[:lines]
        out[-1] = ellipsize(out[-1], size, width)
    return out


def chip_topics(name, desc, topics, limit=5):
    """Chọn tối đa `limit` topic cho hàng chip của ảnh, theo thứ tự hiện trên ảnh.

    topics đến theo thứ tự GitHub trả về: gần như a-b-c, không cho biết topic nào quan trọng hơn. Xếp lại:
    topic có trong mô tả theo thứ tự đọc, rồi topic chỉ có trong tên repo, rồi phần còn lại theo GitHub;
    topic mà số là chính (40a, 60a) xuống cuối. Bỏ topic cùng họ với topic đã chọn (homeassistant,
    esp32-c6, jk-bms). Hàm thuần: cùng đầu vào ra cùng ảnh.
    """
    def norm(s):                                    # " home assistant ": so trọn cụm từ, không khớp nửa từ
        return " " + " ".join(re.findall(r"[^\W_]+", s.lower())) + " "

    text, title = norm(desc), norm(name)

    def rank(item):
        i, t = item
        p = norm(t)
        weak = 3 if sum(c.isdigit() for c in t) * 2 > len(t.replace("-", "")) else 0
        if p in text:
            return (weak, text.index(p), i)
        if p in title:
            return (weak + 1, title.index(p), i)
        return (weak + 2, 0, i)

    def kin(a, b):                                  # b ghép từ đầu hay cuối ra a: home-assistant ~ homeassistant
        a, b = sorted((a.lower(), b.lower()), key=len)
        la, parts = "".join(re.findall(r"[^\W_]+", a)), re.findall(r"[^\W_]+", b)
        return any("".join(parts[:k]) == la or "".join(parts[-k:]) == la for k in range(1, len(parts) + 1))

    out = []
    for _, t in sorted(enumerate(topics), key=rank):
        if len(out) < limit and not any(kin(t, k) for k in out):
            out.append(t)
    return out


def social_svg(slug, desc, topics):
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    owner, name = slug.split("/", 1)
    size = next((z for z in (88, 68, 52) if text_px(name, z) <= TEXT_W), 52)
    name = fit(name, size, TEXT_W)
    font = "'Be Vietnam Pro','Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
    desc_lines = wrap(desc, 40, TEXT_W, 3)
    y0 = 330 if desc_lines else 300
    body = "".join(f'<text x="{MARGIN}" y="{y0 + i * 54}" font-size="40" fill="#c9d4e5">{esc(t)}</text>'
                   for i, t in enumerate(desc_lines))
    chips, x = [], MARGIN
    for t in chip_topics(slug.split("/", 1)[1], desc, topics):
        label_ = fit(t, 24, TEXT_W - 32)
        w = round(32 + text_px(label_, 24))
        if x + w > SOCIAL_W - MARGIN:
            continue                        # chip không vừa: thử chip sau, có thể ngắn hơn
        chips.append(f'<rect x="{x}" y="520" width="{w}" height="44" rx="22" fill="#12324a"/>'
                     f'<text x="{x + w / 2}" y="550" font-size="24" fill="#7fd8f5" text-anchor="middle">{esc(label_)}</text>')
        x += w + 12
    foot = fit(f"Built in Việt Nam · github.com/{slug}", 24, TEXT_W)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="640" viewBox="0 0 1280 640" font-family="{font}">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0d1b2e"/><stop offset="1" stop-color="#081018"/></linearGradient></defs>
<rect width="1280" height="640" fill="url(#g)"/>
<rect x="0" y="0" width="1280" height="10" fill="#2bb5d8"/>
<text x="96" y="150" font-size="34" fill="#8a9bb3">{esc(owner)} /</text>
<text x="96" y="{150 + size + 10}" font-size="{size}" font-weight="700" fill="#f2f6fb">{esc(name)}</text>
{body}
{''.join(chips)}
<text x="1184" y="604" font-size="24" fill="#8a9bb3" text-anchor="end">{esc(foot)}</text>
</svg>"""


def find_browser():
    if "READMEAXI_BROWSER" in os.environ:          # test: "" = không có trình duyệt
        return os.environ["READMEAXI_BROWSER"] or None
    for b in ("msedge", "chrome", "google-chrome", "chromium", "chromium-browser"):
        if shutil.which(b):
            return shutil.which(b)
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"):
        if Path(p).exists():
            return p
    return None


def cmd_social(root, slug, out):
    target = Path(out) if out else Path("social-preview.png")
    if target.suffix.lower() not in (".png", ".svg"):
        die(f"--out phải là tệp .png hoặc .svg: {target}", 2, "Pass --out social-preview.png")
    if not target.parent.is_dir():
        die(f"thư mục đích không có: {target.parent}", 2, "Create the folder first, or pick another --out")
    meta, err = gh_meta(slug)                       # gh thiếu hay lỗi: vẫn vẽ được từ README
    desc = ((meta or {}).get("description") or "").strip()
    source = "github" if desc else "readme intro" + (f" (gh failed: {err[:80]})" if err else "")
    if not desc and (root / EN).exists():
        desc = intro(read(root / EN))
    topics = [t["name"] if isinstance(t, dict) else t for t in (meta or {}).get("repositoryTopics") or []]
    svg = target.with_suffix(".svg")
    svg.write_bytes(social_svg(slug, desc, topics).encode("utf-8"))
    rows = [{"file": str(svg), "action": "written"}]
    if target.suffix.lower() == ".png":
        png = target
        png.unlink(missing_ok=True)                 # "written" chỉ khi trình duyệt vừa ghi tệp mới
        browser = find_browser()
        if not browser:
            rows.append({"file": str(png), "action": "skipped (no Edge/Chrome)"})
        else:
            try:
                r = subprocess.run([browser, "--headless", "--disable-gpu", "--hide-scrollbars",
                                    "--window-size=1280,640", f"--screenshot={png.resolve()}",
                                    svg.resolve().as_uri()], capture_output=True, text=True, timeout=60)
                ok = r.returncode == 0 and png.exists() and png.stat().st_size > 0
            except (OSError, subprocess.TimeoutExpired):
                ok = False
            rows.append({"file": str(png), "action": "written" if ok else "failed"})
    print(f"repo: {toon(slug)}")
    print(f"description_from: {toon(source)}")
    print("\n".join(table("social", ["file", "action"], rows)))
    done = rows[-1]["action"] == "written"
    if done:
        print("help[2]:\n  Upload the PNG in GitHub: Settings > General > Social preview > Edit (no API for this)"
              "\n  The image is 1280x640, the size GitHub recommends; keep the PNG under 1 MB")
    else:
        print("help[1]:\n  No PNG: open the SVG in a browser and save a 1280x640 PNG, or install Edge/Chrome and rerun")
    return 0 if done else 1


# ---------- support ----------

CURRENT_ERA = "0.3"
# mẫu khối Ủng hộ cũ vẫn được chấp nhận (cảnh báo support-outdated): main là bản phát hành cho mọi repo,
# đổi mẫu mà không nhận mẫu cũ thì README của mọi repo public đỏ cùng lúc (gặp 16/11/2026 ở bản 0.2.1)
LEGACY_ERAS = ("0.2.0", "0.2.1")


def support_block(repo, vi, era=CURRENT_ERA):
    """Khối Ủng hộ theo mẫu hiện hành, hoặc theo mẫu cũ era (để check còn nhận README chưa làm mới)."""
    if vi:
        title, note = "## Ủng hộ dự án", (f"🇻🇳 VietQR: quét bằng app ngân hàng bất kỳ, nội dung <code>Ung ho {repo}</code>. "
                                          "Cảm ơn bạn đã giúp dự án tiếp tục phát triển!")
        crypto = "Ví tiền mã hoá, chỉ gửi qua mạng BNB Smart Chain (BEP20)"
        pays = "Một người Việt tự xây dựng và duy trì, miễn phí và mã nguồn mở. Sự ủng hộ của bạn giúp hỗ trợ thêm " \
               "thiết bị, sửa lỗi nhanh hơn và ra bản mới đều đặn."
    else:
        title, note = "## Support the project", (f"🇻🇳 VietQR: scan with any Vietnamese banking app, transfer note "
                                                 f"<code>Ung ho {repo}</code>. Thank you for keeping this project alive!")
        crypto = "Crypto wallet, BNB Smart Chain (BEP20) only"
        pays = "Free and open source. Your support pays for new device support, faster fixes and every release."
    if era == CURRENT_ERA:
        # banner-v2 chỉ còn tiêu đề chữ to (đọc được trên điện thoại); câu giải thích là chữ thật, theo ngôn ngữ tệp.
        # Tên tệp mới để README chưa làm mới vẫn hiện banner.svg cũ, đủ các dòng phụ vẽ trong ảnh.
        banner = f"""<p align="center">
  <img src="{ASSET}/banner-v2.svg" width="560" alt="Built and maintained by one person in Việt Nam">
</p>

<p align="center">{pays}</p>"""
    else:
        banner = f"""<p align="center">
  <img src="{ASSET}/banner.svg" width="720" alt="Built and maintained by one person in Việt Nam">
</p>"""
    if era == "0.2.0":      # 0.2.0 và 0.2.2: ghi chú trong <sub>
        note = f"<sub>{note}</sub>"
    return f"""{START}
{title}

{banner}

<p align="center">
  <a href="https://buymeacoffee.com/ngoviet"><img src="{ASSET}/btn-coffee.svg" height="56" alt="Buy me a coffee"></a>
  &nbsp;
  <a href="https://github.com/sponsors/ngoviet"><img src="{ASSET}/btn-sponsors.svg" height="56" alt="GitHub Sponsors"></a>
</p>

<p align="center">
  <img src="{ASSET}/vietqr-card.svg" width="300" alt="VietQR — MB Bank — NGO DUC VIET — 911051212">
  &nbsp;
  <img src="{ASSET}/crypto-card.svg" width="300" alt="Crypto — BNB Smart Chain (BEP20) — {BEP20}">
</p>

<p align="center"><b>{crypto}:</b><br><code>{BEP20}</code></p>

<p align="center">{note}</p>
{END}"""


def place_support(text, repo, vi):
    new = support_block(repo, vi)
    if START in text and END in text:
        return re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: new, text, flags=re.S), "replaced"
    lines = text.rstrip("\n").split("\n")
    lic = "## " + label("License", vi)
    for i, ln in enumerate(lines):
        if ln.strip() == lic:
            return "\n".join(lines[:i] + new.split("\n") + [""] + lines[i:]) + "\n", "inserted"
    return "\n".join(lines) + "\n\n" + new + "\n", "appended"


def cmd_support(root, repo, write):
    if is_private(root):
        print(f"repo: {toon(repo)}")
        print("profile: private")
        print("result: skipped, a private repo needs no support block")
        print("help[1]:\n  When the repo goes public, drop `private` from the marker, then rerun with --write")
        return 0
    rows = []
    for f, vi in ((EN, False), (VI, True)):
        p = root / f
        if not p.exists():
            rows.append({"file": f, "action": "skipped (missing)"})
            continue
        raw = p.read_bytes()
        text = read(p)
        out, how = place_support(text, repo, vi)
        changed = out != text
        if write and changed:
            p.write_bytes((out.replace("\n", "\r\n") if b"\r\n" in raw else out).encode("utf-8"))
        rows.append({"file": f, "action": how if changed else "unchanged"})
    print(f"repo: {toon(repo)}")
    print("\n".join(table("support", ["file", "action"], rows)))
    print(f"mode: {'written' if write else 'dry run'}")
    if not write:
        print("help[1]:\n  Add --write to apply")
    return 0


# ---------- scaffold ----------

SCAFFOLD_BODY = {
    "ha": ["Features", "Supported devices", "Requirements", "Installation", "Configuration", "Entities",
           "Troubleshooting", "Development"],
    "card": ["Features", "Installation", "Usage", "Options", "Development"],
    "esp32": ["Features", "Hardware", "Quick start", "Home Assistant", "Configuration", "Troubleshooting",
              "Project layout"],
    "tool": ["Installation", "Usage", "Commands", "Development"],
    "app": ["Features", "Requirements", "Configuration", "Development", "Deployment", "Troubleshooting"],
    "ops": ["Usage", "Commands", "Configuration", "Project layout", "Troubleshooting"],
    "config": ["Project layout", "Configuration", "Deployment", "Troubleshooting"],
    "docs": ["Contents", "Project layout"],
}


def cmd_scaffold(root, rtype, title, repo, force, private):
    if rtype not in SCAFFOLD_BODY:
        die(f"--type phải là một trong {TYPES.replace('|', ', ')}")
    if not title:
        die("thiếu --title")
    made = []
    for f, vi in ((EN, False), (VI, True)):
        p = root / f
        if p.exists() and not force:
            made.append({"file": f, "action": "exists (use --force)"})
            continue
        mark = f"<!-- readme-axi type={rtype}{' private' if private else ''} -->"
        body = [f"# {title}", "", mark, "", SWITCH_VI if vi else SWITCH_EN, "",
                "Một câu: làm gì, cho thiết bị nào." if vi else "One sentence: what it does, for which device.", ""]
        for n in SCAFFOLD_BODY[rtype]:
            body += [f"## {label(n, vi)}", "", "TODO", ""]
        if not private:
            body += [support_block(repo, vi), "", f"## {label('License', vi)}", "",
                     "[MIT](LICENSE) © Ngô Đức Việt", ""]
        # write_bytes: write_text trên Windows tự đổi \n thành \r\n
        p.write_bytes("\n".join(body).encode("utf-8"))
        made.append({"file": f, "action": "written"})
    print(f"profile: {'private' if private else 'public'}")
    print("\n".join(table("scaffold", ["file", "action"], made)))
    hints = ["Fill the TODO sections, then run `readme_axi.py check`"]
    if not private and not (root / "LICENSE").exists():
        hints.append("Add a LICENSE file: the License section links to it")
    print(f"help[{len(hints)}]:")
    for h in hints:
        print(f"  {h}")
    return 0


def cmd_names():
    rows = [{"en": k, "vi": v} for k, v in NAMES.items()]
    print("\n".join(table("names", ["en", "vi"], rows)))
    req = [{"type": t, "required": " > ".join(r)} for t, r in REQUIRED.items()]
    print("\n".join(table("required", ["type", "required"], req)))
    print(f"tail:\n  public: {' > '.join(TAIL)}\n  private: none")
    return 0


def main(argv):
    if "--version" in argv:
        print(f"readme-axi {VERSION}")
        return 0
    if "--help" in argv or "-h" in argv:
        print(__doc__.strip())
        return 0
    cmds = {"check", "drift", "meta", "social", "support", "scaffold", "names"}
    cmd = argv[0] if argv and argv[0] in cmds else "check"
    rest = argv[1:] if argv and argv[0] in cmds else argv
    opts, pos, i = {}, [], 0
    flags = {"--type", "--title", "--repo", "--out"}
    bools = {"--write", "--force", "--strict", "--private"}
    while i < len(rest):
        a = rest[i]
        if a.split("=", 1)[0] in flags and "=" in a:  # --type=ha
            k, v = a.split("=", 1)
            opts[k] = v
            i += 1
        elif a in flags:
            if i + 1 >= len(rest):
                die(f"{a} cần giá trị")
            opts[a] = rest[i + 1]
            i += 2
        elif a in bools:
            opts[a] = True
            i += 1
        elif a.startswith("-"):
            die(f"cờ lạ: {a}", 2, "Run `readme_axi.py --help`")
        else:
            pos.append(a)
            i += 1
    root = Path(pos[0]) if pos else Path(".")
    if not root.is_dir():
        die(f"không phải thư mục: {root}")
    if cmd == "check":
        return cmd_check(root, opts.get("--type"), opts.get("--repo"), opts.get("--strict", False))
    if cmd == "drift":
        return cmd_drift(root, opts.get("--strict", False))
    if cmd == "names":
        return cmd_names()
    if cmd in ("meta", "social"):
        slug, own = opts.get("--repo"), repo_slug(root)
        if slug and "/" not in slug:  # chỉ tên: lấy chủ repo từ origin
            if not own:
                die(f"--repo {slug}: thiếu chủ repo, origin không trỏ tới github.com", 2, "Pass --repo owner/name")
            slug = f"{own.split('/')[0]}/{slug}"
        slug = slug or own
        if not slug:
            die("không biết repo GitHub nào: origin không trỏ tới github.com", 2, "Pass --repo owner/name")
        if cmd == "meta":
            return cmd_meta(root, slug)
        return cmd_social(root, slug, opts.get("--out"))
    repo = repo_name(root, opts.get("--repo"))[0]
    if cmd == "support":
        return cmd_support(root, repo, opts.get("--write", False))
    return cmd_scaffold(root, opts.get("--type"), opts.get("--title"), repo, opts.get("--force", False),
                        opts.get("--private", False))


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    sys.exit(main(sys.argv[1:]))
