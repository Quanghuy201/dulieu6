import threading
import time
import random
import string
from zlapi import ZaloAPI, ThreadType, Message, Mention
from config import API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES
from collections import defaultdict

class Bot(ZaloAPI):
    def __init__(self, api_key, secret_key, imei=None, session_cookies=None):
        super().__init__(api_key, secret_key, imei, session_cookies)
        self.running = False
        self.is_spamstk_running = False

    def fetchGroupInfo(self):
        try:
            all_groups = self.fetchAllGroups()
            group_list = []
            for group_id, _ in all_groups.gridVerMap.items():
                group_info = super().fetchGroupInfo(group_id)
                group_name = group_info.gridInfoMap[group_id]["name"]
                group_list.append({'id': group_id, 'name': group_name})
            return group_list
        except Exception as e:
            print(f"Lỗi khi lấy danh sách nhóm: {e}")
            return []

    def display_group_menu(self):
        groups = self.fetchGroupInfo()
        if not groups:
            print("Không tìm thấy nhóm nào.")
            return None
        grouped = defaultdict(list)
        for group in groups:
            first_char = group['name'][0].upper()
            if first_char not in string.ascii_uppercase:
                first_char = '#'
            grouped[first_char].append(group)
        print("\nDanh sách các nhóm:")
        index_map = {}
        idx = 1
        for letter in sorted(grouped.keys()):
            print(f"\nNhóm {letter}:")
            for group in grouped[letter]:
                print(f"{idx}. {group['name']} (ID: {group['id']})")
                index_map[idx] = group['id']
                idx += 1
        return index_map

    def select_group(self):
        index_map = self.display_group_menu()
        if not index_map:
            return None
        while True:
            try:
                choice = int(input("Nhập số thứ tự của nhóm: ").strip())
                if choice in index_map:
                    return index_map[choice]
                print("Số không hợp lệ.")
            except ValueError:
                print("Vui lòng nhập số hợp lệ.")

    def list_group_members(self, thread_id):
        try:
            group = super().fetchGroupInfo(thread_id)["gridInfoMap"][thread_id]
            members = group["memVerList"]
            print("\n--- Danh sách thành viên ---")
            members_list = []
            for index, member in enumerate(members, start=1):
                uid = member.split('_')[0]
                user_info = super().fetchUserInfo(uid)
                author_info = user_info.get("changed_profiles", {}).get(uid, {})
                name = author_info.get('zaloName', 'Không xác định')
                members_list.append({"uid": uid, "name": name})
                print(f"{index}. {name} (UID: {uid})")
            choice = int(input("Nhập số để chọn thành viên: ")) - 1
            return members_list[choice] if 0 <= choice < len(members_list) else None
        except Exception as e:
            print(f"Lỗi khi lấy danh sách thành viên: {e}")
            return None

    def send_reo_file(self, thread_id, mentioned_user_id, mentioned_name, filename, delay, enable_sticker, stk_delay):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                base_lines = [line.strip() for line in f if line.strip()]
                if not base_lines:
                    print("❌ File rỗng hoặc không có dòng hợp lệ.")
                    return
                remaining_lines = []
                self.running = True
                self.is_spamstk_running = enable_sticker

                def spam_loop():
                    nonlocal remaining_lines
                    while self.running:
                        if not remaining_lines:
                            remaining_lines = base_lines.copy()
                            random.shuffle(remaining_lines)
                        phrase = remaining_lines.pop()
                        mention_text = f"@1"
                        message_text = f"{phrase} =)) {mention_text}"
                        offset = message_text.index(mention_text)
                        mention = Mention(
                            uid=mentioned_user_id,
                            offset=offset,
                            length=len(mention_text)
                        )
                        full_message = Message(text=message_text, mention=mention)
                        self.setTyping(thread_id, ThreadType.GROUP)
                        time.sleep(1.5)
                        self.send(full_message, thread_id=thread_id, thread_type=ThreadType.GROUP)
                        print(f"✅ Đã gửi: {mentioned_name}: {phrase}")
                        time.sleep(delay)

                def spamstk_loop():
                    while self.is_spamstk_running:
                        try:
                            self.sendSticker(
                                stickerType=3,
                                stickerId=21979,
                                cateId=10136,
                                thread_id=thread_id,
                                thread_type=ThreadType.GROUP
                            )
                            print("⚡ Đã gửi sticker")
                        except Exception:
                            pass
                        time.sleep(stk_delay)

                thread1 = threading.Thread(target=spam_loop)
                thread1.daemon = True
                thread1.start()

                if enable_sticker:
                    thread2 = threading.Thread(target=spamstk_loop)
                    thread2.daemon = True
                    thread2.start()

                try:
                    while self.running:
                        time.sleep(1)
                except KeyboardInterrupt:
                    self.stop_sending()

        except FileNotFoundError:
            print(f"❌ Không tìm thấy file: {filename}")
        except Exception as e:
            print(f"❌ Lỗi khi gửi nội dung: {e}")

    def stop_sending(self):
        self.running = False
        self.is_spamstk_running = False
        print("⛔ Đã dừng gửi tin nhắn.")

def run_tool():
    print("TOOL RÉO TAG TỪ FILE KHÔNG LẶP LẠI")
    print("[1] Gửi nội dung từ file (có réo 1 người)")
    print("[0] Thoát")
    choice = input("Nhập lựa chọn: ").strip()
    if choice != '1':
        print("Đã thoát tool.")
        return
    client = Bot(API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES)
    thread_id = client.select_group()
    if not thread_id:
        return
    selected_user = client.list_group_members(thread_id)
    if not selected_user:
        return
    filename = input("Nhập tên file chứa nội dung: ").strip()
    try:
        delay = float(input("Nhập delay giữa các tin nhắn (giây): ").strip())
    except ValueError:
        print("⏱️ Dùng mặc định 10s.")
        delay = 10
    enable_sticker = False
    stk_delay = 5
    ask = input("Bạn có muốn bật gửi sticker lag không ⚡ (Y/N): ").strip().lower()
    if ask == 'y':
        enable_sticker = True
        try:
            stk_delay = float(input("Nhập delay gửi sticker (giây): ").strip())
        except ValueError:
            stk_delay = 3
    client.send_reo_file(
        thread_id=thread_id,
        mentioned_user_id=selected_user["uid"],
        mentioned_name=selected_user["name"],
        filename=filename,
        delay=delay,
        enable_sticker=enable_sticker,
        stk_delay=stk_delay
    )

if __name__ == "__main__":
    run_tool()
