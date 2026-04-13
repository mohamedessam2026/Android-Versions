import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
from markdownify import markdownify as md
import json
import time
import socket
import sys
import smtplib
from email.message import EmailMessage
from enum import Enum
import difflib
import html
#========================= Configuration =======================
ANDROID_VERSION = os.getenv("ANDROID_VERSION")
BASE_URL = "https://developer.android.com/about/versions/"+ANDROID_VERSION
DOMAIN = "developer.android.com"
OUTPUT_DIR = "android_"+ANDROID_VERSION+"_docs_snapshots"
REQUEST_TIMEOUT_IN_SEC = 30
SLEEP_TIME_IN_SEC = 1
#==============================================================

#========================= Email Configuration =======================
SMTP_SERVER = "smtp.gmail.com"  # Change this if your company uses a different server , example : smtp.office365.com
SMTP_PORT = 587                 # Standard port for TLS
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")
SENDER_PASSWORD = os.getenv("SENDER_PASSWORD")
SMTP_SERVER_TIMEOUT_IN_SEC = 60
#==============================================================

#====================== Web Page ==========================
def get_android_version_links(start_url):
    try:
        response = requests.get(start_url, timeout=REQUEST_TIMEOUT_IN_SEC)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        links = set() # We used `set` to prevent automatic duplication.
        
        # We are looking for all links <a>
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']

            # Converting relative (Relative) links into absolute (Absolute) links
            full_url = urljoin(start_url, href)
            
            # Filter links
            if DOMAIN in full_url and "/about/versions/"+ANDROID_VERSION in full_url:
                # Remove any "Fragments" such as : top - setup
                clean_url = full_url.split('#')[0]
                links.add(clean_url)
                
        return sorted(list(links))
    except Exception as e:
        error_msg = "EXP from get_android_version_links() , message : "+str(e)
        raise Exception(error_msg) from e
    
def get_http_response(url):
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT_IN_SEC)
        response.raise_for_status()
        return response
    except Exception as e:
        error_msg = "Exp from get_http_response() , message : "+str(e)
        raise Exception(error_msg) from e

def get_content_from_artical_and_main_tags_in_web_page(response):
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Specify only the essential content (on Android sites, this will be within the 'article' tag or a specific ID) and We'll focus on the <article> or <main> tags to avoid clutter
        main_content = soup.find('article') or soup.find('main')
        return main_content
    except Exception as e:
        error_msg = "Exp from get_data_from_artical_and_main_tags_in_web_page() , message : "+str(e)
        raise Exception(error_msg) from e

def convert_web_page_to_md(main_content):
    try:
        if not main_content:
            return None

        # Converting HTML to Markdown
        markDown = md(str(main_content), heading_style="ATX")
        return markDown
    except Exception as e:
        error_msg = "Exp from convert_web_page_to_md() , message : "+str(e)
        raise Exception(error_msg) from e
    
def get_file_name_from_url(url):
    try:
        remaining_text = url.replace(BASE_URL, "")
        page_name = remaining_text.strip("/").replace("/", "-")
        if not page_name :
            page_name = "index"
        
        file_name = f"{page_name}.md"
        return file_name
    except Exception as e:
        error_msg = "Exp from get_file_name_from_url() , message : "+str(e)
        raise Exception(error_msg) from e
#==============================================================

#================ Store Operations ==================
def create_directory():
    try:
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR)
    except Exception as e:
        error_msg = "EXP from create_directory() , message : "+str(e)
        raise Exception(error_msg) from e 
    
