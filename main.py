# Import necessary libraries
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import configparser
import deepl
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Environment, FileSystemLoader
import os
import argparse



class EmailSender:
    def __init__(self, email, password, smtp_server, smtp_port):
        self.email = email
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_email(self, recipient, subject, body, images=[]):
        # Create a MIME message object
   
        message = MIMEMultipart()
        message['From'] = self.email
        message['To'] = recipient
        message['Subject'] = subject
      
        message.attach(MIMEText(body, "html"))
   
        
        # Connect to the SMTP server and authenticate
        with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
            server.login(self.email, self.password)

            # Send the email
            server.sendmail(self.email, recipient, message.as_string())
            server.quit()


class ForexScraper:
    # Initialize with base URL and title keywords
    def __init__(self, base_url='https://www.forexlive.com', titles=["ForexLive European FX news wrap",
                                                                      "ForexLive Asia-Pacific FX news wrap",
                                                                      "Forexlive Americas FX news wrap"], deepl_api_key=''):
        self.base_url = base_url
        self.titles = titles
        self.articles = {
            'european': [],
            'asia': [],
            'america': []
        }
        self.deepl_api_key = deepl_api_key


    # Method to scrape the ForexLive website and retrieve article links
    def scrape_links(self):
        # Get current date in YYYYMMDD format
        current_date = datetime.today().strftime('%Y%m%d')
        # URL of the webpage to request
        url = f'{self.base_url}/SessionWraps'
        # Make a GET request to the webpage
        response = requests.get(url)
        # Parse the HTML response using Beautiful Soup
        soup = BeautifulSoup(response.content, 'html.parser')
        # Find all HTML elements with class 'card__content'
        card_contents = soup.find_all(class_='card__content')
        # Loop through each 'card__content' element and extract all links within
        for card_content in card_contents:
            articles = card_content.find_all(class_='article-list__item-wrapper')
            for article in articles:
                title = article.find(class_='article-slot__title')
                link = title.find('a', class_='article-link')
                try:
                    title = link.text.strip()
                    if self.titles[0] in title:
                        self.articles['european'].append(link['href'])
                    if self.titles[1] in title:
                        self.articles['asia'].append(link['href'])
                    if self.titles[2] in title:
                        self.articles['america'].append(link['href'])
                except:
                    pass

    # Method to scrape individual articles and retrieve relevant information
    def scrape_article(self, link):
        # Make a GET request to the article URL
        response = requests.get(self.base_url + link)
        # Parse the HTML response using Beautiful Soup
        soup = BeautifulSoup(response.content, 'html.parser')
        # Get current date in YYYYMMDD format
        current_date = datetime.today().strftime('%Y%m%d')
        # Check if article was published on current date
        current_date = '20230222'
        print (link)
        exit()
        if current_date in link:
            
            title = soup.find('h1').text
            sub_title = soup.find('li', class_='tldr__item').text
            author = soup.find(class_='publisher-details__publisher-name').text
            date = soup.find(class_='publisher-details__date').text
            article = soup.find('article', class_='article-body')
            link_list = article.find('ul')
            new_link_list = []

            for link in link_list:
                new_link_list.append({
                    'text': self.translate_text(link.text),
                    'href': link.find('a')['href']
                }) 



            paragraphs = article.find_all('p')
            translating_paragraphs = []
            for p in paragraphs:
                translating_paragraphs.append(self.translate_text(p.text))
          
          
            images = article.find_all('img')
            translated_article ={
                'title': self.translate_text(title),
                'link': link,
                'sub_title': self.translate_text(sub_title),
                'author': author,
                'date': date,
                'links': new_link_list,
                'paragraphs': translating_paragraphs,
                'images': images
            }
            org_article ={
                'title': title,
                'sub_title': sub_title,
                'author': author,
                'date': date, 
                'paragraphs': paragraphs
                
            }
            return translated_article, org_article
                  

    # Method to scrape all articles for a given region
    def scrape_region(self, region):
        for link in self.articles[region]:
            return self.scrape_article(link)

    def translate_text(self, text, target_lang='DE'):
            auth_key = self.deepl_api_key # replace with your own authentication key
            translator = deepl.Translator(auth_key) 
            result = translator.translate_text(text, target_lang=target_lang) 
            translated_text = result.text
            return translated_text

    
if  __name__ == '__main__':
   
    parser = argparse.ArgumentParser(description='Send a daily ForexLive article by email.')

    parser.add_argument('-r', '--region', type=str, required=True, help='region like european, asia, america')
    args = parser.parse_args()
    config = configparser.ConfigParser()
    config.read('conf.ini')
    deepl_api_key = config.get('deepl', 'deepl_api_key')
    scraper = ForexScraper(deepl_api_key=deepl_api_key)
    scraper.scrape_links()
    translated_article, org_article = scraper.scrape_region(args.region)
    email_sender = EmailSender(config.get('mail', 'mail_from'), config.get('mail', 'mail_password'), config.get('mail', 'mail_host'), config.get('mail', 'mail_port'))
    subject = f"ForexLive {args.region} {translated_article['title']}"
    file_loader = FileSystemLoader('templates')
    env = Environment(loader=file_loader)
    env.trim_blocks = True
    env.lstrip_blocks = True
    env.rstrip_blocks = True
    template = env.get_template('child.html')

  
    output = template.render(translated_article=translated_article,org_article=org_article)

    email_sender.send_email(config.get('mail', 'mail_to'), subject, output)

    
