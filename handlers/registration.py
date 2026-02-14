"""
Ro'yxatdan o'tish handlerlari
"""
import html as html_lib

from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import db
from keyboards.admin_kb import get_admin_main_menu
from keyboards.user_kb import get_user_menu, get_branches_keyboard, get_shift_keyboard, get_cancel_keyboard
from config import ADMIN_IDS, SHIFTS

router = Router()


class Registration(StatesGroup):
    first_name = State()
    last_name = State()
    branch = State()
    shift = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Start buyrug'i"""
    await state.clear()
    user_id = message.from_user.id

    # Admin tekshiruvi
    if user_id in ADMIN_IDS:
        await message.answer(
            "👨‍💼 <b>Admin paneliga xush kelibsiz!</b>\n\n"
            "Sizda tizimni to'liq boshqarish huquqi mavjud.",
            reply_markup=get_admin_main_menu(),
            parse_mode="HTML"
        )
        return

    # Ro'yxatdan o'tganligini tekshirish
    employee = await db.get_employee_by_telegram_id(user_id)

    if employee:
        await message.answer(
            f"👋 <b>Xush kelibsiz, {employee['first_name']}!</b>\n\n"
            "Quyidagi tugmalar orqali o'z vazifalaringiz va profilingizni boshqarishingiz mumkin.",
            reply_markup=get_user_menu(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "👋 <b>Assalomu alaykum!</b>\n\n"
            "Tizimdan foydalanish uchun ro'yxatdan o'ting.\n\n"
            "Iltimos, ismingizni kiriting:",
            parse_mode="HTML"
        )
        await state.set_state(Registration.first_name)


@router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext):
    """Ro'yxatdan o'tish buyrug'i"""
    user_id = message.from_user.id

    # Ro'yxatdan o'tganligini tekshirish
    employee = await db.get_employee_by_telegram_id(user_id)

    if employee:
        await message.answer(
            "✅ Siz allaqachon ro'yxatdan o'tgansiz!",
            reply_markup=get_user_menu()
        )
        return

    await message.answer(
        "📝 <b>Ro'yxatdan o'tish</b>\n\n"
        "Iltimos, ismingizni kiriting:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(Registration.first_name)


@router.message(Registration.first_name)
async def process_first_name(message: Message, state: FSMContext):
    """Ism kiritish"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ro'yxatdan o'tish bekor qilindi.")
        return

    await state.update_data(first_name=message.text.strip())
    await message.answer(
        "📝 Endi familiyangizni kiriting:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(Registration.last_name)


@router.message(Registration.last_name)
async def process_last_name(message: Message, state: FSMContext):
    """Familiya kiritish"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ro'yxatdan o'tish bekor qilindi.")
        return

    await state.update_data(last_name=message.text.strip())

    branches = await db.get_all_branches()
    if not branches:
        await message.answer(
            "❌ <b>Xatolik!</b>\n\n"
            "Hozircha filiallar mavjud emas. Admin bilan bog'laning.",
            parse_mode="HTML"
        )
        await state.clear()
        return

    await message.answer(
        "🏢 Filialni tanlang:",
        reply_markup=get_branches_keyboard(branches)
    )
    await state.set_state(Registration.branch)


@router.message(Registration.branch)
async def process_branch(message: Message, state: FSMContext):
    """Filial tanlash"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ro'yxatdan o'tish bekor qilindi.")
        return

    branches = await db.get_all_branches()
    branch = next((b for b in branches if b['name'] == message.text), None)

    if not branch:
        await message.answer(
            "❌ Noto'g'ri filial. Iltimos, ro'yxatdan tanlang.",
            reply_markup=get_branches_keyboard(branches)
        )
        return

    await state.update_data(branch_id=branch['id'], branch_name=branch['name'])
    await message.answer(
        "⏰ Smenangizni tanlang:",
        reply_markup=get_shift_keyboard()
    )
    await state.set_state(Registration.shift)


@router.message(Registration.shift)
async def process_shift(message: Message, state: FSMContext):
    """Smena tanlash va ro'yxatdan o'tishni yakunlash"""
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("❌ Ro'yxatdan o'tish bekor qilindi.")
        return

    # Smena nomini kalitga aylantirish
    shift_map = {
        "🌅 Kunduzgi smena": "kunduzgi",
        "🌙 Kechki smena": "kechki"
    }
    shift_key = shift_map.get(message.text)

    if not shift_key:
        await message.answer(
            "❌ Noto'g'ri smena. Iltimos, tugmalardan tanlang.",
            reply_markup=get_shift_keyboard()
        )
        return

    data = await state.get_data()

    try:
        await db.create_employee(
            telegram_id=message.from_user.id,
            first_name=data['first_name'],
            last_name=data['last_name'],
            branch_id=data['branch_id'],
            shift=shift_key
        )

        shift_name = SHIFTS.get(shift_key, shift_key)

        await message.answer(
            f"✅ <b>Tabriklaymiz!</b>\n\n"
            f"Siz muvaffaqiyatli ro'yxatdan o'tdingiz.\n\n"
            f"👤 <b>Ma'lumotlaringiz:</b>\n"
            f"• Ism: {data['first_name']} {data['last_name']}\n"
            f"• Filial: {data['branch_name']}\n"
            f"• Smena: {shift_name}\n\n"
            f"Endi siz vazifalarni olishingiz va bajarishingiz mumkin!",
            reply_markup=get_user_menu(),
            parse_mode="HTML"
        )

    except Exception as e:
        safe_error = html_lib.escape(str(e))
        await message.answer(
            f"❌ <b>Xatolik yuz berdi!</b>\n\n"
            f"Iltimos, qaytadan urinib ko'ring yoki "
            f"admin bilan bog'laning.\n"
            f"Xatolik: {safe_error}",
            parse_mode="HTML"
        )

    await state.clear()