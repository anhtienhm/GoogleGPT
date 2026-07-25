API deepseek  <DEEPSEEK_API_KEY -- dat trong file .env, KHONG commit>  

QUY TRÌNH CHUẨN
Cài Telegram để điều khiển Hermes và Terminal
BƯỚC 1. Cài Hermes

Kiểm tra:

hermes --version

Nếu hiện:

Hermes 0.18.x

thì OK.

BƯỚC 2. Kiểm tra Hermes

Chạy:

hermes doctor

Nếu có lỗi:

config.yaml

hoặc

Failed to parse config

=> sửa trước.

Nếu không thì tiếp tục.

BƯỚC 3. Tạo Bot Telegram

Mở Telegram

Tìm

@BotFather

Gõ

/newbot

Đặt tên bot

Ví dụ

Hermes DeepSeek

Đặt username

Ví dụ

hermes01deepseek_bot

BotFather trả về

HTTP API Token

Ví dụ

123456:AA......

Giữ token này.

BƯỚC 4. Cấu hình Telegram cho Hermes

Chạy

hermes gateway setup

Chọn

Telegram

Sau đó

Configure Telegram

Nhập

Bot Token

Khi hỏi

Restart Gateway?

chọn

Y
BƯỚC 5. Cấu hình AI

Chạy

hermes model

Chọn

17
DeepSeek

Nếu Hermes hỏi

Keep / Replace / Clear

thì

R

để thay API Key

Dán

DeepSeek API Key

Base URL

https://api.deepseek.com/v1

Model

deepseek-chat
BƯỚC 6. Restart Gateway
hermes gateway restart
BƯỚC 7. Kiểm tra
hermes doctor

Phải thấy

✓ DeepSeek

KHÔNG được còn

invalid api key
BƯỚC 8. Chat Telegram

Mở Telegram

Chat với bot

/start

Sau đó

Xin chào Hermes

Nếu bot trả lời

=> Thành công.

BƯỚC 9. Test Terminal

Gửi Telegram

Đọc thư mục

~/Desktop/GoogleGPT_Tool

Nếu bot trả về danh sách file

=> Hermes đã điều khiển Terminal.

BƯỚC 10. Test chạy lệnh

Gửi

Mở Terminal

cd ~/Desktop/GoogleGPT_Tool

python --version

Nếu bot trả

Python 3.x.x

=> Terminal hoạt động.

BƯỚC 11. Test chạy project

Gửi

Chuyển tới

~/Desktop/GoogleGPT_Tool

Kích hoạt

source venv_mac/bin/activate

Chạy

python app.py

Hermes sẽ:

mở Terminal
kích hoạt virtualenv
chạy app.py
đọc log
trả kết quả về Telegram
BƯỚC 12. Điều khiển hằng ngày

Ví dụ bạn có thể gửi:

Chạy project
Chạy app.py
Đọc file
Mở

links.txt
Sửa code
Mở app.py

Sửa lỗi

Lưu lại
Tìm lỗi
Đọc log

Tìm lỗi

Sửa

Chạy lại
Chạy Pipeline
run_clean.py

↓

run_filter.py

↓

process_pipeline.py

Dưới đây là quy trình chuẩn mình đã rút ra từ chính quá trình bạn cài Hermes. Làm đúng theo thứ tự này sẽ tránh hầu hết các lỗi.

QUY TRÌNH CHUẨN
Cài Telegram để điều khiển Hermes và Terminal
BƯỚC 1. Cài Hermes

Kiểm tra:

hermes --version

Nếu hiện:

Hermes 0.18.x

thì OK.

BƯỚC 2. Kiểm tra Hermes

Chạy:

hermes doctor

Nếu có lỗi:

config.yaml

hoặc

Failed to parse config

=> sửa trước.

Nếu không thì tiếp tục.

BƯỚC 3. Tạo Bot Telegram

Mở Telegram

Tìm

@BotFather

Gõ

/newbot

Đặt tên bot

Ví dụ

Hermes DeepSeek

Đặt username

Ví dụ

hermes01deepseek_bot

BotFather trả về

HTTP API Token

Ví dụ

123456:AA......

Giữ token này.

BƯỚC 4. Cấu hình Telegram cho Hermes

Chạy

hermes gateway setup

Chọn

Telegram

Sau đó

Configure Telegram

Nhập

Bot Token

Khi hỏi

Restart Gateway?

chọn

Y
BƯỚC 5. Cấu hình AI

Chạy

hermes model

Chọn

17
DeepSeek

Nếu Hermes hỏi

Keep / Replace / Clear

thì

R

để thay API Key

Dán

DeepSeek API Key

Base URL

https://api.deepseek.com/v1

Model

deepseek-chat
BƯỚC 6. Restart Gateway
hermes gateway restart
BƯỚC 7. Kiểm tra
hermes doctor

Phải thấy

✓ DeepSeek

KHÔNG được còn

invalid api key
BƯỚC 8. Chat Telegram

Mở Telegram

Chat với bot

/start

Sau đó

Xin chào Hermes

Nếu bot trả lời

=> Thành công.

BƯỚC 9. Test Terminal

Gửi Telegram

Đọc thư mục

~/Desktop/GoogleGPT_Tool

Nếu bot trả về danh sách file

=> Hermes đã điều khiển Terminal.

BƯỚC 10. Test chạy lệnh

Gửi

Mở Terminal

cd ~/Desktop/GoogleGPT_Tool

python --version

Nếu bot trả

Python 3.x.x

=> Terminal hoạt động.

BƯỚC 11. Test chạy project

Gửi

Chuyển tới

~/Desktop/GoogleGPT_Tool

Kích hoạt

source venv_mac/bin/activate

Chạy

python app.py

Hermes sẽ:

mở Terminal
kích hoạt virtualenv
chạy app.py
đọc log
trả kết quả về Telegram
BƯỚC 12. Điều khiển hằng ngày

Ví dụ bạn có thể gửi:

Chạy project
Chạy app.py
Đọc file
Mở

links.txt
Sửa code
Mở app.py

Sửa lỗi

Lưu lại
Tìm lỗi
Đọc log

Tìm lỗi

Sửa

Chạy lại
Chạy Pipeline
run_clean.py

↓

run_filter.py

↓

process_pipeline.py
Các lỗi thường gặp
Lỗi	Nguyên nhân	Cách xử lý
Provider authentication failed	API key DeepSeek sai/hết hạn	Tạo API key mới và cập nhật trong hermes model
Telegram không trả lời	Gateway chưa chạy	hermes gateway restart
Bot trả lời nhưng không chạy Terminal	Chưa bật hoặc chưa cấp quyền công cụ terminal	Kiểm tra cấu hình công cụ của Hermes
invalid api key	API key DeepSeek không hợp lệ	Thay API key mới
config.yaml parse error	File cấu hình bị lỗi	Sửa hoặc khôi phục config.yaml
Quy trình hoạt động sau khi hoàn tất
Telegram
        │
        ▼
Hermes Gateway
        │
        ▼
DeepSeek (LLM)
        │
        ▼
Hermes Agent
        │
        ▼
Terminal
        │
        ▼
Python (app.py)
        │
        ▼
Kết quả trả về Telegram

Đây là quy trình đầy đủ từ cài đặt đến kiểm tra và vận hành hằng ngày. Sau khi hoàn tất, bạn có thể điều khiển Hermes từ Telegram để đọc file, chạy lệnh Terminal, khởi chạy các script Python và nhận kết quả trực tiếp trên Telegram.