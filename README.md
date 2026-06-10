# Alibaba Cloud ECS Telegram Bot

Bot Telegram berbasis Python untuk mengontrol Alibaba Cloud ECS/VPS/RDP multi-akun. Bot ini hanya dapat digunakan oleh owner berdasarkan Telegram numeric user ID.

## Fitur Utama

- **Multi-akun Alibaba Cloud** - Kelola banyak akun dari satu bot
- **Auto-detect Region** - Scan otomatis region yang memiliki instance
- **Manajemen Instance** - Start, Stop, Reboot, Delete, Reset Password, Reinstall OS
- **Security Group** - Open/Close All TCP & UDP Ports (1-65535)
- **Enkripsi** - AccessKey Secret disimpan terenkripsi (AES/Fernet)
- **Logging** - Semua aksi tercatat di database SQLite
- **Owner-only** - Hanya user dengan ID terdaftar yang bisa menggunakan bot
- **UI Modern** - Inline keyboard dengan loading state profesional

## Persyaratan

- Python 3.11+
- Telegram Bot Token (dari BotFather)
- Alibaba Cloud AccessKey (dari RAM user)

## Instalasi

### 1. Clone Repository

```bash
git clone https://github.com/droidvpsautonode/DroidVPSAutoAlibaba.git
cd DroidVPSAutoAlibaba
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Konfigurasi Environment

Salin file `.env.example` menjadi `.env`:

```bash
cp .env.example .env
```

Edit file `.env`:

```env
# Telegram Bot Token (dari BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz

# Owner IDs (Telegram numeric user ID, pisahkan dengan koma)
OWNER_IDS=123456789,987654321

# Path database SQLite
DB_PATH=bot_database.db

# Master key untuk enkripsi AccessKey Secret
# Generate dengan: openssl rand -hex 32
MASTER_KEY=your_random_64_char_hex_string_here
```

### 4. Jalankan Bot

```bash
python -m app.main
```

## Cara Membuat Bot Telegram via BotFather

1. Buka Telegram dan cari `@BotFather`
2. Kirim `/newbot`
3. Ikuti instruksi untuk memberi nama bot
4. Salin **Bot Token** yang diberikan
5. Paste ke `TELEGRAM_BOT_TOKEN` di file `.env`

## Cara Mendapatkan Telegram Owner ID

1. Buka Telegram dan cari `@userinfobot` atau `@getmyid_bot`
2. Kirim `/start`
3. Bot akan membalas dengan numeric user ID Anda
4. Salin ID tersebut ke `OWNER_IDS` di file `.env`
5. Untuk multiple owner, pisahkan dengan koma: `123456789,987654321`

## Cara Membuat RAM User Alibaba Cloud

1. Login ke [Alibaba Cloud Console](https://ram.console.aliyun.com/)
2. Buka **RAM** → **Users** → **Create User**
3. Centang **Programmatic Access** (AccessKey)
4. Buat user dan **simpan AccessKey ID dan Secret** (Secret hanya ditampilkan sekali!)
5. Buka **Permissions** → **Grant Permission**
6. Tambahkan policy: **AliyunECSFullAccess**
7. (Opsional) Untuk keamanan lebih, buat custom policy yang membatasi aksi tertentu

### Permission Minimal untuk Testing

| Policy | Keterangan |
|--------|-----------|
| `AliyunECSFullAccess` | Full access ke ECS (instances, security groups, images) |

### Permission Granular (Produksi)

Jika ingin membatasi aksi, buat custom policy dengan action:
- `ecs:DescribeRegions`
- `ecs:DescribeInstances`
- `ecs:StartInstance`
- `ecs:StopInstance`
- `ecs:RebootInstance`
- `ecs:DeleteInstance`
- `ecs:ModifyInstanceAttribute`
- `ecs:ReplaceSystemDisk`
- `ecs:AuthorizeSecurityGroup`
- `ecs:RevokeSecurityGroup`

## Contoh .env

```env
TELEGRAM_BOT_TOKEN=7123456789:AAHx1234567890abcdefghijklmnopqrs
OWNER_IDS=123456789
DB_PATH=bot_database.db
MASTER_KEY=a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
```

Generate MASTER_KEY dengan:
```bash
openssl rand -hex 32
```

## Struktur Folder

```
DroidVPSAutoAlibaba/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entry point
│   ├── config.py            # Environment configuration
│   ├── db.py                # SQLite database module
│   ├── auth.py              # Owner-only authentication
│   ├── security.py          # Encryption (Fernet/AES)
│   ├── keyboards.py         # Inline keyboard builders
│   ├── states.py            # Conversation states & callbacks
│   ├── utils.py             # Helper functions
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py         # /start, /help, navigation
│   │   ├── accounts.py      # Add/List/Delete/Select accounts
│   │   ├── regions.py       # Scan/Select regions
│   │   ├── instances.py     # List/Detail instances
│   │   ├── actions.py       # All instance actions
│   │   └── logs.py          # View action logs
│   └── services/
│       ├── __init__.py
│       ├── aliyun_client.py  # Alibaba Cloud client factory
│       └── ecs_service.py    # ECS API wrapper
├── .env.example
├── requirements.txt
└── README.md
```

## Command Bot

| Command | Fungsi |
|---------|--------|
| `/start` | Menu utama |
| `/help` | Bantuan penggunaan |
| `/accounts` | Daftar akun Alibaba |
| `/scan` | Scan region aktif |
| `/instances` | Daftar instance |
| `/logs` | Lihat log aksi |
| `/cancel` | Batalkan operasi aktif |

## Alur Penggunaan

```
/start
 → Pilih Akun Alibaba
   → Scan Region
     → Pilih Region
       → Pilih Instance
         → Pilih Aksi (Reboot/Start/Stop/dll)
           → Konfirmasi
             → Eksekusi
               → Hasil
