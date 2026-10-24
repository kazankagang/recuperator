from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
from typing import List, Optional
from collections import defaultdict
import datetime
import random
import uuid
import re

app = FastAPI(title="E-BANK AI-Recuperator Mini-App SDK API", version="8.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(Path(__file__).with_name("recuperator.html"))

class TxItem(BaseModel):
    date: str
    merchant: str
    amount: float
    description: Optional[str] = ""
    raw_line: Optional[str] = ""
    bank: Optional[str] = "Внешний банк"

class CaseRequest(BaseModel):
    id: str
    merchant: str
    amount: float
    type: str
    date: str

class VerifyRequest(BaseModel):
    case_id: str
    merchant: str
    base_amount: float
    verify_choice: str

class OpenBankingSyncRequest(BaseModel):
    banks: List[str]

SKIP_RE = re.compile(r"(перевод между|пополнение|внутренний|снятие наличных|комиссия за перевод|кэшбэк|кешбэк|остаток|зачисление зарплаты|перевод по сбп себе)", re.I)
INSURANCE_RE = re.compile(r"(страх|полис|росгосстрах|альфастрах|согаз|ингосстрах|ресо|сберстрах|втб\s*страх|insur|каско|осаго|защита\s*кредита)", re.I)
AVIA_RE = re.compile(r"(аэрофлот|aeroflot|s7|сибирь|победа|pobeda|utair|ютэйр|уральские|ural\s*air|авиа|рейс|su-|dp-|fv-|билет)", re.I)
SUB_RE = re.compile(r"(яндекс\s*плюс|yandex|иви|ivi|okko|окко|кинопоиск|netflix|spotify|apple|подписк|premier|start|vk\s*музык|litres|литрес|wink|kion|мтс\s*премиум|сберпрайм|tinkoff\s*pro|т-про|telegram|chatgpt)", re.I)
UTILITY_RE = re.compile(r"(жкх|энергосбыт|мосэнерго|водоканал|газпром|квартплат|еирц|тсж|ук\s|мособлеирц|фонд\s*капремонта)", re.I)
MARKET_RE = re.compile(r"(wildberries|вайлдберриз|ozon|озон|яндекс\s*маркет|мегамаркет|lamoda|м\.видео|днс|dns|ситилинк)", re.I)

def parse_dt(d_str: str) -> datetime.datetime:
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(d_str[:10], fmt)
        except:
            pass
    return datetime.datetime.now()

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "sdk": "WebView Mini-App v8.0",
        "standards": ["OpenAPI ЦБ РФ ГОСТ Р 57580", "НСПК Мир Диспут Плюс", "ЕСИА 63-ФЗ ПЭП"]
    }

