import json
import requests
from bs4 import BeautifulSoup
import time
import datetime
from playwright.sync_api import sync_playwright

filename = "processed_data.json"
url = "https://pedantix.certitudes.org/"
tree_titles_name = "titles"
min_search_depth = 10
guess_delay_seconds = 0.5

def fetch_html(url):
    # Retrieve html content from the URL
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        raise Exception(f"Failed to fetch data from {url}")

def retrieve_content(html):
    title_lengths = []
    text_lengths = []
    soup = BeautifulSoup(html, 'html.parser')

    puzzle_num = soup.find('b', id='puzzle-num')
    if puzzle_num is None:
        raise Exception("No puzzle number found in the HTML content")
    day = int(puzzle_num.text)

    wiki_div = soup.find('div', id='wiki')
    if wiki_div is None:
        raise Exception("No wiki div found in the HTML content")
    # Retrieve the content of the h2 tag inside the wiki div
    h2_tag = wiki_div.find('h2')
    if h2_tag is None:
        raise Exception("No h2 tag found inside the wiki div")
    # Loop through all the span tags inside the h2_tag
    span_tags = h2_tag.find_all('span')
    if not span_tags:
        raise Exception("No span tags found inside the h2 tag")
    for span in span_tags:
        title_lengths.append(len(span.text) - 2)

    # Retrieve content of "article" div id inside the wiki div
    article_div = wiki_div.find('div', id='article')
    if article_div is None:
        raise Exception("No article div found in the HTML content")
    # Retrieve all span tags nested inside the article div
    span_tags = article_div.find_all('span')
    if not span_tags:
        raise Exception("No span tags found inside the article div")
    for span in span_tags:
        text_lengths.append(len(span.text) - 2)
    return day, title_lengths, text_lengths

def title_found(title_lengths, correct_words):
    return len([word for word in correct_words if word != ""]) == len(title_lengths)

# Guess a title, return updated (correct_words, guessed_words)
def guess(url, title_lengths, title, day, correct_words, guessed_words, close_guessed_words):
    print(f"Guessing title: {title}")
    url = url + "/score?n=" + str(day)
    if len(title) != len(title_lengths): # If the guessed title is longer/shorted than the title to guess, do nothing
        return correct_words, guessed_words, close_guessed_words
    if title_found(title_lengths, correct_words): # If the title was already found, do nothing
        return correct_words, guessed_words, close_guessed_words
    word_index_to_guess = [i for i in range(len(correct_words)) if correct_words[i] == ""]
    for i in word_index_to_guess:
        if title_lengths[i] != len(title[i]): # If the guessed word is longer/shorter than the word to guess, do nothing
            return correct_words, guessed_words, close_guessed_words
        if title[i] in guessed_words: # If the guessed word was already guessed, do nothing
            return correct_words, guessed_words, close_guessed_words
        if title[i] in correct_words: # If the guessed word was already found, do nothing
            return correct_words, guessed_words, close_guessed_words
        time.sleep(guess_delay_seconds) # Delay to avoid overwhelming the server
        guessed_words.append(title[i]) # Append the guessed word to the list
        correct_words, close_guessed_words = playwright_guess(page, title[i], correct_words, close_guessed_words)
    return correct_words, guessed_words, close_guessed_words

# Return (correct_words, guessed_words)
def depth_first_search(tree, day, title_lengths, current_text_lengths, depth=0):
    correct_words = ["" for _ in range(len(title_lengths))]
    guessed_words = []
    close_guessed_words = []
    if not isinstance(tree, dict): # The tree is not a dictionary
        return [], [], []

    if len(current_text_lengths) == 0: # We reached the end of the text
        if not tree_titles_name in tree: # No result to try
            return [], [], []
        for title in tree[tree_titles_name]: # Try the results
            correct_words, guessed_words, close_guessed_words = guess(url, title_lengths, title, day, correct_words, guessed_words, close_guessed_words)
            if title_found(title_lengths, correct_words): # If the title was found, return directly
                return correct_words, guessed_words, close_guessed_words
        return correct_words, guessed_words, close_guessed_words

    number_keys = [item for item in tree.keys() if item.isdigit()]
    sorted_number_keys = sorted(number_keys, key=lambda key: abs(current_text_lengths[0] - int(key)))
    if depth < min_search_depth: # Only search the closest key and return the result
        return depth_first_search(tree[sorted_number_keys[0]], day, title_lengths, current_text_lengths[1:], depth + 1)

    # Search all the keys and also try the results
    for key in sorted_number_keys:
        correct_words, guessed_words, close_guessed_words = depth_first_search(tree[key], day, title_lengths, current_text_lengths[1:], depth + 1)
        if title_found(title_lengths, correct_words): # If the title was found, return directly
            return correct_words, guessed_words, close_guessed_words

    if tree_titles_name in tree:
        for title in tree[tree_titles_name]:
            correct_words, guessed_words, close_guessed_words = guess(url, title_lengths, title, day, correct_words, guessed_words, close_guessed_words)
            if title_found(title_lengths, correct_words): # If the title was found, return directly
                return correct_words, guessed_words, close_guessed_words
    return correct_words, guessed_words, close_guessed_words

def playwright_guess(page, word, correct_words, close_guessed_words):
    print(f"Guessing word: {word}")
    page.locator("#guess").fill(word)
    with page.expect_response(lambda response: url in response.url) as response_info:
        page.locator("#guess-btn").click()  # Trigger the network request
    response = response_info.value
    if response.status != 200:
        raise Exception(f"Failed to fetch data from {response.url}")
    response_data = response.json()
    x = response_data["x"]
    for key, positions in x.items():
        if key.startswith("#"): # Ignore the close words
            continue
        if key not in close_guessed_words: # Append the guessed word if it is not already in the list
            close_guessed_words.append(key)
        for position in positions:
            if position < len(correct_words):
                correct_words[position] = key
                print(f"Correct word found: {key} at position {position}")
    return correct_words, close_guessed_words

def sleep_until(hour, minute):
    t = datetime.datetime.today()
    future = datetime.datetime(t.year, t.month, t.day, hour, minute)
    if t.timestamp() > future.timestamp():
        future += datetime.timedelta(days=1)
    time.sleep((future-t).total_seconds())

with open(filename, "r") as f:
    tree_data = json.load(f)
    print(f"Tree data loaded from {filename}")
    print(f"Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Sleeping until the next puzzle...")
    sleep_until(12, 0) # Sleep until the time is 12:00
    print(f"Current time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    day, title_lengths, text_lengths = retrieve_content(fetch_html(url))
    print(f"Day: {day}, Title lengths: {title_lengths}, Text lengths: {text_lengths}")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url)
        page.wait_for_selector(".fc-button.fc-cta-consent.fc-primary-button")
        page.locator(".fc-button.fc-cta-consent.fc-primary-button").click() # Accept cookies
        page.wait_for_selector("#dialog-close")
        page.locator("#dialog-close").click() # Close the tutorial dialog
        correct_words, guessed_words, close_guessed_words = depth_first_search(tree_data, day, title_lengths, text_lengths)
        print(f"Correct words: {correct_words}")
        print(f"Guessed words: {guessed_words}")
        print(f"Close guessed words: {close_guessed_words}")
        if title_found(title_lengths, correct_words):
            print("Title found!")
            ranking = page.locator("#ranking").inner_text()[:-1] # Read the ranking and remove the last character
            print(f"Ranking: {ranking}")
            page.screenshot(path=f"ranking_{day}.png")
        print(f"Tries: {len(guessed_words)}")
        browser.close()
exit(0)
