# substack-to-json

Get the metadata and content as an HTML string of every post on a substack publication.

The script simulates a web browser and uses element searches to find everything relevant. It is updated and working as of **2022-11-25**.

In the future, many of the `XPATH` and related queries may need to be updated as substack's DOM structure changes. Look in `parse_archive()`, `parse_post()`, and `sign-in()` if updating yourself. I never tried parsing a paywalled blog, so this feature may not work currently.

## Note
The original script created an EPUB. This fork uses the same techniques but is intended to be an intermediate processor in the face of lacking a substack API. It skips the final rendering and outputs all blog post data to a JSON file specified in [main.py](main.py) `OUTFILE_NAME`.

## Usage:
```sh
pip install -r requirements
python main.py [Substack_URL]
```
Substack_URL must point to the main page eg. [https://worm.substack.com/]()

## BONUS!!

What if it was more than substack? Check other branches on this repo to see any platforms I've adapted this script to support.
