# Menjalankan Bot 24 Jam Nonstop (systemd)

Panduan agar bot tetap hidup walaupun SSH ditutup, dan otomatis nyala lagi
saat server di-reboot.

## 1. Pastikan path benar

Cek lokasi repo dan python:

```bash
pwd                 # contoh: /root/DroidVPSAutoAlibaba
which python3       # contoh: /usr/bin/python3
```

Jika repo Anda **bukan** di `/root/DroidVPSAutoAlibaba`, edit file
`deploy/alibaba-ecs-bot.service` dan sesuaikan `WorkingDirectory`.

## 2. Pasang service

```bash
sudo cp deploy/alibaba-ecs-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable alibaba-ecs-bot      # auto-start saat boot
sudo systemctl start alibaba-ecs-bot       # jalankan sekarang
```

## 3. Cek status & log

```bash
sudo systemctl status alibaba-ecs-bot      # lihat status (running?)
journalctl -u alibaba-ecs-bot -f           # lihat log real-time
journalctl -u alibaba-ecs-bot -n 100       # lihat 100 baris log terakhir
```

## 4. Perintah harian

```bash
sudo systemctl restart alibaba-ecs-bot     # restart (mis. setelah git pull)
sudo systemctl stop alibaba-ecs-bot        # matikan
sudo systemctl disable alibaba-ecs-bot     # batal auto-start saat boot
```

## 5. Update kode lalu restart

```bash
cd /root/DroidVPSAutoAlibaba
git pull origin main
pip3 install -r requirements.txt           # kalau ada dependency baru
sudo systemctl restart alibaba-ecs-bot
```

---

## Alternatif cepat (tanpa systemd)

### Opsi A: tmux/screen (manual)

```bash
sudo apt install -y tmux
tmux new -s bot
python3 -m app.main
# tekan Ctrl+B lalu D untuk detach (bot tetap jalan)
# masuk lagi: tmux attach -t bot
```

### Opsi B: nohup

```bash
nohup python3 -m app.main > bot.log 2>&1 &
# lihat log: tail -f bot.log
# stop: cari PID dengan 'ps aux | grep app.main' lalu 'kill <PID>'
```

> Rekomendasi: pakai **systemd** karena otomatis restart kalau bot crash
> dan otomatis nyala saat server reboot. tmux/nohup tidak auto-restart.
