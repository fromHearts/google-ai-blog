import requests
import json
import time
import re
from bs4 import BeautifulSoup
from os import listdir, mkdir, system
from os.path import isfile, join

science_parse = "./science-parse-cli-assembly-2.0.3.jar"
paper_sites = ["arxiv.org", 'research.google.com']
excluded = ['wikipedia', '.png', '.jpg', '.gif']


# Gets raw unparsed data from blog post
def get_raw_blogs(blogs, current):
  try:
    start_url = input('Please give the url to start (https://ai.googleblog.com): ')
    if start_url == '':
      start_url = 'https://ai.googleblog.com'

    force = False
    resume = True
    while resume and start_url:
      start_len = len(current["raw"])

      page = requests.get(start_url)
      soup = BeautifulSoup(page.content, 'html.parser')

      posts = soup.find_all(class_='post')
      for post in posts:
        blog_id = post.get('data-id')
        if blog_id not in current["raw"]:
          blog = {
            'blog_id': blog_id,
            'link': post.find('a').get('href'),
            'title': post.find('a').get('title'),
            'publish_date': post.find(class_='publishdate').get_text().strip(),
            'html_content': ''.join(post.find(class_='post-body').script.descendants)
          }

          with open(join(blogs["raw"], blog_id + ".json"), 'w') as blog_file:
            json.dump(blog, blog_file)

          current["raw"].append(blog_id)

      start_url = soup.find(class_='blog-pager-older-link').get('href')

      print('Total found:', len(current["raw"]))
      if len(current["raw"]) == start_len and not force:
        cont = None
        while cont not in ['y','n']:
          cont = input('No new papers found, want to force scan all pages (y\\n)?: ')
        if cont == 'y':
          force = True
        else:
          resume = False

      time.sleep(5)
  except KeyboardInterrupt:
    pass


# Parse raw blogs and extract interesting features
def parse_raw_blogs(blogs, current):
  start_len = len(current["parsed"])
  for blog_id in current["raw"]:
    if blog_id not in current["parsed"]:
      with open(join(blogs["raw"], blog_id + ".json"), 'r') as blog_file:
        raw_blog = json.load(blog_file)
        blog = BeautifulSoup(raw_blog['html_content'], 'html.parser')
        
        links = [a.get('href') for a in blog.find_all('a') if a.get('href')]
        authors = None

        # Get sections
        sections = []
        section_content = []
        previous_section = 'Introduction'
        
        for line in blog:
          if line.name == 'b' or line.name == 'strong':
            sections.append(
              {'name': previous_section,
               'content': "".join(section_content).replace('\n',' ').strip().replace('  ', ' ')})
            previous_section = line.text
            section_content = []
          elif line.name == 'br' and authors is None:
            authors = "".join(section_content).replace('\n',' ').strip().replace('  ', ' ')
            section_content = []
          else:
            if hasattr(line, 'get_text'):
              section_content.append(line.get_text())
            else:
              section_content.append(line)

        if section_content:
            sections.append(
              {'name': previous_section,
               'content': "".join(section_content).replace('\n',' ').strip().replace('  ', ' ')})

        del raw_blog['html_content']
        raw_blog['authors'] = authors
        raw_blog['sections'] = sections
        raw_blog['links'] = links
        
        with open(join(blogs["parsed"], blog_id + ".json"), 'w') as blog_file:
          json.dump(raw_blog, blog_file)
        
        current["parsed"].append(blog_id)
  print('Parsed {} new files'.format(len(current["parsed"]) - start_len))


# Manually annotate which paper corresponds to the blog
def mark_papers(blogs, current):
  for blog_id in current["parsed"]:
    if blog_id not in current["marked"]:
      with open(join(blogs["parsed"], blog_id + ".json"), 'r') as blog_file:
        parsed_blog = json.load(blog_file)
        
      print('Title: {}'.format(parsed_blog["title"]))
      print('Link:  {}'.format(parsed_blog['link']))
      print()
      print("[0] Skip")

      possible_sources = []
      for link in parsed_blog['links']:
        for paper_site in paper_sites:
          if paper_site in link.lower() and link not in possible_sources:
            possible_sources.append(link)
            print("[{}] {}".format(len(possible_sources), link))
            break

      print()

      for link in parsed_blog['links']:
        eligible = True
        for exclude in excluded:
          if exclude in link.lower():
            eligible = False
            break
        if eligible and link not in possible_sources:
          possible_sources.append(link)
          print("[{}] {}".format(len(possible_sources), link))

      skip = False
      chosen_link = None

      choice = input('Which link to use? (none):')
      if choice != '':
        if choice == "0":
          skip = True
        else:
          chosen_link = possible_sources[int(choice) - 1]

      if skip:
        with open(join(blogs["marked"], blog_id + ".skip"), 'w') as blog_file:
          blog_file.write('')
      elif not chosen_link:
        with open(join(blogs["marked"], blog_id + ".none"), 'w') as blog_file:
          blog_file.write('')
      else:
        with open(join(blogs["marked"], blog_id + ".txt"), 'w') as blog_file:
          blog_file.write(chosen_link)

      print("\n")
      current["marked"].append(blog_id)


