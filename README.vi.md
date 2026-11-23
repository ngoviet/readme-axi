# readme-axi

<!-- readme-axi type=tool -->

[English](README.md) · **Tiếng Việt**

Kiểm tra `README.md` (tiếng Anh) và `README.vi.md` (tiếng Việt) của một repo có theo khung chung của
ngoviet và khớp nhau không. Một tệp, chỉ dùng thư viện chuẩn Python, output dạng
[TOON](https://toonformat.dev/) cho agent; mã thoát 0 = đạt, 1 = có lỗi, 2 = sai cách gọi.

## Cài đặt

Không cần cài: `readme_axi.py` là một tệp duy nhất, chạy trên Python 3.9 trở lên, chỉ dùng thư viện
chuẩn. Chép đi đâu cũng chạy, hoặc tải từ nhánh `main`:

```bash
curl -fsSL https://raw.githubusercontent.com/ngoviet/readme-axi/main/readme_axi.py -o readme_axi.py
```

`drift` và phần lấy tên repo đọc lịch sử git, nên máy cần có `git` trong `PATH`.

## Cách dùng

```bash
python3 readme_axi.py check [dir]            # khung, dòng chuyển ngôn ngữ, mục bắt buộc, khớp EN/VI, khối Ủng hộ
python3 readme_axi.py drift [dir] [--strict] # commit sửa README.md mà README.vi.md chưa theo
python3 readme_axi.py meta [dir]             # ô About trên GitHub (cần gh): mô tả, topic, giấy phép, ảnh preview
python3 readme_axi.py social [dir]           # vẽ ảnh social preview 1280x640 (SVG, PNG khi có Edge/Chrome)
python3 readme_axi.py support [dir] --write  # chèn/làm mới khối "Ủng hộ dự án" dùng chung
python3 readme_axi.py scaffold --type ha --title "Name for Home Assistant"
python3 readme_axi.py scaffold --type ops --title "nas" --private   # khung cho repo private
python3 readme_axi.py ci [dir] --write       # thêm tệp CI readme: GitHub Actions (public), Woodpecker (private)
python3 readme_axi.py hook session-start     # hook cho Claude Code, đọc JSON của phiên qua stdin
python3 readme_axi.py names                  # tên mục chuẩn Anh -> Việt và thứ tự bắt buộc
```

## Cách hoạt động

### Khung README

README nào cũng mở đầu giống nhau:

1. `# Tiêu đề` ở dòng đầu, rồi dấu `<!-- readme-axi type=<loại> -->`
   (`<!-- readme-axi type=<loại> private -->` ở repo private).
2. Huy hiệu (badge), rồi dòng chuyển ngôn ngữ: `**English** · [Tiếng Việt](README.vi.md)` trong README.md,
   `[English](README.md) · **Tiếng Việt**` trong README.vi.md.
3. Một đoạn: làm gì, cho thiết bị nào. Có thể thêm nút cài đặt, một dòng mời ủng hộ, ảnh chụp màn hình.

và, ở repo public, kết thúc giống nhau: khối Ủng hộ dùng chung, rồi `## License` / `## Giấy phép`
(`[MIT](LICENSE) © Ngô Đức Việt`, thêm "Không liên kết với …" khi dự án dành cho thiết bị của một hãng).

Các mục `##` bắt buộc, đúng thứ tự này (mục khác được chen vào giữa):

| Loại | Bắt buộc |
|---|---|
| `ha` tích hợp Home Assistant | Tính năng · Cài đặt · Cấu hình · Thực thể · Xử lý sự cố · Phát triển |
| `card` card / theme Lovelace | Tính năng · Cài đặt · Cách dùng |
| `esp32` thiết bị ESPHome | Tính năng · Phần cứng · Bắt đầu nhanh · Home Assistant |
| `tool` CLI / thư viện | Cài đặt · Cách dùng |
| `app` web app / dịch vụ | Tính năng · Phát triển · Triển khai |
| `ops` repo vận hành (script, máy chủ) | Cách dùng · Cấu trúc dự án |
| `config` repo cấu hình | Cấu trúc dự án · Triển khai |
| `docs` tài liệu, ghi chép | Cấu trúc dự án |

Hai tệp có cùng số mục `##`, cùng thứ tự, dùng tên chuẩn (`readme_axi.py names`). Tiêu đề không có
emoji để anchor sạch.

Khối Ủng hộ ghi tên repo. Tên lấy từ `--repo`, rồi git remote `origin`, rồi tên thư mục, nên chạy trong
worktree hay bản clone tạm vẫn kiểm đúng tên.

CI của mọi repo tải bản ở `main`, nên đổi mẫu khối Ủng hộ không làm README đang có đỏ lên: khối do
readme-axi 0.2.x viết vẫn đạt, kèm cảnh báo `support-outdated`, và `support --write` đưa nó lên mẫu hiện
hành. Khối bị sửa tay vẫn là lỗi.

### Link, ảnh và kích thước

`check` còn đọc link và ảnh nằm ngoài code (khối code có rào, code trong dòng, chú thích `<!-- -->`):
link Markdown kiểu inline và kiểu tham chiếu, ảnh lồng trong link (badge), các thẻ `<a>`, `<img>`,
`<source>`, kể cả thẻ viết trên nhiều dòng.

- `link`: link hay ảnh tương đối phải trỏ tới tệp có trong repo, đúng cả chữ hoa chữ thường như trên
  GitHub và CI Linux. Link web, anchor và đường dẫn trèo ra ngoài repo (`../../issues`, `../repo-khác`)
  không được kiểm.
- `alt`: ảnh nào cũng cần chữ thay thế.
- `size`: README quá 500 KiB, vì GitHub cắt phần thừa.

Ba luật này chỉ cảnh báo, không làm đỏ; `check --strict` thì đỏ cả với cảnh báo. Khối code thụt bốn dấu
cách (không có rào) chưa được nhận là code.

### Ô About trên GitHub

Ô tìm của GitHub chỉ đọc tên repo, mô tả và topic, trừ khi người tìm gõ thêm `in:readme`; Google lấy
mô tả làm đoạn tóm tắt của trang. `meta` đọc các trường này qua `gh` và báo: thiếu mô tả hoặc mô tả quá
120 ký tự, dưới 5 topic hoặc topic sai dạng, GitHub không nhận ra giấy phép, chưa có ảnh social preview,
đoạn giới thiệu README nói khác mô tả, và dấu `private` không khớp với GitHub. Bản fork và repo hồ sơ
được bỏ qua luật topic, giấy phép, ảnh preview. Máy không có `gh` thì lệnh báo bỏ qua và thoát 0.

GitHub không có API tải ảnh social preview: `social` vẽ sẵn ảnh (tên, mô tả, topic) để chủ tải lên ở
Settings > General > Social preview. GitHub trả topic gần như theo a-b-c, nên ảnh chọn tối đa năm topic
theo mô tả: topic có trong mô tả đứng trước, theo thứ tự đọc; topic na ná nhau (`homeassistant` cạnh
`home-assistant`) bị bỏ.

### Repo private

Thêm chữ `private` vào dấu ở cả hai tệp: `<!-- readme-axi type=ops private -->`. Repo private vẫn giữ khung
song ngữ (tiêu đề và dấu, dòng chuyển ngôn ngữ, đoạn giới thiệu, mục theo loại, tên mục chuẩn, khớp EN/VI,
tiêu đề không emoji, `drift`) nhưng không bắt khối Ủng hộ và mục `## Giấy phép`: không ai ngoài chủ đọc,
mã không cấp phép MIT. `support --write` không đụng tới repo private.

Khi chuyển repo sang public, bỏ chữ `private` khỏi dấu; `check` sẽ liệt kê phần còn thiếu (khối Ủng hộ,
Giấy phép).

## Cấu hình

Mỗi repo public gọi workflow dùng chung trong repo này (GitHub Actions):

```yaml
# .github/workflows/readme.yml
name: README
on:
  push:
    paths: [README.md, README.vi.md, .github/workflows/readme.yml]
  pull_request:
    paths: [README.md, README.vi.md, .github/workflows/readme.yml]
jobs:
  readme:
    uses: ngoviet/readme-axi/.github/workflows/readme.yml@main
```

Repo private chạy trên Woodpecker tự host https://ci.vokupt.top (GitHub Actions hết phút cho repo
private). Repo phải được bật ở đó và có tệp này:

