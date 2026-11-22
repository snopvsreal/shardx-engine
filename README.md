# shardx-engine

Bản sao nhân trình duyệt **ShardX** của [ShardBrowser](https://github.com/ProxyShard/ShardBrowser) (giấy phép MIT)
để [dytool](https://github.com/snopvsreal/douyin-down) tải về.

- File trong mỗi bản phát hành chép **nguyên vẹn** từ nguồn chính thức của ShardBrowser, không sửa gì.
- `runtime.json` chép nguyên từ ProxyShard/ShardBrowser lúc tạo bản.
- Không chứa Widevine CDM (của Google): SDK `shardx` tự tải từ Google.
- dytool kiểm tra SHA256 của từng file (mã GitHub công bố) trước khi dùng.
- Tạo bản mới: `scripts/mirror_shardx.py --publish` trong kho dytool.

Nhân dựa trên Chromium (giấy phép BSD và các thành phần bên thứ ba). Giấy phép ShardBrowser: `LICENSE-ShardBrowser.txt`
trong mỗi bản phát hành.
