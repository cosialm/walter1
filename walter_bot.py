from playwright.sync_api import sync_playwright, expect, Error as PlaywrightError
from playwright_stealth.stealth import Stealth
import time
import os

# User-provided content to humanize
content_to_humanize = """This is a sample text that needs to be humanized. It is being used to test the Walter Writes AI bot. The purpose of this test is to ensure the bot can log in, navigate, input text, select options, and retrieve the processed output, while also attempting to bypass potential Cloudflare protections."""

# Login details
email = "aaaliyanzmoreau255@gmail.com"
password = "Create1#"

# --- PLAYWRIGHT MANAGED USER DATA DIRECTORY ---
# Playwright will create and manage this directory for persistent sessions.
# This is NOT your Google Chrome profile directory.
# USER_DATA_DIR = os.path.expanduser("~/playwright_user_data") # For cross-platform compatibility
# Path to the Chrome user data directory (parent of "Profile 79")
USER_DATA_DIR = r"C:\Users\Administrator\AppData\Local\Google\Chrome\User Data"
# ----------------------------------------

def main():
    with Stealth().use_sync(sync_playwright()) as p:
        browser = None
        try:
            print(f"Launching Chromium browser with Playwright-managed user data directory: {USER_DATA_DIR}")
            print("IMPORTANT: For the first run, ensure headless=False below to manually log in if needed.")
            print("After successful manual login, change headless=True for automated runs.")

            browser_launch_args = [
                # These arguments are generally good for cross-platform compatibility
                # and avoiding common issues.
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--window-size=1920,1080', # Set a consistent window size
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36', # Realistic User-Agent
                '--profile-directory=Profile 79' # Specify the Chrome profile directory
            ]

            browser = p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False, # <--- CHANGE THIS TO True AFTER FIRST MANUAL LOGIN
                args=browser_launch_args
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            print("Browser and page initialized.")

            # 1. Navigate to the login page
            login_url = "https://app.walterwrites.ai/en/login?callbackUrl=https%3A%2F%2Fapp.walterwrites.ai"
            print(f"Navigating to login page: {login_url}" )
            page.goto(login_url, timeout=90000, wait_until="domcontentloaded")
            print(f"Initial navigation complete. Current URL: {page.url}")

            # Cloudflare Bypass Strategy
            if "cloudflare" in page.url.lower() or "just a moment" in page.content().lower():
                print("Cloudflare challenge detected. Waiting for challenge to resolve...")
                # Wait for network to be idle, indicating page has loaded all resources
                try:
                    page.wait_for_load_state("networkidle", timeout=60000) # Increased timeout
                    print(f"Cloudflare challenge potentially resolved. Current URL: {page.url}")
                except PlaywrightError:
                    print("Network idle timeout exceeded during Cloudflare challenge. Continuing anyway.")

                # Check if still on Cloudflare page after waiting
                if "cloudflare" in page.url.lower() or "just a moment" in page.content().lower():
                    print("Still stuck on Cloudflare page after waiting. Attempting to click any visible button.")
                    # Corrected way to combine locators with .or()
                    verify_button = page.locator("button:has-text('Verify you are human')").or(
                                    page.locator("button:has-text('I am not a robot')")).or(
                                    page.locator("input[type='button'][value='Verify']"))
                    try:
                        if verify_button.is_visible():
                            print("Found a Cloudflare verification button. Clicking it...")
                            verify_button.click()
                            page.wait_for_load_state("networkidle", timeout=60000) # Wait after clicking
                            print(f"After clicking verify button. Current URL: {page.url}")
                        else:
                            print("No common Cloudflare verification button found.")
                    except PlaywrightError as e:
                        print(f"Error attempting to click Cloudflare button: {e}")

            # After Cloudflare, check if we are on the login page or dashboard
            if "login" in page.url.lower():
                # Fill email
                print(f"Filling email: {email}")
                email_locator = page.get_by_placeholder("Email")
                email_locator.wait_for(state="attached", timeout=60000)
                email_locator.wait_for(state="visible", timeout=60000)
                print("Typing email...")
                email_locator.type(email, delay=50)

                # Fill password
                print("Typing password...")
                password_locator = page.get_by_placeholder("Password")
                password_locator.wait_for(state="attached", timeout=30000)
                password_locator.wait_for(state="visible", timeout=30000)
                password_locator.type(password, delay=50)
                print("Password typed. Attempting to submit by pressing Enter.")
                password_locator.press("Enter")

                # Wait for navigation or specific element on dashboard/error page
                try:
                    # Wait for either dashboard URL or an error message to appear
                    print("Waiting for navigation to dashboard or login error...")
                    page.wait_for_url("https://app.walterwrites.ai/en/dashboard", timeout=30000 )
                    print("Successfully navigated to dashboard.")
                except PlaywrightError:
                    print("Did not navigate to dashboard within timeout. Checking for login errors or Cloudflare.")
                    # Debug: Save screenshot and print page content if login fails
                    screenshot_path = "login_failure_debug.png"
                    page.screenshot(path=screenshot_path)
                    print(f"Screenshot saved to {screenshot_path}")
                    print(f"Page content after failed login attempt (first 1000 chars):\n{page.content()[:1000]}")

                    # Check for login error messages
                    possible_error_selectors = [
                        "[role=\'alert\']",
                        "div[class*=\'error\']",
                        "p[class*=\'error\']",
                        "div[data-testid*=\'error\']",
                        "span[class*=\'error\']",
                        "text=Invalid credentials", # Specific error message text
                        "text=incorrect email or password" # Another specific error message text
                    ]
                    error_message_found = False
                    for i, selector in enumerate(possible_error_selectors):
                        try:
                            error_locator = page.locator(selector).first
                            error_locator.wait_for(state="visible", timeout=5000)
                            error_text = error_locator.inner_text()
                            if error_text:
                                print(f"Potential login error message found (selector {i+1}): {error_text.strip()}")
                                error_message_found = True
                                break
                        except PlaywrightError:
                            pass # No error message found with this selector

                    if error_message_found:
                        raise Exception("Login failed: Error message detected on page.")
                    elif "cloudflare" in page.url.lower() or "just a moment" in page.content().lower():
                        raise Exception("Login failed: Cloudflare challenge still present or re-triggered.")
                    else:
                        raise Exception("Login failed: Unknown reason, no dashboard or error message found.")
            else:
                print("Not on login page, assuming already logged in or redirected.")

            # 2. Navigate to the humanizer page
            print("Navigating to Humanizer page...")
            page.locator("a[href='/en/humanizer']").click()

            humanizer_url_pattern = "https://app.walterwrites.ai/en/humanizer"
            print(f"Waiting for navigation to Humanizer URL pattern: {humanizer_url_pattern}" )
            page.wait_for_url(humanizer_url_pattern, timeout=20000)
            print("Successfully navigated to Humanizer page.")

            # 3. Paste the content
            print("Pasting content into the editor...")
            input_editor_locator = page.locator("div.ql-editor")
            input_editor_locator.wait_for(state="visible", timeout=20000)
            input_editor_locator.fill(content_to_humanize)
            print("Content pasted.")

            # 4. Select dropdown for Readability as Masters
            print("Selecting Readability: Masters...")
            readability_dropdown_locator = page.locator("//label[contains(text(), \'Readability\')]/following-sibling::div//select")
            readability_dropdown_locator.select_option(label="Masters")
            print("Readability selected.")

            # 5. Select dropdown for Purpose as Report
            print("Selecting Purpose: Report...")
            purpose_dropdown_locator = page.locator("//label[contains(text(), \'Purpose\')]/following-sibling::div//select")
            purpose_dropdown_locator.select_option(label="Report")
            print("Purpose selected.")

            # 6. Click the Detection Bypass Level as Enhanced
            print("Clicking Detection Bypass Level: Enhanced...")
            page.get_by_role("button", name="Enhanced", exact=True).click()
            print("Enhanced bypass level clicked.")

            # 7. Click the button Humanize & Scan
            print("Clicking \'Humanize & Scan\' button...")
            page.get_by_role("button", name="Humanize & Scan", exact=True).click()
            print("\'Humanize & Scan\' button clicked.")

            # 8. Wait until the text has been humanized in the div id="editorQuillContainer"
            print("Waiting for humanized output container to be visible...")
            humanized_output_container_locator = page.locator("#editorQuillContainer")
            humanized_output_container_locator.wait_for(state="visible", timeout=60000)
            print("Humanized output container is visible.")

            print("Waiting for a short delay for content to settle...")
            page.wait_for_timeout(5000)

            # 9. Click the copy button
            copy_button_css_selector = ".absolute.inset-0.flex.size-full.grow.items-center.justify-center.transition-opacity.duration-300.opacity-100"
            print(f"Attempting to click copy button with CSS selector: {copy_button_css_selector}")
            try:
                copy_button_locator = page.locator(copy_button_css_selector)
                if copy_button_locator.count() == 1 and copy_button_locator.is_visible():
                    copy_button_locator.click()
                    print("Copy button clicked.")
                elif copy_button_locator.count() > 1:
                    print(f"Warning: Multiple elements found for copy button selector. Clicking the first one.")
                    copy_button_locator.first.click()
                    print("Copy button (first match) clicked.")
                else:
                    print("Warning: Copy button not found or not visible with the generic selector. Skipping click.")

            except Exception as copy_e:
                print(f"Warning: Could not click copy button (selector might be too generic or element changed): {copy_e}")

            # 10. Output the humanized content
            print("Extracting humanized content...")
            humanized_content = humanized_output_container_locator.inner_text()
            print("--- Humanized Content Start ---")
            print(humanized_content)
            print("--- Humanized Content End ---")

        except PlaywrightError as e:
            print(f"A Playwright Error occurred: {e}")
            print("Please ensure you have installed Playwright browsers by running: playwright install")
            print("Also, ensure all necessary system dependencies for Playwright are installed.")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if browser:
                print("Closing browser...")
                browser.close()
                print("Browser closed.")

if __name__ == "__main__":
    main()
