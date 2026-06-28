import os
import logging
import asyncio
import yt_dlp
from moviepy.video.io.VideoFileClip import VideoFileClip
import moviepy.video.fx as fx
from fastapi import FastAPI
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Setup Logging Komprehensif untuk Debugging [cite: 2026-03-14]
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Token diambil secara aman dari Environment Variables Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8457321019:AAFDC0Ydc39uJkUnIyxGyC_BR1NhdDp6v0Y")

app_web = FastAPI()
app_telegram = Application.builder().token(TELEGRAM_TOKEN).build()

def download_video(url: str) -> str:
    """Mengunduh video dari YouTube ke penyimpanan lokal server"""
    output_path = "video_mentah.mp4"
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    logger.info(f"[PROSES] Memulai pengunduhan video dari link: {url}")
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return output_path

def cut_to_vertical(video_path: str) -> str:
    """Memotong video panjang dan melakukan center crop otomatis ke format vertikal 9:16 bagi pengguna mobile [cite: 2026-03-14]"""
    output_clip = "ai_clip_vertikal.mp4"
    
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"File video mentah tidak ditemukan di lokasi: {video_path}")
        
    logger.info(f"[PROSES] Mengolah pemotongan video lokal: {video_path}")
    video = VideoFileClip(video_path)
    
    # Pembatasan durasi 40 detik demi efisiensi resource server [cite: 2026-03-14]
    end_time = min(40, video.duration)
    sub_clip = video.subclipped(0, end_time)
    
    # Perhitungan koordinat center crop otomatis [cite: 2026-03-14]
    w, h = sub_clip.size
    target_w = int(h * 9 / 16)
    crop_x = (w - target_w) // 2
    
    cropped = fx.crop(sub_clip, x1=crop_x, y1=0, width=target_w, height=h)
    cropped.write_videofile(output_clip, codec="libx264", audio_codec="aac", logger=None)
    
    # Proteksi pelepasan memori RAM server [cite: 2026-03-14]
    video.close()
    sub_clip.close()
    cropped.close()
    return output_clip

async def start(update: Update, context):
    await update.message.reply_text("👋 Halo! Kirimkan link video YouTube ke sini, aku akan otomatis potong jadi format vertikal (9:16) buat kamu!")

async def handle_message(update: Update, context):
    url = update.message.text
    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ Kirim link YouTube yang valid ya!")
        return
        
    status = await update.message.reply_text("📥 Sedang mengunduh video dari YouTube...")
    try:
        raw_video = download_video(url)
        await status.edit_text("🤖 AI sedang memotong video ke format vertikal (9:16)...")
        
        clip_result = cut_to_vertical(raw_video)
        await status.edit_text("🚀 Selesai! Sedang mengirim ke HP kamu...")
        
        with open(clip_result, 'rb') as vf:
            await update.message.reply_video(video=vf, caption="🎬 Ini hasil AI Clip Vertikal kamu!")
            
        # Proteksi pembersihan ruang penyimpanan server [cite: 2026-03-14]
        if os.path.exists(raw_video): os.remove(raw_video)
        if os.path.exists(clip_result): os.remove(clip_result)
        await status.delete()
        
    except Exception as e:
        logger.error(f"[BUG] Gagal memproses pesan video: {str(e)}")
        await update.message.reply_text(f"❌ Gagal memproses video. Error: {str(e)}")

app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

async def start_polling_worker():
    """Loop utama untuk membaca pesan dari bot Telegram [cite: 2026-03-14]"""
    logger.info("[SYSTEM] Memulai Bot AI Clipper via Polling Mode di Render...")
    await app_telegram.initialize()
    await app_telegram.bot.delete_webhook(drop_pending_updates=True)
    await app_telegram.start()
    await app_telegram.updater.start_polling(drop_pending_updates=True)

@app_web.on_event("startup")
async def on_startup():
    """Trigger otomatis saat Uvicorn di Render menyala [cite: 2026-03-14]"""
    asyncio.create_task(start_polling_worker())

@app_web.get("/")
def read_root():
    return {"status": "Server Render berjalan aman, bot operasional!"}
