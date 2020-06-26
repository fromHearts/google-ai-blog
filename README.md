## Google AI Blog Dataset
This codebase contains the script used to collect and parse blog posts from the [Google AI Blog](ai.googleblog.com/). The script returns a dataset intended for long abstractive summarization of scientific papers.

## Requirements
To collect the dataset, first install the requirements listed in `requirements.txt` and make sure you are using Python 3. This project makes use of [Science Parse 2.0.3](https://github.com/allenai/science-parse/releases/tag/v2.0.3), you need to download the jar file and put this in the same directory as the script.

## How to run
The dataset is collected in four steps, reachable with:
```
python googleblog.py
```

You will receive a promt asking to use any of the following actions:
```
[1] Collect blog posts
[2] Mark paper urls
[3] Download papers
[4] Convert papers
[5] Statistics
```

Start by collecting all the blog posts. This code base already contains marking for the first 825 blog posts. If you wish to mark more manually, use step 2. Afterwards the third step will attempt to automatically download the marked papers. Lastly in step 4 these are converted to text and combined with the blog post in the same format as this [CNN / DailyMail dataset](https://github.com/abisee/cnn-dailymail).
