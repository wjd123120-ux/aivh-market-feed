"""매일 아침 브리핑용 시세 수집 (GitHub Actions에서 실행).
결과: data/prices.json, data/prices.csv  (종목별 '마감된' 최근 종가, 전일 대비, 기준일)
- 장이 아직 열려 있는 날의 가격(장중 가격)은 종가로 쓰지 않고 버린다.
공개 시세만 저장한다. 보유 수량·금액 같은 개인 정보는 넣지 않는다.
"""
import json
import os
from datetime import datetime, timezone, timedelta, time

import pandas as pd

KST = timezone(timedelta(hours=9))
# (표시 이름, yfinance 티커, FinanceDataReader 코드(한국 대체용), 시장: KR/US/24H)
ITEMS = [
    ("코스피", "^KS11", "KS11", "KR"), ("코스닥", "^KQ11", "KQ11", "KR"),
    ("S&P500", "^GSPC", None, "US"), ("나스닥종합", "^IXIC", None, "US"), ("VIX", "^VIX", None, "US"),
    ("미국10년금리", "^TNX", None, "US"), ("원달러환율", "KRW=X", "USD/KRW", "24H"), ("금(달러/온스)", "GC=F", None, "24H"),
    ("기아", "000270.KS", "000270", "KR"), ("휴메딕스", "200670.KQ", "200670", "KR"),
    ("코리아에프티", "123410.KQ", "123410", "KR"), ("대한약품", "023910.KQ", "023910", "KR"),
    ("페이팔", "PYPL", None, "US"), ("어도비", "ADBE", None, "US"), ("인튜이트", "INTU", None, "US"),
    ("QQQ", "QQQ", None, "US"), ("QQQM", "QQQM", None, "US"), ("VOO", "VOO", None, "US"), ("SCHB", "SCHB", None, "US"),
]
MARKET = {"KR": ("Asia/Seoul", time(15, 40)), "US": ("America/New_York", time(16, 20))}


def completed(s: pd.Series, mkt: str) -> pd.Series:
    """오늘 장이 아직 안 끝났으면 오늘 줄(장중 가격)을 버린다."""
    if mkt not in MARKET or s.empty:
        return s
    tz, close = MARKET[mkt]
    now = pd.Timestamp.now(tz=tz)
    last = pd.Timestamp(s.index[-1])
    last_date = (last.tz_convert(tz) if last.tzinfo else last).date()
    if last_date == now.date() and now.time() < close:
        return s.iloc[:-1]
    return s


def hist_yf(tk):
    import yfinance as yf
    return yf.Ticker(tk).history(period="15d", interval="1d", auto_adjust=False)["Close"].dropna()


def hist_fdr(code):
    import FinanceDataReader as fdr
    start = (datetime.now(KST) - timedelta(days=20)).strftime("%Y-%m-%d")
    return fdr.DataReader(code, start)["Close"].dropna()


def row(name, yt, fc, mkt):
    err = ""
    for src, fn, arg in (("yfinance", hist_yf, yt), ("FinanceDataReader", hist_fdr, fc)):
        if not arg:
            continue
        try:
            s = completed(fn(arg), mkt)
            if len(s) >= 2:
                d = pd.Timestamp(s.index[-1]).strftime("%Y-%m-%d")
                c, p = float(s.iloc[-1]), float(s.iloc[-2])
                return {"이름": name, "티커": yt, "기준일": d, "종가": round(c, 4), "전일종가": round(p, 4),
                        "등락률(%)": round((c / p - 1) * 100, 2), "구분": "실시간(24시간 시장)" if mkt == "24H" else "마감 종가",
                        "출처": src}
        except Exception as e:  # 다음 출처로
            err = f"{src}: {e}"
    return {"이름": name, "티커": yt, "기준일": None, "종가": None, "전일종가": None, "등락률(%)": None,
            "구분": None, "출처": "실패", "오류": err}


def main():
    os.makedirs("data", exist_ok=True)
    rows = [row(*it) for it in ITEMS]
    out = {"생성시각(KST)": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "시세": rows}
    with open("data/prices.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    pd.DataFrame(rows).to_csv("data/prices.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
