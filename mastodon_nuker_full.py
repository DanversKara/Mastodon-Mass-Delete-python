import requests
import time

# Config
ACCESS_TOKEN = 'TOKEN'
MASTODON_INSTANCE = 'DOMAIN'

HEADERS = {
    'Authorization': f'Bearer {ACCESS_TOKEN}'
}

def get_account_info():
    res = requests.get(f"{MASTODON_INSTANCE}/api/v1/accounts/verify_credentials", headers=HEADERS)
    res.raise_for_status()
    return res.json()

def get_statuses(account_id, max_id=None):
    params = {
        'limit': 40,
        'exclude_reblogs': True,
        'exclude_replies': False,
    }
    if max_id:
        params['max_id'] = max_id

    url = f"{MASTODON_INSTANCE}/api/v1/accounts/{account_id}/statuses"
    res = requests.get(url, headers=HEADERS, params=params)
    res.raise_for_status()
    return res.json()

def delete_status(status_id):
    url = f"{MASTODON_INSTANCE}/api/v1/statuses/{status_id}"
    for attempt in range(5):
        res = requests.delete(url, headers=HEADERS)
        if res.status_code == 200:
            return True
        elif res.status_code == 429:
            wait = 2 ** attempt
            print(f"⏳ Rate limited. Waiting {wait}s before retrying...")
            time.sleep(wait)
        else:
            print(f"❌ Failed to delete {status_id}: {res.status_code} - {res.text}")
            return False
    return False

def nuke_all_statuses():
    account_info = get_account_info()
    account_id = account_info['id']
    username = account_info['username']
    print(f"🔍 Your account ID: {account_id} | Username: @{username}")

    total_deleted = 0
    max_id = None

    while True:
        statuses = get_statuses(account_id, max_id)
        if not statuses:
            break

        for status in statuses:
            status_id = status['id']
            created = status['created_at']
            content = status.get('content', '')
            preview = content.replace('<p>', '').replace('</p>', '').strip()
            if len(preview) > 30:
                preview = preview[:30] + '...'
            print(f"📝 {created} | {status_id} | {preview}")

            if delete_status(status_id):
                print(f"✅ Deleted status {status_id}")
                total_deleted += 1
            else:
                print(f"⚠️ Skipped status {status_id}")
            time.sleep(0.8)  # slight delay to avoid 429s

        max_id = statuses[-1]['id']

    print(f"\n🧹 Wipe complete. Total deleted: {total_deleted}")

if __name__ == '__main__':
    nuke_all_statuses()
