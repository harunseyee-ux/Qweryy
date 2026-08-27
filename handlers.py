import os
from telebot import types
from config import bot, ADMIN_ID, REQUIRED_CHANNEL, HEADER_MENU_PHOTO, get_state, set_state, get_user_temp, set_user_temp
from database import (
    db_get_all_products, db_get_product, db_add_product, db_update_product_desc, db_delete_product,
    db_set_payment_info, db_get_payment_info, db_add_to_cart, db_get_cart, db_clear_cart,
    db_create_order, db_update_order_status, db_get_order, db_get_user_orders,
    db_register_user, db_get_stats
)

# --- NAVIGATION HELPER ---
def check_join_channel(user_id):
    if not REQUIRED_CHANNEL:
        return True
    try:
        member = bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ['creator', 'administrator', 'member']
    except Exception:
        return True

def send_main_menu(chat_id):
    caption_text = (
        "👋 **Selamat Datang di Official Store!**\n\n"
        "Silakan pilih menu di bawah ini untuk mencari produk digital atau melihat status keranjang Anda."
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛍️ Katalog", callback_data="btn_catalog"),
        types.InlineKeyboardButton("🛒 Keranjang", callback_data="btn_cart"),
        types.InlineKeyboardButton("🔍 Cari", callback_data="btn_search"),
        types.InlineKeyboardButton("📜 Riwayat Order", callback_data="btn_history"),
        types.InlineKeyboardButton("💳 Info Bayar", callback_data="btn_payment_info")
    )
    if chat_id == ADMIN_ID:
        markup.add(types.InlineKeyboardButton("⚙️ Menu Admin", callback_data="btn_admin_menu"))
    
    bot.send_photo(chat_id, photo=HEADER_MENU_PHOTO, caption=caption_text, reply_markup=markup, parse_mode="Markdown")

