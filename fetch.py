"""매일 아침 브리핑용 시세 수집 (GitHub Actions에서 실행).
결과: data/prices.json, data/prices.csv  (종목별 최근 종가, 전일 대비, 기준일)
공개 시세만 저장한다. 보유 수량·금액 같은 개인 정보는 넣지 않는다.
"""
import json
from datetime import datetime, timezone, timedelta

import pandas as pd

KST = timezone(timedelta(hours=9))
# (표시 이름, yfinance 티커, FinanceDataReader 코드(한국 대체용))
ITEMS = [
    ("코스피", "^KS11", "KS11"), ("코스닥", "^KQ11", "KQ11"),
    ("S&P500", "^GSPC", None), ("나스닥종합", "^IXIC", None), ("VIX", "^VIX", None),
    ("미국10년금리", "^TNX", None), ("원달러환율", "KRW=X", "USD/KRW"), ("금(달러/온스)", "GC=F", None),
    ("기아", "000270.KS", "000270"), ("휴메딕스", "200670.KQ", "200670"),
    ("코리아에프티", "123410.KQ", "123410"), ("대한약품", "023910.KQ", "023910"),
    ("페이팔", "PYPL", None), ("어도비", "ADBE", None), ("인튜이트", "INTU", None),
    ("QQQ", "QQQ", None), ("VOO", "VOO", None), ("SCHB", "SCHB", None),
]


def last2_yf(tk):
    import yfinance as yf
    h = yf.Ticker(tk).history(period="10d", interval="1d", auto_adjust=False)["Close"].dropna()
    return h


def last2_fdr(code):
    import FinanceDataReader as fdr
    start = (datetime.now(KST) - timedelta(days=15)).strftime("%Y-%m-%d")
    return fdr.DataReader(code, start)["Close"].dropna()


def row(name, yt, fc):
    err = ""
    for src, fn, arg in (("yfinance", last2_yf, yt), ("FinanceDataReader", last2_fdr, fc)):
        if not arg:
            continue
        try:
            s = fn(arg)
            if len(s) >= 2:
                d = pd.to_datetime(s.index[-1]).strftime("%Y-%m-%d")
                c, p = float(s.iloc[-1]), float(s.iloc[-2])
                return {"이름": name, "티커": yt, "기준일": d, "종가": round(c, 4),
                        "전일종가": round(p, 4), "등락률(%)": round((c / p - 1) * 100, 2), "출처": src}
        except Exception as e:  # 다음 출처로
            err = f"{src}: {e}"
    return {"이름": name, "티커": yt, "기준일": None, "종가": None, "전일종가": None, "등락률(%)": None,
            "출처": "실패", "오류": err}


def main():
    rows = [row(*it) for it in ITEMS]
    out = {"생성시각(KST)": datetime.now(KST).strftime("%Y-%m-%d %H:%M"), "시세": rows}
    with open("data/prices.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    pd.DataFrame(rows).to_csv("data/prices.csv", index=False, encoding="utf-8-sig")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