def store_page_content_into_file(path_of_file,content):
    try:
        with open(path_of_file, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        error_msg = "Exp from store_page_content_into_file() , message : "+str(e)
        raise Exception(error_msg) from e
    
def is_file_name_exist(fName):
    try:
        file_path = OUTPUT_DIR+"/"+fName

        if not os.path.exists(file_path):
            return False
        
        return True
    except Exception as e:
        error_msg = "Exp from is_file_name_exist() , message : "+str(e)
        raise Exception(error_msg) from e

def get_content_of_exist_file(fName):
    try:
        file_path = OUTPUT_DIR+"/"+fName

        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        error_msg = "Exp from get_content_of_exist_file() , message : "+str(e)
        raise Exception(error_msg) from e
#==============================================================

#================ Sends the report via SMTP ==================
class EmailStatus:
    SUCCESS_TYPE = "SUCCESS"
    FAILED_TYPE = "FAILED"
    TIMEOUT_TYPE = "TIMEOUT"
    MISSING_TYPE = "MISSING_CREDENTIALS"

    def __init__(self, type, message=""):
        self.type = type
        self.message = message

    def is_failure(self):
        return self.type != EmailStatus.SUCCESS_TYPE

    def __str__(self):
        return self.message
    
def send_email_report(report_html):
    if not SENDER_EMAIL or not SENDER_PASSWORD:
        return EmailStatus(EmailStatus.MISSING_TYPE, "Failed: Email credentials missing.")
    
    msg = EmailMessage()
    msg.set_content("Please use an HTML compatible email client to view the report.")
    msg.add_alternative(report_html, subtype='html')
    
    msg['Subject'] = "Android Attestation Root Certs Report"
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL

    # set mail as a high Priority 
    msg['X-Priority'] = '1 (Highest)'
    msg['Importance'] = 'High'

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=SMTP_SERVER_TIMEOUT_IN_SEC)
        server.set_debuglevel(0)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return EmailStatus(EmailStatus.SUCCESS_TYPE, "Email sent successfully via TLS.")
    except (socket.timeout, TimeoutError):
        return EmailStatus(EmailStatus.TIMEOUT_TYPE, "Exp from send_email_report() , message : SMTP server connection timed out.")
    except Exception as e:
        return EmailStatus(EmailStatus.FAILED_TYPE, f"Exp from send_email_report() , message : Failed to send email - {str(e)}")
    
def logEmailStatus(status_obj: EmailStatus):
    print(status_obj)
    if status_obj.is_failure():
        sys.exit(1)
#==============================================================

#======================Filteration Operations=============================
def is_old_content_is_match_current_content(old_content,current_content):
    if old_content == current_content:
        return True
    
    return False
#==============================================================

#=========================HTML and Table Operations ===========================
def add_new_row_in_change_table(changes_table_rows,content_of_change_table_rows,file_name, old_content, new_content):
    try:
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if not tag == 'equal':
                old_part = "<br>".join(old_lines[i1:i2])
                new_part = "<br>".join(new_lines[j1:j2])
                changes_table_rows.append(f"| `{file_name}` | 📝 Modified |")
                content_of_change_table_rows.append(f"| `{file_name}` | {old_part} | {new_part}")
    except Exception as e:
        error_msg = "Exp from add_new_row_in_change_table() , message : "+str(e)
        raise Exception(error_msg) from e

def add_new_row_in_not_change_table(not_change_table_rows,file_name):
    not_change_table_rows.append(f"| `{file_name}` | ✅ No Changes  |")

def add_new_row_in_new_file_table(new_file_table_rows,file_name):
    new_file_table_rows.append(f"| `{file_name}` | ✨ Added  |")

def get_tables_header():
    return f"""
        <html>
        <body style="padding: 20px; background-color: #fafafa;">
            <h2 style="color: #2c3e50; text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 10px;">
                Android Docs Monitor Report
            </h2>
        """

