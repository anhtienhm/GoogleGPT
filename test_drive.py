import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']

def test_google_drive():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("LỖI: Không tìm thấy file credentials.json trong thư mục!")
                return
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    try:
        service = build('drive', 'v3', credentials=creds)
        print(">>> Kết nối thành công! Đang quét danh sách file trên Google Drive của bạn...")
        
        results = service.files().list(
            pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            print('Không tìm thấy file nào trên Drive.')
        else:
            print('Danh sách file tìm thấy trên Drive của bạn:')
            for item in items:
                print(f"- {item['name']} (ID: {item['id']})")
                
    except Exception as error:
        print(f'Đã xảy ra lỗi: {error}')

if __name__ == '__main__':
    test_google_drive()