# Download all papers in pdf form
def download_papers(blogs, current):
  for blog_id in current["marked"]:
    if blog_id not in current["papers"]:
      try:
        with open(join(blogs["marked"], blog_id + ".txt"), 'r') as blog_file:
          url = blog_file.readline()

        try:
          # Fix some url issues
          if url.startswith('http://'):
            url = url.replace('http://', 'https://')
          if url.startswith('//'):
            url = url.replace('//', 'https://')

          # Follow any redirects first to get the actual page
          url = requests.get(url).url

          # Check if known and downloadable
          downloadable = True
          if not url.endswith('.pdf'):
            if url.startswith('https://arxiv.org') or url.startswith('http://arxiv.org'):
              url = url.replace('abs', 'pdf') + '.pdf'
            elif url.startswith('https://dl.acm.org'):
              url = url.replace('abs', 'pdf')
            elif url.startswith('https://www.nature.com/articles'):
              url = url + '.pdf'
            elif url.startswith('https://research.google.com/pubs') or url.startswith('https://research.google/pubs'):
              if url.endswith('.html'):
                url = url.replace('.html', '.pdf')
              elif url.endswith('/'):
                url = url[:-1] + '.pdf'
            elif url.startswith('https://openreview.net/'):
              url = url.replace('forum', 'pdf')
            else:
              downloadable = False

          # Download paper
          if downloadable:
            print('[{}] Downloading from {}'.format(blog_id, url))
            file = requests.get(url)

            with open(join(blogs["papers"], blog_id + '.pdf'), 'wb') as pdf_file:
              pdf_file.write(file.content)

            current["papers"].append(blog_id)
          else:
            print('[{}] Unknown url {}'.format(blog_id, url))
        except:
          print('[{}] Error downloading {}'.format(blog_id, url))
      except FileNotFoundError:
        pass


# Use science-parse to convert papers to text
def convert_papers(blogs, current):
  system("java -jar {} -o {} {}".format(science_parse, blogs["papers_text"], blogs["papers"]))
  current["papers_text"] = [f.split(".")[0] for f in listdir(blogs["papers_text"])]


# Combine paper text and blog text for use in the pointer-generator network model
def combine_papers(blogs, current):
  re1 = '^https?:\/\/.*[\r\n]*'
  re2 = '[\(\[].*?[\))\]]'
  generic_re = re.compile("(%s|%s)" % (re1, re2))

  for blog_id in current["papers_text"]:
    if blog_id not in current["combined"]:
      try :
        full_text = ''
        blog_text = ''
        with open(join(blogs["papers_text"], blog_id + '.pdf.json'), 'r') as f:
          text_json = json.load(f)
          sections = text_json["metadata"]["sections"]
          
          for section in sections:
            text = re.sub(generic_re, "", section["text"])
            full_text += text.replace("\n", "") + " "

        with open(join(blogs["parsed"], blog_id + '.json'), 'r') as f:
          text_json = json.load(f)
          sections = text_json["sections"]
          for section in sections:
            text = section["content"]
            text = text.replace(". ", "</s> <s>")
            text = "<s>" + text + "</s> "
            blog_text += text

        with open(join(blogs["combined"], blog_id + '.txt'), 'w') as f:
          f.write(full_text + "\n" + blog_text)
      except:
        pass


def statistics(blogs, current):
  print()
  for directory in current:
    print("Total in {}: {}".format(directory, len(current[directory])))
  
  document_length = 0
  summary_length = 0
  for blog_id in current["combined"]:
    with open(join(blogs["combined"], blog_id + ".txt"), 'r') as blog_file:
      document_length += len(blog_file.readline().split(' '))
      summary_length += len(blog_file.readline().split(' '))
  print()
  print('Average document length: {}'.format(document_length / len(current["combined"])))
  print('Average summary length: {}'.format(summary_length / len(current["combined"])))


if __name__ == '__main__':
  blogs_dir = input('Which directory should be used? (./blogs): ')
  if blogs_dir == '':
    blogs_dir = "./blogs"
  
  # Intialize directories needed
  blogs = {
    'raw': join(blogs_dir, "raw"),
    'parsed': join(blogs_dir, "parsed"),
    'marked': join(blogs_dir, "marked"),
    'papers': join(blogs_dir, "papers"),
    'papers_text': join(blogs_dir, "papers_text"),
    'combined': join(blogs_dir, "combined")
  }
  
  # Create dir or get current files
  current = {}
  for directory in blogs:
    try:
      mkdir(blogs[directory])
      current[directory] = []
    except FileExistsError:
      current[directory] = [f.split(".")[0] for f in listdir(blogs[directory])]
  
  print('[1] Collect blog posts')
  print('[2] Mark paper urls')
  print('[3] Download papers')
  print('[4] Convert papers')
  print('[5] Statistics')
  
  choice = None
  while choice not in ['1','2','3','4','5']:
    choice = input('What do you want to do?: ')
  
  if choice == '1':
    get_raw_blogs(blogs, current)
    parse_raw_blogs(blogs, current)
  elif choice == '2':
    mark_papers(blogs, current)
  elif choice == '3':
    download_papers(blogs, current)
  elif choice == '4':
    convert_papers(blogs, current)
    combine_papers(blogs, current)
  elif choice == '5':
    statistics(blogs, current)