```yaml
# .woodpecker/readme.yaml
when:
  - event: pull_request
    path: [README.md, README.vi.md, .woodpecker/readme.yaml]
  - event: push
    branch: main
    path: [README.md, README.vi.md, .woodpecker/readme.yaml]
  - event: manual

clone:
  - name: clone
    image: woodpeckerci/plugin-git
    settings:
      partial: false # drift đọc lịch sử git: clone đủ, không shallow
      depth: 0

steps:
  - name: readme
    image: python:3.13-bookworm # có sẵn python3, git và curl
    commands:
      - git config --global --add safe.directory "$CI_WORKSPACE"
      - curl -fsSL https://raw.githubusercontent.com/ngoviet/readme-axi/main/readme_axi.py -o /tmp/readme_axi.py
      - python3 /tmp/readme_axi.py check
      - python3 /tmp/readme_axi.py drift
```

Nhánh `main` của repo public này là bản phát hành, nên tải về không cần token. CI mọi nơi chạy đúng tệp
đó: thay đổi tới mọi repo ngay khi vào `main`.

`readme_axi.py ci --write` ghi đúng một trong hai tệp trên, chọn theo cờ `private` trong dòng đánh dấu.
Tệp đã có mà khác mẫu thì được giữ nguyên, trừ khi thêm `--force`.

