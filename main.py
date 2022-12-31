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

BASE_URL = "https://www.spikeartmagazine.com/?q=contributors/"
POST_RETRY_LIMIT = 4
TIMEOUT_SECONDS = 15
OUTFILE_NAME = "posts.json"
FILTER = None # FILTER = "^\s*#" # Must be a valid regexp
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
  """ Use with WebDriverWait to combine expected_conditions in an OR. """
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

def parse_archive(contributor, limit=None, filter=None):
    driver.get(BASE_URL + contributor)
    author = driver.find_element(By.CSS_SELECTOR, 'h1.page-header').text

    posts = driver.find_elements(By.CSS_SELECTOR, '#page-content div.node-article:not(:has(.field-name-print-article-extra))')
    posts_parsed = []
    for post in posts[0:limit]:
        url = post.find_element(By.CSS_SELECTOR, '.article-title a').get_attribute('href')
        title = post.find_element(By.CSS_SELECTOR, ".article-title a").text
        if post.find_element(By.CSS_SELECTOR, '#article-category').text == "OFFLINE ARTICLE":
            continue
        if filter and not re.match(filter, title):
            continue
        posts_parsed.append({'url': url, 'title': title})
    return {'blog_name': author, 'posts': posts_parsed}

def parse_post(url):
    print(f'Parsing {url}')
    driver.get(url)
    post = WebDriverWait(driver, TIMEOUT_SECONDS).until(
        EC.presence_of_element_located((By.TAG_NAME, "html"))
    )

    title = post.find_element(By.XPATH, '//meta[@property="og:title"]').get_attribute('content')
    subtitle = post.find_element(By.XPATH, '//meta[@name="description"]').get_attribute('content')
    datetime = post.find_element(By.XPATH, '//meta[@property="article:published_time"]').get_attribute('content')
    body = post.find_element(By.CSS_SELECTOR, ".field-name-body .field-item")
    text_list = [
        e.get_attribute('outerHTML') 
        for e 
        in body.find_elements(By.XPATH, "*")
    ]
    text_html = '\n'.join(text_list)
    print(f'  | title:    {title[:50]}{["", "(...)"][len(title) > 40]}\n  | datetime: {datetime}')
    return {
      'url': url,
      'title': title,
      'subtitle': subtitle,
      'date': datetime,
      'text_html': text_html,
    }

def main(author_slug):
    archive = parse_archive(author_slug, limit=None, filter=FILTER)

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

    not_posts = []

    for i, post in enumerate(archive['posts'][::-1]): # TEMP ([::-1] / [:3])
        j = 0
        while True:
            try:
                p = parse_post(post['url'])
                break
            except TimeoutException:
                j += 1
                if j >= POST_RETRY_LIMIT:
                    p = None
                    break
                print(f'  Retrying parse ({j + 1} of {POST_RETRY_LIMIT} times)')
        if p is None:
            not_posts.append(post['url'])
            continue
        agg.append(p)
        write_json(OUTFILE_NAME, agg)

    print_separator()
    print(f'Number of new posts skipped: {len(not_posts)}')

    agg.sort(key=lambda a: a['date'])
    write_json(OUTFILE_NAME, agg)

    print(f"Sorted and wrote any new data to {OUTFILE_NAME}")

    driver.quit()

if __name__ == "__main__":
    main(sys.argv[1])
