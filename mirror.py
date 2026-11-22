"""Chép nhân trình duyệt ShardX mới nhất của ShardBrowser thành 1 bản phát hành của kho này (dytool tải từ đây).

Chạy tự động bằng GitHub Actions (.github/workflows/mirror.yml, 6 giờ / lần). Chạy tay:
    GH_TOKEN=... python mirror.py --publish --repo snopvsreal/shardx-engine

Nguồn: runtime.json trên GitHub ProxyShard/ShardBrowser + kho Cloudflare R2 của họ (file zip) — đúng nơi SDK `shardx`
tự tải. Chép NGUYÊN runtime.json (cùng phiên bản / etag) để SDK trên máy dytool coi nhân đã cài là mới nhất. Không chép
Widevine (của Google — SDK tự tải từ Google). Tag: shardx-<chromium_version>-b<engine_build>; đã có -> thôi.
Nhân mới đòi SDK shardx mới hơn bản dytool đang ghim (SDK_PIN) -> dừng, báo lỗi (GitHub gửi email), KHÔNG đăng: dytool
phải nâng SDK và thử lại trước.
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import httpx

UPSTREAM_MANIFEST = "https://raw.githubusercontent.com/ProxyShard/ShardBrowser/main/runtime.json"
UPSTREAM_LICENSE = "https://raw.githubusercontent.com/ProxyShard/ShardBrowser/main/LICENSE"
PUB_BASE = "https://pub-e57a7c60f6934eb09a6600bf2fc59cdc.r2.dev"
ARCHIVES = ["ShardX-Windows.zip", "ShardX-Mac-arm64.zip", "ShardX-Fingerprints.zip"]
TAG_PREFIX = "shardx-"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _num(v) -> tuple:
    return tuple(int(x) if x.isdigit() else 0 for x in str(v).split("."))


def download(url: str, dest: Path) -> str:
    """Tải về, trả etag. Etag không có '-' (tải 1 phần) = MD5 cả file -> so luôn."""
    md5 = hashlib.md5()
    with httpx.stream("GET", url, follow_redirects=True, timeout=httpx.Timeout(60, connect=15)) as r:
        r.raise_for_status()
        total = int(r.headers.get("content-length", 0))
        etag = r.headers.get("etag", "").strip('"')
        got = 0
        with dest.open("wb") as f:
            for chunk in r.iter_bytes(1 << 20):
                f.write(chunk)
                md5.update(chunk)
                got += len(chunk)
    if total and got != total:
        raise SystemExit(f"{dest.name}: tải thiếu ({got}/{total} byte)")
    if etag and "-" not in etag and md5.hexdigest() != etag:
        raise SystemExit(f"{dest.name}: MD5 không khớp etag của nguồn")
    return etag


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--publish", action="store_true", help="tạo bản phát hành (cần gh + GH_TOKEN)")
    ap.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY", "snopvsreal/shardx-engine"))
    args = ap.parse_args()

    manifest = httpx.get(UPSTREAM_MANIFEST, follow_redirects=True, timeout=30).json()
    ver, build = manifest["chromium_version"], manifest.get("engine_build") or 0
    tag = f"{TAG_PREFIX}{ver}-b{build}"
    print(f"Nhân mới nhất của ShardBrowser: {ver} (build {build}) -> tag {tag}")
    have = subprocess.run(["gh", "release", "view", tag, "--repo", args.repo], capture_output=True)
    if have.returncode == 0:
        print("Đã có bản này — không cần làm gì")
        return
    pin = os.environ.get("SDK_PIN", "")
    need = manifest.get("min_sdk_version")
    if pin and need and _num(need) > _num(pin):
        raise SystemExit(f"Nhân {ver} cần SDK shardx >= {need}, dytool đang ghim {pin}: nâng shardx trong dytool "
                         "(pyproject.toml, thử lại browsers._use_mirror), sửa SDK_PIN trong workflow rồi chạy lại.")

    work = Path(tempfile.mkdtemp(prefix="shardx-mirror-"))
    files = []
    for key in ARCHIVES:
        dest = work / key
        etag = download(f"{PUB_BASE}/{key}", dest)
        want = (manifest.get("archives") or {}).get(key)
        if want and etag and etag != want:
            raise SystemExit(f"{key}: etag nguồn {etag} khác runtime.json ({want}) — họ đang đổi file, lần sau thử lại")
        with zipfile.ZipFile(dest) as z:
            bad = z.testzip()
            if bad:
                raise SystemExit(f"{key}: file hỏng bên trong zip ({bad})")
        files.append(dest)
        print(f"   OK {key}  {dest.stat().st_size / 1e6:.1f} MB")

    (work / "runtime.json").write_text(json.dumps(manifest, indent=2), "utf-8")
    (work / "LICENSE-ShardBrowser.txt").write_text(
        httpx.get(UPSTREAM_LICENSE, follow_redirects=True, timeout=30).text, "utf-8")
    files += [work / "runtime.json", work / "LICENSE-ShardBrowser.txt"]
    if not args.publish:
        print(f"Đã tải đủ vào {work} — chưa đăng (thêm --publish)")
        return
    notes = (f"Bản sao nhân trình duyệt ShardX {ver} (build {build}) để dytool tải về — chép nguyên vẹn, không sửa.\n\n"
             "- Nguồn: ShardBrowser — https://github.com/ProxyShard/ShardBrowser (giấy phép MIT, xem "
             "LICENSE-ShardBrowser.txt). Nhân dựa trên Chromium (giấy phép BSD và các thành phần bên thứ ba).\n"
             "- runtime.json: chép nguyên từ ProxyShard/ShardBrowser lúc tạo bản này.\n"
             "- Không kèm Widevine CDM (của Google) — SDK shardx tự tải từ Google.\n"
             "- dytool kiểm tra SHA256 của từng file trước khi dùng.")
    subprocess.run(["gh", "release", "create", tag, *map(str, files), "--repo", args.repo,
                    "--title", f"ShardX engine {ver} b{build}", "--notes", notes], check=True)
    print(f"Đã đăng {tag}")


if __name__ == "__main__":
    main()
