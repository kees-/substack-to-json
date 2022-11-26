import os
import sys
import time
import re
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from pprint import pprint
# from ebooklib import epub

POST_RETRY_LIMIT = 3
TIMEOUT_SECONDS = 10
FILTER = None # FILTER = "^\s*#" # Must be a valid regexp
ALLOW_PAYWALLED = True
PAYWALLED_ONLY = False
EMAIL = os.environ.get("SUBSTACK_EMAIL")
PASSWORD = os.environ.get("SUBSTACK_PASS")
OUTFILE_NAME = "posts.json"
CHROME_BINARY = "/Applications/Chromium.app/Contents/MacOS/Chromium"
SKIP_EXISTING = True

try:
  with open(OUTFILE_NAME, "r") as f:
    agg = json.load(f)
    existing = [ v['url'] for v in agg ]
    f.close
except FileNotFoundError:
  agg = []
  existing = []

options = webdriver.ChromeOptions();
options.add_argument('--headless');
options.add_argument('log-level=1');
options.binary_location = CHROME_BINARY
driver = webdriver.Chrome(options=options)

# Source: https://stackoverflow.com/a/16464305
class AnyEC:
  """ Use with WebDriverWait to combine expected_conditions
  in an OR.
  """
  def __init__(self, *args):
      self.ecs = args
  def __call__(self, driver):
      for fn in self.ecs:
          try:
              res = fn(driver)
              if res:
                  return res
          except:
            pass

def print_separator():
  print("=" * os.get_terminal_size().columns)

def write_json(file, data):
  with open(file, 'w') as f:
    f.write(
      json.dumps(data, indent=2)
    )
    f.close

def get_filename(s):
    s = str(s).strip().replace(' ', '_')
    return re.sub(r'(?u)[^-\w.]', '', s)

def parse_archive(url, limit=None, filter=None):
    driver.get(url + '/archive?sort=new')
    blog_name = driver.find_element(By.XPATH, '//a[@class="navbar-title-link"]').text
    last_height = driver.execute_script("return document.body.scrollHeight")
    print("Scrolling down:")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(0.5)
        WebDriverWait(driver, 30).until(
            EC.invisibility_of_element_located((By.CLASS_NAME, "post-preview-silhouette"))
        )
        recent_height = driver.execute_script("return document.body.scrollHeight")
        print(f"  | Previous: {last_height}, Current: {recent_height}")
        if recent_height == last_height: # TEMP (or recent_height > 5000)
            break
        last_height = recent_height

    posts = driver.find_elements(By.CLASS_NAME, "post-preview")
    posts_parsed = []
    for post in posts[0:limit]:
        url = post.find_element(By.CLASS_NAME, "post-preview-title").get_attribute('href')
        title = post.find_element(By.CLASS_NAME, "post-preview-title").text
        if filter and not re.match(filter, title):
            continue
        try:
            post.find_element(By.CLASS_NAME, "audience-lock")
            paywalled = True
        except NoSuchElementException:
            paywalled = False
        posts_parsed.append({'url': url, 'paywalled': paywalled, 'title': title})
    # pprint(posts_parsed)
    return {'blog_name': blog_name, 'posts': posts_parsed}

def parse_post(url):
    print(f'Parsing {url}')
    driver.get(url)
    post = WebDriverWait(driver, TIMEOUT_SECONDS).until(
        AnyEC(          
            EC.presence_of_element_located((By.CLASS_NAME, "single-post")),
            EC.presence_of_element_located((By.CLASS_NAME, "comments-page"))
        )
    )

    try:
        driver.find_element(By.XPATH, '//div[@class="single-post"]//div[contains(@class,"paywall")]')
        paywalled = True
    except NoSuchElementException:
        paywalled = False

    title = post.find_element(By.CLASS_NAME, "post-title").text
    try:
        subtitle = post.find_element(By.CLASS_NAME, "subtitle").text
    except NoSuchElementException:
        subtitle = ""
    datetime = post.find_element(By.TAG_NAME, "time").get_attribute('datetime')
    try:
        like_count = post.find_element(By.XPATH, '//a[contains(@class, "post-ufi-button") and contains(@class, "has-label")]//div[@class="label"]').text
    except NoSuchElementException:
        like_count = 0
    body = post.find_element(By.CLASS_NAME, "body")
    text_list = [
        e.get_attribute('outerHTML') 
        for e 
        in body.find_elements(By.XPATH, './*[not(contains(@class,"subscribe-widget"))]')
    ]
    text_html = '\n'.join(text_list)
    print(f'  | title:     {title[:50]}{["", "(...)"][len(title) > 40]}\n  | paywalled: {paywalled}\n  | likes:     {like_count}')
    return {
      'url': url,
      'title': title,
      'subtitle': subtitle,
      'date': datetime,
      'like_count': like_count,
      'text_html': text_html,
      'paywalled': paywalled
    }

