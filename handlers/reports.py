from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from db.base import async_session_factory
from db import crud
from services.forwarder import format_amount

router = Router(name="reports_router")


def build_report_text(stats: dict) -> str:
    period_names = {
        "day": "Bugungi (24 soatlik)",
        "week": "Haftalik (7 kunlik)",
        "month": "Oylik (30 kunlik)"
    }
    period_title = period_names.get(stats["period"], stats["period"])

    inflow_str = ""
    if stats["inflow"]:
        for cur, amt in stats["inflow"].items():
            inflow_str += f"  • +{format_amount(amt, cur)}\n"
    else:
        inflow_str = "  • 0 UZS\n"

    outflow_str = ""
    if stats["outflow"]:
        for cur, amt in stats["outflow"].items():
            outflow_str += f"  • -{format_amount(amt, cur)}\n"
    else:
        outflow_str = "  • 0 UZS\n"

    text = (
        f"📊 <b>Tranzaksiyalar hisoboti: {period_title}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━\n\n"
        f"🟢 <b>Kirimlar ({stats['inflow_count']} ta):</b>\n{inflow_str}\n"
        f"🔴 <b>Chiqimlar ({stats['outflow_count']} ta):</b>\n{outflow_str}\n"
        f"❓ <b>Aniqlanmagan xabarlar:</b> {stats['unparsed_count']} ta\n"
        f"━━━━━━━━━━━━━━━━━━━\n"
        f"<i>Hisobot faqat faol tranzaksiyalar bo'yicha tuzildi.</i>"
    )
    return text


def get_report_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Kun", callback_data="report_day"),
                InlineKeyboardButton(text="🗓 Hafta", callback_data="report_week"),
                InlineKeyboardButton(text="📆 Oy", callback_data="report_month"),
            ]
        ]
    )


@router.message(Command("hisobot"))
@router.message(F.text.in_({"📈 Hisobot", "📈 Hisobotlar"}))
async def cmd_report(message: Message):
    user_id = message.from_user.id
    async with async_session_factory() as session:
        stats = await crud.get_report_stats(session, user_id, period="day")

    text = build_report_text(stats)
    await message.answer(text, reply_markup=get_report_kb(), parse_mode="HTML")


@router.callback_query(F.data == "menu_reports")
async def on_menu_reports(callback: CallbackQuery):
    user_id = callback.from_user.id
    async with async_session_factory() as session:
        stats = await crud.get_user_transaction_stats(session, user_id, period="day")
    text = build_report_text(stats)
    await callback.message.answer(text, reply_markup=get_report_kb(), parse_mode="HTML")
    await callback.answer()


@router.callback_query(F.data.startswith("report_"))
async def on_report_period_change(callback: CallbackQuery):
    period = callback.data.split("_")[1]
    user_id = callback.from_user.id

    async with async_session_factory() as session:
        stats = await crud.get_report_stats(session, user_id, period=period)

    text = build_report_text(stats)
    await callback.message.edit_text(text, reply_markup=get_report_kb(), parse_mode="HTML")
    await callback.answer()
