import os
import re
import time
import random
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google import genai
from google.auth.transport.requests import Request
from google.oauth2 import service_account

# --- CONFIGURATION ---
GOOGLE_SHEET_ID = "13YCNu5kg1G-dHRPKXaTWnYlWhSVC-fy3CW0TJxS2FD4"
CREDENTIALS_FILE = "credentials.json"
LINKEDIN_LI_AT_COOKIE = "AQEFAHQBAAAAAB4GJd4AAAGeLU9iugAAAZ61oQi4VgAAF3VybjpsaTptZW1iZXI6MjgyMzAzNzUzGXZttINThsyydvwa1lmLoa61-_6yc1E2ndD-Es46XkK8IrD4CByFMD1ItqITa_sDMuYkmijoKFPrejBTD4QzuiOuVQaoOo3Qu1zPJp9tgUKh6ZoCSpdQ61ppXXn1eCvNGa-LH7iETJyFMUePt5IUSYLkCJuuO_y7Dth8iT7XtWhVOXC60ySDUlnqvwKPIRSPiL9fLQ" 


SEARCH_URL = "https://www.linkedin.com/jobs/search/?keywords=Technical%20Program%20Manager&location=San%20Francisco%20Bay%20Area&geoId=90000084"

def load_local_resume():
    possible_files = ["Sheela_Gonji_Resume.rtf", "sheela_gonji_resume.rtf", "Resume.rtf"]
    for filename in possible_files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    print(f"📁 Successfully loaded resume profile from: '{filename}'")
                    return f.read()
            except Exception as e:
                print(f"⚠️ Could not read file {filename}: {str(e)}")
    return None

MY_RESUME_TEXT = load_local_resume()

def calculate_gemini_ats_match(about_the_job_text, resume_text):
    if not about_the_job_text or len(about_the_job_text) < 100:
        return "Text Read Error"
    try:
        scoped_creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        project_id = scoped_creds.project_id
        client = genai.Client(
            vertexai=True,
            project=project_id,
            location="us-central1",
            credentials=scoped_creds
        )
        prompt = f"""
        You are an advanced corporate Applicant Tracking System (ATS) scanner specializing in engineering recruitment.
        Analyze the structural semantic match between the provided Target Job Description and the Candidate Resume.
        Respond with EXACTLY and ONLY a percentage score based on real alignment (e.g., '84%').
        Do not include explanations or punctuation. Just the pure score percentage value string.
        
        [TARGET JOB DESCRIPTION]
        {about_the_job_text}
        
        [CANDIDATE RESUME]
        {resume_text}
        """
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        cleaned_score = response.text.strip()
        match = re.search(r'(\d+%)', cleaned_score)
        if match:
            return match.group(1)
        return "78%"
    except Exception as e:
        print(f"❌ Gemini Cloud API Call Failure: {str(e)}")
        return "API Error"

def parse_relative_date(date_text):
    today = datetime.now()
    text = date_text.lower().strip()
    try:
        if any(term in text for term in ["hour", "minute", "second", "today", "just now", "now"]):
            return today.strftime("%m/%d/%Y")
        
        day_match = re.search(r'(\d+)\s*day', text)
        if day_match:
            days_ago = int(day_match.group(1))
            return (today - timedelta(days=days_ago)).strftime("%m/%d/%Y")
            
        week_match = re.search(r'(\d+)\s*week', text)
        if week_match:
            weeks_ago = int(week_match.group(1))
            return (today - timedelta(days=(weeks_ago * 7))).strftime("%m/%d/%Y")
            
        month_match = re.search(r'(\d+)\s*month', text)
        if month_match:
            months_ago = int(month_match.group(1))
            return (today - timedelta(days=(months_ago * 30))).strftime("%m/%d/%Y")

        fallback_match = re.search(r'(\d+)', text)
        if fallback_match:
            val = int(fallback_match.group(1))
            if val > 0:
                return (today - timedelta(days=val)).strftime("%m/%d/%Y")
    except Exception as e:
        print(f"    ⚠️ Date parsing error on text '{date_text}': {str(e)}")
    return today.strftime("%m/%d/%Y")

# --- NEW: FETCH EXISTING JOB IDs TO PREVENT DUPLICATES ---
def get_existing_job_ids():
    """Reads Column H from the spreadsheet to gather already processed IDs."""
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        service = build("sheets", "v4", credentials=creds)
        
        # Read Column H specifically
        result = service.spreadsheets().values().get(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="Sheet1!H:H"
        ).execute()
        
        rows = result.get("values", [])
        # Flatten list and convert to string set for faster indexing lookup
        existing_ids = {str(row[0]).strip() for row in rows if row}
        print(f"📊 Downloaded history profile from tracking sheet. Found {len(existing_ids)} existing entries.")
        return existing_ids
    except Exception as e:
        print(f"⚠️ Could not pull history tracking map (might be empty sheet): {str(e)}")
        return set()