# --- COMMAND HANDLERS ---
def register_handlers(bot_instance):

    @bot_instance.message_handler(commands=['start'])
    def cmd_start(message):
        chat_id = message.chat.id
        db_register_user(chat_id, message.from_user.username)
        set_state(chat_id, None)
        
        if not check_join_channel(chat_id):
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL.replace('@','')}\"))
            markup.add(types.InlineKeyboardButton("✅ Sudah Join", callback_data="btn_check_join"))
            bot_instance.send_message(chat_id, f"⚠️ Anda harus bergabung ke channel {REQUIRED_CHANNEL} terlebih dahulu.", reply_markup=markup)
            return
        
        send_main_menu(chat_id)

    @bot_instance.message_handler(commands=['admin'])
    def cmd_admin(message):
        if message.chat.id != ADMIN_ID:
            bot_instance.send_message(message.chat.id, "❌ Akses Admin ditolak.")
            return
        
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("➕ Tambah Produk", callback_data="admin_add_prod"),
            types.InlineKeyboardButton("📝 Edit Deskripsi", callback_data="admin_edit_desc"),
            types.InlineKeyboardButton("🗑️ Hapus Produk", callback_data="admin_del_prod"),
            types.InlineKeyboardButton("💳 Set Payment", callback_data="admin_set_pay"),
            types.InlineKeyboardButton("📊 Statistik", callback_data="admin_stats"),
            types.InlineKeyboardButton("💾 Backup DB", callback_data="admin_backup_db")
        )
        bot_instance.send_message(message.chat.id, "🛠️ **Panel Kontrol Admin**", reply_markup=markup, parse_mode="Markdown")

    # --- CALLBACK ROUTER ---
    @bot_instance.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        chat_id = call.message.chat.id
        data = call.data
        bot_instance.answer_callback_query(call.id)

        if data == "btn_check_join":
            if check_join_channel(chat_id):
                bot_instance.delete_message(chat_id, call.message.message_id)
                send_main_menu(chat_id)
            else:
                bot_instance.send_message(chat_id, "❌ Terdeteksi belum bergabung.")

        elif data == "btn_catalog":
            products = db_get_all_products()
            if not products:
                bot_instance.send_message(chat_id, "📦 Belum ada produk tersedia.")
                return
            markup = types.InlineKeyboardMarkup()
            for p in products:
                markup.add(types.InlineKeyboardButton(f"{p['name']} - Rp{p['price']:,.0f}", callback_data=f"prod_{p['id']}"))
            bot_instance.send_message(chat_id, "🛍️ **Daftar Katalog Produk:**", reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("prod_"):
            pid = int(data.split("_")[1])
            p = db_get_product(pid)
            if p:
                text = f"📦 **{p['name']}**\n\n💰 Harga: Rp{p['price']:,.0f}\n📝 Deskripsi:\n{p['description'] or '-'}"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("➕ Tambah Keranjang", callback_data=f"cart_add_{p['id']}"))
                bot_instance.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

        elif data.startswith("cart_add_"):
            pid = int(data.split("_")[2])
            db_add_to_cart(chat_id, pid, 1)
            bot_instance.send_message(chat_id, "✅ Produk dimasukkan ke keranjang.")

        elif data == "btn_cart":
            items = db_get_cart(chat_id)
            if not items:
                bot_instance.send_message(chat_id, "🛒 Keranjang Anda kosong.")
                return
            total = 0
            text = "🛒 **Keranjang Belanja:**\n\n"
            for item in items:
                sub = item['price'] * item['quantity']
                total += sub
                text += f"• **{item['name']}** ({item['quantity']}x) = Rp{sub:,.0f}\n"
            text += f"\n💰 Total: **Rp{total:,.0f}**"

            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("💳 Checkout Sekarang", callback_data="btn_checkout"),
                types.InlineKeyboardButton("🗑️ Kosongkan", callback_data="btn_clear_cart")
            )
            bot_instance.send_message(chat_id, text, reply_markup=markup, parse_mode="Markdown")

        elif data == "btn_clear_cart":
            db_clear_cart(chat_id)
            bot_instance.send_message(chat_id, "🗑️ Keranjang telah dikosongkan.")

        elif data == "btn_checkout":
            items = db_get_cart(chat_id)
            if not items: return
            total = sum(i['price'] * i['quantity'] for i in items)
            order_id = db_create_order(chat_id, total, items)
            db_clear_cart(chat_id)
            
            set_user_temp(chat_id, 'active_order_id', order_id)
            set_state(chat_id, "WAITING_PROOF")
            
            bot_instance.send_message(
                chat_id, 
                f"✅ **Order Tagihan #{order_id} dibuat!**\n\nTotal Bayar: **Rp{total:,.0f}**\n\n"
                f"Silakan transfer sesuai detail pembayaran di menu Payment, lalu **kirimkan foto/bukti struk transfer** di sini.",
                parse_mode="Markdown"
            )

        elif data == "btn_history":
            orders = db_get_user_orders(chat_id)
            if not orders:
                bot_instance.send_message(chat_id, "📜 Anda belum memiliki histori pesanan.")
                return
            text = "📜 **Histori Transaksi Terakhir:**\n\n"
            for o in orders:
                text += f"• Order #{o['id']} | Rp{o['total_amount']:,.0f} | Status: `{o['status'].upper()}`\n"
            bot_instance.send_message(chat_id, text, parse_mode="Markdown")

        elif data == "btn_payment_info":
            dana = db_get_payment_info('dana')
            gopay = db_get_payment_info('gopay')
            qris = db_get_payment_info('qris')
            
            text = "💳 **Metode Pembayaran:**\n\n"
            text += f"🔹 **DANA:** `{dana or 'Belum diatur'}`\n"
            text += f"🔹 **GoPay:** `{gopay or 'Belum diatur'}`\n"
            bot_instance.send_message(chat_id, text, parse_mode="Markdown")
            
            if qris:
                bot_instance.send_photo(chat_id, photo=qris, caption="📲 **Scan QRIS Pembayaran**")

        elif data == "btn_search":
            set_state(chat_id, "WAITING_SEARCH")
            bot_instance.send_message(chat_id, "🔍 Ketik nama produk yang ingin dicari:")

        # --- ADMIN CALLBACKS ---
        elif data == "btn_admin_menu":
            cmd_admin(call.message)

        elif data == "admin_add_prod":
            if chat_id != ADMIN_ID: return
            set_state(chat_id, "WAITING_ADD_PROD")
            bot_instance.send_message(chat_id, "📝 Kirim data produk:\n\n`Nama | Harga | Deskripsi | KontenDigital`", parse_mode="Markdown")

        elif data == "admin_edit_desc":
            if chat_id != ADMIN_ID: return
            products = db_get_all_products()
            markup = types.InlineKeyboardMarkup()
            for p in products:
                markup.add(types.InlineKeyboardButton(f"Edit #{p['id']}: {p['name']}", callback_data=f"adm_edesc_{p['id']}"))
            bot_instance.send_message(chat_id, "📝 Pilih produk yang di-edit deskripsinya:", reply_markup=markup)

        elif data.startswith("adm_edesc_"):
            pid = int(data.split("_")[2])
            set_user_temp(chat_id, 'edit_pid', pid)
            set_state(chat_id, "WAITING_NEW_DESC")
            bot_instance.send_message(chat_id, f"📝 Masukkan deskripsi baru untuk ID #{pid}:")

        elif data == "admin_set_pay":
            if chat_id != ADMIN_ID: return
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(
                types.InlineKeyboardButton("DANA", callback_data="adm_pay_dana"),
                types.InlineKeyboardButton("GoPay", callback_data="adm_pay_gopay"),
                types.InlineKeyboardButton("QRIS", callback_data="adm_pay_qris")
            )
            bot_instance.send_message(chat_id, "💳 Pilih metode bayar yang diset:", reply_markup=markup)

        elif data in ["adm_pay_dana", "adm_pay_gopay"]:
            method = data.replace("adm_pay_", "")
            set_user_temp(chat_id, 'pay_method', method)
            set_state(chat_id, "WAITING_PAY_TEXT")
            bot_instance.send_message(chat_id, f"📥 Masukkan nomor/rekening {method.upper()}:")

        elif data == "adm_pay_qris":
            set_user_temp(chat_id, 'pay_method', 'qris')
            set_state(chat_id, "WAITING_QRIS_PHOTO")
            bot_instance.send_message(chat_id, "🖼️ Upload/kirim foto QRIS:")

        elif data == "admin_stats":
            if chat_id != ADMIN_ID: return
            u, o, r = db_get_stats()
            bot_instance.send_message(chat_id, f"📊 **Statistik Bot Store:**\n\n• Total Pengguna: {u}\n• Order Sukses: {o}\n• Omset Total: Rp{r:,.0f}", parse_mode="Markdown")

        elif data == "admin_backup_db":
            if chat_id != ADMIN_ID: return
            from config import DB_NAME
            if os.path.exists(DB_NAME):
                with open(DB_NAME, 'rb') as f:
                    bot_instance.send_document(chat_id, f, caption="💾 Database Backup")

        # --- ADMIN APPROVAL ACTIONS ---
        elif data.startswith("approve_"):
            oid = int(data.split("_")[1])
            order, items = db_get_order(oid)
            if order:
                db_update_order_status(oid, 'paid')
                bot_instance.send_message(order['user_id'], f"🎉 **Order #{oid} telah DIKONFIRMASI!**\nBerikut detail akses produk Anda:")
                for item in items:
                    p = db_get_product(item['product_id'])
                    content = p['digital_content'] if p and p['digital_content'] else "Terima kasih telah membeli!"
                    bot_instance.send_message(order['user_id'], f"📦 **{item['product_name']}**:\n`{content}`", parse_mode="Markdown")
                bot_instance.send_message(ADMIN_ID, f"✅ Order #{oid} berhasil disetujui.")

        elif data.startswith("reject_"):
            oid = int(data.split("_")[1])
            order, _ = db_get_order(oid)
            if order:
                db_update_order_status(oid, 'rejected')
                bot_instance.send_message(order['user_id'], f"❌ Pembayaran untuk Order #{oid} ditolak/tidak valid. Silakan hubungi admin.")
                bot_instance.send_message(ADMIN_ID, f"❌ Order #{oid} ditolak.")

    # --- TEXT MESSAGE HANDLER ---
    @bot_instance.message_handler(content_types=['text'])
    def handle_text(msg):
        chat_id = msg.chat.id
        state = get_state(chat_id)
        text = msg.text.strip()
        if not state: return

        if state == "WAITING_SEARCH":
            set_state(chat_id, None)
            prods = [p for p in db_get_all_products() if text.lower() in p['name'].lower()]
            if not prods:
                bot_instance.send_message(chat_id, f"❌ Produk '{text}' tidak ditemukan.")
                return
            markup = types.InlineKeyboardMarkup()
            for p in prods:
                markup.add(types.InlineKeyboardButton(f"{p['name']} - Rp{p['price']:,.0f}", callback_data=f"prod_{p['id']}"))
            bot_instance.send_message(chat_id, f"🔎 Hasil Pencarian '{text}':", reply_markup=markup)

        elif state == "WAITING_ADD_PROD" and chat_id == ADMIN_ID:
            set_state(chat_id, None)
            try:
                parts = text.split("|")
                name = parts[0].strip()
                price = float(parts[1].strip())
                desc = parts[2].strip() if len(parts) > 2 else ""
                content = parts[3].strip() if len(parts) > 3 else ""
                db_add_product(name, price, desc, 999, content)
                bot_instance.send_message(chat_id, f"✅ Produk **{name}** berhasil ditambahkan!", parse_mode="Markdown")
            except Exception:
                bot_instance.send_message(chat_id, "❌ Format salah. Gunakan: `Nama | Harga | Deskripsi | Konten`", parse_mode="Markdown")

        elif state == "WAITING_NEW_DESC" and chat_id == ADMIN_ID:
            pid = get_user_temp(chat_id, 'edit_pid')
            db_update_product_desc(pid, text)
            set_state(chat_id, None)
            bot_instance.send_message(chat_id, f"✅ Deskripsi Produk #{pid} telah diperbarui!")

        elif state == "WAITING_PAY_TEXT" and chat_id == ADMIN_ID:
            method = get_user_temp(chat_id, 'pay_method')
            db_set_payment_info(method, text)
            set_state(chat_id, None)
            bot_instance.send_message(chat_id, f"✅ Info **{method.upper()}** diperbarui: `{text}`", parse_mode="Markdown")

    # --- PHOTO MESSAGE HANDLER ---
    @bot_instance.message_handler(content_types=['photo'])
    def handle_photo(msg):
        chat_id = msg.chat.id
        state = get_state(chat_id)
        if not state: return

        # FIX QRIS PAYMENT PHOTO
        if state == "WAITING_QRIS_PHOTO" and chat_id == ADMIN_ID:
            file_id = msg.photo[-1].file_id
            db_set_payment_info('qris', file_id)
            set_state(chat_id, None)
            bot_instance.send_message(chat_id, "✅ Foto QRIS berhasil disimpan!")

        # BUKTI TRANSFER PEMBELI
        elif state == "WAITING_PROOF":
            order_id = get_user_temp(chat_id, 'active_order_id')
            file_id = msg.photo[-1].file_id
            db_update_order_status(order_id, 'waiting_approval', file_id)
            set_state(chat_id, None)
            
            bot_instance.send_message(chat_id, f"✅ Bukti pembayaran untuk Order #{order_id} berhasil dikirim! Menunggu verifikasi Admin.")
            
            # Forward Bukti ke Admin dengan Button Aksi
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ Terima Order", callback_data=f"approve_{order_id}"),
                types.InlineKeyboardButton("❌ Tolak Order", callback_data=f"reject_{order_id}")
            )
            bot_instance.send_photo(
                ADMIN_ID, photo=file_id, 
                caption=f"🔔 **Bukti Pembayaran Baru!**\nOrder ID: #{order_id}\nFrom User ID: `{chat_id}`",
                reply_markup=markup, parse_mode="Markdown"
            )
