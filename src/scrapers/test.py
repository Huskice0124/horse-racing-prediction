import requests
from bs4 import BeautifulSoup

# 你要求的特定格式
url = "https://db.netkeiba.com/race/202505040811/"
headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3 Safari/605.1.15"}

try:
    res = requests.get(url, headers=headers, timeout=5)
    res.encoding = 'EUC-JP'
    print(f"伺服器回應狀態碼: {res.status_code}") # 200 代表成功，403 代表被擋

    # 把程式看到的內容存下來
    with open("what_the_bot_sees.html", "w", encoding="utf-8") as f:
        f.write(res.text)
    
    print("已將網頁內容存至 what_the_bot_sees.html，請打開這個檔案看看裡面有沒有表格。")

    soup = BeautifulSoup(res.content, "html.parser")
    # 嘗試找看看任何表格
    tables = soup.find_all('table')
    print(f"網頁中總共發現了 {len(tables)} 個表格")

except Exception as e:
    print(f"連線發生錯誤: {e}")