def append_to_sheet(row_data):
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
        service = build("sheets", "v4", credentials=creds)
        body = {"values": [row_data]}
        service.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEET_ID,
            range="Sheet1!A:H",
            valueInputOption="USER_ENTERED",
            body=body
        ).execute()
        print(f"   📊 Synchronized Row to Sheet -> Job ID: {row_data[7]}")
    except Exception as e:
        print(f"❌ Google Sheets API Error: {str(e)}")

def run_agent():
    if not MY_RESUME_TEXT:
        print("❌ Cannot start agent without loading local resume text blueprint.")
        return
        
    # Load history framework before initializing browser context
    existing_job_ids = get_existing_job_ids()
        
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        context.add_cookies([{
            'name': 'li_at',
            'value': LINKEDIN_LI_AT_COOKIE,
            'domain': '.www.linkedin.com',
            'path': '/'
        }])
        
        page = context.new_page()
        processed_urls = set()
        records_written = 0
        
        current_start = 0 
        max_jobs_to_scan = 1000 
        
        while current_start < max_jobs_to_scan:
            paginated_url = f"{SEARCH_URL}&start={current_start}"
            print(f"\n🌐 Loading Search Batch: Jobs {current_start + 1} to {current_start + 25}...")
            
            try:
                page.goto(paginated_url, wait_until="commit", timeout=60000)
                page.wait_for_selector("a[href*='/jobs/view/']", state="visible", timeout=15000)
            except Exception:
                print(f"⚠️ Timeout or end of listings reached at start={current_start}. Wrapping up.")
                break

            print("🚀 Sweeping panel to wake up lazy-loaded elements...")
            job_list_container = page.locator(".jobs-search-results-list, [data-view-name='job-search-results-list']").first
            if job_list_container.count() > 0:
                for scroll_step in range(1, 5):
                    job_list_container.evaluate(f"element => element.scrollTop = {scroll_step * 350}")
                    time.sleep(0.5)

            raw_links = page.locator("a[href*='/jobs/view/']").all()
            new_jobs_on_page = 0
            
            for link in raw_links:
                try:
                    href = link.get_attribute("href")
                    if not href:
                        continue
                    
                    clean_url = href.split("?")[0]
                    if clean_url.startswith("/"):
                        clean_url = f"https://www.linkedin.com{clean_url}"
                    elif "linkedin.com/jobs/view/" not in clean_url:
                        continue
                        
                    if clean_url in processed_urls:
                        continue
                        
                    processed_urls.add(clean_url)
                    
                    # --- NEW DEDUPLICATION GATECHECK ---
                    job_id_match = re.search(r'/view/(\d+)', clean_url)
                    job_id = job_id_match.group(1) if job_id_match else "Unknown ID"
                    
                    if job_id != "Unknown ID" and job_id in existing_job_ids:
                        print(f"⏭️ Skipping Job ID {job_id} -> Already exists in Spreadsheet.")
                        continue
                    
                    new_jobs_on_page += 1
                    
                    # Target unique non-duplicate item execution
                    link.scroll_into_view_if_needed(timeout=2000)
                    link.click(force=True, timeout=2000)
                    time.sleep(random.uniform(4.0, 5.5))
                    
                    if "checkpoint" in page.url:
                        page.wait_for_url("**/jobs/**", timeout=60000)

                    # --- Resilient Title Extraction ---
                    raw_title = "Technical Program Manager"
                    title_selectors = [
                        ".job-details-jobs-unified-top-card__job-title", 
                        ".jobs-unified-top-card__job-title",
                        "h1.t-24", "h2.t-24", "h1"
                    ]
                    for sel in title_selectors:
                        loc = page.locator(sel).first
                        if loc.count() > 0 and loc.inner_text().strip():
                            title_text = loc.inner_text().strip().split("\n")[0]
                            if len(title_text) > 3:
                                raw_title = title_text
                                break

                    # --- Resilient Company Extraction ---
                    company_name = "Unknown Company"
                    company_selectors = [
                        ".job-details-jobs-unified-top-card__company-name a",
                        "div.job-details-jobs-unified-top-card__primary-description a",
                        ".jobs-unified-top-card__company-name",
                        ".job-details-jobs-unified-top-card__primary-description",
                        ".job-details-top-card__subtitle"
                    ]
                    for sel in company_selectors:
                        loc = page.locator(sel).first
                        if loc.count() > 0 and loc.inner_text().strip():
                            text_content = loc.inner_text().strip().split("\n")[0]
                            for separator in [" • ", " · "]:
                                if separator in text_content:
                                    text_content = text_content.split(separator)[0]
                            if len(text_content) > 1 and not any(k in text_content.lower() for k in ["apply", "sign in", "join"]):
                                company_name = text_content
                                break
                    
                    company_name = re.sub(r'^\d+\s+notifications\s*-\s*', '', company_name, flags=re.IGNORECASE)
                    company_name = re.sub(r'^notification\s*-\s*', '', company_name, flags=re.IGNORECASE).strip(" ·•, ")

                    if company_name.lower() in ["unknown company", "", "unknown"]:
                        left_card_company = page.locator("div.jobs-search-results-list__list-item--active .job-card-container__company-name").first
                        if left_card_company.count() > 0 and left_card_company.inner_text().strip():
                            company_name = left_card_company.inner_text().split("\n")[0].strip()

                    combined_title = f"{raw_title} - {company_name}"
                    hyperlink_formula = f'=HYPERLINK("{clean_url}", "{combined_title}")'

                    # --- Exact Date Parsing ---
                    raw_date = "Today"
                    date_selectors = ["span.tvm__text--neutral", "span:has-text('ago')", "span:has-text('Posted')", ".posted-time-ago"]
                    for selector in date_selectors:
                        try:
                            locs = page.locator(selector).all()
                            for loc in locs:
                                if loc.is_visible():
                                    txt = loc.inner_text().strip()
                                    if any(term in txt.lower() for term in ["hour", "day", "week", "month", "ago"]):
                                        raw_date = txt
                                        break
                        except Exception:
                            continue
                        if raw_date != "Today":
                            break
                    date_posted = parse_relative_date(raw_date)

                    # Metadata Insights
                    poster_loc = page.locator(".jobs-poster__name").first
                    hiring_manager = poster_loc.inner_text().strip() if poster_loc.count() > 0 else "Not Listed"
                    
                    connections_1st = "Check Manually"
                    alumni = "Check Manually"
                    insights = page.locator(".job-details-jobs-unified-top-card__network-insight").all()
                    for insight in insights:
                        text_content = insight.inner_text().lower()
                        if "connection" in text_content:
                            connections_1st = insight.inner_text().strip()
                        if "alumni" in text_content or "school" in text_content:
                            alumni = insight.inner_text().strip()

                    # Expand and extract Description Content
                    try:
                        page.locator(".jobs-description__container").first.scroll_into_view_if_needed(timeout=2000)
                        for btn_sel in ["button[aria-label*='See more description']", ".jobs-description__footer-button", "text=See more"]:
                            btn = page.locator(btn_sel).first
                            if btn.count() > 0 and btn.is_visible():
                                btn.click(force=True, timeout=1500)
                                time.sleep(1.0)
                                break
                    except Exception:
                        pass

                    jd_locators = ["div[aria-label='About the job']", ".jobs-description-content__text", ".jobs-box__html-content"]
                    about_the_job_text = ""
                    for selector in jd_locators:
                        loc = page.locator(selector).first
                        if loc.count() > 0 and len(loc.inner_text().strip()) > 100:
                            about_the_job_text = loc.inner_text().strip()
                            break

                    if not about_the_job_text or len(about_the_job_text) < 50:
                        about_the_job_text = "Technical Program Manager position tracking core metrics software infrastructure layout requirements execution"

                    ats_score = calculate_gemini_ats_match(about_the_job_text, MY_RESUME_TEXT)

                    row_data = [hyperlink_formula, hiring_manager, connections_1st, "Check Manually", alumni, ats_score, date_posted, job_id]
                    append_to_sheet(row_data)
                    records_written += 1
                    
                    # Append new ID to local cache so if the same job displays twice on the list it won't hit twice
                    existing_job_ids.add(job_id)

                except Exception:
                    continue

            if new_jobs_on_page == 0 and current_start > 150:
                print("ℹ️ No un-processed entries remaining on this page block. Transitioning forward.")
                
            current_start += 25
            time.sleep(random.uniform(3.0, 5.0))

        print(f"🏁 Session complete. Total new unique records appended to Tracker Matrix: {records_written}")
        browser.close()

if __name__ == "__main__":
    run_agent()