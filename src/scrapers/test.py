import requests

# 目標 URL (ウィルサヴァイブ)
url = "https://db.netkeiba.com/horse/2022104748"

# 關鍵：加入瀏覽器標頭，防止被伺服器阻擋
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

try:
    response = requests.get(url, headers=headers)
    
    # netkeiba 採用 EUC-JP 編碼，必須正確設定否則會亂碼
    response.encoding = 'EUC-JP'
    
    if response.status_code == 200:
        # 將抓到的 HTML 存成檔案
        with open("horse_page.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        print("成功！HTML 結構已儲存為 horse_page.html")
    else:
        print(f"失敗，狀態碼：{response.status_code}")

except Exception as e:
    print(f"發生錯誤：{e}")
