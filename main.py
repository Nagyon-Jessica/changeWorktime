import os
import sys
from datetime import date

from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
from selenium.webdriver.support.wait import WebDriverWait

# １日以外はスキップするための条件
if __name__ == "__main__":
    today = date.today().day
    if today != 1:
        print(f"Job skipped: today is {today}th, not 1st")
        sys.exit()

URL = os.environ.get("URL")
ID = os.environ.get("ID")
PW = os.environ.get("PW")

options = Options()
options.add_argument('--headless')
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 30)

count = 0
while count < 5:
    try:
        driver.get(URL)
        wait.until(
            EC.presence_of_element_located((By.ID, "username"))
        )
    except TimeoutException:
        if count < 4:
            print("ログイン画面を再読込します。")
            count += 1
        else:
            print("ログインに失敗しました。")
            sys.exit(1)
    else:
        print(driver.title)
        break

driver.find_element(by=By.ID, value='username').send_keys(ID)
driver.find_element(by=By.ID, value='password').send_keys(PW)
driver.find_element(by=By.ID, value='Login').submit()

wait.until(
    EC.presence_of_element_located((By.ID, "mainTableBody"))
)
table = driver.find_element(by=By.ID, value="mainTableBody")
rows = table.find_elements(by=By.XPATH, value="tr[contains(@class, 'days')]")
workdays = []
for row in rows:
    if '通常出勤日' in row.find_element(by=By.XPATH, value='td[contains(@class, "vstatus")]').get_attribute('title'):
        workdays.append(row)

# 終了日探索用カーソル
cur = 0
# 変更申請中フラグ
in_progress = False
# 勤務日の日数
length = len(workdays)

def modal_close(workday):
    # 関数外の変数を更新するため，グローバル宣言
    global cur, in_progress
    # 現在開いている「勤務時間変更申請」タブを取得
    current_tab = driver.find_element(by=By.XPATH, value="//div[contains(@class, 'dijitVisible')]")
    # カレンダーのボタンアイコン
    calendar = current_tab.find_element(by=By.XPATH, value=".//input[contains(@id, 'dialogApplyEndDateCal')]")
    # 再申請の場合「から」がチェック済み
    if 'dis' in calendar.get_attribute('class'):
        current_tab.find_element(by=By.XPATH, value=".//input[contains(@id, 'dialogApplyRangeOn')]").click()
    calendar.click()
    # カレンダーが表示されるまで待機
    wait.until(
        EC.element_to_be_clickable((By.ID, "_atk_cal_cancel"))
    )
    # 勤務時間変更申請の終了日
    day = int(workday.get_attribute('id').split("-")[-1])
    # カレンダーで終了日をクリック
    driver.find_element(by=By.XPATH, value=f"//td[contains(@class, 'dijitCalendarEnabledDate')]/span[text()='{str(day)}']").click()
    # 「承認申請」／「再申請」をクリック
    current_tab.find_element(by=By.XPATH, value=".//button[contains(@id, 'empApplyDone')]").click()
    cur += 1
    in_progress = False

for i, workday in enumerate(workdays):
    if i < cur:
        continue
    elif i == cur and in_progress:
        modal_close(workday)
    else:
        in_progress = True
        # 前の申請が完了するまで待機
        wait.until(
            EC.invisibility_of_element_located((By.ID, "BusyWait_underlay"))
        )
        # 「申請」カラムの「＋」をクリック
        workday.find_element(by=By.XPATH, value='td[contains(@class, "vapply")]').click()
        # モーダルが表示されるまで待機
        wait.until(
            EC.element_to_be_clickable((By.ID, "empApplyTab_tablist_empApplyContent0"))
        )
        # モーダルの「メニュー」タブをクリック
        driver.find_element(by=By.ID, value="empApplyTab_tablist_empApplyContent0").click()
        # 「勤務時間変更申請」をクリック
        driver.find_element(by=By.ID, value="applyNew_patternS").click()
        # 現在開いている「勤務時間変更申請」タブを取得
        current_tab = driver.find_element(by=By.XPATH, value="//div[contains(@class, 'dijitVisible')]")
        # 「勤務日」を選択
        select_daytype_element = current_tab.find_element(by=By.XPATH, value=".//select[contains(@id, 'dlgApplyDayType')]")
        Select(select_daytype_element).select_by_index(1)
        # 「手入力はこちら」を選択
        select_pattern_element = current_tab.find_element(by=By.XPATH, value=".//select[contains(@id, 'dlgApplyPatternList')]")
        Select(select_pattern_element).select_by_index(9)
        # 勤務時間変更申請の開始日
        day = int(workday.get_attribute('id').split("-")[-1])

        # 勤務日がどこまで続くか探索
        # 最終勤務日はループに入らない（インデックスエラー起こす）
        while cur + 1 < length:
            d = int(workdays[cur + 1].get_attribute('id').split("-")[-1])
            if d - day == 1:
                day += 1
                cur += 1
            else:
                break

        # ループに入らなかった場合は孤立した勤務日のため，即座に登録
        if i == cur:
            modal_close(workday)

driver.quit()