def format_table_html(table_title, title_of_column1, title_of_column2, title_of_column3, rows):
    try:
        if not rows:
            return ""
        
        table_header = ""
        if(not title_of_column3):
            table_header = f"""
            <h3 style="font-family: Arial, sans-serif; color: #333; margin-top: 20px;">{table_title}</h3>
            <table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; margin-bottom: 20px; table-layout: fixed; border: 1px solid #ddd;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column1}</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column2}</th>
                    </tr>
                </thead>
                <tbody>
            """
        
        if(title_of_column3):
            table_header = f"""
            <h3 style="font-family: Arial, sans-serif; color: #333; margin-top: 20px;">{table_title}</h3>
            <table style="border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; margin-bottom: 20px; table-layout: fixed; border: 1px solid #ddd;">
                <thead>
                    <tr style="background-color: #f2f2f2;">
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column1}</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column2}</th>
                        <th style="padding: 12px; text-align: left; border: 1px solid #ddd; width: 45%; font-size: 14px;">{title_of_column3}</th>
                    </tr>
                </thead>
                <tbody>
            """

        table_body = ""
        for row in rows:
            parts = [p.strip() for p in row.split('|') if p.strip()]
            
            if len(parts) == 2:
                col1_raw = parts[0].replace('`', '')
                col2_raw = parts[1]
            
                col1 = html.escape(col1_raw)
                col2 = html.escape(col2_raw)

                status_color = "#28a745" if any(word in col2 for word in ["New", "Added"]) else "#333"
                if "No Changes" in col2: status_color = "#6c757d"
                if "Modified" in col2: status_color = "#e67e22"
                
                table_body += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top;">{col1}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top; color: {status_color};">{col2}</td>
                </tr>
                """

            if len(parts) == 3:
                col1_raw = parts[0].replace('`', '')
                col2_raw = parts[1]
                col3_raw = parts[2]
                col1 = html.escape(col1_raw)
                col2 = html.escape(col2_raw)
                col3 = html.escape(col3_raw)

                table_body += f"""
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top;">{col1}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top;">{col2}</td>
                    <td style="padding: 10px; border: 1px solid #ddd; font-family: 'Courier New', monospace; font-size: 13px; word-wrap: break-word; white-space: pre-wrap; vertical-align: top;">{col3}</td>
                </tr>
                """
        if not table_body:
            return ""
            
        return table_header + table_body + "</tbody></table>"
    except Exception as e:
        error_msg = "Exp from format_table_html() , message : "+str(e)
        raise Exception(error_msg) from e

def get_tables_footer():
    return"""
            <p style="font-size: 12px; color: #888; text-align: center; margin-top: 30px;">
                This is an automated report.
            </p>
        </body>
        </html>
        """
#================ Main Function ==================
if __name__ == "__main__":
    try:
        create_directory()

        # Get all the links
        all_links = get_android_version_links(BASE_URL)
        
        # Download the old record
        new_file_table_rows = []
        not_change_table_rows=[]
        change_table_rows = []
        content_of_change_table_rows = []

        # Go through all the links
        for i, url in enumerate(all_links, 1):
            file_name = get_file_name_from_url(url)
            
            # Get current data
            response = get_http_response(url)
            web_page_content  = get_content_from_artical_and_main_tags_in_web_page(response)
            mark_down = convert_web_page_to_md(web_page_content)
            current_content = mark_down

            if(not is_file_name_exist(file_name)):
                file_path = os.path.join(OUTPUT_DIR, file_name)
                store_page_content_into_file(file_path,current_content)
                add_new_row_in_new_file_table(new_file_table_rows,file_name)
                continue

            old_content = get_content_of_exist_file(file_name)

            if not is_old_content_is_match_current_content(old_content,current_content):
                add_new_row_in_change_table(change_table_rows,content_of_change_table_rows,file_name, old_content, current_content)
                file_path = os.path.join(OUTPUT_DIR, file_name)
                store_page_content_into_file(file_path,current_content)
                continue

            if is_old_content_is_match_current_content(old_content,current_content):
                add_new_row_in_not_change_table(not_change_table_rows,file_name)
            

            # A slight delay (policy delay) to prevent Google from blocking your IP address.
            time.sleep(SLEEP_TIME_IN_SEC)


        final_report_html = get_tables_header()

        final_report_html += format_table_html("✨ NEW FILES TABLE","File Name","Status","", new_file_table_rows)
        final_report_html += format_table_html("📝 CHANGES TABLE","File Name","Status","", change_table_rows)
        final_report_html += format_table_html("📝 CHANGES TABLE Content","File Name","Old Content","New Content", content_of_change_table_rows)
        final_report_html += format_table_html("✅ NOT CHANGES TABLE","File Name","Status","", not_change_table_rows)

        final_report_html += get_tables_footer()


        # Step 5: Send Email (Regardless of outcome as requested)
        email_status = send_email_report(final_report_html)
        logEmailStatus(email_status)

    except Exception as e:
        error_msg = str(e)
        print(error_msg)

        # Send error as a report too
        email_status = send_email_report(error_msg)
        logEmailStatus(email_status)
#==============================================================