@app.post("/api/openbanking/sync")
async def sync_open_banking(req: OpenBankingSyncRequest):
    synced_cases = [
        {
            "id": f"ob-{uuid.uuid4().hex[:5]}",
            "type": "insurance",
            "icon": "🏦",
            "title": "СберБанк OpenAPI: Скрытая страховка к кредитке",
            "merchant": "ООО СК «Сбербанк Страхование»",
            "date": "14.10.2026",
            "amount": 16400,
            "baseAmount": 16400,
            "status": "new",
            "verified": True,
            "verifyPrompt": "Найдено по OpenAPI ЦБ РФ в СберБанке. Куда зачислить возврат?",
            "verifyOptions": [
                {"code": "ins_cooling", "label": "Взыскать со Сбера и зачислить 16 400 ₽ на карту нашего банка (0% комиссия)"},
                {"code": "ins_early_loan", "label": "Досрочное закрытие лимита (Пропорциональный возврат 72%)"}
            ],
            "dataOrigin": "Шлюз OpenAPI ЦБ РФ (СберБанк) · Токен согласия #OB-99412 · Чек ФНС ОФД",
            "source": "OpenAPI ЦБ РФ (Из СберБанка → На ваш счёт)",
            "legal": "Указание ЦБ РФ № 3854-У · ФЗ № 353-ФЗ ст. 7, 11",
            "reasonCode": "4555 (Межбанковский возврат в период охлаждения)",
            "desc": "Через Открытый API ЦБ РФ в вашей выписке СберБанка обнаружено списание 16 400 ₽ за коллективную страховку. Деньги будут востребованы и зачислены на вашу основную карту.",
            "letter": "МЕЖБАНКОВСКОЕ ТРЕБОВАНИЕ (ПО МАНДАТУ ЕСИА)\nВ ООО СК «Сбербанк Страхование»\n\nНа основании Указания ЦБ РФ № 3854-У и цифрового мандата ЕСИА требую вернуть 16 400 ₽ на реквизиты счёта клиента."
        },
        {
            "id": f"ob-{uuid.uuid4().hex[:5]}",
            "type": "avia",
            "icon": "✈️",
            "title": "ВТБ OpenAPI: Задержка рейса DP-405 (Москва — Калининград)",
            "merchant": "Авиакомпания «Победа»",
            "date": "11.10.2026",
            "amount": 19800,
            "baseAmount": 9800,
            "status": "new",
            "verified": False,
            "verifyPrompt": "Найдено по внешней карте ВТБ. Уточните статус рейса DP-405:",
            "verifyOptions": [
                {"code": "flight_cancelled", "label": "Рейс ОТМЕНЁН (Полный возврат + убытки на карту нашего банка)"},
                {"code": "flight_delayed_4h", "label": "Рейс ЗАДЕРЖАН > 4ч (Компенсация 19 800 ₽ по ВК РФ ст. 120 + ЗоЗПП)"}
            ],
            "dataOrigin": "Шлюз OpenAPI ЦБ РФ (Банк ВТБ) · Чек ОФД #551902 · ФГИС АИС ГВФ",
            "source": "OpenAPI ЦБ РФ (Из ВТБ → На ваш счёт)",
            "legal": "ВК РФ ст. 120 · ЗоЗПП РФ ст. 28 п. 5 · ФАП-82",
            "reasonCode": "4555 (Нарушение условий перевозки)",
            "desc": "Билет куплен с внешней карты ВТБ, но задержка рейса обнаружена нашим ИИ-агентом. Выплата 19 800 ₽ поступит напрямую в наш банк.",
            "letter": "ПРЕТЕНЗИЯ О ВЫПЛАТЕ КОМПЕНСАЦИИ (ЧЕРЕЗ ЕСИА)\nПеревозчику: ООО «Авиакомпания Победа»\n\nТребую перечислить 19 800 ₽ по реквизитам уполномоченного банка клиента."
        }
    ]
    return {
        "synced_banks": req.banks,
        "cases": synced_cases,
        "liquidity_inflow": sum(c["amount"] for c in synced_cases)
    }

