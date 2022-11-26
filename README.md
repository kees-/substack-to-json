# substack-to-json

## Note
The original script created an EPUB. This fork uses the same techniques but is intended to be an intermediate processor in the face of lacking a substack API. It skips the final rendering and outputs all blog post data to a JSON file specified in [main.py](main.py) `OUTFILE_NAME`.

## Usage:
```sh
pip install -r requirements
python main.py [Substack_URL]
```
Substack_URL must point to the main page eg. [https://forcoloredgirlswhotech.substack.com/]()
