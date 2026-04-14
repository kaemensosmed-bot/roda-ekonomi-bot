import os, re, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
import gspread
from google.oauth2.service_account import Credentials

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN  = os.getenv('TELEGRAM_TOKEN', '8513031052:AAFeCapx1ClO89x0VcrSBGQG5xXSG39n07U')
SHEET_ID        = os.getenv('SHEET_ID', '1-REFSqrOZuuAKdHDRRcL_2Z6oaOxDkDJEDVgXpg4gec')
ALLOWED_USER    = os.getenv('ALLOWED_USER_ID', '6300167136')
SHEET_TAB       = os.getenv('SHEET_TAB', 'TRANSAKSI_APRIL')
CREDS_FILE      = os.getenv('CREDS_FILE', 'credentials.json')

def get_sheet():
    creds = Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=[
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet(SHEET_TAB)

def get_saldo_sheet():
    creds = Credentials.from_service_account_file(
        CREDS_FILE,
        scopes=['https://www.googleapis.com/auth/spreadsheets']
    )
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID).worksheet('SALDO_AKUN_APRIL')

# ── KATA KUNCI ──────────────────────────────────────────────────
KEYWORDS = {
    'makan': 'Makan', 'sarapan': 'Makan', 'lunch': 'Makan', 'dinner': 'Makan',
    'nasi': 'Makan', 'bakso': 'Makan', 'ayam': 'Makan', 'pop mie': 'Makan',
    'popmie': 'Makan', 'soto': 'Makan', 'warteg': 'Makan', 'warung': 'Makan',
    'kopi': 'Jajan', 'jajan': 'Jajan', 'snack': 'Jajan', 'es': 'Jajan',
    'boba': 'Jajan', 'basreng': 'Jajan', 'lok lok': 'Jajan', 'loklok': 'Jajan',
    'minuman': 'Jajan', 'ice cream': 'Jajan', 'es krim': 'Jajan',
    'rokok': 'Rokok/Vape', 'vape': 'Rokok/Vape', 'liquid': 'Rokok/Vape', 'magnum': 'Rokok/Vape',
    'laundry': 'Kebutuhan', 'bensin': 'Kebutuhan', 'cukur': 'Kebutuhan',
    'potong rambut': 'Kebutuhan', 'belanja': 'Kebutuhan', 'cartridge': 'Kebutuhan',
    'wifi': 'Kebutuhan', 'listrik': 'Kebutuhan', 'air': 'Kebutuhan',
    'grab': 'Transport', 'ojek': 'Transport', 'parkir': 'Transport',
    'netflix': 'Langganan', 'claude': 'Langganan', 'icloud': 'Langganan',
    'spotify': 'Langganan', 'langganan': 'Langganan', 'website': 'Langganan',
    'sauna': 'Hiburan', 'mall': 'Hiburan', 'nonton': 'Hiburan',
    'mencari kemenangan': 'Hiburan', 'game': 'Hiburan',
    'traktir': 'Sosial', 'patungan': 'Sosial', 'ptpt': 'Sosial', 'sumbangan': 'Sosial',
    'topup': 'Top Up', 'top up': 'Top Up', 'gopay': 'Top Up', 'dana': 'Top Up', 'ovo': 'Top Up',
    'transfer': 'Transfer', 'kirim': 'Transfer',
    'cicilan': 'Bayar Utang', 'bayar hutang': 'Bayar Utang', 'bri': 'Bayar Utang',
    'nalangin': 'Talangan', 'talangan': 'Talangan', 'nitip': 'Talangan', 'nalangi': 'Talangan',
    'pinjam': 'Piutang', 'kasih pinjam': 'Piutang', 'minjemin': 'Piutang',
    'pulsa': 'Pulsa', 'kuota': 'Pulsa',
    'donasi': 'Donasi', 'sawer': 'Donasi',
    'bayar wifi': 'Rumah', 'sewa': 'Rumah', 'kontrakan': 'Rumah',
    # Masuk
    'gaji': 'Gajian', 'gajian': 'Gajian',
    'uang makan': 'Uang Makan', 'um masuk': 'Uang Makan',
    'balik': 'Cashflow', 'bayar balik': 'Cashflow', 'balikin': 'Cashflow',
    'wd': 'WD Trading', 'withdraw': 'WD Trading',
    'profit': 'Hasil Trading', 'trading': 'Hasil Trading',
}