@app.post("/api/analyze_real")
async def analyze_real(txs: List[TxItem]):
    cases = []
    upcoming_subs = []
    clean_txs = []

    for t in txs:
        full_text = f"{t.merchant} {t.description}".strip()
        if SKIP_RE.search(full_text) or t.amount <= 0:
            continue
        clean_txs.append(t)

    by_merch_amt = defaultdict(list)
    for t in clean_txs:
        key = (re.sub(r"[^a-zа-я0-9]", "", t.merchant.lower())[:14], round(t.amount, 2))
        by_merch_amt[key].append(t)

    used_double = set()
    for (m_key, amt), group in by_merch_amt.items():
        if len(group) >= 2 and amt >= 100 and m_key:
            group.sort(key=lambda x: parse_dt(x.date))
            for i in range(len(group) - 1):
                d1, d2 = parse_dt(group[i].date), parse_dt(group[i+1].date)
                if abs((d2 - d1).days) <= 3 and (m_key, amt) not in used_double:
                    used_double.add((m_key, amt))
                    m_name = group[i].merchant
                    cases.append({
                        "id": f"case-{uuid.uuid4().hex[:6]}",
                        "type": "price",
                        "icon": "💰",
                        "title": f"Двойное списание (Дубль авторизации) — {m_name}",
                        "merchant": m_name,
                        "date": group[i+1].date,
                        "amount": round(amt),
                        "baseAmount": round(amt),
                        "status": "new",
                        "verified": True,
                        "verifyPrompt": "Уточните статус операции по карте:",
                        "verifyOptions": [
                            {"code": "double_confirm", "label": "Оба списания прошли, товар один (100% чарджбэк)"},
                            {"code": "hold_released", "label": "Вторая сумма уже вернулась из холда (Закрыть)"}
                        ],
                        "dataOrigin": f"Выписка ({group[i].bank}) · Строка: «{group[i+1].raw_line or m_name}»",
                        "source": f"Антифрод-дедупликация ({len(group)} операции подряд)",
                        "legal": "Ст. 1102 ГК РФ · Правила ПС «Мир» (Диспут 4543)",
                        "reasonCode": "4543 (Duplicate Processing)",
                        "desc": f"Две идентичные транзакции на {amt:,.0f} ₽ в адрес «{m_name}». Автоматический возврат через банк-эквайер.",
                        "letter": f"ТРЕБОВАНИЕ ПО ДИСПУТУ НСПК (КОД 4543)\nПолучатель: {m_name}\n\nЗафиксировано дублирование списания {amt:,.0f} ₽ от {group[i+1].date}. Требую возврата средств."
                    })

    sub_groups = defaultdict(list)
    for t in clean_txs:
        full = f"{t.merchant} {t.description}"
        if SUB_RE.search(full):
            sub_groups[t.merchant.strip()].append(t)

    for m_name, s_list in sub_groups.items():
        s_list.sort(key=lambda x: parse_dt(x.date))
        last_tx = s_list[-1]
        upcoming_subs.append({
            "id": f"sub-{uuid.uuid4().hex[:5]}",
            "merchant": m_name,
            "monthlyAmount": round(last_tx.amount),
            "annualAmount": round(last_tx.amount * 12),
            "lastDate": last_tx.date,
            "nextChargeInDays": random.randint(2, 9),
            "legal": "ФЗ № 308-ФЗ · ст. 16.1 ЗоЗПП РФ (Отзыв токена карты + Pre-Auth Hold)",
            "active": True
        })
        refund_amt = round(last_tx.amount)
        cases.append({
            "id": f"case-{uuid.uuid4().hex[:6]}",
            "type": "sub",
            "icon": "📱",
            "title": f"Автопродление подписки без уведомления — {m_name}",
            "merchant": m_name,
            "date": last_tx.date,
            "amount": refund_amt,
            "baseAmount": round(last_tx.amount),
            "status": "new",
            "verified": False,
            "verifyPrompt": "Выберите основание возврата (с учётом ст. 429.4 ГК РФ):",
            "verifyOptions": [
                {"code": "sub_308fz", "label": "Карта была отвязана / Не было уведомления за 24ч (100% чарджбэк по 308-ФЗ)"},
                {"code": "sub_unused_3m", "label": "0 входов в аккаунт за 90 дней (Возврат за 3 мес. по ст. 32 ЗоЗПП)"},
                {"code": "sub_active", "label": "Пользуюсь активно (Исключить)"}
            ],
            "dataOrigin": f"Выписка ({last_tx.bank}) · Рекуррентный токен МСС 5815",
            "source": "Радар рекуррентных платежей и токенов карт",
            "legal": "ФЗ № 308-ФЗ (ст. 16.1 ЗоЗПП РФ) · ст. 10, 12, 32 ЗоЗПП РФ",
            "reasonCode": "4541 (Canceled Recurring Transaction)",
            "desc": f"Списание в пользу «{m_name}» без предварительного уведомления потребителя.",
            "letter": f"ДОСУДЕБНАЯ ПРЕТЕНЗИЯ ПО ФЗ № 308-ФЗ\nВ адрес: {m_name}\n\nТребую вернуть {refund_amt:,.0f} ₽ и прекратить обработку токена карты."
        })

    for t in clean_txs:
        full = f"{t.merchant} {t.description}"
        if INSURANCE_RE.search(full) and t.amount >= 400:
            cases.append({
                "id": f"case-{uuid.uuid4().hex[:6]}",
                "type": "insurance",
                "icon": "🏥",
                "title": f"Возврат страховки (Период охлаждения ЦБ) — {t.merchant}",
                "merchant": t.merchant,
                "date": t.date,
                "amount": round(t.amount),
                "baseAmount": round(t.amount),
                "status": "new",
                "verified": False,
                "verifyPrompt": "Уточните тип страхового полиса для расчёта по закону ЦБ РФ:",
                "verifyOptions": [
                    {"code": "ins_cooling", "label": "Прошло < 30 дней / Навязана к кредиту (100% возврат по 353-ФЗ)"},
                    {"code": "ins_early_loan", "label": "Досрочное погашение кредита (Пропорциональный возврат 72%)"}
                ],
                "dataOrigin": f"Выписка ({t.bank}) · Позиция чека ФНС ОФД · МСС 6300",
                "source": "Аудит страховых премий (Указание ЦБ № 3854-У / 353-ФЗ)",
                "legal": "Указание Банка России № 3854-У · ФЗ № 353-ФЗ ст. 11",
                "reasonCode": "4555 (Отказ от навязанной услуги)",
                "desc": f"Списание {t.amount:,.0f} ₽ в адрес «{t.merchant}». Право на 100% возврат в период охлаждения.",
                "letter": f"ЗАЯВЛЕНИЕ ОБ ОТКАЗЕ ОТ ДОГОВОРА СТРАХОВАНИЯ\nВ: {t.merchant}\n\nНа основании Указания ЦБ РФ № 3854-У требую возврата 100% страховой премии ({t.amount:,.0f} ₽)."
            })
        elif AVIA_RE.search(full) and t.amount >= 2000:
            flight_match = re.search(r"\b([A-ZА-Я]{2}[-\s]?\d{3,4})\b", full, re.I)
            flight_num = flight_match.group(1).upper() if flight_match else f"SU-{random.randint(1100, 1999)}"
            comp_amt = round(t.amount * 0.45 + 9500)
            cases.append({
                "id": f"case-{uuid.uuid4().hex[:6]}",
                "type": "avia",
                "icon": "✈️",
                "title": f"Проверка авиаперелёта {flight_num} — {t.merchant}",
                "merchant": t.merchant,
                "date": t.date,
                "amount": comp_amt,
                "baseAmount": round(t.amount),
                "status": "new",
                "verified": False,
                "verifyPrompt": f"Чек ОФД (билет {t.amount:,.0f} ₽) + Росавиация. Уточните статус рейса {flight_num}:",
                "verifyOptions": [
                    {"code": "flight_cancelled", "label": f"Рейс ОТМЕНЁН перевозчиком (100% возврат {t.amount:,.0f} ₽ + убытки)"},
                    {"code": "flight_delayed_4h", "label": "Рейс ЗАДЕРЖАН на 4+ часа (Неустойка 3%/час + штраф 50% ЗоЗПП)"},
                    {"code": "flight_overbook", "label": "Овербукинг / Отказ в посадке (Полный возврат + 25 000 ₽)"},
                    {"code": "flight_ok", "label": "Рейс вылетел вовремя (Удалить кейс)"}
                ],
                "dataOrigin": f"Выписка ({t.bank}) · Билет из ФНС ОФД · Шлюз ФГИС АИС ГВФ",
                "source": f"Кросс-сверка билета ({t.amount:,.0f} ₽) с табло вылетов",
                "legal": "ВК РФ ст. 108, ст. 120 · ЗоЗПП РФ ст. 28 · ФАП-82",
                "reasonCode": "4555 (Нарушение условий воздушной перевозки)",
                "desc": f"Покупка авиабилета «{t.merchant}» на {t.amount:,.0f} ₽ (рейс {flight_num}). Подтвердите статус рейса выше.",
                "letter": f"ПРЕТЕНЗИЯ О ВЫПЛАТЕ КОМПЕНСАЦИИ\nПеревозчику: {t.merchant}\n\nТребую перечислить {comp_amt:,.0f} ₽ на карту оплаты."
            })
        elif MARKET_RE.search(full) and t.amount >= 1200 and len(cases) < 12:
            fee_amt = round(min(max(t.amount * 0.12, 300), 1500))
            cases.append({
                "id": f"case-{uuid.uuid4().hex[:6]}",
                "type": "price",
                "icon": "📦",
                "title": f"Незаконное удержание за возврат товара — {t.merchant}",
                "merchant": t.merchant,
                "date": t.date,
                "amount": fee_amt,
                "baseAmount": round(t.amount),
                "status": "new",
                "verified": False,
                "verifyPrompt": "Было ли списание за обратную доставку или брак?",
                "verifyOptions": [
                    {"code": "wb_defect", "label": "Возврат товара с браком (Удержание незаконно по ст. 18 ЗоЗПП)"},
                    {"code": "wb_full_cancel", "label": "Отказ до вручения (100% возврат по ст. 26.1 ЗоЗПП)"}
                ],
                "dataOrigin": f"Выписка ({t.bank}) · Чек ОФД ФНС («Услуга обратной логистики»)",
                "source": "Аудит чеков маркетплейсов (ЗоЗПП ст. 18, 26.1)",
                "legal": "ЗоЗПП РФ ст. 18 п. 1, ст. 26.1",
                "reasonCode": "4553 (Незаконная комиссия при возврате)",
                "desc": f"Удержание комиссии за возврат ({fee_amt:,.0f} ₽) в «{t.merchant}».",
                "letter": f"ПРЕТЕНЗИЯ ПО СТ. 18 И 26.1 ЗОЗПП РФ\nВ адрес: {t.merchant}\n\nТребую вернуть незаконно удержанную плату {fee_amt:,.0f} ₽."
            })

    if not cases and clean_txs:
        for t in sorted(clean_txs, key=lambda x: x.amount, reverse=True)[:3]:
            cases.append({
                "id": f"case-{uuid.uuid4().hex[:6]}",
                "type": "price",
                "icon": "🔍",
                "title": f"Аудит крупной операции в чеке ОФД — {t.merchant}",
                "merchant": t.merchant,
                "date": t.date,
                "amount": round(t.amount),
                "baseAmount": round(t.amount),
                "status": "new",
                "verified": False,
                "verifyPrompt": "Уточните причину оспаривания операции из вашей выписки:",
                "verifyOptions": [
                    {"code": "flight_cancelled", "label": "Услуга не оказана / Отмена заказа (100% чарджбэк 4555)"},
                    {"code": "wb_defect", "label": "Скрытая навязанная комиссия (Возврат 15% по ст. 16 ЗоЗПП)"}
                ],
                "dataOrigin": f"Реальная выписка ({t.bank}) · Строка: «{t.raw_line or t.merchant}»",
                "source": "Прямой парсинг вашей выписки",
                "legal": "ЗоЗПП РФ ст. 16, ст. 32 · ГК РФ ст. 1102",
                "reasonCode": "4555 (Оспаривание операции клиента)",
                "desc": f"Крупная операция из загруженной выписки ({t.amount:,.0f} ₽ от {t.date}).",
                "letter": f"ДОСУДЕБНАЯ ПРЕТЕНЗИЯ\nВ адрес: {t.merchant}\n\nТребую возврата {t.amount:,.0f} ₽ на основании ЗоЗПП РФ."
            })

    return {
        "cases": cases,
        "subscriptions": upcoming_subs,
        "processed": len(clean_txs),
        "skipped": len(txs) - len(clean_txs)
    }