def sign_in(email, password=None, login_link=None):
    print(f"signing for email: {email}")
    driver.get("https://substack.com/sign-in")
    driver.find_element(By.CLASS_NAME, "substack-login__login-option").click()
    driver.find_element(By.XPATH, '//input[@name="email"]').send_keys(email)
    driver.find_element(By.XPATH, '//input[@name="password"]').send_keys(password)
    driver.find_element(By.CLASS_NAME, "substack-login__go-button").click()
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CLASS_NAME, 'homepage-nav-user-indicator')) 
    )
    print("signed in")

def main():
    if EMAIL and PASSWORD:
        sign_in(EMAIL, PASSWORD)
    archive = parse_archive(sys.argv[1], limit=None, filter=FILTER)

    # book = epub.EpubBook()
    # book.set_identifier('id00000')
    # book.set_title(archive['blog_name'])
    # book.set_language('en')
    # book.add_metadata('DC', 'description', 'generated by pkonkol/substack-to-pdf')
    # book.add_metadata('DC', 'publisher', 'substack-to-pdf')

    # toc = []
    # spine = []
    not_posts = []

    print_separator()
    print(f"Total posts found: {len(archive['posts'])}")

    # Remove objects with urls that match a preexisting outfile.
    # Subsequent process will skip and not update posts scraped previously.
    if SKIP_EXISTING:
        archive.update(
            {'posts': list(filter(lambda d: d['url'] not in existing, archive['posts']))}
        )
        print(f"Number of posts already saved: {len(agg)}")
 
    print_separator()
    print(f"Posts needed to parse: {len(archive['posts'])}")

    for i, post in enumerate(archive['posts'][::-1]): # TEMP ([::-1] / [:3])
        j = 0
        while True:
            try:
                if ALLOW_PAYWALLED or post['paywalled'] == PAYWALLED_ONLY:
                    p = parse_post(post['url'])
                break
            except TimeoutException:
                j += 1
                if j >= POST_RETRY_LIMIT:
                    p = None
                    break
                print(f'  Retrying parse ({j + 1} of {POST_RETRY_LIMIT} times)')
        if p is None:
            not_posts.append(post["url"])
            continue

        agg.append(p)
        write_json(OUTFILE_NAME, agg)
        
        continue # TEMP

        # chapter = epub.EpubHtml(
        #     title=p['title'],
        #     file_name = str(i) + '.' + get_filename(p['title']) + '.xhtml',
        #     lang='en'
        # )
        # chapter.content = (
        #     f'<h1>{p["title"]}</h1>\n'
        #      '<p>'
        #     f'<time datetime={p["date"]}> {p["date"]} </time>'
        #     f'<span>Likes:{p["like_count"]} </span><span> Paywalled: {p["paywalled"]}</span>'
        #      '</p>\n'
        #     f'<a href="{post["url"]}">URL: {post["url"]}</a>\n'
        #     f'<h2>{p["subtitle"]}</h2>\n'
        # )
        # chapter.content += p['text_html']
        # book.add_item(chapter)
        # spine.append(chapter)
        # toc.append(epub.Link(str(i) + '.' + get_filename(p['title']) + '.xhtml', p['title'], ""))

    print_separator()
    print(f'Number of new posts skipped: {len(not_posts)}')

    # book.toc = toc
    # book.add_item(epub.EpubNcx())
    # book.add_item(epub.EpubNav())
    # book.spine = (['nav',] + spine)
    # epub.write_epub(get_filename(archive['blog_name']) + '.epub', book, {})

    agg.sort(key=lambda a: a['date'])
    write_json(OUTFILE_NAME, agg)
    print(f"Sorted and wrote any new data to {OUTFILE_NAME}")

    driver.quit()

if __name__ == "__main__":
    main()
