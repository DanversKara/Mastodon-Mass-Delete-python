import requests
import time
import random
import os

# ==== CONFIG ====
ACCESS_TOKEN = 'TOKEN'
MASTODON_INSTANCE = 'https://DOMAIN'
ACCOUNT_ID = ''  # Leave blank to auto-fetch
PER_PAGE = 40
WAIT_SECONDS_BETWEEN_DELETIONS = 30  # 🐢 slow mode

PROGRESS_FILE = 'deleted_statuses.txt'
FAILED_FILE = 'failed_deletions.txt'

# ==== HEADERS ====
headers = {
    'Authorization': f'Bearer {ACCESS_TOKEN}'
}

def get_account_id():
    url = f"{MASTODON_INSTANCE}/api/v1/accounts/verify_credentials"
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    account_id = res.json()['id']
    print(f"🔍 Your account ID: {account_id}")
    return account_id

def get_statuses(account_id, max_id=None):
    url = f"{MASTODON_INSTANCE}/api/v1/accounts/{account_id}/statuses"
    params = {
        'limit': PER_PAGE,
        'exclude_reblogs': True,
        'exclude_replies': False
    }
    if max_id:
        params['max_id'] = max_id
    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()
    return res.json()

def load_logged_ids(file_path):
    if not os.path.exists(file_path):
        return set()
    with open(file_path, 'r') as f:
        return set(line.strip() for line in f.readlines())

def save_logged_ids(file_path, ids):
    with open(file_path, 'w') as f:
        for id in ids:
            f.write(f"{id}\n")

def log_status(file_path, status_id):
    with open(file_path, 'a') as f:
        f.write(f"{status_id}\n")

def delete_status(status_id, deleted_ids, failed_ids):
    if status_id in deleted_ids:
        print(f"⚠️ Already deleted {status_id}, skipping.")
        return
    if status_id in failed_ids:
        print(f"⚠️ Already failed on {status_id}, skipping.")
        return

    url = f"{MASTODON_INSTANCE}/api/v1/statuses/{status_id}"
    for attempt in range(3):
        res = requests.delete(url, headers=headers)
        if res.status_code == 200:
            print(f"✅ Deleted status {status_id}")
            log_status(PROGRESS_FILE, status_id)
            return
        elif res.status_code == 429:
            wait = (2 ** attempt) + random.uniform(1, 3)
            print(f"⏳ Rate limited. Waiting {wait:.1f}s before retrying...")
            time.sleep(wait)
        else:
            print(f"❌ Failed to delete {status_id}: {res.status_code} - {res.text}")
            log_status(FAILED_FILE, status_id)
            return

    print(f"⚠️ Giving up on {status_id} for now.")
    log_status(FAILED_FILE, status_id)

def nuke_all_statuses():
    account_id = ACCOUNT_ID or get_account_id()
    deleted_ids = load_logged_ids(PROGRESS_FILE)
    failed_ids = load_logged_ids(FAILED_FILE)
    max_id = None

    while True:
        statuses = get_statuses(account_id, max_id)
        if not statuses:
            print("🎉 No more statuses to delete.")
            break
        for status in statuses:
            delete_status(status['id'], deleted_ids, failed_ids)
            time.sleep(WAIT_SECONDS_BETWEEN_DELETIONS + random.uniform(0, 3))
        max_id = statuses[-1]['id']

def retry_failed():
    deleted_ids = load_logged_ids(PROGRESS_FILE)
    failed_ids = load_logged_ids(FAILED_FILE)
    still_failed = set()

    print("\n🔁 Retrying failed deletions...")

    for status_id in failed_ids:
        if status_id in deleted_ids:
            continue
        url = f"{MASTODON_INSTANCE}/api/v1/statuses/{status_id}"
        for attempt in range(5):
            res = requests.delete(url, headers=headers)
            if res.status_code == 200:
                print(f"✅ Retried and deleted {status_id}")
                log_status(PROGRESS_FILE, status_id)
                break
            elif res.status_code == 429:
                wait = (2 ** attempt) + random.uniform(1, 3)
                print(f"⏳ Rate limited. Waiting {wait:.1f}s before retrying...")
                time.sleep(wait)
            else:
                print(f"❌ Retry failed for {status_id}: {res.status_code} - {res.text}")
                still_failed.add(status_id)
                break
        time.sleep(WAIT_SECONDS_BETWEEN_DELETIONS + random.uniform(0, 3))

    save_logged_ids(FAILED_FILE, still_failed)
    print(f"\n✨ Retry complete. Remaining failed deletions: {len(still_failed)}")

if __name__ == '__main__':
    nuke_all_statuses()
    retry_failed()