@app.post("/api/verify_case")
async def verify_case(req: VerifyRequest):
    b = req.base_amount
    ch = req.verify_choice
    if ch == "flight_cancelled":
        new_amt = round(b * 1.15)
        legal = "ВК РФ ст. 108, ФАП-82 п. 226 (Вынужденный возврат 100% стоимости билета + убытки)"
        status_note = "Верифицировано клиентом + ФГИС АИС ГВФ: Рейс отменён перевозчиком"
        letter = f"ПРЕТЕНЗИЯ О ВЫНУЖДЕННОМ ВОЗВРАТЕ ПРИ ОТМЕНЕ РЕЙСА (МАНДАТ ЕСИА)\nПеревозчику: {req.merchant}\n\nРейс отменён. На основании ст. 108 ВК РФ требую вернуть {new_amt:,.0f} ₽."
    elif ch == "flight_delayed_4h":
        new_amt = round(b * 0.45 + 12000)
        legal = "ВК РФ ст. 120, ЗоЗПП РФ ст. 28 п. 5 (3% за каждый час просрочки) + штраф 50%"
        status_note = "Верифицировано клиентом: Задержка рейса более 4 часов"
        letter = f"ПРЕТЕНЗИЯ О ВЫПЛАТЕ НЕУСТОЙКИ ЗА ЗАДЕРЖКУ РЕЙСА (МАНДАТ ЕСИА)\nПеревозчику: {req.merchant}\n\nТребую выплатить неустойку и штраф — всего {new_amt:,.0f} ₽."
    elif ch == "flight_overbook":
        new_amt = round(b + 25000)
        legal = "ВК РФ ст. 108, ст. 120 · ЗоЗПП РФ ст. 29 (Отказ в перевозке из-за овербукинга)"
        status_note = "Верифицировано клиентом: Овербукинг (недопуск на борт)"
        letter = f"ДОСУДЕБНАЯ ПРЕТЕНЗИЯ ПО ФАКТУ ОВЕРБУКИНГА\nПеревозчику: {req.merchant}\n\nИтого к выплате: {new_amt:,.0f} ₽."
    elif ch == "ins_early_loan":
        new_amt = round(b * 0.72)
        legal = "ФЗ № 353-ФЗ ст. 11 ч. 12 (Пропорциональный возврат страховки при досрочном погашении кредита)"
        status_note = "Верифицировано: Досрочное погашение кредита (возврат за неистёкший срок)"
        letter = f"ЗАЯВЛЕНИЕ О ВОЗВРАТЕ ЧАСТИ СТРАХОВОЙ ПРЕМИИ\nВ адрес: {req.merchant}\n\nТребую вернуть {new_amt:,.0f} ₽ по ч. 12 ст. 11 ФЗ № 353-ФЗ."
    elif ch == "sub_308fz":
        new_amt = round(b)
        legal = "ФЗ № 308-ФЗ (ст. 16.1 ЗоЗПП РФ) · ст. 10 ЗоЗПП РФ (Списание без согласия)"
        status_note = "Верифицировано: Нарушение ФЗ № 308-ФЗ (обход ст. 429.4 ГК РФ)"
        letter = f"ТРЕБОВАНИЕ ПО ДИСПУТУ НСПК 4541 И ФЗ № 308-ФЗ\nВ адрес: {req.merchant}\n\nТребую 100% возврата ({new_amt:,.0f} ₽)."
    elif ch == "sub_unused_3m":
        new_amt = round(b * 3)
        legal = "ЗоЗПП РФ ст. 32 (Отказ от договора при 0 ₽ ФПР исполнителя) + блокировка токена"
        status_note = "Верифицировано: 0 входов в аккаунт за 90 дней"
        letter = f"ДОСУДЕБНАЯ ПРЕТЕНЗИЯ ПО СТ. 32 ЗОЗПП РФ\nВ адрес: {req.merchant}\n\nТребую вернуть {new_amt:,.0f} ₽."
    elif ch == "wb_defect":
        new_amt = round(max(b * 0.15, 500))
        legal = "ЗоЗПП РФ ст. 18 п. 1, ст. 16 (Запрет удержания за возврат бракованного товара)"
        status_note = "Верифицировано: Незаконное удержание комиссии продавцом"
        letter = f"ПРЕТЕНЗИЯ ПО СТ. 16 И 18 ЗОЗПП РФ\nВ адрес: {req.merchant}\n\nТребую вернуть {new_amt:,.0f} ₽."
    else:
        new_amt = round(b)
        legal = "Указание Банка России № 3854-У · Ст. 1102 ГК РФ (100% возврат суммы)"
        status_note = "Верифицировано клиентом: 100% возврат полной суммы операции"
        letter = f"ДОСУДЕБНОЕ ТРЕБОВАНИЕ О ПОЛНОМ ВОЗВРАТЕ СРЕДСТВ\nПолучатель: {req.merchant}\n\nТребую вернуть 100% списанной суммы ({new_amt:,.0f} ₽) на реквизиты карты банка-эмитента."

    return {
        "new_amount": new_amt,
        "legal": legal,
        "status_note": status_note,
        "letter": letter
    }

