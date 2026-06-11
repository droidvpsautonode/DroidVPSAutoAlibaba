"""
Script diagnostik untuk Alibaba Cloud ECS Telegram Bot.

Tujuan: mencari tahu kenapa instance tidak terdeteksi saat scan region.
Script ini akan:
  1. Membaca akun dari database (atau dari argumen langsung)
  2. Memanggil DescribeRegions
  3. Mengecek jumlah instance di SEMUA region
  4. Menampilkan SEMUA error tanpa disembunyikan

Cara pakai:
  python3 diagnose.py
  python3 diagnose.py --region ap-southeast-1
  python3 diagnose.py --ak <ACCESS_KEY_ID> --secret <ACCESS_KEY_SECRET>
"""

import argparse
import sys
import traceback

from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_tea_util.models import RuntimeOptions

from app.services.aliyun_client import create_ecs_client


def pick_account_from_db():
    """Ambil akun dari database (decrypt secret)."""
    try:
        from app.db import db
        from app.security import security
    except Exception as e:
        print(f"[!] Gagal load db/security: {e}")
        return None, None

    accounts = db.get_accounts()
    if not accounts:
        print("[!] Tidak ada akun di database. Tambahkan via bot dulu, "
              "atau jalankan dengan --ak dan --secret.")
        return None, None

    acc = accounts[0]
    print(f"[i] Memakai akun: {acc['account_name']} "
          f"(AccessKey: {acc['access_key_id'][:6]}...)")
    try:
        secret = security.decrypt(acc["access_key_secret_encrypted"])
    except Exception as e:
        print(f"[!] Gagal decrypt secret (cek MASTER_KEY di .env): {e}")
        return None, None
    return acc["access_key_id"], secret


def describe_regions(ak, secret):
    client = create_ecs_client(ak, secret, "ap-southeast-1")
    req = ecs_models.DescribeRegionsRequest(accept_language="en-US")
    resp = client.describe_regions_with_options(req, RuntimeOptions())
    regions = []
    if resp.body and resp.body.regions and resp.body.regions.region:
        for r in resp.body.regions.region:
            regions.append((r.region_id, r.local_name or r.region_id))
    return regions


def count_instances(ak, secret, region_id):
    client = create_ecs_client(ak, secret, region_id)
    req = ecs_models.DescribeInstancesRequest(
        region_id=region_id, page_size=100, page_number=1
    )
    resp = client.describe_instances_with_options(req, RuntimeOptions())
    total = resp.body.total_count or 0
    names = []
    if resp.body and resp.body.instances and resp.body.instances.instance:
        for inst in resp.body.instances.instance:
            names.append(f"{inst.instance_id} ({inst.status})")
    return total, names


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ak", help="AccessKey ID")
    parser.add_argument("--secret", help="AccessKey Secret")
    parser.add_argument("--region", help="Cek 1 region tertentu saja")
    args = parser.parse_args()

    if args.ak and args.secret:
        ak, secret = args.ak, args.secret
        print(f"[i] Memakai AccessKey dari argumen: {ak[:6]}...")
    else:
        ak, secret = pick_account_from_db()

    if not ak or not secret:
        sys.exit(1)

    # 1. DescribeRegions
    print("\n=== STEP 1: DescribeRegions ===")
    try:
        regions = describe_regions(ak, secret)
        print(f"[OK] {len(regions)} region ditemukan.")
    except Exception as e:
        print(f"[ERROR] DescribeRegions gagal:")
        traceback.print_exc()
        sys.exit(1)

    # 2. Hitung instance per region
    if args.region:
        regions = [(r, n) for (r, n) in regions if r == args.region]
        if not regions:
            regions = [(args.region, args.region)]

    print("\n=== STEP 2: Cek instance per region ===")
    found_any = False
    for region_id, region_name in regions:
        try:
            total, names = count_instances(ak, secret, region_id)
            if total > 0:
                found_any = True
                print(f"[FOUND] {region_name} ({region_id}): {total} instance")
                for n in names:
                    print(f"          - {n}")
            else:
                print(f"  ...... {region_name} ({region_id}): 0")
        except Exception as e:
            print(f"[ERROR] {region_name} ({region_id}): {type(e).__name__}: {e}")

    print("\n=== HASIL ===")
    if found_any:
        print("[OK] Ada instance terdeteksi. Lihat baris [FOUND] di atas.")
    else:
        print("[!] Tidak ada instance terdeteksi di region manapun.")
        print("    Cek baris [ERROR] di atas untuk tahu penyebabnya.")


if __name__ == "__main__":
    main()
