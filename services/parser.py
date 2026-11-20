from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import List, Optional
from db.models import TransactionType


@dataclass
class ParsedTransaction:
    is_parsed: bool
    tx_type: Optional[TransactionType] = None
    amount: float = 0.0
    currency: str = "UZS"
    vendor: Optional[str] = None
    parsed_at: Optional[datetime] = None


def clean_number(num_str: str) -> float:
    """
    Raqam matnini tozalash (bo'sh joylar, vergullarni nuqtaga aylantirish).
    Masalan: '150 000,00' -> 150000.0, '1,250.50' -> 1250.5
    """
    cleaned = num_str.replace(" ", "").replace(" ", "")  # oddiy va no-break space
    if "," in cleaned and "." in cleaned:
        # Masalan 1,500.00 yoki 1.500,00
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    return float(cleaned)


class TransactionParserProfile:
    """Baza profili"""
    def parse(self, text: str) -> Optional[ParsedTransaction]:
        raise NotImplementedError


class PaymeProfile(TransactionParserProfile):
    """
    Payme bildirishnomalari uchun profil:
    Misol:
    "To'lov: 45 000 UZS. Korzinka.uz"
    "Qabul qilindi: +150 000 UZS. O'tkazma"
    """
    INFLOW_PATTERN = re.compile(
        r"(?:qabul\s+qilindi|to'ldirildi|kirim|popolnenie|zachislenie)[:\s]+(?:\+)?([\d\s.,]+)\s*(uzs|so['`ʼ]m|usd|rub)",
        re.IGNORECASE
    )
    OUTFLOW_PATTERN = re.compile(
        r"(?:to'lov|chiqim|oplata|spisanie)[:\s]+(?:-)?([\d\s.,]+)\s*(uzs|so['`ʼ]m|usd|rub)",
        re.IGNORECASE
    )

    def parse(self, text: str) -> Optional[ParsedTransaction]:
        # Kirim tekshirish
        inflow_match = self.INFLOW_PATTERN.search(text)
        if inflow_match:
            amount = clean_number(inflow_match.group(1))
            currency = inflow_match.group(2).upper()
            if "SO" in currency:
                currency = "UZS"
            return ParsedTransaction(
                is_parsed=True,
                tx_type=TransactionType.INFLOW,
                amount=amount,
                currency=currency,
                vendor="Payme",
                parsed_at=datetime.now(timezone.utc)
            )

        # Chiqim tekshirish
        outflow_match = self.OUTFLOW_PATTERN.search(text)
        if outflow_match:
            amount = clean_number(outflow_match.group(1))
            currency = outflow_match.group(2).upper()
            if "SO" in currency:
                currency = "UZS"
            return ParsedTransaction(
                is_parsed=True,
                tx_type=TransactionType.OUTFLOW,
                amount=amount,
                currency=currency,
                vendor="Payme",
                parsed_at=datetime.now(timezone.utc)
            )

        return None


class ClickProfile(TransactionParserProfile):
    """
    Click bildirishnomalari uchun profil:
    Misol:
    "CLICK: Oplata 50 000 UZS uspeshno. Dostavka"
    "CLICK: Popolnenie karty *1234 na 100 000 UZS"
    """
    CLICK_INFLOW = re.compile(
        r"click.*?(?:popolnenie|zachislenie|qabul).*?(?:na\s+)?(?:\+)?([\d\s.,]+)\s*(uzs|so['`ʼ]m|usd)",
        re.IGNORECASE
    )
    CLICK_OUTFLOW = re.compile(
        r"click.*?(?:oplata|perevod|spisanie|to'lov).*?(?:na\s+)?(?:-)?([\d\s.,]+)\s*(uzs|so['`ʼ]m|usd)",
        re.IGNORECASE
    )

    def parse(self, text: str) -> Optional[ParsedTransaction]:
        match = self.CLICK_INFLOW.search(text)
        if match:
            amount = clean_number(match.group(1))
            return ParsedTransaction(
                is_parsed=True,
                tx_type=TransactionType.INFLOW,
                amount=amount,
                currency="UZS",
                vendor="Click",
                parsed_at=datetime.now(timezone.utc)
            )
        match = self.CLICK_OUTFLOW.search(text)
        if match:
            amount = clean_number(match.group(1))
            return ParsedTransaction(
                is_parsed=True,
                tx_type=TransactionType.OUTFLOW,
                amount=amount,
                currency="UZS",
                vendor="Click",
                parsed_at=datetime.now(timezone.utc)
            )
        return None


