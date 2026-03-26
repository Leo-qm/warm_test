from playwright.sync_api import sync_playwright

def get_dom():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('https://rural.touchit.com.cn/agri/#/admin?redirect=%2FcleanEnergy')
        page.wait_for_selector("input[placeholder*='验证码']", timeout=10000)
        
        with open('test_dom.html', 'w', encoding='utf-8') as f:
            f.write(page.content())
        browser.close()

if __name__ == '__main__':
    get_dom()