AKUN_MAP = {
    'aba': 'ABA',
    'bca ops': 'BCA Operasional', 'bca operasional': 'BCA Operasional',
    'bca tab': 'BCA Tabungan', 'bca tabungan': 'BCA Tabungan',
    'bca': 'BCA Operasional',
    'cash': 'Cash',
    'mexc': 'MEXC',
    'titipan': 'Titipan',
}

MASUK_KEYWORDS = [
    'gaji', 'gajian', 'uang makan', 'balik', 'bayar balik', 'balikin',
    'wd', 'withdraw', 'profit', 'trading', 'masuk', 'terima', 'dapat',
    'kemenangan', 'bayar ke saya', 'transfer masuk'
]

def detect_category(text):
    t = text.lower()
    for kw in sorted(KEYWORDS.keys(), key=len, reverse=True):
        if kw in t:
            return KEYWORDS[kw]
    return 'Lainnya'

def detect_akun(text):
    t = text.lower()
    for kw in sorted(AKUN_MAP.keys(), key=lambda x: len(x), reverse=True):
        if kw in t:
            return AKUN_MAP[kw]
    return 'Cash'

def detect_currency(text):
    t = text.lower()
    if 'usd' in t or '$' in t: return 'USD'
    if 'idr' in t or 'rp' in t or 'rupiah' in t: return 'IDR'
    if 'khr' in t: return 'KHR'
    # Tebak dari akun
    akun = detect_akun(text)
    if akun == 'ABA': return 'USD'
    if akun in ['BCA Operasional', 'BCA Tabungan']: return 'IDR'
    return 'KHR'

def detect_nominal(text):
    # Hapus titik ribuan: 3.000 → 3000
    t = re.sub(r'(\d)\.(\d{3})(?!\d)', r'\1\2', text)
    t = t.replace(',', '.')
    nums = re.findall(r'\d+(?:\.\d+)?', t)
    if nums:
        return max(float(n) for n in nums)
    return 0

def detect_jenis(text):
    t = text.lower()
    if t.startswith('keluar') or t.startswith('out'): return 'Keluar'
    if t.startswith('masuk') or t.startswith('in'): return 'Masuk'
    if any(kw in t for kw in MASUK_KEYWORDS): return 'Masuk'
    return 'Keluar'

def parse_transaction(text, timestamp):
    text_clean = text.strip()
    # Hapus prefix keluar/masuk dari keterangan
    ket = re.sub(r'^(keluar|masuk)[,\s]*', '', text_clean, flags=re.IGNORECASE).strip()
    # Hapus "bayar pake", "pake", "via", nominal, currency, akun dari keterangan
    ket_clean = ket
    ket_clean = re.sub(r'\b\d[\d.,]*\b', '', ket_clean)
    ket_clean = re.sub(r'\b(khr|usd|idr|rp|rupiah)\b', '', ket_clean, flags=re.IGNORECASE)
    ket_clean = re.sub(r'\b(aba|bca ops|bca tab|bca|cash|mexc)\b', '', ket_clean, flags=re.IGNORECASE)
    ket_clean = re.sub(r'\b(bayar pake|pake|via|voucher\s*\+?|ke|dari)\b', '', ket_clean, flags=re.IGNORECASE)
    ket_clean = re.sub(r'\s+', ' ', ket_clean).strip().strip(',+').strip()

    return {
        'tanggal': timestamp.strftime('%-d %b %Y'),
        'jam': timestamp.strftime('%H:%M'),
        'jenis': detect_jenis(text_clean),
        'kategori': detect_category(text_clean),
        'keterangan': ket_clean or ket[:40],
        'nominal': detect_nominal(text_clean),
        'currency': detect_currency(text_clean),
        'akun': detect_akun(text_clean),
        'raw': text_clean,
    }