### Hook cho Claude Code

`hook` nhắc Claude Code khi repo đang làm thuộc `ngoviet` (đặt `READMEAXI_OWNER` cho chủ khác) mà còn
thiếu dòng đánh dấu, `README.vi.md` hay tệp CI. Thư mục làm việc còn thiếu thì lệnh so tiếp với nhánh
chính đã fetch gần nhất (`origin/HEAD`), nên bản clone chậm hay nhánh tính năng cũ không bị nhắc khi `main`
đã đạt. Lệnh chỉ dùng git cục bộ, không mạng, luôn thoát 0 và không bao giờ chặn. SessionStart thêm lời
nhắc vào phiên; Stop báo một lần cho người dùng khi repo vào
phạm vi giữa phiên. Mỗi repo được nhắc nhiều nhất một lần mỗi phiên. Repo hồ sơ, `.github` và repo có tệp
`.readme-axi-skip` ở gốc được bỏ qua.

```json
"hooks": {
  "SessionStart": [{"hooks": [{"type": "command", "command": "python /path/to/readme_axi.py hook session-start"}]}],
  "Stop": [{"hooks": [{"type": "command", "command": "python /path/to/readme_axi.py hook stop"}]}]
}
```

## Phát triển

```bash
python3 -m unittest discover -s . -v
```

Test chạy CLI trên các README tạm (và repo git tạm cho `drift` và phần lấy tên repo). Chính README này
cũng được kiểm: `python3 readme_axi.py check` phải đạt trước khi commit.

Muốn phát hành thì tăng `VERSION` trong `readme_axi.py` rồi đẩy tag `vX.Y.Z`. Workflow release kiểm tag
khớp `VERSION`, chạy test rồi tạo release trên GitHub. Các repo vẫn tải `main`, nên tag là bản ghi lịch
sử, không phải bản được ghim: muốn quay lại bản trước thì revert trên `main`.

<!-- support:start -->
## Ủng hộ dự án

<p align="center">
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/banner-v2.svg" width="560" alt="Built and maintained by one person in Việt Nam">
</p>

<p align="center">Một người Việt tự xây dựng và duy trì, miễn phí và mã nguồn mở. Sự ủng hộ của bạn giúp hỗ trợ thêm thiết bị, sửa lỗi nhanh hơn và ra bản mới đều đặn.</p>

<p align="center">
  <a href="https://buymeacoffee.com/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-coffee.svg" height="56" alt="Buy me a coffee"></a>
  &nbsp;
  <a href="https://github.com/sponsors/ngoviet"><img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/btn-sponsors.svg" height="56" alt="GitHub Sponsors"></a>
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/vietqr-card.svg" width="300" alt="VietQR — MB Bank — NGO DUC VIET — 911051212">
  &nbsp;
  <img src="https://raw.githubusercontent.com/ngoviet/.github/main/assets/support/crypto-card.svg" width="300" alt="Crypto — BNB Smart Chain (BEP20) — 0xcbf0402b232cb24b4d998f09a4884f87b5f74750">
</p>

<p align="center"><b>Ví tiền mã hoá, chỉ gửi qua mạng BNB Smart Chain (BEP20):</b><br><code>0xcbf0402b232cb24b4d998f09a4884f87b5f74750</code></p>

<p align="center">🇻🇳 VietQR: quét bằng app ngân hàng bất kỳ, nội dung <code>Ung ho readme-axi</code>. Cảm ơn bạn đã giúp dự án tiếp tục phát triển!</p>
<!-- support:end -->

## Giấy phép

[MIT](LICENSE) © Ngô Đức Việt
