import pytest
from db.models import TransactionType
from services.parser import MasterTransactionParser, clean_number


def test_clean_number():
    assert clean_number("150 000") == 150000.0
    assert clean_number("150 000,50") == 150000.5
    assert clean_number("1,250,000.00") == 1250000.0
    assert clean_number("25.000,00") == 25000.0


def test_payme_inflow():
    parser = MasterTransactionParser()
    text = "Karta to'ldirildi: +150 000 UZS. Manba: Click orqali o'tkazma"
    res = parser.parse(text)
    assert res.is_parsed is True
    assert res.tx_type == TransactionType.INFLOW
    assert res.amount == 150000.0
    assert res.currency == "UZS"


def test_payme_outflow():
    parser = MasterTransactionParser()
    text = "To'lov: 45 500 so'm. Korzinka supermarket"
    res = parser.parse(text)
    assert res.is_parsed is True
    assert res.tx_type == TransactionType.OUTFLOW
    assert res.amount == 45500.0
    assert res.currency == "UZS"


def test_click_messages():
    parser = MasterTransactionParser()
    inflow_text = "CLICK: Popolnenie karty *1234 na 250 000 UZS"
    res1 = parser.parse(inflow_text)
    assert res1.is_parsed is True
    assert res1.tx_type == TransactionType.INFLOW
    assert res1.amount == 250000.0

    outflow_text = "CLICK: Oplata uspeshno sovershena na 70 000 UZS"
    res2 = parser.parse(outflow_text)
    assert res2.is_parsed is True
    assert res2.tx_type == TransactionType.OUTFLOW
    assert res2.amount == 70000.0


def test_uzum_bank():
    parser = MasterTransactionParser()
    text = "Uzum Bank: Kiruvchi o'tkazma +500 000 UZS"
    res = parser.parse(text)
    assert res.is_parsed is True
    assert res.tx_type == TransactionType.INFLOW
    assert res.amount == 500000.0


def test_bank_sms_signs():
    parser = MasterTransactionParser()
    plus_text = "Karta *8899: +1 200 000 UZS. Ostatok 3 000 000 UZS"
    res1 = parser.parse(plus_text)
    assert res1.is_parsed is True
    assert res1.tx_type == TransactionType.INFLOW
    assert res1.amount == 1200000.0

    minus_text = "Karta *8899: -35 000 UZS. Oplata Yandex Go"
    res2 = parser.parse(minus_text)
    assert res2.is_parsed is True
    assert res2.tx_type == TransactionType.OUTFLOW
    assert res2.amount == 35000.0


def test_unparsed_message():
    parser = MasterTransactionParser()
    # Oddiy suhbat yoki tranzaksiyaga aloqasi bo'lmagan xabar
    text = "Salom, bugun soat 5 da uchrashamizmi?"
    res = parser.parse(text)
    assert res.is_parsed is False
    assert res.amount == 0.0