def format_preview(tx):
    emoji = '💸' if tx['jenis'] == 'Keluar' else '💰'
    nom = int(tx['nominal']) if tx['nominal'] == int(tx['nominal']) else tx['nominal']
    return (
        f"{emoji} *{tx['jenis']}* | _{tx['kategori']}_\n"
        f"📝 {tx['keterangan']}\n"
        f"💵 `{nom:,} {tx['currency']}` via *{tx['akun']}*\n"
        f"📅 {tx['tanggal']} {tx['jam']}\n"
    )

def write_to_sheet(tx):
    ws = get_sheet()
    all_vals = ws.col_values(1)
    next_row = len(all_vals) + 1
    nom = int(tx['nominal']) if tx['nominal'] == int(tx['nominal']) else tx['nominal']
    ws.update(
        f'A{next_row}:I{next_row}',
        [[
            tx['tanggal'],
            tx['jenis'],
            tx['kategori'],
            tx['keterangan'],
            nom,
            tx['currency'],
            tx['akun'],
            f"via bot {tx['jam']}",
            ''
        ]]
    )
    return next_row

# ── PENDING STATE ────────────────────────────────────────────────
pending = {}

# ── HANDLERS ────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = (
        "👋 *Roda Ekonomi Bot*\n\n"
        "Catat transaksi langsung dari sini.\n\n"
        "*Format:*\n"
        "`keluar, makan pagi 15000 KHR cash`\n"
        "`keluar, beli kopi 5000 KHR ABA`\n"
        "`keluar, nalangin mas candra kopi 4000 KHR ABA`\n"
        "`masuk, gajian 9100000 IDR BCA`\n\n"
        "*Commands:*\n"
        "/saldo — cek saldo semua akun\n"
        "/rekap — rekap pengeluaran hari ini\n"
        "/help — panduan lengkap"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = (
        "📖 *Panduan Bot*\n\n"
        "*Kata kunci Keluar (otomatis):*\n"
        "makan, kopi, jajan, rokok, laundry, grab, wifi, netflix, nalangin, talangan, cicilan, transfer, topup...\n\n"
        "*Kata kunci Masuk (otomatis):*\n"
        "gaji, uang makan, balik, bayar balik, wd, profit, trading...\n\n"
        "*Akun yang dikenali:*\n"
        "ABA, BCA / BCA Ops, BCA Tab, Cash, MEXC\n\n"
        "*Mata Uang:*\n"
        "KHR, USD / $, IDR / Rp\n\n"
        "*Contoh pesan:*\n"
        "`keluar, makan pagi 15000 KHR cash`\n"
        "`keluar, beli kopi bayar pake ABA 5000 KHR`\n"
        "`keluar, nalangin mas candra mouse 21.5 USD ABA`\n"
        "`masuk, uang makan 310 USD ABA`\n"
        "`masuk, mas candra balik talangan 25000 KHR cash`"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def saldo_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != ALLOWED_USER:
        await update.message.reply_text("❌ Tidak authorized.")
        return
    try:
        ws = get_saldo_sheet()
        akun_names = ['BCA Operasional', 'BCA Tabungan', 'ABA', 'Cash', 'MEXC']
        msg = "💼 *Saldo Terkini*\n\n"
        total_idr = 0
        for i, akun in enumerate(akun_names, 6):
            real = ws.cell(i, 6).value or '0'
            cur  = ws.cell(i, 8).value or ''
            sistem = ws.cell(i, 5).value or '0'
            selisih = ws.cell(i, 7).value or '0'
            try:
                sel = float(str(selisih).replace(',',''))
                bal = "✓" if abs(sel) < 0.1 else f"⚠ {sel:+.2f}"
            except:
                bal = "?"
            msg += f"• *{akun}*: `{real} {cur}` {bal}\n"
        msg += "\n_Kiri = Real | ⚠ = ada selisih_"
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def rekap_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != ALLOWED_USER:
        await update.message.reply_text("❌ Tidak authorized.")
        return
    try:
        ws = get_sheet()
        today = datetime.now().strftime('%-d %b %Y')
        all_rows = ws.get_all_values()
        total_keluar = 0; total_masuk = 0
        detail = []
        for row in all_rows[2:]:
            if not row[0]: continue
            if row[0] == today:
                try:
                    nom = float(str(row[4]).replace(',',''))
                    cur = row[5]; via = row[6]; ket = row[3]; jenis = row[1]
                    usd = nom if cur=='USD' else nom/17000 if cur=='IDR' else nom/4000
                    if jenis == 'Keluar':
                        total_keluar += usd
                        detail.append(f"  💸 {ket[:20]} {nom:,.0f} {cur}")
                    elif jenis == 'Masuk':
                        total_masuk += usd
                        detail.append(f"  💰 {ket[:20]} {nom:,.0f} {cur}")
                except:
                    pass
        msg = f"📊 *Rekap {today}*\n\n"
        if detail:
            msg += "\n".join(detail[:10])
            if len(detail) > 10:
                msg += f"\n  ...+{len(detail)-10} lagi"
            msg += f"\n\n💸 Total keluar: `${total_keluar:.2f}`"
            msg += f"\n💰 Total masuk: `${total_masuk:.2f}`"
            msg += f"\n📈 Net: `${total_masuk-total_keluar:.2f}`"
        else:
            msg += "Belum ada transaksi hari ini."
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data == 'confirm' and user_id in pending:
        tx = pending.pop(user_id)
        try:
            row = write_to_sheet(tx)
            nom = int(tx['nominal']) if tx['nominal'] == int(tx['nominal']) else tx['nominal']
            await query.edit_message_text(
                f"✅ *Tercatat!* (baris {row})\n\n"
                f"{format_preview(tx)}",
                parse_mode='Markdown'
            )
        except Exception as e:
            await query.edit_message_text(f"❌ Gagal catat: {e}")

    elif data == 'cancel':
        pending.pop(user_id, None)
        await query.edit_message_text("❌ *Dibatalkan.*", parse_mode='Markdown')

async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id != ALLOWED_USER:
        await update.message.reply_text("❌ Tidak authorized.")
        return

    text = update.message.text.strip()
    timestamp = update.message.date

    # Deteksi apakah ini transaksi
    t = text.lower()
    is_tx = (
        t.startswith('keluar') or t.startswith('masuk') or
        any(kw in t for kw in [
            'makan','kopi','jajan','rokok','laundry','grab','wifi','gaji',
            'uang makan','nalangin','talangan','cicilan','bayar','beli',
            'transfer','topup','top up','wd','profit','balik','nitip'
        ])
    )

    if not is_tx:
        await update.message.reply_text(
            "❓ Tidak dikenali. Coba format:\n"
            "`keluar, makan pagi 15000 KHR cash`\n\n"
            "Atau ketik /help untuk panduan lengkap.",
            parse_mode='Markdown'
        )
        return

    tx = parse_transaction(text, timestamp)
    if tx['nominal'] == 0:
        await update.message.reply_text(
            "⚠️ *Nominal tidak ditemukan.*\n"
            "Pastikan ada angka di pesan. Contoh:\n"
            "`keluar, makan pagi 15000 KHR cash`",
            parse_mode='Markdown'
        )
        return

    pending[user_id] = tx

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Catat", callback_data='confirm'),
            InlineKeyboardButton("❌ Batal", callback_data='cancel'),
        ]
    ])

    await update.message.reply_text(
        f"*Konfirmasi transaksi:*\n\n{format_preview(tx)}",
        parse_mode='Markdown',
        reply_markup=keyboard
    )

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('saldo', saldo_cmd))
    app.add_handler(CommandHandler('rekap', rekap_cmd))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
