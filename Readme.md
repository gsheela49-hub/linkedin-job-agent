This section details the structure, prerequisites, and runtime steps required to operate the automation engine.

**System Features
Targeted Filtering:** Programmatically restricts active pipelines to Technical Program Manager roles within the geographical area of your choice. In the current .py file, I use San Francisco Bay Area but you can update it to your preferred geographical location

**ATS Match Engine:** Iterates over the "About the Job" description sections of live listings and calculates a match percentage score based on core professional keyword densities.

**Google Cloud Integration**: Automatically syncs and appends qualified opportunities to an external tracking spreadsheet using authorized service account keys.

**Project Directory Layout**

Plaintext
linkedin-job-agent/
  a)  agent.py            # Main agent script (Scraping, ATS scoring, API logging)
  b)  .gitignore          # Excludes environment configurations & credentials
  c) README.md           # Documentation and execution guide
  d) Resume.rtf          #resume file

**Setup & Installation**
1) Navigate to the Directory:
    Bash
    cd /Users/sheela/Documents/linkedin-job-agent
2)Isolate Python Dependencies via a Virtual Environment:    
    Bash
    python3 -m venv venv
    source venv/bin/activate
3) Install Required Libraries:
    Bash
    pip install requests beautifulsoup4 google-auth google-api-python-client
4) Credential Provisioning:
    Ensure your authorized Google Cloud .json key file is staged directly inside the root directory.

**Execution**
With your virtual environment active, run the core script to scrape listings, score them, and log them to your spreadsheet:
  Bash
  python agent.py
**Modifications & Calibration**
Adjust Scope or Boundaries: Edit the geographic and job title filter arrays directly inside agent.py.

Tune ATS Matching: Update or assign heavier weights to key technical skills inside the text parsing function in agent.py to match evolving resume parameters.