```

## Fitur Security Group

### Open All Ports

Bot dapat membuka semua port TCP dan/atau UDP ke seluruh internet:

- **Open All TCP** - Rule: TCP 1/65535, Source: 0.0.0.0/0
- **Open All UDP** - Rule: UDP 1/65535, Source: 0.0.0.0/0
- **Open All TCP + UDP** - Kedua rule di atas sekaligus

### Revoke All Ports

Menghapus rule yang telah dibuat:

- **Revoke All TCP** - Hapus rule TCP 1/65535
- **Revoke All UDP** - Hapus rule UDP 1/65535
- **Revoke All TCP + UDP** - Hapus kedua rule

## ⚠️ Peringatan Keamanan

### AccessKey Security

- **JANGAN** gunakan AccessKey root account. Selalu gunakan RAM user.
- **JANGAN** share AccessKey Secret ke siapapun.
- AccessKey Secret disimpan terenkripsi di database menggunakan MASTER_KEY.
- Jika MASTER_KEY berubah, semua AccessKey yang tersimpan tidak bisa didekripsi.
- Bot akan menghapus pesan yang berisi AccessKey jika memiliki permission.

### Open All Ports Warning

⚠️ **PERINGATAN KERAS:**

Fitur "Open All TCP/UDP Ports" membuka port **1-65535** ke **seluruh internet** (0.0.0.0/0).

Ini berarti:
- **SEMUA** port di server Anda bisa diakses dari **MANA SAJA** di internet
- Jika ada layanan yang berjalan tanpa password/auth, siapapun bisa mengaksesnya
- Ini adalah konfigurasi yang **SANGAT BERISIKO** untuk server produksi

**Kapan boleh digunakan:**
- Server testing/development yang tidak berisi data sensitif
- Anda yakin semua layanan di server sudah diamankan dengan auth
- Anda memahami konsekuensi keamanan sepenuhnya

**Rekomendasi:**
- Setelah selesai testing, segera tutup kembali port yang tidak diperlukan
- Gunakan firewall internal tambahan (iptables/ufw) di dalam server
- Aktifkan monitoring untuk mendeteksi akses tidak sah

### Aksi Destruktif

Aksi berikut memerlukan konfirmasi ganda (double confirmation):
- **Delete Instance** - Ketik `CONFIRM DELETE <instance_id>`
- **Reinstall OS** - Ketik `CONFIRM REINSTALL <instance_id>`
- **Open All TCP + UDP** - Ketik `CONFIRM OPEN ALL <instance_id>`

### Best Practices

1. Gunakan MASTER_KEY yang kuat (minimal 32 karakter hex)
2. Jangan commit file `.env` ke repository
3. Backup database secara berkala
4. Gunakan RAM user dengan permission minimal
5. Rotasi AccessKey secara berkala
6. Jangan jalankan bot di server yang tidak aman

## Troubleshooting

### Bot tidak merespons
- Pastikan `TELEGRAM_BOT_TOKEN` valid
- Pastikan `OWNER_IDS` berisi numeric ID Anda (bukan username)
- Cek log untuk error message

### Error "Unauthorized"
- Anda bukan owner. Tambahkan Telegram numeric ID ke `OWNER_IDS`

### Error "Gagal mendekripsi AccessKey Secret"
- `MASTER_KEY` mungkin berubah setelah akun ditambahkan
- Hapus akun lama dan tambahkan ulang dengan MASTER_KEY baru

### Error "AccessKey ID tidak valid"
- Periksa AccessKey ID yang dimasukkan
- Pastikan RAM user masih aktif

### Error "Akses ditolak"
- RAM user tidak memiliki permission yang cukup
- Tambahkan policy `AliyunECSFullAccess`

### Scan region lambat
- Normal jika pertama kali. Alibaba Cloud memiliki 20+ region
- Setelah scan, hasil di-cache di database
- Gunakan "Lihat Cache Region" untuk akses cepat

## Lisensi

MIT License

## Kontributor

Bot ini dibuat untuk memudahkan pengelolaan VPS/ECS Alibaba Cloud dari Telegram.
