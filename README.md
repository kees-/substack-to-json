# spike-to-json

Get the metadata and content as an HTML string of every post on a [SPIKE](https://www.spikeartmagazine.com/) publication.

The script simulates a web browser and uses element searches to find everything relevant. It is updated and working as of **2022-12-30**.

In the future, many of the DOM queries may need to be updated as SPIKE's DOM structure changes. Look in `parse_archive()` and `parse_post()` if updating yourself.

## Usage:
```sh
pip install -r requirements
python main.py [author_slug]
```
`author_slug` must point to the correct portion of the URL eg. `dean-kissick-0` from [spikeartmagazine.com/?q=contributors/dean-kissick-0](https://www.spikeartmagazine.com/?q=contributors/dean-kissick-0)
