"""Test readme-axi bằng cách chạy CLI thật trên các thư mục mẫu tạm.

Chạy: python -m unittest discover -s . -v
Chỉ dùng thư viện chuẩn (và git cho drift / tên repo từ origin).
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CLI = Path(__file__).with_name("readme_axi.py")
TYPES = ["ha", "card", "esp32", "tool", "app", "ops", "config", "docs"]


def run(*args, cwd=None, **extra_env):
    env = dict(os.environ, PYTHONIOENCODING="utf-8", **extra_env)
    r = subprocess.run([sys.executable, str(CLI), *map(str, args)], cwd=cwd, env=env,
                       capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout


def git(root, *args):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@t")
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, env=env)


# Khối Ủng hộ đúng nguyên văn bản 0.2.0 (cũng là 0.2.2) cho repo demo-repo, sinh từ mã thật của bản đó.
# README của các repo public đang mang khối này: check phải tiếp tục nhận nó.
LEGACY_020_EN = '<!-- support:start -->\n## Support the project\n\n<p align="center">\n  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/banner.svg" width="720" alt="Built and maintained by one person in Việt Nam">\n</p>\n\n<p align="center">\n  <a href="https://buymeacoffee.com/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-coffee.svg" height="56" alt="Buy me a coffee"></a>\n  &nbsp;\n  <a href="https://github.com/sponsors/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-sponsors.svg" height="56" alt="GitHub Sponsors"></a>\n</p>\n\n<p align="center">\n  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/vietqr-card.svg" width="300" alt="VietQR — MB Bank — NGO DUC VIET — 911051212">\n  &nbsp;\n  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/crypto-card.svg" width="300" alt="Crypto — BNB Smart Chain (BEP20) — 0xcbf0402b232cb24b4d998f09a4884f87b5f74750">\n</p>\n\n<p align="center"><b>Crypto wallet, BNB Smart Chain (BEP20) only:</b><br><code>0xcbf0402b232cb24b4d998f09a4884f87b5f74750</code></p>\n\n<p align="center"><sub>🇻🇳 VietQR: scan with any Vietnamese banking app, transfer note <code>Ung ho demo-repo</code>. Thank you for keeping this project alive!</sub></p>\n<!-- support:end -->'
LEGACY_020_VI = '<!-- support:start -->\n## Ủng hộ dự án\n\n<p align="center">\n  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/banner.svg" width="720" alt="Built and maintained by one person in Việt Nam">\n</p>\n\n<p align="center">\n  <a href="https://buymeacoffee.com/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-coffee.svg" height="56" alt="Buy me a coffee"></a>\n  &nbsp;\n  <a href="https://github.com/sponsors/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-sponsors.svg" height="56" alt="GitHub Sponsors"></a>\n</p>\n\n<p align="center">\n  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/vietqr-card.svg" width="300" alt="VietQR — MB Bank — NGO DUC VIET — 911051212">\n  &nbsp;\n  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/crypto-card.svg" width="300" alt="Crypto — BNB Smart Chain (BEP20) — 0xcbf0402b232cb24b4d998f09a4884f87b5f74750">\n</p>\n\n<p align="center"><b>Ví tiền mã hoá, chỉ gửi qua mạng BNB Smart Chain (BEP20):</b><br><code>0xcbf0402b232cb24b4d998f09a4884f87b5f74750</code></p>\n\n<p align="center"><sub>🇻🇳 VietQR: quét bằng app ngân hàng bất kỳ, nội dung <code>Ung ho demo-repo</code>. Cảm ơn bạn đã giúp dự án tiếp tục phát triển!</sub></p>\n<!-- support:end -->'


def private_pair(rtype="ops", en_extra="", vi_extra=""):
    """README song ngữ hợp lệ cho repo private loại ops (không khối Ủng hộ, không License)."""
    en = ("# Demo\n\n<!-- readme-axi type=%s private -->\n\n**English** · [Tiếng Việt](README.vi.md)\n\n"
          "Runs the NAS scripts.\n\n## Usage\n\nRun it.\n\n## Project layout\n\nFiles.\n%s") % (rtype, en_extra)
    vi = ("# Demo\n\n<!-- readme-axi type=%s private -->\n\n[English](README.md) · **Tiếng Việt**\n\n"
          "Chạy script NAS.\n\n## Cách dùng\n\nChạy.\n\n## Cấu trúc dự án\n\nTệp.\n%s") % (rtype, vi_extra)
    return en, vi


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        # git không được leo lên repo cha của thư mục tạm (nếu có) để đọc origin của nó
        os.environ["GIT_CEILING_DIRECTORIES"] = str(self.tmp.parent)
        self.root = self.tmp / "demo-repo"
        self.root.mkdir()
        (self.root / "LICENSE").write_text("MIT", encoding="utf-8")  # mục License của repo public trỏ tới đây

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, en=None, vi=None):
        if en is not None:
            (self.root / "README.md").write_bytes(en.encode("utf-8"))
        if vi is not None:
            (self.root / "README.vi.md").write_bytes(vi.encode("utf-8"))

    def rules(self, out, table="issues"):
        """Tập (tệp, luật) trong bảng issues (hoặc warnings) của output check."""
        rows, on = set(), False
        for ln in out.splitlines():
            if ln.startswith(f"{table}["):
                on = True
            elif on and ln.startswith("  "):
                f, rule = ln.strip().split(",")[:2]
                rows.add((f, rule))
            else:
                on = False
        return rows

    def warned(self, out):
        return self.rules(out, "warnings")


class PrivateProfile(Base):
    def test_private_pair_passes_without_support_and_license(self):
        self.write(*private_pair())
        code, out = run("check", self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("profile: private", out)
        self.assertIn("result: pass, 0 issues", out)

    def test_same_readme_without_private_flag_needs_support_and_license(self):
        en, vi = private_pair()
        self.write(en.replace(" private -->", " -->"), vi.replace(" private -->", " -->"))
        code, out = run("check", self.root)
        self.assertEqual(code, 1)
        self.assertIn("profile: public", out)
        got = self.rules(out)
        for f in ("README.md", "README.vi.md"):
            self.assertIn((f, "support"), got)
            self.assertIn((f, "section"), got)  # thiếu ## License / ## Giấy phép

    def test_private_still_requires_vietnamese_file(self):
        self.write(private_pair()[0])
        code, out = run("check", self.root)
        self.assertEqual(code, 1)
        self.assertIn(("README.vi.md", "missing"), self.rules(out))

    def test_private_still_requires_type_sections_switcher_and_plain_headings(self):
        en, vi = private_pair()
        en = en.replace("## Project layout", "## Layout 🚀").replace("**English** · [Tiếng Việt](README.vi.md)", "")
        self.write(en, vi)
        code, out = run("check", self.root)
        self.assertEqual(code, 1)
        got = self.rules(out)
        self.assertIn(("README.md", "section"), got)        # thiếu ## Project layout
        self.assertIn(("README.md", "switcher"), got)
        self.assertIn(("README.md", "emoji-heading"), got)

    def test_private_flag_must_match_in_both_files(self):
        en, vi = private_pair()
        self.write(en, vi.replace(" private -->", " -->"))
        code, out = run("check", self.root)
        self.assertEqual(code, 1)
        self.assertIn(("README.vi.md", "type-marker"), self.rules(out))

    def test_unknown_marker_flag_is_reported(self):
        en, vi = private_pair()
        self.write(en.replace(" private -->", " private secret -->"), vi)
        code, out = run("check", self.root)
        self.assertEqual(code, 1)
        self.assertIn("cờ lạ trong dấu: secret", out)

    def test_support_skips_private_repo_and_leaves_files(self):
        en, vi = private_pair()
        self.write(en, vi)
        code, out = run("support", self.root, "--write")
        self.assertEqual(code, 0)
        self.assertIn("result: skipped", out)
        self.assertEqual((self.root / "README.md").read_bytes().decode("utf-8"), en)

    def test_private_profile_tolerates_a_leftover_support_block(self):
        self.write(*private_pair(en_extra="\n<!-- support:start -->\nold\n<!-- support:end -->\n"))
        code, out = run("check", self.root)
        self.assertEqual(code, 0, out)


class Types(Base):
    def test_scaffold_then_check_passes_for_every_type_and_profile(self):
        for rtype in TYPES:
            for private in (False, True):
                with self.subTest(type=rtype, private=private):
                    for f in ("README.md", "README.vi.md"):
                        (self.root / f).unlink(missing_ok=True)
                    extra = ["--private"] if private else []
                    code, out = run("scaffold", self.root, "--type", rtype, "--title", "Demo", *extra)
                    self.assertEqual(code, 0, out)
                    code, out = run("check", self.root)
                    self.assertEqual(code, 0, out)
                    self.assertIn(f"type: {rtype}", out)
                    self.assertIn(f"profile: {'private' if private else 'public'}", out)
                    text = (self.root / "README.md").read_text(encoding="utf-8")
                    self.assertEqual("<!-- support:start -->" in text, not private)

    def test_new_types_enforce_their_sections(self):
        cases = {"app": ["Features", "Development", "Deployment"], "ops": ["Usage", "Project layout"],
                 "config": ["Project layout", "Deployment"], "docs": ["Project layout"]}
        for rtype, need in cases.items():
            with self.subTest(type=rtype):
                en = ("# Demo\n\n<!-- readme-axi type=%s private -->\n\n**English** · [Tiếng Việt](README.vi.md)\n\n"
                      "Intro.\n\n## Notes\n\nx\n") % rtype
                vi = ("# Demo\n\n<!-- readme-axi type=%s private -->\n\n[English](README.md) · **Tiếng Việt**\n\n"
                      "Giới thiệu.\n\n## Ghi chú\n\nx\n") % rtype
                self.write(en, vi)
                code, out = run("check", self.root)
                self.assertEqual(code, 1)
                for n in need:
                    self.assertIn(f"thiếu mục ## {n}", out)

    def test_deployment_has_vietnamese_name(self):
        code, out = run("names")
        self.assertEqual(code, 0)
        self.assertIn("Deployment,Triển khai", out)
        for rtype in TYPES:
            self.assertIn(f"\n  {rtype},", out)
        self.assertIn("private: none", out)

    def test_bad_type_is_usage_error(self):
        code, out = run("scaffold", self.root, "--type", "web", "--title", "x")
        self.assertEqual(code, 2)
        self.assertIn("code: USAGE", out)
        code, out = run("check", self.root, "--type", "web")
        self.assertEqual(code, 2)


class Parsing(Base):
    def test_scaffold_writes_lf_line_endings(self):
        run("scaffold", self.root, "--type", "tool", "--title", "Demo")
        self.assertNotIn(b"\r\n", (self.root / "README.md").read_bytes())

    def test_long_fence_hides_inner_fence_and_headings(self):
        run("scaffold", self.root, "--type", "tool", "--title", "Demo")
        p = self.root / "README.md"
        text = p.read_text(encoding="utf-8").replace(
            "## Development\n", "## Development\n\n````md\n```\n## License\n```\n````\n", 1)
        p.write_bytes(text.encode("utf-8"))
        code, out = run("check", self.root)
        self.assertEqual(code, 0, out)

    def test_missing_license_file_is_a_broken_link_warning(self):
        (self.root / "LICENSE").unlink()
        code, out = run("scaffold", self.root, "--type", "tool", "--title", "Demo")
        self.assertIn("Add a LICENSE file", out)
        code, out = run("check", self.root)
        self.assertEqual(code, 0, out)  # luật mới chỉ cảnh báo
        self.assertIn(("README.md", "link"), self.warned(out))
        self.assertIn("LICENSE không có trong repo", out)
        self.assertIn("0 issues, 2 warnings", out)
        code, out = run("check", self.root, "--strict")
        self.assertEqual(code, 1)
        self.assertIn(("README.md", "link"), self.rules(out))

    def check_extra(self, extra):
        """Chạy check --strict với extra chèn vào README.md private hợp lệ; trả output."""
        self.write(*private_pair(en_extra=extra))
        return run("check", self.root, "--strict")

    def test_valid_links_and_images_pass(self):
        (self.root / "docs").mkdir()
        (self.root / "docs" / "a b.png").write_bytes(b"x")
        (self.root / "docs" / "a_(1).md").write_bytes(b"x")
        extra = (
            "\n[ok](docs/a%20b.png#x) [root](/LICENSE) [web](https://x.y/z) [anchor](#usage) [mail](mailto:a@b.c)"
            "\n[paren](docs/a_(1).md) [angle](<docs/a b.png>) [title](LICENSE 'single') [t2](LICENSE (paren))"
            "\n[up](../../issues) [sibling](../other-repo/README.md) [dir](docs/)"
            "\n![ok](docs/a%20b.png) <img src=\"docs/a b.png\" alt=\"ok\"> <img alt=\"a > b\" src=\"docs/a b.png\">"
            "\n<img src=docs/a%20b.png alt=shot> <img src=\"docs/a b.png\" alt=\"x\" data-src=\"docs/lazy.png\">"
            "\n<picture><source srcset=\"docs/a%20b.png 1x, docs/a%20b.png 2x\"><img src=\"docs/a b.png\" alt=\"p\"></picture>"
            "\n[![badge](https://img.shields.io/x)](LICENSE) [ref link][r1] ![ref img][r1]"
            "\n\n[r1]: docs/a%20b.png \"title\"\n"
            "\n`[code](nope.md)` ``[code2](nope.md) ` `` <!-- [comment](nope.md)\n![](nope.png) -->"
            "\n\n```\n[fenced](nope.md)\n```\n\n> ```\n> [quoted](nope.md)\n> ```\n"
            "\n1. step\n\n    ```js\n    handlers[name](event)\n    ```\n"
            "\n[Note]: this line is prose, not a reference definition\n")
        code, out = self.check_extra(extra)
        self.assertEqual(code, 0, out)
        self.assertIn("0 issues, 0 warnings", out)

    def test_broken_links_and_missing_alt_are_found(self):
        (self.root / "docs").mkdir()
        (self.root / "docs" / "Guide.md").write_bytes(b"x")
        extra = (
            "\n[gone](docs/missing.md)\n![](LICENSE)\n<img src=\"https://x.y/i.png\">\n<a href=\"old/\">x</a>\n"
            "[case](docs/guide.md)\n[slash](docs\\Guide.md)\n"
            "[![](LICENSE)](docs/outer.md)\n"                    # badge: cả link ngoài lẫn alt của ảnh trong
            "[ref][r2] ![][r2] ![x][nodef]\n\n[r2]: docs/ref.md\n"
            "<img\n  src=\"docs/multi.png\"\n  width=\"10\">\n"  # thẻ xuống dòng
            "<source srcset=\"docs/s1.png 1x, docs/s2.png 2x\">\n")
        code, out = self.check_extra(extra)
        self.assertEqual(code, 1)
        for url in ("docs/missing.md", "old/", "docs/guide.md", "docs\\Guide.md", "docs/outer.md", "docs/ref.md",
                    "docs/multi.png", "docs/s1.png", "docs/s2.png"):
            self.assertIn(f": {url} không có trong repo", out)
        self.assertIn("tham chiếu [nodef] chưa có dòng định nghĩa", out)
        self.assertEqual(out.count(",alt,"), 5, out)   # ![](LICENSE), img web, badge trong, ![][r2], img nhiều dòng
        lines = (self.root / "README.md").read_text(encoding="utf-8").split("\n")
        self.assertIn(f"dòng {lines.index('<img') + 1}: docs/multi.png", out)  # dòng mở thẻ, tính trên cả tệp

    def test_size_warning(self):
        self.write(*private_pair(en_extra="x" * (500 * 1024)))
        code, out = run("check", self.root)
        self.assertEqual(code, 0, out)
        self.assertIn(("README.md", "size"), self.warned(out))

    def test_flag_with_equals_sign(self):
        run("scaffold", self.root, "--type=tool", "--title=Demo")
        code, out = run("check", self.root, "--type=tool")
        self.assertEqual(code, 0, out)


class Meta(Base):
    """Ô About trên GitHub; READMEAXI_GH_JSON thay cho gh để test chạy không cần mạng."""

    def fake(self, **kw):
        data = {"description": "Runs the NAS scripts for the home lab", "visibility": "PUBLIC", "isFork": False,
                "licenseInfo": {"key": "mit"}, "usesCustomOpenGraphImage": True,
                "repositoryTopics": [{"name": n} for n in ("nas", "scripts", "home-lab", "backup", "linux")]}
        data.update(kw)
        p = self.tmp / "gh.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        os.environ["READMEAXI_GH_JSON"] = str(p)

    def tearDown(self):
        os.environ.pop("READMEAXI_GH_JSON", None)
        super().tearDown()

    def public_pair(self):
        en, vi = private_pair()
        self.write(en.replace(" private -->", " -->"), vi.replace(" private -->", " -->"))

    def fields(self, out):
        return {f for f, _ in self.rules(out)}

    def test_good_about_box_passes(self):
        self.public_pair()
        self.fake()
        code, out = run("meta", self.root, "--repo", "ngoviet/demo")
        self.assertEqual(code, 0, out)
        self.assertIn("topics[5]: nas,scripts,home-lab,backup,linux", out)

    def test_each_about_problem_is_reported(self):
        self.public_pair()
        self.fake(description="x" * 130, repositoryTopics=[{"name": "Bad_Topic"}], licenseInfo=None,
                  usesCustomOpenGraphImage=False)
        code, out = run("meta", self.root, "--repo", "ngoviet/demo")
        self.assertEqual(code, 1)
        self.assertEqual(self.fields(out), {"description", "intro", "topics", "license", "social-preview"}, out)
        self.assertIn("Bad_Topic: chỉ chữ thường", out)

    def test_intro_must_match_description_in_either_language(self):
        self.public_pair()
        self.fake(description="Chạy script NAS")
        code, out = run("meta", self.root, "--repo", "ngoviet/demo")
        self.assertEqual(code, 0, out)  # khớp bản tiếng Việt
        self.fake(description="Quantum chess engine with neural evaluation")
        code, out = run("meta", self.root, "--repo", "ngoviet/demo")
        self.assertIn("intro", self.fields(out))

    def test_private_repo_skips_topics_license_and_preview_but_checks_marker(self):
        self.write(*private_pair())
        self.fake(visibility="PRIVATE", repositoryTopics=[], licenseInfo=None, usesCustomOpenGraphImage=False)
        code, out = run("meta", self.root, "--repo", "ngoviet/demo")
        self.assertEqual(code, 0, out)
        self.public_pair()
        code, out = run("meta", self.root, "--repo", "ngoviet/demo")
        self.assertIn("visibility", self.fields(out))

    def test_no_github_origin_is_usage_error(self):
        code, out = run("meta", self.root)
        self.assertEqual(code, 2)
        self.assertIn("--repo owner/name", out)

    def test_fork_and_profile_repo_skip_topics_license_and_preview(self):
        self.public_pair()
        self.fake(repositoryTopics=[], licenseInfo=None, usesCustomOpenGraphImage=False, isFork=True)
        code, out = run("meta", self.root, "--repo", "ngoviet/demo")
        self.assertEqual(code, 0, out)
        self.fake(repositoryTopics=[], licenseInfo=None, usesCustomOpenGraphImage=False)
        code, out = run("meta", self.root, "--repo", "ngoviet/ngoviet")
        self.assertEqual(code, 0, out)

    def test_too_many_topics(self):
        self.public_pair()
        self.fake(repositoryTopics=[{"name": f"t{i}"} for i in range(21)])
        code, out = run("meta", self.root, "--repo", "ngoviet/demo")
        self.assertEqual(code, 1)
        self.assertIn("21 topic, GitHub chỉ cho 20", out)

    def test_gh_error_fails_meta_but_not_social(self):
        self.public_pair()
        p = self.tmp / "gh.json"
        p.write_text(json.dumps({"__gh_error__": "Could not resolve to a Repository"}), encoding="utf-8")
        os.environ["READMEAXI_GH_JSON"] = str(p)
        code, out = run("meta", self.root, "--repo", "ngoviet/nope")
        self.assertEqual(code, 1)
        self.assertIn("Could not resolve", out)
        code, out = run("social", self.root, "--repo", "ngoviet/nope", "--out", self.tmp / "e.svg")
        self.assertEqual(code, 0, out)
        self.assertIn("readme intro (gh failed", out)
        self.assertIn("Runs the NAS scripts.", (self.tmp / "e.svg").read_text(encoding="utf-8"))

    def test_gh_missing_skips_meta(self):
        self.public_pair()
        empty = self.tmp / "no-tools"
        empty.mkdir()
        code, out = run("meta", self.root, "--repo", "ngoviet/demo", PATH=str(empty))
        self.assertEqual(code, 0, out)
        self.assertIn("result: skipped, gh is not installed", out)

    def test_repo_owner_comes_from_origin(self):
        self.public_pair()
        self.fake()
        git(self.root, "init", "-q")
        git(self.root, "remote", "add", "origin", "git@github.com:ngoviet/foo.bar.git")
        code, out = run("meta", self.root)
        self.assertIn("repo: ngoviet/foo.bar", out)
        code, out = run("meta", self.root, "--repo", "other")
        self.assertIn("repo: ngoviet/other", out)
        git(self.root, "remote", "set-url", "origin", "https://gitlab.com/ngoviet/foo.git")
        code, out = run("social", self.root, "--repo", "foo", "--out", self.tmp / "x.svg")
        self.assertEqual(code, 2)  # chỉ có tên, origin không phải GitHub: không đoán chủ repo
        self.assertIn("--repo owner/name", out)

    def test_social_writes_svg_with_name_description_and_topics(self):
        self.public_pair()
        self.fake(description="A & B <tool> " + "word " * 40)
        code, out = run("social", self.root, "--repo", "ngoviet/demo", "--out", self.tmp / "s.svg")
        self.assertEqual(code, 0, out)
        self.assertFalse((self.tmp / "s.png").exists())   # --out .svg: chỉ vẽ SVG
        svg = (self.tmp / "s.svg").read_text(encoding="utf-8")
        self.assertIn(">demo</text>", svg)
        self.assertIn("A &amp; B &lt;tool&gt;", svg)
        self.assertIn("…", svg)  # mô tả dài bị cắt ở dòng thứ ba
        self.assertIn(">home-lab</text>", svg)
        self.assertIn('width="1280" height="640"', svg)

    def test_social_wide_text_stays_inside_the_card(self):
        self.public_pair()
        self.fake(description="W" * 200, repositoryTopics=[{"name": "w" * 50}])
        run("social", self.root, "--repo", "ngoviet/" + "M" * 40, "--out", self.tmp / "w.svg")
        svg = (self.tmp / "w.svg").read_text(encoding="utf-8")
        spec = importlib.util.spec_from_file_location("ra", CLI)
        ra = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(ra)
        for size, txt in re.findall(r'font-size="(\d+)"[^>]*>([^<]+)</text>', svg):
            self.assertLessEqual(ra.text_px(txt.replace("&amp;", "&"), int(size)), ra.TEXT_W, txt)

    def test_social_out_must_be_png_or_svg_in_an_existing_folder(self):
        self.public_pair()
        self.fake()
        code, out = run("social", self.root, "--repo", "ngoviet/demo", "--out", self.tmp / "c.txt")
        self.assertEqual(code, 2)
        code, out = run("social", self.root, "--repo", "ngoviet/demo", "--out", self.tmp / "nodir" / "x.png")
        self.assertEqual(code, 2)
        self.assertIn("thư mục đích không có", out)

    def test_social_png_without_browser_is_reported(self):
        self.public_pair()
        self.fake()
        stale = self.tmp / "p.png"
        stale.write_bytes(b"STALE")
        code, out = run("social", self.root, "--repo", "ngoviet/demo", "--out", stale, READMEAXI_BROWSER="")
        self.assertEqual(code, 1)
        self.assertIn("skipped (no Edge/Chrome)", out)
        self.assertFalse(stale.exists())   # ảnh cũ không được coi là ảnh mới


class SupportCompat(Base):
    """main là bản phát hành của mọi repo: đổi mẫu khối Ủng hộ không được làm đỏ README đang dùng mẫu cũ."""

    def public_with(self, en_block, vi_block):
        en, vi = private_pair()
        tail_en = f"\n{en_block}\n\n## License\n\n[MIT](LICENSE) © Ngô Đức Việt\n"
        tail_vi = f"\n{vi_block}\n\n## Giấy phép\n\n[MIT](LICENSE) © Ngô Đức Việt\n"
        self.write(en.replace(" private -->", " -->") + tail_en, vi.replace(" private -->", " -->") + tail_vi)

    def test_legacy_block_passes_with_a_warning(self):
        self.public_with(LEGACY_020_EN, LEGACY_020_VI)
        code, out = run("check", self.root, "--type", "ops")
        self.assertEqual(code, 0, out)
        self.assertIn(("README.md", "support-outdated"), self.warned(out))
        self.assertIn(("README.vi.md", "support-outdated"), self.warned(out))
        self.assertIn("support --write", out)
        code, out = run("check", self.root, "--type", "ops", "--strict")
        self.assertEqual(code, 1)

    def test_support_write_moves_legacy_block_to_current_template(self):
        self.public_with(LEGACY_020_EN, LEGACY_020_VI)
        code, out = run("support", self.root, "--write")
        self.assertIn("README.md,replaced", out)
        text = (self.root / "README.md").read_text(encoding="utf-8")
        self.assertIn("banner-v2.svg", text)
        self.assertNotIn("<sub>", text)
        code, out = run("check", self.root, "--type", "ops")
        self.assertEqual(code, 0, out)
        self.assertIn("0 issues, 0 warnings", out)

    def test_edited_block_is_still_an_error(self):
        self.public_with(LEGACY_020_EN.replace("911051212", "000000000"), LEGACY_020_VI)
        code, out = run("check", self.root, "--type", "ops")
        self.assertEqual(code, 1)
        self.assertIn(("README.md", "support"), self.rules(out))


class RepoName(Base):
    """Khối Ủng hộ chứa tên repo: lấy từ --repo, rồi origin, rồi tên thư mục."""

    def scaffold_for(self, repo):
        code, out = run("scaffold", self.root, "--type", "tool", "--title", "Demo", "--repo", repo, "--force")
        self.assertEqual(code, 0, out)

    def test_origin_wins_over_directory_name(self):
        git(self.root, "init", "-q")
        git(self.root, "remote", "add", "origin", "https://github.com/ngoviet/foo-bar.git")
        self.scaffold_for("foo-bar")
        code, out = run("check", self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("repo: foo-bar", out)
        self.assertIn("repo_from: origin", out)

    def test_ssh_origin_without_dot_git(self):
        git(self.root, "init", "-q")
        git(self.root, "remote", "add", "origin", "git@github.com:ngoviet/foo-bar")
        self.scaffold_for("foo-bar")
        code, out = run("check", self.root)
        self.assertEqual(code, 0, out)

    def test_worktree_uses_origin_not_folder(self):
        git(self.root, "init", "-q")
        git(self.root, "remote", "add", "origin", "https://github.com/ngoviet/foo-bar.git")
        self.scaffold_for("foo-bar")
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "init")
        wt = self.tmp / "wt-tam-123"
        git(self.root, "worktree", "add", "-q", str(wt))
        code, out = run("check", wt)
        self.assertEqual(code, 0, out)
        self.assertIn("repo: foo-bar", out)

    def test_flag_wins_over_origin(self):
        git(self.root, "init", "-q")
        git(self.root, "remote", "add", "origin", "https://github.com/ngoviet/foo-bar.git")
        self.scaffold_for("other")
        code, out = run("check", self.root)
        self.assertEqual(code, 1)
        self.assertIn(("README.md", "support"), self.rules(out))
        code, out = run("check", self.root, "--repo", "other")
        self.assertEqual(code, 0, out)
        self.assertIn("repo_from: flag", out)

    def test_directory_name_without_git(self):
        code, out = run("scaffold", self.root, "--type", "tool", "--title", "Demo")
        self.assertEqual(code, 0)
        code, out = run("check", self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("repo: demo-repo", out)
        self.assertIn("repo_from: dir", out)


class Drift(Base):
    def test_drift_reports_english_commits_after_vietnamese(self):
        git(self.root, "init", "-q")
        self.write(*private_pair())
        git(self.root, "add", ".")
        git(self.root, "commit", "-qm", "both")
        code, out = run("drift", self.root)
        self.assertEqual(code, 0)
        self.assertIn("result: in sync", out)
        self.write(private_pair(en_extra="\nMore.\n")[0])
        git(self.root, "commit", "-qam", "en only")
        code, out = run("drift", self.root)
        self.assertEqual(code, 0)
        self.assertIn("result: drift", out)
        code, out = run("drift", self.root, "--strict")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