class UzumProfile(TransactionParserProfile):
    """
    Uzum Bank bildirishnomalari uchun profil:
    Misol:
    "Uzum Bank: Kiruvchi o'tkazma +250 000 UZS"
    "Uzum Bank: Xarid uchun to'lov 35 000 UZS"
    """
    UZUM_INFLOW = re.compile(
        r"uzum.*?(?:kiruvchi|kirim|popolnenie).*?(?:\+)?([\d\s.,]+)\s*(uzs|so['`ʼ]m)",
        re.IGNORECASE
    )
    UZUM_OUTFLOW = re.compile(
        r"uzum.*?(?:xarid|to'lov|chiqim|oplata).*?(?:-)?([\d\s.,]+)\s*(uzs|so['`ʼ]m)",
        re.IGNORECASE
    )

    def parse(self, text: str) -> Optional[ParsedTransaction]:
        match = self.UZUM_INFLOW.search(text)
        if match:
            amount = clean_number(match.group(1))
            return ParsedTransaction(
                is_parsed=True,
                tx_type=TransactionType.INFLOW,
                amount=amount,
                currency="UZS",
                vendor="Uzum",
                parsed_at=datetime.now(timezone.utc)
            )
        match = self.UZUM_OUTFLOW.search(text)
        if match:
            amount = clean_number(match.group(1))
            return ParsedTransaction(
                is_parsed=True,
                tx_type=TransactionType.OUTFLOW,
                amount=amount,
                currency="UZS",
                vendor="Uzum",
                parsed_at=datetime.now(timezone.utc)
            )
        return None


class GenericBankSMSProfile(TransactionParserProfile):
    """
    Umumiy bank SMS va bot xabarlari:
    - Belgili format: +100 000 UZS yoki -50 000 UZS
    - Standart bank so'zlari: Popolnenie, Oplata, Perevod, Zachislenie, To'lov, Kirim
    """
    SIGN_INFLOW = re.compile(r"\+\s*([\d\s.,]{3,})\s*(uzs|so['`ʼ]m|usd|eur|rub)", re.IGNORECASE)
    SIGN_OUTFLOW = re.compile(r"-\s*([\d\s.,]{3,})\s*(uzs|so['`ʼ]m|usd|eur|rub)", re.IGNORECASE)

    KEYWORDS_INFLOW = re.compile(
        r"(?:popolnenie|zachisleno|postuplenie|qabul\s+qilindi|to'ldirildi|kirim).*?([\d\s.,]{3,})\s*(uzs|so['`ʼ]m|usd|eur|rub)",
        re.IGNORECASE
    )
    KEYWORDS_OUTFLOW = re.compile(
        r"(?:oplata|spisanie|perevod|pokupka|to'lov|chiqim).*?([\d\s.,]{3,})\s*(uzs|so['`ʼ]m|usd|eur|rub)",
        re.IGNORECASE
    )

    def parse(self, text: str) -> Optional[ParsedTransaction]:
        # 1. Belgilarga qarab tekshirish (+ / -)
        match = self.SIGN_INFLOW.search(text)
        if match:
            amount = clean_number(match.group(1))
            currency = self._norm_currency(match.group(2))
            return ParsedTransaction(
                is_parsed=True,
                tx_type=TransactionType.INFLOW,
                amount=amount,
                currency=currency,
                vendor="Bank/SMS",
                parsed_at=datetime.now(timezone.utc)
            )

        match = self.SIGN_OUTFLOW.search(text)
        if match:
            amount = clean_number(match.group(1))
            currency = self._norm_currency(match.group(2))
            return ParsedTransaction(
                is_parsed=True,
                tx_type=TransactionType.OUTFLOW,
                amount=amount,
                currency=currency,
                vendor="Bank/SMS",
                parsed_at=datetime.now(timezone.utc)
            )

        # 2. Kalit so'zlarga qarab tekshirish
        match = self.KEYWORDS_INFLOW.search(text)
        if match:
            amount = clean_number(match.group(1))
            currency = self._norm_currency(match.group(2))
            return ParsedTransaction(
                is_parsed=True,
                tx_type=TransactionType.INFLOW,
                amount=amount,
                currency=currency,
                vendor="Bank/SMS",
                parsed_at=datetime.now(timezone.utc)
            )

        match = self.KEYWORDS_OUTFLOW.search(text)
        if match:
            amount = clean_number(match.group(1))
            currency = self._norm_currency(match.group(2))
            return ParsedTransaction(
                is_parsed=True,
                tx_type=TransactionType.OUTFLOW,
                amount=amount,
                currency=currency,
                vendor="Bank/SMS",
                parsed_at=datetime.now(timezone.utc)
            )

        return None

    def _norm_currency(self, cur_str: str) -> str:
        cur = cur_str.upper()
        if "SO" in cur:
            return "UZS"
        return cur


class MasterTransactionParser:
    """
    Barcha profillarni birlashtiruvchi master parser.
    Xabarni tartib bilan profillardan o'tkazadi.
    Agar hech qaysi profil mos kelmasa, is_parsed=False qaytaradi.
    """
    def __init__(self, profiles: Optional[List[TransactionParserProfile]] = None):
        if profiles is None:
            self.profiles = [
                PaymeProfile(),
                ClickProfile(),
                UzumProfile(),
                GenericBankSMSProfile(),
            ]
        else:
            self.profiles = profiles

    def add_profile(self, profile: TransactionParserProfile):
        self.profiles.append(profile)

    def parse(self, text: Optional[str]) -> ParsedTransaction:
        if not text:
            return ParsedTransaction(is_parsed=False)

        for profile in self.profiles:
            try:
                res = profile.parse(text)
                if res and res.is_parsed and res.amount > 0:
                    return res
            except Exception:
                continue

        return ParsedTransaction(is_parsed=False)


# Standart master parser instansi
parser = MasterTransactionParser()