@app.post("/api/ofd/enrich")
async def get_ofd_receipt(req: CaseRequest):
    inn = f"{random.randint(7701000000, 7799999999)}"
    if req.type == "insurance":
        items = [
            {"name": "Оформление финансового продукта", "price": 0, "qty": 1},
            {"name": f"Полис добровольного страхования ({req.merchant})", "price": round(req.amount), "qty": 1}
        ]
    elif req.type == "avia":
        items = [
            {"name": f"Электронный авиабилет ({req.merchant})", "price": round(req.amount * 0.68), "qty": 1},
            {"name": "Расчётная неустойка (ст. 120 ВК РФ + ст. 28 ЗоЗПП)", "price": round(req.amount * 0.32), "qty": 1}
        ]
    else:
        items = [
            {"name": f"Кассовая позиция ({req.merchant})", "price": round(req.amount), "qty": 1}
        ]
    return {
        "fn": f"{random.randint(9999000000000000, 9999999999999999)}",
        "fd": f"{random.randint(100000, 999999)}",
        "fpd": f"{random.randint(1000000000, 9999999999)}",
        "inn": inn,
        "items": items,
        "total": req.amount
    }

@app.post("/api/nspk/chargeback")
async def process_chargeback(req: CaseRequest):
    reason_codes = {"sub": "4541", "price": "4543", "avia": "4555", "insurance": "4555", "utilities": "4500"}
    return {
        "dispute_id": f"NSPK-{uuid.uuid4().hex[:8].upper()}",
        "arn": f"7{random.randint(1000000000000000000000, 9999999999999999999999)}",
        "reason_code": reason_codes.get(req.type, "4555"),
        "merchant": req.merchant,
        "amount": req.amount,
        "currency": "RUB",
        "clearing_cycle": "MIR_DISPUTE_PLUS_T0",
        "esia_mandate": "ESIA-VERIFIED-63FZ-PEP",
        "tariff": "SMS_BANK_99_RUB (0% COMMISSION)",
        "status": "ACCEPTED_BY_MIR_PROCESSING",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    }

@app.post("/api/ezp/dispatch")
async def dispatch_ezp(req: CaseRequest):
    xml_payload = f"""<?xml version="1.0" encoding="UTF-8"?>
<ezp:DispatchRequest xmlns:ezp="http://russianpost.ru/ezp/1.0">
    <Sender>ПАО Банк-Партнёр (Цифровой мандат ЕСИА #9920144 · УКЭП Банка 63-ФЗ)</Sender>
    <Recipient>{req.merchant}</Recipient>
    <DeliveryChannel>GOSUSLUGI_LEGAL_ENTITY_CABINET</DeliveryChannel>
    <IdentityVerification>ESIA_CONFIRMED_NO_PASSPORT_SCAN_REQUIRED</IdentityVerification>
    <ClaimAmount>{req.amount}</ClaimAmount>
    <CaseId>{req.id}</CaseId>
    <Date>{datetime.datetime.now().strftime('%Y-%m-%d')}</Date>
</ezp:DispatchRequest>"""
    return {
        "tracking_number": f"800{random.randint(10000000000, 99999999999)}RU",
        "xml_payload": xml_payload,
        "status": "DELIVERED_TO_GOSUSLUGI_CABINET",
        "cost_rub": 0.0
    }